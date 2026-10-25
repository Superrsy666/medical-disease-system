# -*- coding: utf-8 -*-
"""
增强版疾病数据爬虫 - 多数据源、丰富字段
目标网站:
  1. 医学百科 (https://www.yixue.com/)  - 丰富的疾病知识
  2. 中医中药网疾病百科 (https://jbk.39.net/) - 39健康网
  3. WHO ICD-11 (已有)

依赖安装:
    pip install requests beautifulsoup4 lxml selenium webdriver-manager

运行方式:
    python scraper_diseases_enhanced.py

说明:
    - 多数据源策略：requests + BeautifulSoup 优先，Selenium 兜底
    - 爬取字段更丰富：病因、临床表现、并发症、检查、治疗、预防、预后
    - 智能去重 + 多源数据合并
    - 断点续传、随机延时、反爬策略
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
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, quote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装依赖: pip install requests beautifulsoup4")
    sys.exit(1)

# ======================== 配置区域 ========================

OUTPUT_DIR = "data"
CSV_FILE = "diseases_enhanced.csv"
PROGRESS_FILE = "disease_enhanced_progress.json"

MIN_DELAY = 2
MAX_DELAY = 5
ANTI_BOT_PAUSE = 30
PAGE_LOAD_TIMEOUT = 30

# 增强的CSV字段
CSV_FIELDS = [
    "疾病名称", "英文名称", "ICD编码", "别名",
    "疾病概述", "发病部位", "多发人群", "传染性",
    "典型症状", "病因", "发病机制",
    "并发症", "相关检查", "诊断依据", "鉴别诊断",
    "治疗原则", "药物治疗", "手术治疗", "其他治疗",
    "预后情况", "预防措施", "日常护理", "饮食建议",
    "是否遗传", "是否医保", "就诊科室",
    "数据来源", "来源URL", "采集时间",
]

# 随机User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 常见疾病分类（用于生成爬取列表）
DISEASE_CATEGORIES = [
    "呼吸系统疾病", "消化系统疾病", "心血管系统疾病", "神经系统疾病",
    "内分泌系统疾病", "泌尿生殖系统疾病", "血液系统疾病", "免疫系统疾病",
    "皮肤科疾病", "眼科疾病", "耳鼻喉科疾病", "口腔科疾病",
    "骨科疾病", "外科疾病", "妇科疾病", "儿科疾病",
    "精神心理疾病", "感染性疾病", "肿瘤癌症", "代谢性疾病",
]

# 常见疾病列表（优先爬取）
COMMON_DISEASES = [
    "感冒", "流行性感冒", "急性支气管炎", "慢性支气管炎", "肺炎", "哮喘", "肺结核", "肺气肿", "慢阻肺", "肺癌",
    "高血压", "冠心病", "心绞痛", "心肌梗死", "心力衰竭", "心律失常", "房颤", "心肌炎", "心包炎",
    "糖尿病", "甲状腺功能亢进", "甲状腺功能减退", "高脂血症", "肥胖症", "痛风", "骨质疏松",
    "胃炎", "胃溃疡", "十二指肠溃疡", "肠炎", "结肠炎", "阑尾炎", "胆囊炎", "胆结石", "胰腺炎", "肝炎", "肝硬化", "脂肪肝",
    "偏头痛", "三叉神经痛", "面瘫", "癫痫", "帕金森病", "阿尔茨海默病", "脑梗塞", "脑出血", "蛛网膜下腔出血",
    "湿疹", "荨麻疹", "银屑病", "白癜风", "痤疮", "皮炎", "皮肤过敏", "带状疱疹", "尖锐湿疣",
    "近视", "远视", "散光", "白内障", "青光眼", "结膜炎", "角膜炎", "干眼症", "中耳炎", "耳鸣", "耳聋",
    "过敏性鼻炎", "鼻窦炎", "咽炎", "扁桃体炎", "喉炎", "口腔溃疡", "牙龈炎", "牙周炎",
    "颈椎病", "腰椎间盘突出", "关节炎", "类风湿关节炎", "骨折", "扭伤", "肌肉拉伤",
    "肾炎", "肾病综合征", "肾结石", "尿路感染", "膀胱炎", "前列腺炎", "前列腺增生",
    "阴道炎", "宫颈炎", "盆腔炎", "子宫肌瘤", "卵巢囊肿", "月经不调", "痛经", "不孕不育",
    "小儿感冒", "小儿腹泻", "小儿肺炎", "小儿哮喘", "小儿湿疹", "佝偻病", "手足口病", "水痘", "麻疹",
    "抑郁症", "焦虑症", "强迫症", "精神分裂症", "失眠症", "神经衰弱", "恐惧症",
    "艾滋病", "梅毒", "淋病", "尖锐湿疣", "生殖器疱疹", "乙肝", "丙肝", "甲肝",
    "胃癌", "肝癌", "肠癌", "乳腺癌", "宫颈癌", "前列腺癌", "白血病", "淋巴瘤",
]

# ======================== 日志配置 ========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("disease_enhanced_scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class EnhancedDiseaseScraper:
    """增强版疾病数据爬虫 - 多数据源"""

    def __init__(self):
        self.all_diseases: List[Dict] = []
        self.visited_urls: Set[str] = set()
        self.visited_names: Set[str] = set()
        self.processed_count = 0
        self.session = requests.Session()

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.progress = self._load_progress()

    def _load_progress(self) -> dict:
        path = os.path.join(OUTPUT_DIR, PROGRESS_FILE)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"✓ 发现断点，已处理 {data.get('processed_count', 0)} 条")
                return data
            except Exception:
                pass
        return {"processed_count": 0, "visited_urls": [], "visited_names": []}

    def _save_progress(self):
        data = {
            "processed_count": self.processed_count,
            "visited_urls": list(self.visited_urls),
            "visited_names": list(self.visited_names),
            "timestamp": datetime.now().isoformat(),
        }
        with open(os.path.join(OUTPUT_DIR, PROGRESS_FILE), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _random_delay(self, min_s=MIN_DELAY, max_s=MAX_DELAY):
        time.sleep(random.uniform(min_s, max_s))

    def _get_headers(self) -> dict:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _fetch_url(self, url: str, timeout: int = PAGE_LOAD_TIMEOUT) -> Optional[str]:
        """使用requests获取页面"""
        if url in self.visited_urls:
            return None
        self.visited_urls.add(url)

        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            elif resp.status_code in [403, 429]:
                logger.warning(f"⚠ 反爬检测 ({resp.status_code})，暂停 {ANTI_BOT_PAUSE}s")
                time.sleep(ANTI_BOT_PAUSE)
                return None
            else:
                logger.warning(f"请求失败: {url} status={resp.status_code}")
                return None
        except Exception as e:
            logger.debug(f"请求异常: {url} {e}")
            return None

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('\u3000', ' ')
        return text

    # ==================== 数据源1: 医学百科 yixue.com ====================

    def scrape_yixue_com(self, disease_name: str) -> Optional[Dict]:
        """从医学百科爬取疾病信息"""
        search_url = f"https://www.yixue.com/index.php?search={quote(disease_name)}"
        html = self._fetch_url(search_url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")

            # 查找疾病页面链接
            disease_link = None
            for a in soup.select("a[href*='.yixue.com/']"):
                text = self._clean_text(a.get_text())
                if disease_name in text or text and len(text) < 30:
                    href = a.get("href", "")
                    if href and "yixue.com" in href and "search" not in href:
                        disease_link = href if href.startswith("http") else urljoin(search_url, href)
                        break

            if not disease_link:
                # 尝试直接访问疾病页面
                disease_link = f"https://www.yixue.com/{quote(disease_name)}.html"

            detail_html = self._fetch_url(disease_link)
            if not detail_html:
                return None

            detail_soup = BeautifulSoup(detail_html, "lxml")

            record = self._create_empty_record()
            record["疾病名称"] = disease_name
            record["来源URL"] = disease_link
            record["数据来源"] = "医学百科"
            record["采集时间"] = datetime.now().isoformat()

            # 提取页面内容
            content = detail_soup.select_one("#content, .content, .mw-parser-output, article, main")
            if not content:
                content = detail_soup.body

            full_text = self._clean_text(content.get_text())

            # 智能提取各字段
            sections = self._parse_wiki_sections(content)

            record["疾病概述"] = sections.get("概述", sections.get("简介", sections.get("疾病简介", "")))[:500]

            symptom_text = sections.get("临床表现", sections.get("症状", sections.get("典型症状", "")))
            if not symptom_text:
                # 从全文中找症状相关
                for kw in ["症状", "临床表现", "体征"]:
                    idx = full_text.find(kw)
                    if idx >= 0:
                        symptom_text = full_text[idx:idx+300]
                        break
            record["典型症状"] = symptom_text[:400]

            cause_text = sections.get("病因", sections.get("发病原因", sections.get("病因病理", "")))
            if not cause_text:
                for kw in ["病因", "发病原因", "诱因"]:
                    idx = full_text.find(kw)
                    if idx >= 0:
                        cause_text = full_text[idx:idx+300]
                        break
            record["病因"] = cause_text[:400]

            record["发病机制"] = sections.get("发病机制", sections.get("病理生理", ""))[:300]
            record["并发症"] = sections.get("并发症", "")[:300]
            record["相关检查"] = sections.get("检查", sections.get("辅助检查", sections.get("实验室检查", "")))[:300]
            record["诊断依据"] = sections.get("诊断", sections.get("诊断标准", ""))[:300]
            record["鉴别诊断"] = sections.get("鉴别诊断", "")[:300]

            treatment = sections.get("治疗", sections.get("治疗方法", sections.get("西医治疗", "")))
            record["治疗原则"] = treatment[:300]
            record["药物治疗"] = sections.get("药物治疗", sections.get("用药", ""))[:300]
            record["手术治疗"] = sections.get("手术治疗", "")[:200]
            record["其他治疗"] = sections.get("其他治疗", sections.get("中医治疗", sections.get("综合治疗", "")))[:200]

            record["预后情况"] = sections.get("预后", sections.get("预后转归", ""))[:200]
            record["预防措施"] = sections.get("预防", sections.get("疾病预防", ""))[:200]
            record["日常护理"] = sections.get("护理", sections.get("日常护理", ""))[:200]
            record["饮食建议"] = sections.get("饮食", sections.get("饮食保健", ""))[:200]

            # 查找ICD编码
            icd_match = re.search(r'ICD[\-\s]?1[01][:：\s]*([A-Z0-9\.]+)', full_text, re.I)
            if icd_match:
                record["ICD编码"] = icd_match.group(1)

            # 找就诊科室
            for kw in ["就诊科室", "挂号科室", "治疗科室"]:
                idx = full_text.find(kw)
                if idx >= 0:
                    dept = full_text[idx:idx+50]
                    dept_match = re.search(r'[:：]\s*([^，。、\n]+)', dept)
                    if dept_match:
                        record["就诊科室"] = dept_match.group(1).strip()
                    break

            # 判断是否有有效数据
            has_data = any([
                record["疾病概述"], record["典型症状"], record["病因"],
                record["治疗原则"], record["并发症"]
            ])

            if has_data:
                return record
            return None

        except Exception as e:
            logger.debug(f"解析yixue.com失败: {disease_name} {e}")
            return None

    def _parse_wiki_sections(self, soup) -> Dict[str, str]:
        """解析百科类页面的章节内容"""
        sections = {}
        current_heading = None
        current_content = []

        for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "div"]):
            tag_name = element.name

            if tag_name in ["h1", "h2", "h3", "h4"]:
                if current_heading and current_content:
                    sections[current_heading] = self._clean_text(" ".join(current_content))
                current_heading = self._clean_text(element.get_text())
                current_content = []
            elif current_heading:
                text = self._clean_text(element.get_text())
                if text and len(text) > 5:
                    current_content.append(text)

        if current_heading and current_content:
            sections[current_heading] = self._clean_text(" ".join(current_content))

        return sections

    # ==================== 数据源2: 39健康网 jbk.39.net ====================

    def scrape_39health(self, disease_name: str) -> Optional[Dict]:
        """从39健康网疾病百科爬取"""
        search_url = f"https://jbk.39.net/bw/{quote(disease_name)}/"
        html = self._fetch_url(search_url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")

            record = self._create_empty_record()
            record["疾病名称"] = disease_name
            record["来源URL"] = search_url
            record["数据来源"] = "39健康网"
            record["采集时间"] = datetime.now().isoformat()

            full_text = self._clean_text(soup.get_text())

            # 提取基本信息区
            info_box = soup.select_one(".disease_info, .info, .disease-basic, .basic-info")
            if info_box:
                info_text = info_box.get_text()
                for label, field in [("别名", "别名"), ("就诊科室", "就诊科室"),
                                      ("是否医保", "是否医保"), ("传染性", "传染性"),
                                      ("多发人群", "多发人群"), ("发病部位", "发病部位")]:
                    idx = info_text.find(label)
                    if idx >= 0:
                        val = info_text[idx+len(label):idx+len(label)+50]
                        val = re.sub(r'[:：\s]+', '', val).split()[0] if val.strip() else ""
                        if val and len(val) < 30:
                            record[field] = val

            # 提取各章节
            selectors = {
                "疾病概述": [".disease_overview", ".overview", ".gailan", "#gailan"],
                "典型症状": [".disease_symptom", ".symptom", ".zhengzhuang", "#zhengzhuang", ".clinical"],
                "病因": [".disease_cause", ".cause", ".bingyin", "#bingyin"],
                "并发症": [".disease_complication", ".complication", ".bingfazheng", "#bingfazheng"],
                "相关检查": [".disease_check", ".check", ".jiancha", "#jiancha"],
                "诊断依据": [".disease_diagnosis", ".diagnosis", ".zhenduan", "#zhenduan"],
                "鉴别诊断": [".disease_identify", ".identify", ".jianbie", "#jianbie"],
                "治疗原则": [".disease_treat", ".treat", ".zhiliao", "#zhiliao"],
                "预防措施": [".disease_prevent", ".prevent", ".yufang", "#yufang"],
                "预后情况": [".disease_prognosis", ".prognosis", ".yuhou", "#yuhou"],
                "饮食建议": [".disease_food", ".food", ".yinshi", "#yinshi"],
                "日常护理": [".disease_nurse", ".nurse", ".huli", "#huli"],
            }

            for field, sels in selectors.items():
                for sel in sels:
                    el = soup.select_one(sel)
                    if el:
                        text = self._clean_text(el.get_text())
                        if text and len(text) > 10:
                            record[field] = text[:500]
                            break

            # 如果没找到，从全文提取
            if not record["疾病概述"]:
                for kw in ["概述", "简介", "什么是"]:
                    idx = full_text.find(kw)
                    if idx >= 0:
                        record["疾病概述"] = full_text[idx:idx+400]
                        break

            if not record["典型症状"]:
                for kw in ["症状", "临床表现", "体征"]:
                    idx = full_text.find(kw)
                    if idx >= 0:
                        record["典型症状"] = full_text[idx:idx+400]
                        break

            if not record["病因"]:
                for kw in ["病因", "发病原因", "诱因"]:
                    idx = full_text.find(kw)
                    if idx >= 0:
                        record["病因"] = full_text[idx:idx+400]
                        break

            has_data = any([
                record["疾病概述"], record["典型症状"], record["病因"],
                record["治疗原则"], record["并发症"]
            ])

            if has_data:
                return record
            return None

        except Exception as e:
            logger.debug(f"解析39健康网失败: {disease_name} {e}")
            return None

    # ==================== 数据源3: 百度百科健康 ====================

    def scrape_baike_health(self, disease_name: str) -> Optional[Dict]:
        """从百度百科健康类词条爬取"""
        url = f"https://baike.baidu.com/item/{quote(disease_name)}"
        html = self._fetch_url(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")

            # 检查是否是疾病词条
            title = self._clean_text(soup.title.get_text() if soup.title else "")
            if "病" not in title and "症" not in title and disease_name not in title:
                return None

            record = self._create_empty_record()
            record["疾病名称"] = disease_name
            record["来源URL"] = url
            record["数据来源"] = "百度百科"
            record["采集时间"] = datetime.now().isoformat()

            # 提取摘要
            summary = soup.select_one(".lemma-summary, .lemmaWgt-lemmaSummary, .summary-pic")
            if summary:
                record["疾病概述"] = self._clean_text(summary.get_text())[:500]

            # 提取基本信息
            info_items = soup.select(".basic-info .basicInfo-item, .basic-info-item")
            for i in range(0, len(info_items)-1, 2):
                name_el = info_items[i]
                val_el = info_items[i+1] if i+1 < len(info_items) else None
                if not val_el:
                    continue
                name = self._clean_text(name_el.get_text()).replace(":", "").replace("：", "").strip()
                value = self._clean_text(val_el.get_text())

                field_map = {
                    "别名": "别名", "英文名称": "英文名称", "英文别名": "英文名称",
                    "就诊科室": "就诊科室", "挂号科室": "就诊科室",
                    "多发群体": "多发人群", "常见发病部位": "发病部位",
                    "常见病因": "病因", "常见症状": "典型症状",
                    "传染性": "传染性", "是否进入医保": "是否医保",
                    "并发症": "并发症",
                }

                for kw, field in field_map.items():
                    if kw in name and value:
                        record[field] = value[:300]
                        break

            # 提取目录章节内容
            content = soup.select_one(".lemma-content, .content-wrapper, #jlemma-content")
            if content:
                sections = self._parse_wiki_sections(content)

                if not record["典型症状"]:
                    record["典型症状"] = sections.get("临床表现", sections.get("症状", sections.get("典型症状", "")))[:400]
                if not record["病因"]:
                    record["病因"] = sections.get("病因", sections.get("发病原因", ""))[:400]

                record["发病机制"] = sections.get("发病机制", sections.get("病理生理", ""))[:300]
                record["并发症"] = sections.get("并发症", record.get("并发症", ""))[:300]
                record["相关检查"] = sections.get("检查", sections.get("辅助检查", ""))[:300]
                record["诊断依据"] = sections.get("诊断", sections.get("诊断标准", ""))[:300]
                record["鉴别诊断"] = sections.get("鉴别诊断", "")[:300]
                record["治疗原则"] = sections.get("治疗", sections.get("治疗方法", ""))[:400]
                record["药物治疗"] = sections.get("药物治疗", "")[:300]
                record["手术治疗"] = sections.get("手术治疗", "")[:200]
                record["预后情况"] = sections.get("预后", "")[:200]
                record["预防措施"] = sections.get("预防", sections.get("疾病预防", ""))[:200]
                record["日常护理"] = sections.get("护理", sections.get("日常护理", ""))[:200]
                record["饮食建议"] = sections.get("饮食", "")[:200]

            has_data = any([
                record["疾病概述"], record["典型症状"], record["病因"],
                record["治疗原则"], record["并发症"]
            ])

            if has_data:
                return record
            return None

        except Exception as e:
            logger.debug(f"解析百度百科失败: {disease_name} {e}")
            return None

    def _create_empty_record(self) -> Dict:
        return {f: "" for f in CSV_FIELDS}

    # ==================== 多源数据合并 ====================

    def merge_records(self, records: List[Dict]) -> Optional[Dict]:
        """合并多个数据源的记录，取最丰富的信息"""
        if not records:
            return None

        merged = self._create_empty_record()
        # 用第一个记录作为基础
        base = records[0]
        for k, v in base.items():
            if v:
                merged[k] = v

        # 用后续记录补充缺失字段
        for rec in records[1:]:
            for k, v in rec.items():
                if not merged.get(k) and v:
                    merged[k] = v
                # 如果已有但更短，优先用更长的
                elif v and len(str(v)) > len(str(merged.get(k, ""))):
                    if k in ["疾病概述", "典型症状", "病因", "治疗原则"]:
                        merged[k] = v

        return merged

    # ==================== 主流程 ====================

    def scrape_disease(self, disease_name: str) -> Optional[Dict]:
        """爬取单个疾病（多数据源）"""
        if disease_name in self.visited_names:
            return None

        records = []

        # 数据源1: 医学百科
        try:
            r1 = self.scrape_yixue_com(disease_name)
            if r1:
                records.append(r1)
                logger.info(f"  ✓ 医学百科: {disease_name}")
        except Exception as e:
            logger.debug(f"医学百科异常: {e}")

        self._random_delay(1, 3)

        # 数据源2: 39健康网
        try:
            r2 = self.scrape_39health(disease_name)
            if r2:
                records.append(r2)
                logger.info(f"  ✓ 39健康网: {disease_name}")
        except Exception as e:
            logger.debug(f"39健康网异常: {e}")

        self._random_delay(1, 3)

        # 数据源3: 百度百科
        try:
            r3 = self.scrape_baike_health(disease_name)
            if r3:
                records.append(r3)
                logger.info(f"  ✓ 百度百科: {disease_name}")
        except Exception as e:
            logger.debug(f"百度百科异常: {e}")

        if not records:
            logger.info(f"  ✗ 未获取到数据: {disease_name}")
            return None

        merged = self.merge_records(records)
        if merged:
            merged["疾病名称"] = disease_name
            self.visited_names.add(disease_name)
            return merged
        return None

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

    def run(self):
        logger.info("=" * 60)
        logger.info("增强版疾病数据爬虫启动")
        logger.info(f"目标数据源: 医学百科、39健康网、百度百科")
        logger.info(f"输出: {os.path.join(OUTPUT_DIR, CSV_FILE)}")
        logger.info("=" * 60)

        if self.progress.get("visited_names"):
            self.visited_names = set(self.progress["visited_names"])
            self.visited_urls = set(self.progress.get("visited_urls", []))

        # 优先爬取常见疾病
        all_diseases_to_scrape = list(dict.fromkeys(COMMON_DISEASES))

        logger.info(f"待爬取疾病数: {len(all_diseases_to_scrape)}")

        try:
            for i, disease in enumerate(all_diseases_to_scrape):
                if disease in self.visited_names:
                    continue

                logger.info(f"\n[{i+1}/{len(all_diseases_to_scrape)}] 爬取: {disease}")

                try:
                    record = self.scrape_disease(disease)
                    if record:
                        self.all_diseases.append(record)
                        self.processed_count += 1
                        logger.info(f"  完成! 累计: {self.processed_count}")

                        if self.processed_count % 5 == 0:
                            self._save_csv()
                            self._save_progress()

                except Exception as e:
                    logger.error(f"处理出错: {disease} {e}")

                self._random_delay()

            self._save_csv()
            self._save_progress()

            logger.info("=" * 60)
            logger.info(f"✓ 爬取完成! 共采集 {len(self.all_diseases)} 条疾病数据")
            logger.info("=" * 60)

        except KeyboardInterrupt:
            logger.info("\n用户中断，正在保存...")
            self._save_csv()
            self._save_progress()
        except Exception as e:
            logger.error(f"运行异常: {e}", exc_info=True)
            self._save_csv()
            self._save_progress()


if __name__ == "__main__":
    scraper = EnhancedDiseaseScraper()
    scraper.run()
