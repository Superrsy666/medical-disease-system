# -*- coding: utf-8 -*-
"""
增强版药品数据爬虫 - 多数据源、丰富字段
目标网站:
  1. 国家药监局 NMPA (已有)
  2. 药智网 (https://www.yaozh.com/)
  3. 医学百科药品

依赖安装:
    pip install requests beautifulsoup4 lxml

运行方式:
    python scraper_drugs_enhanced.py
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
from urllib.parse import quote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装依赖: pip install requests beautifulsoup4")
    sys.exit(1)

# ======================== 配置区域 ========================

OUTPUT_DIR = "data"
CSV_FILE = "drugs_enhanced.csv"
PROGRESS_FILE = "drug_enhanced_progress.json"

MIN_DELAY = 2
MAX_DELAY = 5
ANTI_BOT_PAUSE = 30

CSV_FIELDS = [
    "药品名称", "英文名称", "商品名", "别名",
    "批准文号", "生产单位", "生产地址",
    "剂型", "规格", "药品分类", "处方类型", "是否医保", "是否OTC",
    "主要成分", "性状", "适应症", "功能主治",
    "用法用量", "不良反应", "禁忌", "注意事项",
    "药物相互作用", "药理作用", "毒理作用",
    "药代动力学",
    "孕妇及哺乳期妇女用药", "儿童用药", "老年用药",
    "药物过量", "贮藏", "包装", "有效期",
    "执行标准", "说明书修订日期",
    "数据来源", "来源URL", "采集时间",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 扩展的药品搜索关键词（按疾病和类别分类）
DRUG_KEYWORDS = [
    # 解热镇痛
    "布洛芬", "对乙酰氨基酚", "阿司匹林", "双氯芬酸钠", "萘普生", "吲哚美辛",
    "美洛昔康", "塞来昔布", "尼美舒利", "氨基比林", "安乃近",
    # 感冒止咳
    "复方氨酚烷胺", "氨酚黄那敏", "感冒灵", "板蓝根", "连花清瘟",
    "复方甘草", "氨溴索", "溴己新", "乙酰半胱氨酸", "右美沙芬",
    "喷托维林", "可待因", "愈创甘油醚",
    # 抗生素
    "阿莫西林", "头孢氨苄", "头孢拉定", "头孢克洛", "头孢呋辛",
    "头孢克肟", "头孢地尼", "青霉素V钾", "氨苄西林", "哌拉西林",
    "阿奇霉素", "罗红霉素", "红霉素", "克拉霉素", "乙酰螺旋霉素",
    "左氧氟沙星", "环丙沙星", "诺氟沙星", "氧氟沙星", "莫西沙星",
    "甲硝唑", "替硝唑", "奥硝唑", "呋喃唑酮", "小檗碱",
    "磺胺甲恶唑", "复方磺胺甲恶唑", "四环素", "多西环素", "米诺环素",
    "万古霉素", "去甲万古霉素", "利奈唑胺",
    # 抗病毒
    "阿昔洛韦", "更昔洛韦", "伐昔洛韦", "泛昔洛韦",
    "奥司他韦", "扎那米韦", "帕拉米韦", "玛巴洛沙韦",
    "利巴韦林", "阿比多尔", "连花清瘟", "金花清感",
    "拉米夫定", "阿德福韦酯", "恩替卡韦", "替诺福韦",
    "索磷布韦", "达拉他韦",
    # 心血管
    "硝苯地平", "氨氯地平", "左旋氨氯地平", "非洛地平", "拉西地平",
    "尼莫地平", "尼群地平", "地尔硫卓", "维拉帕米",
    "卡托普利", "依那普利", "贝那普利", "赖诺普利", "培哚普利",
    "缬沙坦", "厄贝沙坦", "氯沙坦", "替米沙坦", "奥美沙坦", "坎地沙坦",
    "美托洛尔", "比索洛尔", "阿替洛尔", "普萘洛尔", "卡维地洛",
    "氢氯噻嗪", "螺内酯", "呋塞米", "托拉塞米", "吲达帕胺",
    "阿托伐他汀", "瑞舒伐他汀", "辛伐他汀", "普伐他汀", "洛伐他汀",
    "非诺贝特", "苯扎贝特", "吉非罗齐",
    "阿司匹林肠溶片", "氯吡格雷", "替格瑞洛", "华法林", "利伐沙班",
    "硝酸甘油", "硝酸异山梨酯", "单硝酸异山梨酯",
    "地高辛", "去乙酰毛花苷", "毒毛花苷K",
    "胺碘酮", "普罗帕酮", "美西律", "普萘洛尔",
    # 消化系统
    "奥美拉唑", "兰索拉唑", "泮托拉唑", "雷贝拉唑", "埃索美拉唑",
    "雷尼替丁", "法莫替丁", "西咪替丁",
    "铝碳酸镁", "氢氧化铝", "枸橼酸铋钾", "胶体果胶铋",
    "多潘立酮", "莫沙必利", "伊托必利",
    "雷贝拉唑", "复方氢氧化铝", "硫糖铝",
    "乳酶生", "乳酸菌素", "双歧杆菌", "枯草杆菌",
    "蒙脱石散", "洛哌丁胺", "地芬诺酯",
    "熊去氧胆酸", "茴三硫", "消炎利胆", "排石颗粒",
    "乳果糖", "聚乙二醇", "开塞露", "甘油灌肠剂",
    "甲氧氯普胺", "昂丹司琼", "格拉司琼",
    "复方消化酶", "胰酶", "乳酶生", "干酵母",
    # 内分泌代谢
    "二甲双胍", "格列本脲", "格列齐特", "格列吡嗪", "格列喹酮",
    "格列美脲", "瑞格列奈", "那格列奈", "阿卡波糖", "伏格列波糖",
    "吡格列酮", "罗格列酮", "西格列汀", "沙格列汀", "维格列汀",
    "利拉鲁肽", "艾塞那肽", "达格列净", "恩格列净", "卡格列净",
    "胰岛素", "门冬胰岛素", "赖脯胰岛素", "甘精胰岛素", "地特胰岛素",
    "甲巯咪唑", "丙硫氧嘧啶", "左甲状腺素钠", "甲状腺片",
    "苯溴马隆", "别嘌醇", "非布司他", "秋水仙碱",
    "碳酸钙", "葡萄糖酸钙", "骨化三醇", "阿法骨化醇",
    "阿仑膦酸钠", "唑来膦酸", "鲑降钙素",
    # 神经系统
    "谷维素", "维生素B1", "维生素B12", "甲钴胺", "叶酸",
    "吡拉西坦", "奥拉西坦", "茴拉西坦", "胞磷胆碱",
    "氟桂利嗪", "倍他司汀", "天麻素",
    "地西泮", "艾司唑仑", "阿普唑仑", "佐匹克隆", "右佐匹克隆", "唑吡坦",
    "苯妥英钠", "卡马西平", "丙戊酸钠", "拉莫三嗪", "托吡酯",
    "左旋多巴", "多巴丝肼", "卡比多巴", "普拉克索", "司来吉兰",
    "溴隐亭", "苯海索", "金刚烷胺",
    "氟西汀", "帕罗西汀", "舍曲林", "氟伏沙明", "西酞普兰", "艾司西酞普兰",
    "文拉法辛", "度洛西汀", "米氮平", "阿米替林", "多塞平",
    "地昔帕明", "氯丙嗪", "奋乃静", "氟哌啶醇", "利培酮", "奥氮平", "喹硫平",
    "阿立哌唑", "齐拉西酮",
    # 呼吸系统
    "沙丁胺醇", "特布他林", "福莫特罗", "沙美特罗",
    "布地奈德", "氟替卡松", "倍氯米松", "泼尼松", "甲泼尼龙", "地塞米松",
    "异丙托溴铵", "噻托溴铵",
    "孟鲁司特", "扎鲁司特", "色甘酸钠", "酮替芬",
    "茶碱", "氨茶碱", "多索茶碱",
    "乙酰半胱氨酸", "羧甲司坦", "厄多司坦", "标准桃金娘油",
    # 泌尿生殖
    "左氧氟沙星", "环丙沙星", "头孢克洛", "头孢克肟",
    "三金片", "复方石韦", "癃清片",
    "坦索罗辛", "特拉唑嗪", "多沙唑嗪", "阿夫唑嗪",
    "非那雄胺", "依立雄胺", "普适泰",
    "西地那非", "他达拉非", "伐地那非",
    "达泊西汀", "利多卡因凝胶",
    "黄体酮", "地屈孕酮", "甲地孕酮", "甲羟孕酮",
    "炔雌醇", "戊酸雌二醇", "结合雌激素",
    "米非司酮", "米索前列醇",
    "左炔诺孕酮", "炔诺酮", "甲地孕酮",
    "甲硝唑", "克霉唑", "咪康唑", "制霉菌素", "硝酸咪康唑",
    # 血液系统
    "硫酸亚铁", "富马酸亚铁", "琥珀酸亚铁", "多糖铁复合物",
    "叶酸", "维生素B12", "甲钴胺", "腺苷钴胺",
    "重组人促红素", "罗沙司他",
    "氨甲环酸", "氨甲苯酸", "酚磺乙胺", "维生素K1",
    "氯吡格雷", "阿司匹林", "双嘧达莫", "西洛他唑",
    "华法林", "利伐沙班", "达比加群", "阿哌沙班",
    "肝素钠", "低分子肝素", "依诺肝素",
    "尿激酶", "链激酶", "阿替普酶", "瑞替普酶",
    "重组人凝血因子", "人凝血酶原复合物", "纤维蛋白原",
    # 免疫系统
    "氯雷他定", "西替利嗪", "左西替利嗪", "地氯雷他定",
    "氯苯那敏", "苯海拉明", "异丙嗪", "赛庚啶",
    "阿司咪唑", "特非那定",
    "泼尼松", "甲泼尼龙", "地塞米松", "氢化可的松", "倍他米松",
    "曲安奈德", "布地奈德", "氟替卡松",
    "环孢素", "他克莫司", "霉酚酸酯", "硫唑嘌呤", "甲氨蝶呤",
    "环磷酰胺", "来氟米特", "羟氯喹", "雷公藤多苷",
    "白芍总苷",
    "胸腺肽", "转移因子", "免疫球蛋白", "干扰素",
    "白介素", "肿瘤坏死因子",
    # 肿瘤相关
    "环磷酰胺", "甲氨蝶呤", "氟尿嘧啶", "替加氟", "卡培他滨",
    "顺铂", "卡铂", "奥沙利铂",
    "紫杉醇", "多西他赛",
    "长春新碱", "长春瑞滨", "长春地辛",
    "多柔比星", "表柔比星", "吡柔比星",
    "丝裂霉素", "博来霉素", "平阳霉素",
    "依托泊苷", "替尼泊苷",
    "羟基脲", "阿糖胞苷", "巯嘌呤", "甲氨蝶呤",
    "他莫昔芬", "来曲唑", "阿那曲唑", "依西美坦",
    "吉非替尼", "厄洛替尼", "埃克替尼", "阿法替尼",
    "伊马替尼", "吉非替尼", "厄洛替尼",
    "利妥昔单抗", "曲妥珠单抗", "贝伐珠单抗",
    # 皮肤外用
    "莫匹罗星软膏", "红霉素软膏", "四环素软膏",
    "金霉素软膏", "夫西地酸乳膏",
    "复方酮康唑乳膏", "硝酸咪康唑乳膏", "特比萘芬乳膏",
    "克霉唑乳膏", "联苯苄唑乳膏", "咪康唑氯倍他索乳膏",
    "地塞米松软膏", "糠酸莫米松乳膏", "丁酸氢化可的松乳膏",
    "卤米松乳膏", "曲安奈德乳膏", "氟轻松软膏",
    "炉甘石洗剂", "氧化锌软膏", "鱼肝油软膏", "凡士林",
    "维A酸乳膏", "阿达帕林凝胶", "过氧苯甲酰凝胶",
    "克林霉素凝胶", "甲硝唑凝胶",
    "尿素软膏", "水杨酸软膏", "苯甲酸软膏",
    "鱼石脂软膏", "湿润烧伤膏", "京万红软膏",
    "云南白药气雾剂", "双氯芬酸二乙胺乳胶剂",
    "扶他林软膏", "布洛芬凝胶", "酮洛芬凝胶",
    "伤湿止痛膏", "麝香壮骨膏", "关节止痛膏",
    "创可贴", "止血贴", "医用胶布", "纱布绷带",
    "碘伏", "碘酒", "酒精", "双氧水", "红药水", "紫药水",
    "氯霉素滴眼液", "左氧氟沙星滴眼液", "妥布霉素滴眼液",
    "氯霉素眼膏", "金霉素眼膏", "四环素眼膏",
    "人工泪液", "玻璃酸钠滴眼液", "羟丙甲纤维素滴眼液",
    "萘敏维滴眼液", "珍珠明目滴眼液",
    "色甘酸钠滴眼液", "奥洛他定滴眼液",
    "左氧氟沙星滴耳液", "氯霉素滴耳液",
    "苯酚滴耳液", "碳酸氢钠滴耳液",
    "复方硼砂溶液", "呋喃西林溶液", "氯己定含漱液",
    "甲硝唑含漱液", "复方氯己定含漱液",
    "开喉剑喷雾剂", "西瓜霜喷剂", "冰硼散", "锡类散",
    "口腔溃疡贴膜", "意可贴",
    # 维生素营养
    "维生素A", "维生素B1", "维生素B2", "维生素B6", "维生素B12",
    "维生素C", "维生素D", "维生素D2", "维生素D3",
    "维生素E", "维生素K", "烟酸", "烟酰胺", "泛酸", "生物素",
    "叶酸", "复合维生素B", "多维元素",
    "葡萄糖酸钙", "碳酸钙", "乳酸钙", "枸橼酸钙",
    "葡萄糖酸锌", "硫酸锌", "甘草锌",
    "富马酸亚铁", "硫酸亚铁", "琥珀酸亚铁",
    "卵磷脂", "深海鱼油", "鱼肝油",
    "辅酶Q10", "大豆异黄酮", "蛋白粉", "钙片",
    # 中成药
    "感冒清热颗粒", "银翘解毒丸", "双黄连口服液", "清热解毒口服液",
    "藿香正气水", "藿香正气软胶囊", "十滴水", "人丹",
    "云南白药", "片仔癀", "安宫牛黄丸", "牛黄解毒片",
    "六神丸", "保济丸", "整肠丸", "喇叭正露丸",
    "乌鸡白凤丸", "逍遥丸", "加味逍遥丸",
    "六味地黄丸", "金匮肾气丸", "知柏地黄丸", "杞菊地黄丸",
    "补中益气丸", "归脾丸", "人参健脾丸", "参苓白术散",
    "附子理中丸", "香砂养胃丸", "木香顺气丸",
    "复方丹参片", "丹参滴丸", "速效救心丸", "麝香保心丸",
    "地奥心血康", "步长脑心通", "通心络胶囊",
    "血塞通片", "血栓通胶囊",
    "步长稳心颗粒", "参松养心胶囊",
    "金水宝胶囊", "百令胶囊",
    "桂枝茯苓丸", "大黄蛰虫丸",
    "排石颗粒", "肾石通颗粒",
    "癃闭舒胶囊", "前列康片", "前列舒通胶囊",
    "腰痛宁胶囊", "颈复康颗粒", "根痛平颗粒",
    "风湿骨痛胶囊", "仙灵骨葆胶囊",
    "云南白药膏", "活血止痛膏", "奇正消痛贴膏",
    "狗皮膏", "麝香追风膏",
    "川贝枇杷膏", "急支糖浆", "蛇胆川贝液",
    "通宣理肺丸", "苏子降气丸", "蛤蚧定喘丸",
    "小柴胡颗粒", "柴胡口服液",
    "板蓝根颗粒", "夏桑菊颗粒", "金银花露",
    "健胃消食片", "保和丸", "枳实导滞丸",
    "麻仁丸", "便通胶囊", "苁蓉通便口服液",
    "三金片", "癃清片", "热淋清颗粒",
    "洁尔阴洗液", "妇炎洁洗液", "消糜栓", "保妇康栓",
    "金鸡胶囊", "花红片", "妇科千金片",
    "小儿氨酚黄那敏", "小儿感冒颗粒", "小儿止咳糖浆",
    "小儿七星茶", "小儿健脾散", "龙牡壮骨颗粒",
    "健胃消食片", "乳酸菌素片", "双歧杆菌四联活菌片",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("drug_enhanced_scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class EnhancedDrugScraper:
    """增强版药品数据爬虫"""

    def __init__(self):
        self.all_drugs: List[Dict] = []
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
        return {"processed_count": 0, "keyword_idx": 0, "visited_urls": [], "visited_names": []}

    def _save_progress(self):
        data = {
            "processed_count": self.processed_count,
            "keyword_idx": self.current_keyword_idx,
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
        }

    def _fetch_url(self, url: str) -> Optional[str]:
        if url in self.visited_urls:
            return None
        self.visited_urls.add(url)
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            elif resp.status_code in [403, 429]:
                logger.warning(f"⚠ 反爬检测，暂停{ANTI_BOT_PAUSE}s")
                time.sleep(ANTI_BOT_PAUSE)
                return None
            return None
        except Exception as e:
            logger.debug(f"请求异常: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def _create_empty_record(self) -> Dict:
        return {f: "" for f in CSV_FIELDS}

    # ==================== 数据源1: 药智网 ====================

    def scrape_yaozh(self, drug_name: str) -> Optional[Dict]:
        """从药智网爬取药品信息"""
        search_url = f"https://www.yaozh.com/search/?search={quote(drug_name)}&type=yp"
        html = self._fetch_url(search_url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")

            # 查找药品详情链接
            detail_link = None
            for a in soup.select("a[href*='/yaopin/'], a[href*='/drug/']"):
                text = self._clean_text(a.get_text())
                if drug_name in text or text:
                    href = a.get("href", "")
                    if href:
                        detail_link = href if href.startswith("http") else urljoin("https://www.yaozh.com", href)
                        break

            if not detail_link:
                # 尝试直接访问
                detail_link = f"https://www.yaozh.com/yaopin/{quote(drug_name)}.html"

            detail_html = self._fetch_url(detail_link)
            if not detail_html:
                return None

            detail_soup = BeautifulSoup(detail_html, "lxml")
            record = self._create_empty_record()
            record["药品名称"] = drug_name
            record["来源URL"] = detail_link
            record["数据来源"] = "药智网"
            record["采集时间"] = datetime.now().isoformat()

            full_text = self._clean_text(detail_soup.get_text())

            # 提取基本信息表格
            info_items = detail_soup.select("table tr, .info-item, .base-info li, .drug-info tr")
            info_dict = {}
            for item in info_items:
                tds = item.select("td, th, .label, .value")
                if len(tds) >= 2:
                    key = self._clean_text(tds[0].get_text()).replace(":", "").replace("：", "").strip()
                    value = self._clean_text(tds[1].get_text())
                    if key and value:
                        info_dict[key] = value

            field_mappings = [
                (["药品名称", "通用名称", "产品名称"], "药品名称"),
                (["英文名称", "英文名"], "英文名称"),
                (["商品名", "商品名称"], "商品名"),
                (["批准文号", "国药准字"], "批准文号"),
                (["生产单位", "生产企业", "生产厂家", "厂商"], "生产单位"),
                (["剂型"], "剂型"),
                (["规格"], "规格"),
                (["药品分类", "分类", "药物分类"], "药品分类"),
                (["处方类型", "处方药", "处方"], "处方类型"),
                (["主要成分", "成分"], "主要成分"),
                (["性状"], "性状"),
                (["适应症", "功能主治", "主治", "适用症"], "适应症"),
                (["用法用量", "用量", "使用方法"], "用法用量"),
                (["不良反应", "副作用"], "不良反应"),
                (["禁忌", "禁忌症"], "禁忌"),
                (["注意事项", "用药须知"], "注意事项"),
                (["药物相互作用", "相互作用"], "药物相互作用"),
                (["药理作用", "药理"], "药理作用"),
                (["孕妇及哺乳期妇女用药", "孕妇用药"], "孕妇及哺乳期妇女用药"),
                (["儿童用药"], "儿童用药"),
                (["老年用药"], "老年用药"),
                (["贮藏", "储存", "保存"], "贮藏"),
                (["包装"], "包装"),
                (["有效期"], "有效期"),
            ]

            for keys, field in field_mappings:
                for key in keys:
                    if key in info_dict:
                        if not record.get(field):
                            record[field] = info_dict[key]
                        break

            # 从全文中补充缺失字段
            field_fulltext_keywords = {
                "适应症": ["适应症", "功能主治", "用于"],
                "用法用量": ["用法用量", "口服", "一次"],
                "不良反应": ["不良反应", "副作用"],
                "禁忌": ["禁忌", "禁用", "忌用"],
                "注意事项": ["注意事项", "慎用"],
                "药物相互作用": ["药物相互作用"],
                "药理作用": ["药理作用", "药理毒理"],
                "贮藏": ["贮藏", "密封", "阴凉"],
                "有效期": ["有效期"],
            }

            for field, keywords in field_fulltext_keywords.items():
                if not record.get(field):
                    for kw in keywords:
                        idx = full_text.find(kw)
                        if idx >= 0:
                            snippet = full_text[idx:idx+300]
                            end = snippet.find("。")
                            if end > 0 and end < 200:
                                snippet = snippet[:end+1]
                            record[field] = snippet[:400]
                            break

            has_data = any([
                record["适应症"], record["用法用量"], record["不良反应"],
                record["禁忌"], record["注意事项"]
            ])

            if has_data:
                return record
            return None

        except Exception as e:
            logger.debug(f"解析药智网失败: {drug_name} {e}")
            return None

    # ==================== 数据源2: 医学百科药品 ====================

    def scrape_yixue_drug(self, drug_name: str) -> Optional[Dict]:
        """从医学百科爬取药品信息"""
        url = f"https://www.yixue.com/index.php?search={quote(drug_name)}"
        html = self._fetch_url(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")

            # 查找药品链接
            detail_link = None
            for a in soup.select("a[href*='.yixue.com/']"):
                text = self._clean_text(a.get_text())
                if drug_name in text and len(text) < 30:
                    href = a.get("href", "")
                    if "search" not in href:
                        detail_link = href if href.startswith("http") else f"https://www.yixue.com{href}"
                        break

            if not detail_link:
                detail_link = f"https://www.yixue.com/{quote(drug_name)}.html"

            detail_html = self._fetch_url(detail_link)
            if not detail_html:
                return None

            detail_soup = BeautifulSoup(detail_html, "lxml")

            record = self._create_empty_record()
            record["药品名称"] = drug_name
            record["来源URL"] = detail_link
            record["数据来源"] = "医学百科"
            record["采集时间"] = datetime.now().isoformat()

            content = detail_soup.select_one("#content, .content, .mw-parser-output, article")
            if not content:
                content = detail_soup.body

            full_text = self._clean_text(content.get_text())

            sections = {}
            current_heading = None
            current_content = []

            for element in content.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol"]):
                tag = element.name
                if tag in ["h1", "h2", "h3", "h4"]:
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

            field_section_map = {
                "适应症": ["适应症", "临床应用", "用途", "功能主治"],
                "用法用量": ["用法用量", "使用方法", "服用方法"],
                "不良反应": ["不良反应", "副作用"],
                "禁忌": ["禁忌", "禁忌症", "用药禁忌"],
                "注意事项": ["注意事项", "用药须知", "安全用药"],
                "药物相互作用": ["药物相互作用", "相互作用"],
                "药理作用": ["药理作用", "药理", "作用机制"],
                "主要成分": ["主要成分", "成分", "组成"],
                "性状": ["性状"],
                "贮藏": ["贮藏", "储存", "保存方法"],
                "有效期": ["有效期"],
            }

            for field, section_names in field_section_map.items():
                for sname in section_names:
                    for sec_name, sec_content in sections.items():
                        if sname in sec_name:
                            if not record.get(field):
                                record[field] = sec_content[:400]
                            break

            # 从全文补充
            if not record["适应症"]:
                for kw in ["适应症", "用于", "主治", "功能主治"]:
                    idx = full_text.find(kw)
                    if idx >= 0:
                        record["适应症"] = full_text[idx:idx+300]
                        break

            has_data = any([
                record["适应症"], record["用法用量"], record["不良反应"],
                record["药理作用"], record["注意事项"]
            ])

            if has_data:
                return record
            return None

        except Exception as e:
            logger.debug(f"解析医学百科药品失败: {drug_name} {e}")
            return None

    # ==================== 多源合并 ====================

    def merge_records(self, records: List[Dict]) -> Optional[Dict]:
        if not records:
            return None
        merged = self._create_empty_record()
        base = records[0]
        for k, v in base.items():
            if v:
                merged[k] = v
        for rec in records[1:]:
            for k, v in rec.items():
                if not merged.get(k) and v:
                    merged[k] = v
                elif v and len(str(v)) > len(str(merged.get(k, ""))):
                    if k in ["适应症", "用法用量", "不良反应", "注意事项", "药理作用"]:
                        merged[k] = v
        return merged

    def scrape_drug(self, drug_name: str) -> Optional[Dict]:
        if drug_name in self.visited_names:
            return None

        records = []

        try:
            r1 = self.scrape_yaozh(drug_name)
            if r1:
                records.append(r1)
                logger.info(f"  ✓ 药智网: {drug_name}")
        except Exception as e:
            logger.debug(f"药智网异常: {e}")

        self._random_delay(1, 2)

        try:
            r2 = self.scrape_yixue_drug(drug_name)
            if r2:
                records.append(r2)
                logger.info(f"  ✓ 医学百科: {drug_name}")
        except Exception as e:
            logger.debug(f"医学百科异常: {e}")

        if not records:
            logger.info(f"  ✗ 未获取到数据: {drug_name}")
            return None

        merged = self.merge_records(records)
        if merged:
            merged["药品名称"] = drug_name
            self.visited_names.add(drug_name)
            return merged
        return None

    def _save_csv(self):
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
        logger.info("=" * 60)
        logger.info("增强版药品数据爬虫启动")
        logger.info(f"数据源: 药智网、医学百科")
        logger.info(f"待爬取药品数: {len(DRUG_KEYWORDS)}")
        logger.info("=" * 60)

        if self.progress.get("visited_names"):
            self.visited_names = set(self.progress["visited_names"])
            self.visited_urls = set(self.progress.get("visited_urls", []))

        start_idx = self.progress.get("keyword_idx", 0)
        self.current_keyword_idx = start_idx

        try:
            for i in range(start_idx, len(DRUG_KEYWORDS)):
                drug = DRUG_KEYWORDS[i]
                self.current_keyword_idx = i
                if drug in self.visited_names:
                    continue

                logger.info(f"\n[{i+1}/{len(DRUG_KEYWORDS)}] 爬取: {drug}")

                try:
                    record = self.scrape_drug(drug)
                    if record:
                        self.all_drugs.append(record)
                        self.processed_count += 1
                        logger.info(f"  完成! 累计: {self.processed_count}")

                        if self.processed_count % 5 == 0:
                            self._save_csv()
                            self._save_progress()

                except Exception as e:
                    logger.error(f"处理出错: {drug} {e}")

                self._random_delay()

            self._save_csv()
            self._save_progress()

            logger.info("=" * 60)
            logger.info(f"✓ 爬取完成! 共采集 {len(self.all_drugs)} 条药品数据")
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
    scraper = EnhancedDrugScraper()
    scraper.run()
