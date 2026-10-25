# -*- coding: utf-8 -*-
"""
疾病数据爬虫 - WHO ICD-11 国际疾病分类（中文版）
目标网址: https://icd.who.int/browse11/l-m/zh

依赖安装:
    pip install selenium webdriver-manager

运行方式:
    python scraper_diseases.py

说明:
    - 使用 Selenium + Chrome 浏览器动态渲染方案
    - 逐层遍历 ICD-11 疾病分类树
    - 支持断点续传（自动保存进度）
    - 随机延时 + User-Agent 轮换 + 反爬暂停
"""

import os
import sys
import csv
import time
import random
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, WebDriverException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ======================== 配置区域 ========================

TARGET_URL = "https://icd.who.int/browse11/l-m/zh"
OUTPUT_DIR = "data"
CSV_FILE = "diseases.csv"
PROGRESS_FILE = "disease_progress.json"

# 延时范围（秒）
MIN_DELAY = 3
MAX_DELAY = 8

# 反爬：遇到 429/403 时暂停秒数
ANTI_BOT_PAUSE = 60

# 页面加载超时（秒）
PAGE_LOAD_TIMEOUT = 60
ELEMENT_TIMEOUT = 20

# CSV 字段定义
CSV_FIELDS = [
    "疾病名称", "ICD-11编码", "上级分类路径",
    "疾病描述", "临床体征/症状", "排除项", "详情页URL",
]

# 随机 User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ======================== 日志配置 ========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("disease_scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ======================== 爬虫主类 ========================

