# -*- coding: utf-8 -*-
"""
医疗疾病系统 - Python 智能诊断服务（FastAPI）
启动：uvicorn main:app --host 0.0.0.0 --port 8000
"""
import time
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import kb
from embedding_service import embedding
from rule_engine import rule_engine
from ai_agent import agent

app = FastAPI(title="医疗疾病系统 - AI 智能诊断服务", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class AgentChatRequest(BaseModel):
    symptoms: str
    history: Optional[List[ChatMessage]] = None


class AgentChatResponse(BaseModel):
    steps: list
    result: dict


def _disease_summary(disease_id):
    d = kb.disease_by_id.get(disease_id)
    if not d:
        return ""
    return f"{d['disease_name']}（{d['department'] or '未知科室'}）"


@app.on_event("startup")
def startup():
    t0 = time.time()
    kb.load()
    print(f"[startup] 知识库加载耗时 {time.time() - t0:.1f}s")
    embedding.load(kb.diseases)


@app.get("/ai/health")
def health():
    return {
        "status": "ok",
        "knowledgeBase": {"diseases": len(kb.diseases), "drugs": len(kb.drugs),
                          "relations": len(kb.relations),
                          "pharmacopoeiaChunks": len(kb.pharmacopoeia_chunks)},
        "embeddingModel": {"ready": embedding.ready,
                           "model": "bge-small-zh-v1.5",
                           "error": embedding._load_error},
        "ruleEngine": {"synonyms": len(rule_engine.synonyms)},
    }


@app.post("/ai/agent/chat", response_model=AgentChatResponse)
def agent_chat(req: AgentChatRequest):
    user_text = (req.symptoms or "").strip()
    history = [{"role": m.role, "content": m.content} for m in (req.history or [])]
    if not user_text:
        return {"steps": [], "result": {"diagnoses": [], "next_questions": [],
                                        "advice": "请输入症状描述", "source": "none"}}

    steps = []

    # ---- Step 1: 症状理解 ----
    understood = agent.understand(user_text, history)
    if understood:
        syms = understood.get("symptoms") or []
        missing = understood.get("missing") or []
        detail = f"识别出症状：{'、'.join(syms[:8]) or '（未提取到）'}"
        if missing:
            detail += f"；尚缺信息：{'、'.join(missing[:3])}"
        steps.append({"name": "症状理解", "detail": detail, "status": "done"})
    else:
        syms = rule_engine.extract_symptoms(user_text)
        detail = f"识别出症状：{'、'.join(list(syms)[:8]) or '（规则引擎未提取到，继续检索）'}"
        steps.append({"name": "症状理解", "detail": detail + "（本地规则模式）", "status": "done"})

    # ---- Step 2: 知识库检索 ----
    candidates = agent.retrieve(user_text)
    if candidates:
        names = [_disease_summary(c["diseaseId"]) for c in candidates[:5]]
        steps.append({"name": "知识库检索",
                      "detail": f"从 {len(kb.diseases)} 种疾病中召回候选：{'；'.join(names)}",
                      "status": "done"})
    else:
        steps.append({"name": "知识库检索", "detail": "未召回候选，进入规则匹配", "status": "done"})

    # ---- Step 3: AI 综合分析 ----
    ai_result = agent.analyze(user_text, history, candidates) if candidates else None
    if ai_result:
        top_names = "、".join(d["name"] for d in ai_result["diagnoses"][:3])
        steps.append({"name": "AI 综合分析",
                      "detail": f"综合症状与知识库完成鉴别诊断：{top_names}",
                      "status": "done"})
        ai_result["source"] = "ai"
        return {"steps": steps, "result": ai_result}

    # ---- 兜底 ----
    steps.append({"name": "综合分析", "detail": "AI 服务暂不可用，返回规则引擎兜底结果",
                  "status": "done"})
    fallback = agent.fallback_result(user_text)
    return {"steps": steps, "result": fallback}
