# -*- coding: utf-8 -*-
"""
医疗疾病系统 - Python 智能诊断服务配置
"""
import os
import re
from pathlib import Path

# ===== 数据库 =====
# 默认从环境变量读取；本地真实凭据放在同目录的 config_local.py
# （config_local.py 已列入 .gitignore，不会提交到仓库）
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "medical_data"),
    "charset": "utf8mb4",
}

# 本地私有配置覆盖（可选，不存在时忽略）
try:
    from config_local import DB_CONFIG as _LOCAL_DB_CONFIG

    DB_CONFIG.update(_LOCAL_DB_CONFIG)
except ImportError:
    pass

# ===== 深度学习模型 =====
# 中文向量模型（bge-small-zh-v1.5，约 95MB，CPU 可跑）
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
# 模型本地缓存目录（项目内，避免下载到用户目录）
MODEL_CACHE_DIR = str(Path(__file__).resolve().parent / "models")
# 检索时召回的候选疾病数
RETRIEVE_TOP_K = 12

# ===== DeepSeek Agent =====
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 40

# ===== 规则引擎（从 Java 源码自动提取同义词词典）=====
JAVA_CONTROLLER = str(Path(__file__).resolve().parent.parent
                      / "backend/src/main/java/com/medical/controller/PredictionController.java")


def load_synonym_map():
    """从 PredictionController.java 提取 SYMPTOM_SYNONYMS 词典，保证与 Spring 侧单一数据源。"""
    try:
        with open(JAVA_CONTROLLER, encoding="utf-8") as f:
            src = f.read()
        pairs = re.findall(r'Map\.entry\("([^"]+)",\s*"([^"]+)"\)', src)
        syn = {}
        for k, v in pairs:
            k = k.strip()
            if k and k not in syn:
                syn[k] = v.strip()
        return syn
    except Exception as e:
        print(f"[rule] 读取 Java 词典失败: {e}")
        return {}
