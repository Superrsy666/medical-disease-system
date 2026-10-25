# -*- coding: utf-8 -*-
"""
深度学习语义检索服务：bge-small-zh 向量编码 + 疾病库余弦检索。
"""
import os
import numpy as np

# 使用 hf-mirror 加速模型下载（若设置了本地缓存则直连）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from config import EMBEDDING_MODEL, MODEL_CACHE_DIR, RETRIEVE_TOP_K

# bge 中文检索指令（查询侧加前缀，库侧不加）
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class EmbeddingService:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.disease_vectors = None   # (N, D)
        self.disease_ids = None
        self._ready = False
        self._load_error = None

    def load(self, diseases):
        try:
            from transformers import AutoModel, AutoTokenizer
            print(f"[embed] 加载中文向量模型 {EMBEDDING_MODEL} ...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                EMBEDDING_MODEL, cache_dir=MODEL_CACHE_DIR, local_files_only=False)
            self.model = AutoModel.from_pretrained(
                EMBEDDING_MODEL, cache_dir=MODEL_CACHE_DIR, local_files_only=False)
            self.model.eval()
            print("[embed] 模型加载完成，开始构建疾病库向量索引 ...")
            self._build_index(diseases)
            self._ready = True
            print(f"[embed] 索引完成：{len(self.disease_ids)} 种疾病向量")
        except Exception as e:
            self._load_error = str(e)
            print(f"[embed] 加载失败: {e}")

    @property
    def ready(self):
        return self._ready

    def _encode(self, texts):
        import torch
        import torch.nn.functional as F
        encoded = self.tokenizer(
            texts, padding=True, truncation=True, max_length=256,
            return_tensors="pt")
        with torch.no_grad():
            out = self.model(**encoded)
        mask = encoded["attention_mask"].unsqueeze(-1).float()
        emb = (out.last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        return F.normalize(emb, p=2, dim=1).numpy()

    def _build_index(self, diseases):
        texts = []
        ids = []
        for d in diseases:
            parts = [d["disease_name"] or "", d["symptoms"] or "",
                     (d["description"] or "")[:200], d["affected_area"] or "",
                     d["department"] or ""]
            texts.append(" ".join([p for p in parts if p]))
            ids.append(d["id"])
        self.disease_ids = np.array(ids)
        vecs = []
        for i in range(0, len(texts), 64):
            vecs.append(self._encode(texts[i:i + 64]))
        self.disease_vectors = np.vstack(vecs)

    def retrieve(self, query_text, top_k=None):
        """编码用户症状文本，返回候选疾病 (id, 相似度, 文本) 列表。"""
        k = top_k or RETRIEVE_TOP_K
        if not self.ready:
            return []
        qv = self._encode([QUERY_INSTRUCTION + query_text])[0]
        scores = self.disease_vectors @ qv
        idx = np.argsort(scores)[::-1][:k]
        return [{"diseaseId": int(self.disease_ids[i]), "score": float(scores[i])}
                for i in idx]


embedding = EmbeddingService()
