# -*- coding: utf-8 -*-
"""
AI Agent 智能问诊：DeepSeek 驱动的多轮问诊工作流。

Agent 流程（每步返回给前端展示）：
  1) 症状理解    —— 把口语症状结构化，识别缺失信息
  2) 知识库检索  —— 深度学习语义召回 + 规则引擎种子，合并候选
  3) 综合分析    —— LLM 结合知识库候选给出诊断、检查、用药、风险与追问
多轮：history 携带 AI 追问与用户补充，逐步收敛诊断。
"""
import json
import requests
from config import DEEPSEEK_KEY, DEEPSEEK_URL, DEEPSEEK_MODEL, DEEPSEEK_TIMEOUT
from db import kb
from embedding_service import embedding
from rule_engine import rule_engine


class AiAgent:
    def call_llm(self, messages, temperature=0.3, max_tokens=2048):
        """调用 DeepSeek，返回原始文本；失败返回 None。"""
        if not DEEPSEEK_KEY:
            return None
        headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}",
                   "Content-Type": "application/json"}
        payload = {"model": DEEPSEEK_MODEL, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens,
                   "stream": False}
        try:
            resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload,
                                 timeout=DEEPSEEK_TIMEOUT)
            if resp.status_code != 200:
                print(f"[agent] DeepSeek HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[agent] DeepSeek 调用异常: {e}")
            return None

    def _extract_json(self, text):
        """从 LLM 输出中稳妥提取 JSON。"""
        if not text:
            return None
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        # 去掉 ```json 围栏
        m = text.find("{")
        n = text.rfind("}")
        if m >= 0 and n > m:
            try:
                return json.loads(text[m:n + 1])
            except Exception:
                pass
        return None

    # ---------- Step 1: 症状理解 ----------
    def understand(self, user_text, history):
        msgs = [{"role": "system", "content":
                 "你是一名全科医生助理。请把患者口语描述的症状转成结构化医疗信息。"
                 "只输出 JSON，不要解释。格式："
                 '{"symptoms": ["规范症状词列表，如发热/咳嗽/头痛"], '
                 '"duration": "病程描述或null", '
                 '"missing": ["还需追问的关键信息，如体温高低/痰的性质/既往病史"]}'}]
        msgs += history[-4:]
        msgs.append({"role": "user", "content": user_text})
        raw = self.call_llm(msgs, temperature=0.1, max_tokens=600)
        parsed = self._extract_json(raw)
        if parsed:
            syms = parsed.get("symptoms") or []
            missing = parsed.get("missing") or []
            duration = parsed.get("duration") or None
            return {"symptoms": syms[:12], "missing": missing[:6], "duration": duration}
        return None

    # ---------- Step 2: 知识库检索 ----------
    def retrieve(self, query_text):
        """深度学习语义检索 + 规则引擎候选合并。"""
        cands = []
        if embedding.ready:
            hits = embedding.retrieve(query_text)
            cands = [{"diseaseId": h["diseaseId"], "score": round(h["score"], 4)}
                     for h in hits]
        rule_hits = rule_engine.match_diseases(kb.diseases,
                                               rule_engine.extract_symptoms(query_text), top_k=6)
        # 合并：语义优先，规则补充（按疾病 id 去重）
        seen = set()
        merged = []
        for c in cands:
            if c["diseaseId"] not in seen:
                seen.add(c["diseaseId"])
                merged.append(c)
        for d, conf, _ in rule_hits:
            if d["id"] not in seen:
                seen.add(d["id"])
                merged.append({"diseaseId": d["id"], "score": round(conf / 100, 3), "fromRule": True})
        return merged[:10]

    # ---------- Step 3: 综合分析 ----------
    def analyze(self, user_text, history, candidates):
        # 组装候选疾病文本（限长）
        cand_texts = []
        for c in candidates:
            d = kb.disease_by_id.get(c["diseaseId"])
            if not d:
                continue
            drugs = [dr["drugName"] for dr in kb.drugs_for_disease(d["id"], 3)]
            cand_texts.append(
                f"疾病：{d['disease_name']}（症状：{(d['symptoms'] or '')[:120]}；"
                f"病因：{(d['etiology'] or '')[:60]}；常用药：{'、'.join(drugs)}）")
        cand_block = "\n".join(cand_texts[:8]) or "（无候选）"

        consultation_context = "\n".join(
            message.get("content", "") for message in history[-4:]
            if message.get("content")
        )
        pharmacopoeia_chunks = kb.search_pharmacopoeia(
            f"{consultation_context}\n{user_text}", limit=5)
        pharmacopoeia_block = "\n\n".join(
            f"条目：{chunk['entry_name']}；来源：{chunk['source_title']}，"
            f"{chunk['edition']} {chunk['volume']}，{chunk['section']}，"
            f"印页 {chunk['source_pages'] or '未注明'}。\n{chunk['content']}"
            for chunk in pharmacopoeia_chunks
        ) or "（未检索到与本次问诊直接相关的药典整理片段）"

        msgs = [{"role": "system", "content":
                 "你是一名严谨的全科医生，负责给出鉴别诊断建议。患者不能直接就医，你的回答要通俗、可执行、安全。"
                 "以下检索到的药典内容来自用户提供的类风湿关节炎要点整理稿，其中有扫描件OCR识别及AI生成内容，"
                 "只能作为待核对的背景资料，不得声称已直接核验药典原文。"
                 "药典中药材的功能主治和用量不是患者的个体化处方；不得据此建议患者自行购买、煎服、配伍或停换药，"
                 "尤其不得建议自行使用有毒药材。生物制品适应证、剂量和用法必须以现行药品说明书及风湿免疫科医生意见为准。"
                 "你必须只输出一个 JSON 对象（不要任何其他文字），格式："
                 '{"diagnoses":[{"name":"疾病名","confidence":80(整数0-100),"summary":"一句话概述",'
                 '"causes":"可能病因","checks":"建议检查或观察","treatment":"治疗方向",'
                 '"drugs":["药品名"],"risk":"什么情况必须就医/危险信号"}],'
                 '"next_questions":["追问问题1","追问问题2"],'
                 '"advice":"整体生活建议"}。'
                 "要求：1) 从给出的候选疾病中挑选最匹配的1-3个，按置信度排序；"
                 "2) 若症状信息不足，请在 next_questions 里追问关键问题，不要强行确诊；"
                 "3) 药物只推荐候选疾病对应的常用药；4) 有危险信号（高热不退、呼吸困难、胸痛、意识改变、持续出血等）必须写入 risk；"
                 "5) 回答要口语化，让普通患者看得懂。"}]
        # 注入历史（AI 追问 + 用户补充）
        msgs += history[-4:]
        msgs.append({"role": "user",
                     "content": f"患者最新描述：{user_text}\n\n检索到的候选疾病库：\n{cand_block}\n"
                                f"\n与问诊相关的药典整理片段（仅作背景参考，不是处方）：\n{pharmacopoeia_block}\n"
                                "请基于以上信息输出鉴别诊断 JSON。"})
        raw = self.call_llm(msgs, temperature=0.3, max_tokens=2048)
        parsed = self._extract_json(raw)
        if parsed and isinstance(parsed.get("diagnoses"), list):
            return parsed
        return None

    # ---------- 兜底：规则结果包装 ----------
    def fallback_result(self, query_text):
        symptoms = rule_engine.extract_symptoms(query_text)
        hits = rule_engine.match_diseases(kb.diseases, symptoms, top_k=3)
        diagnoses = []
        for d, conf, _ in hits:
            drugs = kb.drugs_for_disease(d["id"], 3)
            diagnoses.append({
                "name": d["disease_name"], "confidence": int(conf),
                "summary": (d["symptoms"] or "")[:80],
                "causes": (d["etiology"] or "")[:60],
                "checks": "建议就医进一步检查",
                "treatment": (d["general_treatment"] or "")[:80],
                "drugs": [x["drugName"] for x in drugs],
                "risk": (d["important_note"] or "若症状持续或加重，请及时就医")[:80],
            })
        return {"diagnoses": diagnoses,
                "next_questions": ["症状持续多久了？", "是否伴有发热或其他不适？"],
                "advice": "规则引擎兜底结果，建议线下就医进一步明确诊断。",
                "source": "rule"}


agent = AiAgent()
