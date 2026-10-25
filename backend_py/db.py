# -*- coding: utf-8 -*-
"""
数据层：从 MySQL 加载疾病库、药品库、疾病-药品关联，构建内存知识库。
"""
import re

import pymysql
from config import DB_CONFIG


class KnowledgeBase:
    def __init__(self):
        self.diseases = []          # 疾病列表（dict）
        self.disease_by_id = {}
        self.drugs = []             # 药品列表（dict）
        self.drug_by_id = {}
        self.relations = []         # (disease_id, drug_id)
        self.pharmacopoeia_chunks = []
        self._loaded = False

    def load(self):
        conn = pymysql.connect(**DB_CONFIG)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, disease_name, english_name, aliases, icd_code, department, "
                        "category_path, description, affected_area, symptoms, symptoms_overview, "
                        "symptoms_detail, etiology, etiology_overview, risk_factors, examination, "
                        "expected_examination, lab_examination, imaging_examination, diagnostic_basis, "
                        "diagnostic_criteria, differential_diagnosis, infectiousness, susceptible_population, "
                        "treatment_prognosis, general_treatment, drug_treatment, prevention, important_note "
                        "FROM diseases")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                self.diseases.append(d)
                self.disease_by_id[d["id"]] = d

            cur.execute("SELECT id, drug_name, drug_category, prescription_type, specification, "
                        "indication, ingredients, usage_dosage, adverse_reactions, contraindications, "
                        "precautions, drug_intro FROM drugs")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                dr = dict(zip(cols, row))
                self.drugs.append(dr)
                self.drug_by_id[dr["id"]] = dr

            cur.execute("SELECT disease_id, drug_id FROM disease_drug_relation")
            self.relations = cur.fetchall()

            try:
                cur.execute(
                    "SELECT source_title, edition, volume, section, entry_name, content, "
                    "keywords, source_pages, source_note FROM pharmacopoeia_chunks")
                cols = [d[0] for d in cur.description]
                self.pharmacopoeia_chunks = [
                    dict(zip(cols, row)) for row in cur.fetchall()
                ]
            except pymysql.err.ProgrammingError as e:
                if not e.args or e.args[0] != 1146:
                    raise
                self.pharmacopoeia_chunks = []
                print("[kb] pharmacopoeia_chunks 表不存在，跳过可选药典知识")
            self._loaded = True
            print(f"[kb] 知识库加载完成：{len(self.diseases)} 疾病 / {len(self.drugs)} 药品 / "
                  f"{len(self.relations)} 关联 / "
                  f"{len(self.pharmacopoeia_chunks)} 药典知识片段")
        finally:
            conn.close()

    @property
    def loaded(self):
        return self._loaded

    def drugs_for_disease(self, disease_id, limit=4):
        """按关联表取疾病对应药品；不足时按适应症文本匹配兜底。"""
        ids = [drug_id for did, drug_id in self.relations if did == disease_id][:limit]
        if len(ids) < limit and disease_id in self.disease_by_id:
            # 适应症兜底：药品适应症中包含疾病名或典型症状
            d = self.disease_by_id[disease_id]
            keys = [d["disease_name"], (d["symptoms"] or "")[:40]]
            for dr in self.drugs:
                if dr["id"] in ids:
                    continue
                ind = dr["indication"] or ""
                if any(k and k in ind for k in keys):
                    ids.append(dr["id"])
                if len(ids) >= limit:
                    break
        drugs = [self.drug_by_id[i] for i in ids if i in self.drug_by_id]
        return [{"id": d["id"], "drugName": d["drug_name"], "drugCategory": d["drug_category"],
                 "indication": (d["indication"] or "")[:80]} for d in drugs]

    def search_drugs(self, keyword, limit=5):
        kw = keyword or ""
        hits = [d for d in self.drugs if kw and (kw in (d["drug_name"] or "") or kw in (d["indication"] or ""))]
        return [{"id": d["id"], "drugName": d["drug_name"], "indication": (d["indication"] or "")[:80]}
                for d in hits[:limit]]

    def search_pharmacopoeia(self, query, limit=5):
        """按文档标注的主题词检索药典整理片段，不作为药品目录查询。"""
        query = (query or "").casefold()
        if not query:
            return []

        hits = []
        for chunk in self.pharmacopoeia_chunks:
            terms = [
                term.strip().casefold()
                for term in re.split(r"[、,，;；|/]+", chunk.get("keywords") or "")
                if term.strip()
            ]
            title = (chunk.get("entry_name") or "").casefold()
            score = sum(
                1 if term in {"ra", "类风湿关节炎"} else min(len(term), 10)
                for term in terms if len(term) > 1 and term in query
            )
            if title and title in query:
                score += len(title) * 2
            if score:
                hits.append((score, chunk))

        hits.sort(key=lambda hit: hit[0], reverse=True)
        return [chunk for _, chunk in hits[:limit]]


kb = KnowledgeBase()
