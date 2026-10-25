#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
药品数据爬虫 - 国家药监局 NMPA 数据查询系统
目标网址: https://www.nmpa.gov.cn/datasearch/

依赖安装:
    pip install selenium webdriver-manager pandas

运行方式:
    python scraper_drugs.py

说明:
    - 使用 Selenium + Chrome 浏览器动态渲染方案
    - 通过关键词循环搜索药品数据
    - 支持翻页、断点续传
    - 随机延时 + User-Agent 轮换 + 模拟人类滚动
    - 验证码断点预留（需人工处理）
"""

import os
import sys
import csv
import time
import random
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select as SeleniumSelect
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, WebDriverException,
    ElementClickInterceptedException,
)

# webdriver-manager 已不再需要，Selenium 4.6+ 内置驱动管理

# ============================================================
#  配置区域 - 可根据需要调整
# ============================================================

TARGET_URL = "https://www.nmpa.gov.cn/datasearch/"
OUTPUT_DIR = "data"
CSV_FILE = "drugs.csv"
PROGRESS_FILE = "drug_progress.json"

# 延时范围（秒）
MIN_DELAY = 5
MAX_DELAY = 10

# 反爬暂停秒数
ANTI_BOT_PAUSE = 60

# 超时设置（秒）
PAGE_LOAD_TIMEOUT = 60
ELEMENT_TIMEOUT = 20

# 搜索关键词列表（可自行增减）
SEARCH_KEYWORDS = [
    "感冒", "降压", "降糖", "阿莫西林", "头孢",
    "布洛芬", "阿司匹林", "抗生素", "抗病毒", "抗癌",
    "胃炎", "止咳", "退烧", "过敏", "高血压",
    "糖尿病", "心脏病", "肝炎", "肺炎", "鼻炎",
    "皮肤病", "眼科", "口腔", "妇科", "儿科",
    "维生素", "钙片", "胰岛素", "青霉素", "止痛",
    "高血脂", "冠心病", "心绞痛", "骨质疏松", "抑郁",
    "痛风", "慢阻肺", "中风", "肾炎", "肝硬化",
    "哮喘", "糖尿病", "类风湿关节炎", "胃溃疡", "肠炎",
]

# 搜索分类（NMPA 数据查询类别）
SEARCH_CATEGORY = "国产药品"

# CSV 字段
CSV_FIELDS = [
    "产品名称", "英文名称", "批准文号", "生产单位",
    "剂型", "规格", "适应症", "药品分类",
    "批准日期", "有效期", "详情页URL",
]

# 随机 User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ============================================================
#  日志配置
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("drug_scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================
#  爬虫主类
# ============================================================

class NMPADrugScraper:
    """国家药监局 NMPA 药品数据爬虫"""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.all_drugs: List[Dict] = []
        self.visited_urls: set = set()
        self.processed_count = 0
        self.current_keyword = ""
        self.current_keyword_idx = 0

        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 加载断点进度
        self.progress = self._load_progress()

    # ----------------------------------------------------------
    #  进度管理
    # ----------------------------------------------------------

    def _progress_path(self) -> str:
        return os.path.join(OUTPUT_DIR, PROGRESS_FILE)

    def _load_progress(self) -> dict:
        """加载上次运行进度"""
        path = self._progress_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(
                    f"✓ 发现断点文件: 已处理 {data.get('processed_count', 0)} 条, "
                    f"关键词索引 {data.get('keyword_idx', 0)}"
                )
                return data
            except Exception:
                pass
        return {
            "processed_count": 0,
            "keyword_idx": 0,
            "visited_urls": [],
        }

    def _save_progress(self):
        """保存当前进度"""
        data = {
            "processed_count": self.processed_count,
            "keyword_idx": self.current_keyword_idx,
            "visited_urls": list(self.visited_urls),
            "timestamp": datetime.now().isoformat(),
        }
        with open(self._progress_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------
    #  浏览器管理
    # ----------------------------------------------------------

    def _create_driver(self) -> webdriver.Chrome:
        """创建 Chrome WebDriver 实例"""
        options = Options()
        ua = random.choice(USER_AGENTS)
        options.add_argument(f"--user-agent={ua}")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        # 如需后台运行，取消下面注释
        # options.add_argument("--headless=new")

        driver = webdriver.Chrome(options=options)

        # 隐藏 Selenium 特征
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        logger.info(f"Chrome 驱动已启动 (UA: {ua[:50]}...)")
        return driver

    def _restart_driver(self):
        """重启浏览器"""
        logger.warning("正在重启浏览器...")
        try:
            self.driver.quit()
        except Exception:
            pass
        time.sleep(3)
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, ELEMENT_TIMEOUT)

    # ----------------------------------------------------------
    #  工具方法
    # ----------------------------------------------------------

    def _random_delay(self, min_s=MIN_DELAY, max_s=MAX_DELAY):
        """随机延时"""
        delay = random.uniform(min_s, max_s)
        logger.debug(f"随机延时 {delay:.1f}s ...")
        time.sleep(delay)

    def _safe_click(self, element, retry=3):
        """安全点击元素"""
        for attempt in range(retry):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});",
                    element,
                )
                time.sleep(0.5)
                element.click()
                return True
            except ElementClickInterceptedException:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    pass
            except StaleElementReferenceException:
                logger.debug(f"元素已过期，重试 ({attempt+1}/{retry})")
                time.sleep(1)
            except Exception as e:
                logger.debug(f"点击失败: {e}")
                time.sleep(1)
        return False

    def _safe_text(self, element) -> str:
        """安全获取元素文本"""
        try:
            return element.text.strip()
        except Exception:
            return ""

    def _simulate_human_scroll(self):
        """模拟人类浏览: 随机滚动页面"""
        scroll_count = random.randint(2, 5)
        for _ in range(scroll_count):
            scroll_px = random.randint(200, 500)
            try:
                self.driver.execute_script(f"window.scrollBy(0, {scroll_px});")
            except Exception:
                pass
            time.sleep(random.uniform(0.5, 1.5))

    def _simulate_human_type(self, element, text: str):
        """模拟人类输入: 逐字符输入，带随机延时"""
        element.clear()
        time.sleep(0.3)
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        time.sleep(0.5)

    # ----------------------------------------------------------
    #  反爬 & 验证码
    # ----------------------------------------------------------

    def _check_anti_bot(self):
        """检测并处理反爬机制"""
        try:
            page_source = self.driver.page_source
            title = self.driver.title.lower()

            # 检测 429/403
            if any(code in title for code in ["429", "403", "too many", "forbidden"]):
                logger.warning(f"检测到反爬! 标题: {self.driver.title}")
                logger.warning(f"暂停 {ANTI_BOT_PAUSE} 秒后重试...")
                time.sleep(ANTI_BOT_PAUSE)
                return True

            # 检测验证码
            captcha_indicators = [
                "验证码", "captcha", "verify", "请拖动", "请完成安全验证",
                "geetest", "slider", "滑块",
            ]
            for indicator in captcha_indicators:
                if indicator.lower() in page_source.lower():
                    self._handle_captcha()
                    return True

        except Exception as e:
            logger.debug(f"反爬检测异常: {e}")
        return False

    def _handle_captcha(self):
        """
        处理验证码 - 预留人工处理断点
        ============================================
        当检测到验证码时，程序暂停等待人工处理。
        请在弹出的浏览器窗口中手动完成验证码。
        完成后按 Enter 继续运行。
        ============================================
        """
        logger.warning("=" * 50)
        logger.warning("!!! 检测到验证码 !!!")
        logger.warning("请在浏览器窗口中手动完成验证")
        logger.warning("完成后按 Enter 键继续...")
        logger.warning("=" * 50)

        # 暂停等待用户手动处理
        try:
            input("\n>>> 请在浏览器中完成验证码，然后按 Enter 继续: ")
        except (EOFError, KeyboardInterrupt):
            logger.info("用户中断，保存进度...")
            self._save_csv()
            self._save_progress()
            sys.exit(0)

        # 验证完成后等待页面加载
        time.sleep(3)
        logger.info("继续运行...")

    # ----------------------------------------------------------
    #  搜索功能
    # ----------------------------------------------------------

    def _load_search_page(self):
        """加载数据查询页面"""
        logger.info(f"加载搜索页面: {TARGET_URL}")
        self.driver.get(TARGET_URL)
        time.sleep(5)
        self._check_anti_bot()

    def _select_category(self, category: str):
        """选择查询分类（如 '国产药品'）"""
        logger.info(f"选择查询分类: {category}")

        # 策略 1: 查找下拉选择框
        select_selectors = [
            "select", "select.form-control",
            "select[name*='type']", "select[name*='category']",
            "#dataType", "#queryType",
        ]
        for selector in select_selectors:
            try:
                select_el = self.driver.find_element(By.CSS_SELECTOR, selector)
                selenium_select = SeleniumSelect(select_el)
                # 尝试按可见文本选择
                try:
                    selenium_select.select_by_visible_text(category)
                    logger.info(f"通过下拉框选择分类: {category}")
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    # 尝试按部分文本匹配
                    for option in selenium_select.options:
                        if category in option.text:
                            selenium_select.select_by_visible_text(option.text)
                            logger.info(f"通过下拉框选择分类: {option.text}")
                            time.sleep(2)
                            return True
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        # 策略 2: 查找标签页/按钮形式的分类切换
        tab_selectors = [
            "a.nav-link", ".tab-item", ".category-item",
            "[role='tab']", ".nav-item a",
            "button[class*='tab']", "div[class*='tab']",
        ]
        for selector in tab_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = self._safe_text(el)
                    if category in text:
                        self._safe_click(el)
                        logger.info(f"通过标签页选择分类: {category}")
                        time.sleep(2)
                        return True
            except Exception:
                continue

        # 策略 3: XPath 查找包含分类文本的可点击元素
        try:
            xpath = f"//*[contains(text(), '{category}')]"
            elements = self.driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed():
                    self._safe_click(el)
                    logger.info(f"通过 XPath 选择分类: {category}")
                    time.sleep(2)
                    return True
        except Exception:
            pass

        logger.warning(f"未能自动选择分类 '{category}'，请检查页面结构")
        return False

    def _search_keyword(self, keyword: str) -> bool:
        """在搜索框中输入关键词并搜索"""
        logger.info(f"搜索关键词: {keyword}")

        # 查找搜索输入框
        input_selectors = [
            "input[type='text'][name*='keyword']",
            "input[type='text'][name*='search']",
            "input[placeholder*='关键']",
            "input[placeholder*='搜索']",
            "input[placeholder*='药品']",
            "input[type='text'].search-input",
            "input.form-control[type='text']",
            "input[type='text']",
        ]

        search_input = None
        for selector in input_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        search_input = el
                        break
                if search_input:
                    break
            except Exception:
                continue

        if not search_input:
            logger.error("未找到搜索输入框")
            return False

        # 模拟人类输入
        self._simulate_human_type(search_input, keyword)

        # 查找并点击搜索按钮
        button_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button.search-btn",
            "button.btn-primary",
            "button.btn-search",
            "a.search-btn",
            ".search-button",
            "button",
        ]

        clicked = False
        for selector in button_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        text = self._safe_text(btn).lower()
                        if any(kw in text for kw in ["搜索", "查询", "search", "查找", ""]):
                            self._safe_click(btn)
                            clicked = True
                            break
                if clicked:
                    break
            except Exception:
                continue

        # 如果没找到按钮，按 Enter 提交
        if not clicked:
            search_input.send_keys(Keys.ENTER)

        # 等待搜索结果加载
        time.sleep(5)
        self._simulate_human_scroll()
        self._check_anti_bot()

        return True

    # ----------------------------------------------------------
    #  结果列表解析
    # ----------------------------------------------------------

    def _get_result_items(self) -> list:
        """获取当前页面的搜索结果列表"""
        item_selectors = [
            ".result-list .result-item",
            ".search-result-list li",
            ".list-item",
            "table tbody tr",
            ".data-list .item",
            ".search-result .item",
            ".result-item",
            ".datasearch-result li",
            "div[class*='result'] li",
            "div[class*='list'] li a",
        ]

        for selector in item_selectors:
            try:
                items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if items and len(items) > 0:
                    logger.debug(f"找到 {len(items)} 个结果项 (selector: {selector})")
                    return items
            except Exception:
                continue

        # 通用策略: 查找包含链接的列表项
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, ".main a[href], #content a[href]")
            result_links = []
            for link in links:
                text = self._safe_text(link)
                href = link.get_attribute("href") or ""
                # 过滤出看起来像药品详情的链接
                if text and len(text) > 2 and len(text) < 200 and href:
                    if any(kw in href for kw in ["detail", "drug", "info", "show", "view"]):
                        result_links.append(link)
            if result_links:
                logger.debug(f"通用策略找到 {len(result_links)} 个结果链接")
                return result_links
        except Exception:
            pass

        return []

    def _get_detail_links(self, items: list) -> List[str]:
        """从结果列表中提取详情页 URL"""
        links = []
        for item in items:
            try:
                # 尝试直接获取 href
                href = item.get_attribute("href")
                if not href:
                    # 在子元素中查找链接
                    a_tag = item.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")
                if href and href.startswith("http"):
                    links.append(href)
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return links

    def _go_to_next_page(self) -> bool:
        """点击下一页，返回是否成功翻页"""
        next_selectors = [
            "a.next", ".pagination .next a",
            "a[title='下一页']", "a[class*='next']",
            ".page-next", "li.next a",
            "a:last-child",  # 最后尝试
        ]

        for selector in next_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        text = self._safe_text(el)
                        cls = el.get_attribute("class") or ""
                        # 检查是否是"下一页"按钮且未被禁用
                        if "disabled" in cls:
                            return False
                        if "下一页" in text or "next" in text.lower() or ">" in text or "›" in text:
                            self._safe_click(el)
                            time.sleep(3)
                            logger.info("翻到下一页")
                            return True
                        # 即使没有文本，如果是 next 类也尝试点击
                        if "next" in selector:
                            self._safe_click(el)
                            time.sleep(3)
                            return True
            except Exception:
                continue

        # XPath 策略
        try:
            next_link = self.driver.find_element(
                By.XPATH, "//a[contains(text(),'下一页') or contains(text(),'>')]"
            )
            if next_link.is_displayed():
                self._safe_click(next_link)
                time.sleep(3)
                return True
        except Exception:
            pass

        return False

    def _get_total_pages(self) -> int:
        """获取搜索结果总页数"""
        page_selectors = [
            ".pagination .page-item",
            ".page-num", "[class*='page']",
            ".total-pages",
        ]
        for selector in page_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return len(elements)
            except Exception:
                continue

        # 从页面文本中提取
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            import re
            match = re.search(r"共\s*(\d+)\s*页", body_text)
            if match:
                return int(match.group(1))
            match = re.search(r"(\d+)\s*/\s*(\d+)", body_text)
            if match:
                return int(match.group(2))
        except Exception:
            pass

        return 1

    # ----------------------------------------------------------
    #  详情页提取
    # ----------------------------------------------------------

    def _extract_drug_detail(self, url: str) -> Optional[Dict]:
        """
        访问药品详情页并提取信息
        """
        logger.info(f"  访问详情页: {url[:80]}...")

        try:
            self.driver.get(url)
            time.sleep(4)
            self._simulate_human_scroll()
            self._check_anti_bot()
        except Exception as e:
            logger.error(f"  详情页加载失败: {e}")
            return None

        record = {
            "产品名称": "",
            "英文名称": "",
            "批准文号": "",
            "生产单位": "",
            "剂型": "",
            "规格": "",
            "适应症": "",
            "药品分类": "",
            "批准日期": "",
            "有效期": "",
            "详情页URL": url,
        }

        # 查找详情面板/表格
        detail_selectors = [
            "table.detail-table",
            ".detail-content table",
            ".drug-detail",
            ".info-table",
            "table",
            ".detail-panel",
            ".content-detail",
            ".main-content",
            "#content",
            "main",
        ]

        detail_container = None
        for selector in detail_selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                if el and self._safe_text(el):
                    detail_container = el
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        if not detail_container:
            logger.debug("  未找到详情容器")
            # 尝试从整个页面提取
            detail_container = self.driver.find_element(By.TAG_NAME, "body")

        full_text = self._safe_text(detail_container)

        # ---------- 通过表格行提取键值对 ----------
        try:
            rows = detail_container.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if len(cells) >= 2:
                    key = self._safe_text(cells[0]).strip().rstrip("：:").strip()
                    value = self._safe_text(cells[1]).strip()

                    if not value:
                        continue

                    # 字段映射
                    key_lower = key.lower()
                    if any(k in key for k in ["产品名称", "药品名称", "通用名称", "商品名"]):
                        record["产品名称"] = value
                    elif any(k in key for k in ["英文名称", "英文"]):
                        record["英文名称"] = value
                    elif "批准文号" in key or "国药准字" in key:
                        record["批准文号"] = value
                    elif any(k in key for k in ["生产单位", "生产企业", "生产厂家"]):
                        record["生产单位"] = value
                    elif "剂型" in key:
                        record["剂型"] = value
                    elif "规格" in key:
                        record["规格"] = value
                    elif any(k in key for k in ["适应症", "功能主治", "用途"]):
                        record["适应症"] = value
                    elif any(k in key for k in ["药品分类", "分类", "类别"]):
                        record["药品分类"] = value
                    elif any(k in key for k in ["批准日期", "注册日期", "发证日期"]):
                        record["批准日期"] = value
                    elif any(k in key for k in ["有效期", "有效期至"]):
                        record["有效期"] = value
        except Exception as e:
            logger.debug(f"  表格解析异常: {e}")

        # ---------- 通过 dd/dt 结构提取 ----------
        try:
            dts = detail_container.find_elements(By.CSS_SELECTOR, "dt")
            for dt in dts:
                key = self._safe_text(dt).strip().rstrip("：:").strip()
                try:
                    dd = dt.find_element(By.XPATH, "following-sibling::dd[1]")
                    value = self._safe_text(dd).strip()
                except NoSuchElementException:
                    continue

                if not value:
                    continue

                if any(k in key for k in ["产品名称", "药品名称", "通用名"]):
                    record["产品名称"] = value
                elif any(k in key for k in ["批准文号", "国药准字"]):
                    record["批准文号"] = value
                elif any(k in key for k in ["生产单位", "生产企业"]):
                    record["生产单位"] = value
                elif "剂型" in key:
                    record["剂型"] = value
                elif "规格" in key:
                    record["规格"] = value
                elif any(k in key for k in ["适应症", "功能主治"]):
                    record["适应症"] = value
        except Exception:
            pass

        # ---------- 从全文正则补充 ----------
        import re

        if not record["批准文号"]:
            match = re.search(r"国药准字[A-Z]\d{8}", full_text)
            if match:
                record["批准文号"] = match.group()

        if not record["产品名称"]:
            # 尝试从页面标题提取
            try:
                title = self.driver.title
                # 去除网站后缀
                for suffix in ["_国家药品监督管理局", "-数据查询", "- NMPA"]:
                    title = title.replace(suffix, "")
                if title and len(title) < 100:
                    record["产品名称"] = title.strip()
            except Exception:
                pass

        # 至少要有名称或文号才算有效
        if record["产品名称"] or record["批准文号"]:
            return record
        return None

    # ----------------------------------------------------------
    #  关键词搜索流程
    # ----------------------------------------------------------

    def _process_keyword(self, keyword: str, keyword_idx: int):
        """处理单个关键词的完整搜索流程"""
        logger.info(f"\n{'='*40}")
        logger.info(f"处理关键词 [{keyword_idx+1}/{len(SEARCH_KEYWORDS)}]: {keyword}")
        logger.info(f"{'='*40}")

        self.current_keyword = keyword
        self.current_keyword_idx = keyword_idx

        # 加载搜索页面
        self._load_search_page()
        self._random_delay(2, 4)

        # 选择分类
        self._select_category(SEARCH_CATEGORY)
        self._random_delay(1, 3)

        # 搜索关键词
        if not self._search_keyword(keyword):
            logger.warning(f"搜索 '{keyword}' 失败，跳过")
            return

        # 处理搜索结果（含翻页）
        page = 1
        max_pages = 100  # 安全上限

        while page <= max_pages:
            logger.info(f"  第 {page} 页结果")

            # 模拟人类浏览
            self._simulate_human_scroll()
            self._random_delay(2, 5)

            # 获取结果列表
            items = self._get_result_items()
            if not items:
                logger.info(f"  第 {page} 页无结果，停止翻页")
                break

            logger.info(f"  找到 {len(items)} 条结果")

            # 提取详情页链接
            detail_links = self._get_detail_links(items)
            logger.info(f"  提取到 {len(detail_links)} 个详情链接")

            # 逐一访问详情页
            for link in detail_links:
                if link in self.visited_urls:
                    logger.debug(f"  已访问过，跳过: {link[:60]}")
                    continue

                self.visited_urls.add(link)
                self._random_delay()

                drug = self._extract_drug_detail(link)
                if drug:
                    self.all_drugs.append(drug)
                    self.processed_count += 1
                    logger.info(
                        f"  ✓ [{self.processed_count}] {drug['产品名称']} "
                        f"({drug['批准文号']})"
                    )

                    # 定期保存
                    if self.processed_count % 10 == 0:
                        self._save_csv()
                        self._save_progress()

                self._random_delay()

            # 翻页
            self._random_delay(3, 6)
            if not self._go_to_next_page():
                logger.info(f"  无更多页面，关键词 '{keyword}' 处理完成")
                break

            page += 1
            self._check_anti_bot()
            self._random_delay()

        # 关键词处理完成，保存进度
        self._save_progress()
        logger.info(f"关键词 '{keyword}' 处理完成")

    # ----------------------------------------------------------
    #  主流程
    # ----------------------------------------------------------

    def _save_csv(self):
        """保存数据到 CSV"""
        if not self.all_drugs:
            return

        csv_path = os.path.join(OUTPUT_DIR, CSV_FILE)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in self.all_drugs:
                writer.writerow(row)

        logger.info(f"CSV 已保存: {csv_path} ({len(self.all_drugs)} 条记录)")

    def run(self):
        """运行爬虫主流程"""
        logger.info("=" * 60)
        logger.info("NMPA 药品数据爬虫启动")
        logger.info(f"目标: {TARGET_URL}")
        logger.info(f"关键词数: {len(SEARCH_KEYWORDS)}")
        logger.info(f"查询分类: {SEARCH_CATEGORY}")
        logger.info(f"输出: {os.path.join(OUTPUT_DIR, CSV_FILE)}")
        logger.info("=" * 60)

        try:
            # 1. 启动浏览器
            self.driver = self._create_driver()
            self.wait = WebDriverWait(self.driver, ELEMENT_TIMEOUT)

            # 2. 恢复进度
            start_idx = self.progress.get("keyword_idx", 0)
            if start_idx > 0:
                logger.info(f"从关键词索引 {start_idx} 继续运行")
                self.visited_urls = set(self.progress.get("visited_urls", []))

            # 3. 逐个关键词搜索
            for idx in range(start_idx, len(SEARCH_KEYWORDS)):
                keyword = SEARCH_KEYWORDS[idx]

                try:
                    self._process_keyword(keyword, idx)
                except WebDriverException as e:
                    logger.error(f"浏览器异常: {e}")
                    self._save_csv()
                    self._save_progress()
                    self._restart_driver()
                    # 重试当前关键词
                    try:
                        self._process_keyword(keyword, idx)
                    except Exception as retry_e:
                        logger.error(f"重试失败: {retry_e}")
                        continue
                except Exception as e:
                    logger.error(f"处理关键词 '{keyword}' 出错: {e}", exc_info=True)
                    self._save_csv()
                    self._save_progress()
                    continue

                # 关键词之间加较长延时
                self._random_delay()

            # 4. 最终保存
            self._save_csv()
            self._save_progress()

            logger.info("=" * 60)
            logger.info(f"✓ 爬取完成! 共采集 {len(self.all_drugs)} 条药品数据")
            logger.info("=" * 60)

        except KeyboardInterrupt:
            logger.info("\n用户中断，正在保存已采集数据...")
            self._save_csv()
            self._save_progress()
        except Exception as e:
            logger.error(f"运行异常: {e}", exc_info=True)
            self._save_csv()
            self._save_progress()
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass


# ============================================================
#  入口
# ============================================================

if __name__ == "__main__":
    scraper = NMPADrugScraper()
    scraper.run()
