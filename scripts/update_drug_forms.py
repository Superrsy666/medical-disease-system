#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
药品剂型更新脚本 - 根据药品名称自动识别并填充 dosage_form 字段

运行方式:
    python scripts/update_drug_forms.py

说明:
    1. 自动连接 MySQL 的 medical_data 数据库
    2. 从 drug_name 提取剂型关键词（片剂、胶囊、颗粒、注射液等）
    3. 默认直接执行 UPDATE 更新数据库，并生成回滚 SQL
"""
import os
import sys
import pymysql
import re

# 与项目其他脚本保持一致
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": os.getenv("DB_PASSWORD", "CHANGE_ME"),  # 通过环境变量 DB_PASSWORD 提供
    "database": "medical_data",
    "charset": "utf8mb4"
}

# 剂型识别规则：按优先级排列，优先匹配更具体的剂型
DOSAGE_FORM_RULES = [
    # 特殊片剂（优先于普通片）
    ("泡腾片", r"泡腾片"),
    ("咀嚼片", r"咀嚼片"),
    ("缓释片", r"缓释片"),
    ("控释片", r"控释片"),
    ("肠溶片", r"肠溶片"),
    ("分散片", r"分散片"),
    ("含片", r"含片"),
    ("舌下片", r"舌下片"),
    ("口腔崩解片", r"口腔崩解片|口崩片"),
    # 注射类
    ("注射液", r"注射液"),
    ("注射用", r"注射用"),
    ("粉针剂", r"粉针|冻干粉针"),
    ("输液", r"输液|氯化钠注射液|葡萄糖注射液"),
    # 胶囊
    ("胶囊", r"胶囊"),
    # 口服液/溶液/混悬液
    ("口服液", r"口服液"),
    ("口服溶液", r"口服溶液"),
    ("混悬液", r"混悬液"),
    ("干混悬剂", r"干混悬剂"),
    ("糖浆剂", r"糖浆"),
    ("合剂", r"合剂"),
    # 丸剂
    ("丸剂", r"丸"),
    ("滴丸", r"滴丸"),
    # 颗粒/散剂
    ("颗粒", r"颗粒"),
    ("散剂", r"散|粉$|粉末"),
    # 外用制剂
    ("软膏", r"软膏"),
    ("乳膏", r"乳膏"),
    ("凝胶", r"凝胶"),
    ("贴剂", r"贴|贴膏"),
    ("栓剂", r"栓"),
    ("滴眼液", r"滴眼液"),
    ("眼膏", r"眼膏"),
    ("滴鼻液", r"滴鼻液"),
    ("喷雾剂", r"喷雾剂|气雾剂"),
    ("吸入剂", r"吸入"),
    ("洗剂", r"洗剂"),
    ("搽剂", r"搽剂"),
    ("酊剂", r"酊"),
    # 中药传统剂型
    ("煎膏剂", r"煎膏|膏滋"),
    ("膏药", r"膏药"),
    ("锭剂", r"锭"),
    ("露剂", r"露"),
    ("酒剂", r"酒$|酒剂"),
    ("茶剂", r"茶剂"),
    ("曲剂", r"曲剂"),
    ("膜剂", r"膜剂"),
    # 普通片剂放最后
    ("片剂", r"片$|片剂"),
]


def normalize_dosage_form(name):
    """从药品名称中提取剂型"""
    if not name:
        return "其他"
    name = str(name).strip()
    for form, pattern in DOSAGE_FORM_RULES:
        if re.search(pattern, name):
            return form
    return "其他"


def build_rollback_sql(rows):
    lines = ["-- 药品剂型更新回滚 SQL", "USE medical_data;", "START TRANSACTION;"]
    for pk, old_form in rows:
        if old_form is None:
            old = "NULL"
        else:
            old = "'" + old_form.replace("'", "''") + "'"
        lines.append(f"UPDATE drugs SET dosage_form = {old} WHERE id = {pk};")
    lines.append("COMMIT;")
    return "\n".join(lines)


def main():
    print("正在连接数据库...")
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, drug_name, dosage_form FROM drugs")
            rows = cur.fetchall()
            print(f"共读取 {len(rows)} 条药品记录")

            updates = []
            rollback_rows = []
            stats = {}
            for pk, name, old_form in rows:
                new_form = normalize_dosage_form(name)
                stats[new_form] = stats.get(new_form, 0) + 1
                rollback_rows.append((pk, old_form))
                if new_form != (old_form or "其他"):
                    updates.append((new_form, pk))

            # 生成回滚 SQL
            rollback_file = "update_drug_forms.sql"
            with open(rollback_file, "w", encoding="utf-8") as f:
                f.write(build_rollback_sql(rollback_rows))
            print(f"回滚 SQL 已保存: {rollback_file}")

            # 执行更新
            if updates:
                cur.executemany("UPDATE drugs SET dosage_form = %s WHERE id = %s", updates)
                conn.commit()
                print(f"已更新 {len(updates)} 条记录的 dosage_form 字段")
            else:
                print("无需更新")

            print("\n剂型分布:")
            for form, cnt in sorted(stats.items(), key=lambda x: -x[1]):
                print(f"  {form}: {cnt}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
