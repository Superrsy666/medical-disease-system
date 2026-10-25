# -*- coding: utf-8 -*-
"""
规则引擎（Python 移植版）：口语症状提取 + 同义词归一 + 加权匹配。
用途：作为 AI Agent 的候选种子与兜底（DeepSeek 不可用时仍可工作）。
词典从 Java 源码自动提取，保持单一数据源。
"""
import re
from config import load_synonym_map

# 口语"部位+不适"开放组合：部位映射
_LOCATIONS = [
    ("肚子", "腹痛"), ("胃", "胃痛"), ("嗓子", "咽痛"), ("喉咙", "咽痛"),
    ("咽喉", "咽痛"), ("胸口", "胸闷"), ("心口", "胸闷"), ("后背", "背痛"),
    ("背", "背痛"), ("腰", "腰痛"), ("头", "头痛"), ("眼睛", "眼干"),
    ("耳朵", "耳痛"), ("肩膀", "肩痛"), ("脖子", "颈痛"), ("膝盖", "关节痛"),
    ("胳膊", "臂痛"), ("手臂", "臂痛"), ("腿", "腿痛"), ("脚", "足痛"),
    ("浑身", "乏力"), ("全身", "乏力"),
]
_SUFFIX_CHARS = "痛疼酸胀麻痒晕闷肿"
_LONG_SUFFIXES = ("不舒服", "难受", "不得劲", "发麻", "发酸", "发痒", "发胀", "发晕", "发闷")


class RuleEngine:
    def __init__(self):
        self.synonyms = load_synonym_map()
        self.keys_sorted = sorted(self.synonyms.keys(), key=len, reverse=True)
        print(f"[rule] 口语同义词词典加载：{len(self.synonyms)} 条（来源 Java 源码）")

    # ---------- 症状提取 ----------
    def normalize(self, text):
        """长词优先整体替换同义词。"""
        t = text or ""
        for k in self.keys_sorted:
            if k in t:
                t = t.replace(k, self.synonyms[k])
        return t

    def extract_symptoms(self, text):
        out = set()
        norm = self.normalize(text)
        tokens = [s for s in re.split(r"[，。,.！!？?\s；;：:、]+", norm) if s]
        # 1) 词典全键扫描
        for k in self.keys_sorted:
            if k in norm:
                for w in self.synonyms[k].split():
                    if len(w) >= 2:
                        out.add(w)
        # 2) 开放组合：部位 + 不适后缀
        for token in tokens:
            suffix = None
            for s in _LONG_SUFFIXES:
                if token.endswith(s):
                    suffix = s
                    break
            if suffix is None and token and token[-1] in _SUFFIX_CHARS:
                suffix = token[-1]
            if not suffix:
                continue
            body = token[:len(token) - len(suffix)]
            for loc, mapped in _LOCATIONS:
                if loc in body:
                    c = suffix[-1]
                    if c == "麻":
                        word = "麻木"
                    elif c == "酸":
                        word = "关节痛" if loc == "膝盖" else "酸痛"
                    elif c == "痒":
                        word = "瘙痒"
                    elif c == "胀":
                        word = "腹胀"
                    elif c == "晕":
                        word = "头晕"
                    elif c == "闷":
                        word = "胸闷"
                    elif c == "肿":
                        word = "水肿"
                    else:
                        word = mapped
                    for w in word.split():
                        if len(w) >= 2:
                            out.add(w)
                    break
        # 3) 症状词种子（补充常见单双字词）
        seeds = ["发热", "发烧", "咳嗽", "腹泻", "呕吐", "恶心", "头痛", "头晕",
                 "乏力", "失眠", "心悸", "气短", "咽痛", "鼻塞", "流涕", "咳痰",
                 "瘙痒", "皮疹", "麻木", "水肿", "便秘", "腹痛", "腹胀"]
        for s in seeds:
            if s in norm:
                out.add(s)
        return out

    # ---------- 疾病匹配 ----------
    def match_diseases(self, diseases, symptoms, top_k=8):
        """症状在 疾病名(3)/症状(2)/描述(1) 加权命中 + 覆盖率 -> 置信度。"""
        scored = []
        for d in diseases:
            name = d["disease_name"] or ""
            sym = d["symptoms"] or ""
            desc = d["description"] or ""
            hit = 0.0
            hit_keys = set()
            for s in symptoms:
                w = 0
                if s in name:
                    w = 3
                elif s in sym:
                    w = 2
                elif s in desc:
                    w = 1
                if w:
                    hit += w
                    hit_keys.add(s)
            if hit > 0:
                ratio = min(1.0, hit / max(1.0, len(symptoms) * 2.0))
                conf = min(98.0, ratio * 70 + (len(hit_keys) / max(1, len(symptoms))) * 28)
                scored.append((d, conf, len(hit_keys)))
        scored.sort(key=lambda x: (-x[1], -x[2]))
        return scored[:top_k]


rule_engine = RuleEngine()
