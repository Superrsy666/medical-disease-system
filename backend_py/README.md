# backend_py — AI 智能问诊服务

AI 问诊服务的完整环境准备、配置、启动、健康检查、接口说明和故障排查统一维护在项目根目录的 [README.md](../README.md)「第五步：启动 AI 智能问诊服务」中。请以该文档为准，避免启动说明重复或不一致。

服务主要由 FastAPI/Uvicorn、MySQL 知识库、PyTorch/Transformers 中文语义模型、DeepSeek API 和本地规则兜底构成。入口文件为 `main.py`，默认监听 8000 端口。

此目录的药典导入脚本 `import_pharmacopoeia.py` 用于导入用户整理的《中国药典》知识片段；这部分是可选知识，不是启动普通 AI 问诊服务的必要条件。该整理稿可能包含 OCR 识别及 AI 生成内容，不能替代药典原文、药品说明书或医生建议。
