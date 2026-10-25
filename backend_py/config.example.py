# -*- coding: utf-8 -*-
"""本地私密配置模板

复制为同目录下的 config_local.py 后填入真实值：
    Windows:      Copy-Item config.example.py config_local.py
    macOS/Linux:  cp config.example.py config_local.py

config_local.py 已列入 .gitignore，不会被提交到仓库。
也可以直接用环境变量 DB_USER / DB_PASSWORD 注入，无需本文件。
"""

DB_CONFIG = {
    "user": "root",
    "password": "你的MySQL密码",
}