class ICD11DiseaseScraper:
    """WHO ICD-11 疾病分类爬虫"""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.all_diseases: List[Dict] = []
        self.visited_keys: set = set()   # 用 name+code 去重
        self.processed_count = 0
        self.current_chapter = ""

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.progress = self._load_progress()

    # -------------------- 进度管理（断点续传）--------------------

    def _progress_path(self) -> str:
        return os.path.join(OUTPUT_DIR, PROGRESS_FILE)

    def _load_progress(self) -> dict:
        path = self._progress_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"✓ 发现断点文件，已处理 {data.get('processed_count', 0)} 条记录")
                return data
            except Exception:
                pass
        return {"processed_count": 0, "visited_keys": [], "current_chapter": ""}

    def _save_progress(self):
        data = {
            "processed_count": self.processed_count,
            "visited_keys": list(self.visited_keys),
            "current_chapter": self.current_chapter,
            "timestamp": datetime.now().isoformat(),
        }
        with open(self._progress_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -------------------- 浏览器管理 --------------------

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        ua = random.choice(USER_AGENTS)
        options.add_argument(f"--user-agent={ua}")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        # 如需后台运行（不弹出浏览器窗口），取消注释下一行:
        # options.add_argument("--headless=new")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.warning(f"webdriver-manager 启动失败: {e}")
            logger.info("尝试使用本地 ChromeDriver 启动")
            driver = webdriver.Chrome(options=options)

        # 隐藏 Selenium 特征
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )
        except Exception:
            pass
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        logger.info(f"Chrome 驱动已启动 (UA: {ua[:50]}...)")
        return driver

    def _restart_driver(self):
        logger.warning("正在重启浏览器...")
        try:
            self.driver.quit()
        except Exception:
            pass
        time.sleep(3)
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, ELEMENT_TIMEOUT)

    # -------------------- 工具方法 --------------------

    def _random_delay(self, min_s=MIN_DELAY, max_s=MAX_DELAY):
        delay = random.uniform(min_s, max_s)
        logger.debug(f"随机延时 {delay:.1f}s ...")
        time.sleep(delay)

    def _safe_click(self, element, retry=3):
        """安全点击，处理遮挡与过期引用"""
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
        try:
            return element.text.strip()
        except Exception:
            return ""

    def _safe_attr(self, element, attr: str) -> str:
        try:
            return (element.get_attribute(attr) or "").strip()
        except Exception:
            return ""

    # -------------------- 页面加载与反爬检测 --------------------

    def _load_page(self):
        logger.info(f"正在加载: {TARGET_URL}")
        self.driver.get(TARGET_URL)
        time.sleep(8)  # SPA 初始化需要较长时间
        self._check_anti_bot()

        # 尝试多种选择器等待树形结构加载
        tree_selectors = [
            "#tree", ".tree", "[role='tree']",
            ".fancytree-container", ".ui-fancytree",
            ".tree-node", ".chapter-node",
            "#icd-browser", ".browser-container",
            "ul[class*='tree']", "div[class*='tree']",
        ]
        tree_loaded = False
        for selector in tree_selectors:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.info(f"✓ 树形结构已加载 (selector: {selector})")
                tree_loaded = True
                break
            except TimeoutException:
                continue

        if not tree_loaded:
            logger.warning("未检测到常见树形选择器，继续尝试...")
            time.sleep(5)

    def _check_anti_bot(self):
        """检测并处理反爬机制（429/403/拦截页面）"""
        try:
            page_source = self.driver.page_source.lower()
            status_title = self.driver.title.lower()

            if any(code in status_title for code in ["429", "403", "too many", "forbidden"]):
                logger.warning(f"⚠ 检测到反爬! 标题: {self.driver.title}")
                logger.warning(f"暂停 {ANTI_BOT_PAUSE} 秒后重试...")
                time.sleep(ANTI_BOT_PAUSE)
                self.driver.get(TARGET_URL)
                time.sleep(8)
                return

            if "access denied" in page_source or "blocked" in page_source:
                logger.warning("⚠ 页面被拦截，暂停 60 秒...")
                time.sleep(ANTI_BOT_PAUSE)
                self.driver.get(TARGET_URL)
                time.sleep(8)
        except Exception as e:
            logger.debug(f"反爬检测异常: {e}")

    # -------------------- 树形结构遍历 --------------------

    def _get_tree_nodes(self) -> list:
        """获取当前可见的树节点（多策略回退）"""
        selectors = [
            # fancytree 风格
            "span.fancytree-title",
            ".fancytree-node .fancytree-title",
            # 通用树节点
            ".tree-node", ".tree-item",
            "[role='treeitem']",
            # ICD 浏览器特定
            ".chapter-node", ".category-node",
            ".node-title", ".tree-title",
            # 通用回退
            ".icd-tree li > span",
            "#tree li > span",
            "ul.tree li > span",
            "div[class*='tree'] li > span",
        ]
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.debug(f"找到 {len(elements)} 个节点 (selector: {selector})")
                    return elements
            except Exception:
                continue

        # XPath 回退
        xpaths = [
            "//div[contains(@class,'tree')]//li",
            "//ul[contains(@class,'tree')]//li",
            "//div[@id='tree']//li",
        ]
        for xpath in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements:
                    return elements
            except Exception:
                continue
        return []

    def _expand_node(self, node) -> bool:
        """展开树节点（点击展开图标）"""
        expand_selectors = [
            ".fancytree-expander", ".tree-expand-icon",
            ".expand-icon", ".toggle-icon",
            "[class*='expand']", "[class*='toggle']",
            "[class*='arrow']", "button[class*='expand']",
        ]
        # 在节点内部查找展开按钮
        for sel in expand_selectors:
            try:
                expander = node.find_element(By.CSS_SELECTOR, sel)
                if expander.is_displayed():
                    self._safe_click(expander)
                    time.sleep(2)
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        # 在父元素中查找
        try:
            parent = node.find_element(By.XPATH, "./..")
            for sel in expand_selectors:
                try:
                    expander = parent.find_element(By.CSS_SELECTOR, sel)
                    if expander.is_displayed():
                        self._safe_click(expander)
                        time.sleep(2)
                        return True
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
        except Exception:
            pass

        # 最后直接点击节点
        self._safe_click(node)
        time.sleep(2)
        return True

    def _node_has_children(self, node) -> bool:
        """检查节点是否有子节点"""
        for sel in ["ul", "ol", ".children", ".sub-nodes", "[role='group']"]:
            try:
                if node.find_elements(By.CSS_SELECTOR, sel):
                    return True
            except Exception:
                continue
        # 检查展开按钮状态
        try:
            for exp in node.find_elements(By.CSS_SELECTOR, "[class*='expand'], [class*='toggle']"):
                cls = exp.get_attribute("class") or ""
                if "collapsed" in cls and "expanded" not in cls:
                    return True
        except Exception:
            pass
        return False

    def _is_node_expanded(self, node) -> bool:
        try:
            for exp in node.find_elements(By.CSS_SELECTOR, "[class*='expand'], [class*='toggle']"):
                if "expanded" in (exp.get_attribute("class") or ""):
                    return True
        except Exception:
            pass
        return False

    def _get_breadcrumb_path(self) -> str:
        """获取面包屑导航路径"""
        for sel in [".breadcrumb", ".breadcrumbs", "[class*='breadcrumb']",
                     ".path", ".hierarchy", ".classification-path"]:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                text = self._safe_text(el)
                if text:
                    return text
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return ""

    # -------------------- 详情面板提取 --------------------

    def _extract_detail(self, path_prefix: str = "") -> Optional[Dict]:
        """从右侧详情面板提取当前选中疾病的信息"""

        # 等待详情面板
        detail_panel = None
        for sel in ["#Content", "#content", ".detail-panel", ".detail-content",
                     ".entity-detail", ".info-panel", ".right-panel",
                     "[class*='detail']", "main", "#main"]:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                if el and self._safe_text(el):
                    detail_panel = el
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        if not detail_panel:
            return None

        full_text = self._safe_text(detail_panel)
        if not full_text or len(full_text) < 5:
            return None

        record = {
            "疾病名称": "", "ICD-11编码": "", "上级分类路径": "",
            "疾病描述": "", "临床体征/症状": "", "排除项": "",
            "详情页URL": self.driver.current_url,
        }

        # --- 疾病名称 ---
        for sel in [".entity-title", ".detail-title", "h1", "h2",
                     ".title", "[class*='title']", ".prefLabel"]:
            try:
                el = detail_panel.find_element(By.CSS_SELECTOR, sel)
                text = self._safe_text(el)
                if text and len(text) < 200:
                    record["疾病名称"] = text
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        # --- ICD-11 编码 ---
        for sel in [".code", ".icd-code", ".entity-code",
                     "[class*='code']", ".badge", ".label-code"]:
            try:
                el = detail_panel.find_element(By.CSS_SELECTOR, sel)
                text = self._safe_text(el)
                if text and len(text) < 20:
                    record["ICD-11编码"] = text
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        if not record["ICD-11编码"]:
            for pat in [r'[A-Z0-9]{2,6}\.\d{0,2}', r'\b[A-Z]\d{2}[A-Z0-9]{0,3}\b']:
                m = re.search(pat, full_text)
                if m:
                    record["ICD-11编码"] = m.group()
                    break

        # --- 分类路径 ---
        breadcrumb = self._get_breadcrumb_path()
        record["上级分类路径"] = breadcrumb if breadcrumb else path_prefix

        # --- 疾病描述 ---
        descriptions = []
        for sel in [".description", ".definition", "[class*='description']",
                     "[class*='definition']", ".detail-text", ".info-text", "p"]:
            try:
                for el in detail_panel.find_elements(By.CSS_SELECTOR, sel):
                    text = self._safe_text(el)
                    if text and len(text) > 20 and text not in descriptions:
                        descriptions.append(text)
            except Exception:
                continue
        record["疾病描述"] = " | ".join(descriptions[:3]) if descriptions else ""

        # --- 临床体征/症状 ---
        symptom_texts = []
        for sel in ["[class*='symptom']", "[class*='sign']",
                     "[class*='clinical']", "[class*='manifestation']",
                     "[class*='presentation']", "[class*='feature']", ".symptoms", ".signs"]:
            try:
                for el in detail_panel.find_elements(By.CSS_SELECTOR, sel):
                    text = self._safe_text(el)
                    if text:
                        symptom_texts.append(text)
            except Exception:
                continue

        # 尝试抓取症状相关标题下的段落内容
        if not symptom_texts:
            for hdr in ["主要症状", "常见症状", "临床表现", "发病特征", "症状特点", "伴随症状"]:
                idx = full_text.find(hdr)
                if idx >= 0:
                    snippet = full_text[idx:idx + 400].strip()
                    symptom_texts.append(snippet)
                    break

        # 如果仍未能提取到症状，尝试使用更宽泛的关键字搜索
        if not symptom_texts:
            for kw in ["体征", "症状", "临床表现", "symptom", "clinical", "manifestation", "sign"]:
                idx = full_text.find(kw)
                if idx >= 0:
                    symptom_texts.append(full_text[idx:idx + 300].strip())
                    break

        # 合并并去重
        record["临床体征/症状"] = " | ".join(dict.fromkeys([s for s in symptom_texts if s]))

        # --- 排除项 ---
        exclusion_texts = []
        for sel in ["[class*='exclusion']", "[class*='exclude']", ".exclusion-note"]:
            try:
                for el in detail_panel.find_elements(By.CSS_SELECTOR, sel):
                    text = self._safe_text(el)
                    if text:
                        exclusion_texts.append(text)
            except Exception:
                continue
        if not exclusion_texts:
            for kw in ["排除", "不包括", "exclusion"]:
                idx = full_text.find(kw)
                if idx >= 0:
                    exclusion_texts.append(full_text[idx:idx + 300].strip())
                    break
        record["排除项"] = " | ".join(exclusion_texts)

        # 至少要有名称或编码才算有效
        if record["疾病名称"] or record["ICD-11编码"]:
            return record
        return None

    # -------------------- 递归遍历核心 --------------------

    def _traverse_tree(self, path: str = "", depth: int = 0, max_depth: int = 8):
        """递归遍历树形结构"""
        if depth > max_depth:
            logger.warning(f"达到最大递归深度 {max_depth}，跳过")
            return

        indent = "  " * depth
        nodes = self._get_tree_nodes()
        if not nodes:
            logger.warning(f"{indent}未找到树节点 (depth={depth})")
            return

        logger.info(f"{indent}发现 {len(nodes)} 个节点 (depth={depth})")

        for i, node in enumerate(nodes):
            try:
                node_text = self._safe_text(node)
                if not node_text:
                    continue

                logger.info(f"{indent}[{i+1}/{len(nodes)}] 处理: {node_text}")

                # 点击节点查看详情
                if self._safe_click(node):
                    self._random_delay(2, 4)
                    self._check_anti_bot()

                    detail = self._extract_detail(path_prefix=path)
                    if detail:
                        detail_key = f"{detail['疾病名称']}|{detail['ICD-11编码']}"
                        if detail_key not in self.visited_keys:
                            self.visited_keys.add(detail_key)
                            self.all_diseases.append(detail)
                            self.processed_count += 1
                            logger.info(
                                f"{indent}  ✓ 已采集: {detail['疾病名称']} "
                                f"({detail['ICD-11编码']})"
                            )
                            if self.processed_count % 10 == 0:
                                self._save_csv()
                                self._save_progress()

                # 展开子节点
                if self._node_has_children(node):
                    if not self._is_node_expanded(node):
                        if not self._expand_node(node):
                            continue
                        self._random_delay(2, 4)

                    new_path = f"{path} > {node_text}" if path else node_text
                    self._traverse_tree(path=new_path, depth=depth + 1, max_depth=max_depth)

                    # 递归返回后折叠
                    if self._is_node_expanded(node):
                        self._expand_node(node)
                        time.sleep(1)

                self._random_delay()

            except StaleElementReferenceException:
                logger.debug(f"{indent}节点已过期，跳过: {node_text}")
                continue
            except WebDriverException as e:
                logger.error(f"{indent}浏览器异常: {e}")
                self._restart_driver()
                self._load_page()
                return
            except Exception as e:
                logger.error(f"{indent}处理节点出错: {e}", exc_info=True)
                self._random_delay()
                continue

    # -------------------- CSV 保存 --------------------

    def _save_csv(self):
        if not self.all_diseases:
            return
        csv_path = os.path.join(OUTPUT_DIR, CSV_FILE)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in self.all_diseases:
                writer.writerow(row)
        logger.info(f"CSV 已保存: {csv_path} ({len(self.all_diseases)} 条记录)")

    # -------------------- 主入口 --------------------

    def run(self):
        logger.info("=" * 60)
        logger.info("WHO ICD-11 疾病数据爬虫启动")
        logger.info(f"目标: {TARGET_URL}")
        logger.info(f"输出: {os.path.join(OUTPUT_DIR, CSV_FILE)}")
        logger.info("=" * 60)

        try:
            self.driver = self._create_driver()
            self.wait = WebDriverWait(self.driver, ELEMENT_TIMEOUT)

            self._load_page()

            # 恢复断点
            if self.progress["processed_count"] > 0:
                logger.info(f"将从上次中断处继续 (已处理 {self.progress['processed_count']} 条)")
                self.visited_keys = set(self.progress.get("visited_keys", []))

            self._traverse_tree()

            self._save_csv()
            self._save_progress()

            logger.info("=" * 60)
            logger.info(f"✓ 爬取完成! 共采集 {len(self.all_diseases)} 条疾病数据")
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


# ======================== 入口 ========================

if __name__ == "__main__":
    scraper = ICD11DiseaseScraper()
    scraper.run()
