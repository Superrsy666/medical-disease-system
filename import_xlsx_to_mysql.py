#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XLSX → MySQL 数据导入脚本（扩展版）
读取 diseases.xlsx 和 drugs.xlsx，导入到 MySQL 数据库，
并自动构建疾病-药品关联关系。

运行方式:
    python import_xlsx_to_mysql.py
"""

import os, sys, time, logging, re
from typing import List, Dict

import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

# ======================== 配置 ========================

MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": os.getenv("DB_PASSWORD", "CHANGE_ME"),  # 通过环境变量 DB_PASSWORD 提供
    "database": "medical_data",
    "charset": "utf8mb4",
}

XLSX_FILES = {
    "diseases": "diseases.xlsx",
    "drugs": "drugs.xlsx",
}

BATCH_SIZE = 50

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("import_xlsx_mysql.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ======================== MySQL 连接 ========================

def get_connection():
    db_name = MYSQL_CONFIG.get("database", "medical_data")
    base_config = {k: v for k, v in MYSQL_CONFIG.items() if k != "database"}
    try:
        conn = pymysql.connect(**base_config, cursorclass=DictCursor)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
    except pymysql.Error as e:
        logger.error(f"MySQL 连接失败: {e}")
        sys.exit(1)

    try:
        conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=DictCursor)
        logger.info(f"MySQL 连接成功: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{db_name}")
        return conn
    except pymysql.Error as e:
        logger.error(f"MySQL 连接失败: {e}")
        sys.exit(1)


def execute_init_sql(conn):
    sql_file = "init_database_expanded.sql"
    if not os.path.exists(sql_file):
        logger.warning(f"未找到 {sql_file}，跳过建表")
        return
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_text = f.read()
    statements = []
    for stmt in sql_text.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("--"):
            statements.append(stmt)
    cursor = conn.cursor()
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except pymysql.Error as e:
            if "already exists" not in str(e).lower():
                logger.debug(f"SQL: {e}")
    conn.commit()
    cursor.close()
    logger.info("数据库表结构已就绪（扩展版）")


# ======================== 疾病导入 ========================

DISEASE_FIELD_MAP = {
    "疾病名称":         "disease_name",
    "英文名称":         "english_name",
    "其它名称":         "aliases",
    "ICD编码":          "icd_code",
    "所属科室":         "department",
    "疾病描述":         "description",
    "发病部位":         "affected_area",
    "典型症状":         "symptoms",
    "症状总述":         "symptoms_overview",
    "症状详述":         "symptoms_detail",
    "主要病因":         "etiology",
    "病因概述":         "etiology_overview",
    "危险因素":         "risk_factors",
    "检查项目":         "examination",
    "预计检查":         "expected_examination",
    "实验室检查":       "lab_examination",
    "影像学检查":       "imaging_examination",
    "诊断依据":         "diagnostic_basis",
    "诊断标准":         "diagnostic_criteria",
    "鉴别诊断":         "differential_diagnosis",
    "传染性":           "infectiousness",
    "传染源":           "infection_source",
    "传播途径":         "transmission_route",
    "发病率":           "incidence_rate",
    "发病趋势":         "incidence_trend",
    "易感人群":         "susceptible_population",
    "遗传性":           "hereditary",
    "是否医保":         "medical_insurance",
    "相关中医疾病":     "tcm_related",
    "治疗预后":         "treatment_prognosis",
    "一般治疗":         "general_treatment",
    "药物治疗":         "drug_treatment",
    "预防治疗":         "prevention",
    "重要提醒":         "important_note",
    "详情链接":         "detail_url",
}

DISEASE_COLUMNS = list(DISEASE_FIELD_MAP.values())


def import_diseases(conn, df: pd.DataFrame) -> int:
    if df.empty:
        logger.warning("无疾病数据")
        return 0

    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE `disease_drug_relation`")
    cursor.execute("TRUNCATE TABLE `diseases`")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    logger.info("已清空 diseases 和 disease_drug_relation 表")

    columns_sql = ", ".join(f"`{c}`" for c in DISEASE_COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in DISEASE_COLUMNS)
    insert_sql = f"INSERT INTO `diseases` ({columns_sql}) VALUES ({placeholders})"

    # 重命名 DataFrame 列
    df_mapped = df.rename(columns=DISEASE_FIELD_MAP)
    for col in DISEASE_COLUMNS:
        if col not in df_mapped.columns:
            df_mapped[col] = None

    df_mapped = df_mapped[DISEASE_COLUMNS].where(pd.notna(df_mapped), None)

    records = df_mapped.to_dict(orient="records")
    for i, r in enumerate(records):
        for k, v in r.items():
            if isinstance(v, float) and pd.isna(v):
                r[k] = None
        records[i] = r

    logger.info(f"预处理: {len(records)} 条疾病记录")

    count = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            count += len(batch)
            pct = min(count, len(records)) / len(records) * 100
            logger.info(f"  疾病导入进度: {min(count, len(records))}/{len(records)} ({pct:.1f}%)")
        except pymysql.Error as e:
            logger.error(f"  批量插入出错 (offset={i}): {e}")
            for rec in batch:
                try:
                    cursor.execute(insert_sql, rec)
                    conn.commit()
                    count += 1
                except pymysql.Error as e2:
                    logger.warning(f"  跳过单条: {rec.get('disease_name', '?')} - {e2}")

    cursor.close()
    logger.info(f"疾病导入完成: 共 {count} 条")
    return count


# ======================== 药品导入 ========================

DRUG_FIELD_MAP = {
    "药品通用名":       "drug_name",
    "英文名称":         "english_name",
    "汉语拼音":         "pinyin",
    "批准文号":         "approval_number",
    "生产厂家":         "manufacturer",
    "药品分类":         "drug_category",
    "规格":             "specification",
    "适应症":           "indication",
    "处方类型":         "prescription_type",
    "医保类型":         "medical_insurance",
    "参考价格":         "reference_price",
    "成分":             "ingredients",
    "用法用量":         "usage_dosage",
    "不良反应":         "adverse_reactions",
    "禁忌":             "contraindications",
    "注意事项":         "precautions",
    "药物相互作用":     "drug_interactions",
    "药理作用":         "pharmacological_action",
    "贮藏方法":         "storage",
    "有效期":           "validity_period",
    "执行标准":         "executive_standard",
    "药品简介":         "drug_intro",
    "详情链接":         "detail_url",
}

DRUG_COLUMNS = list(DRUG_FIELD_MAP.values())


def import_drugs(conn, df: pd.DataFrame) -> int:
    if df.empty:
        logger.warning("无药品数据")
        return 0

    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE `drugs`")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    logger.info("已清空 drugs 表")

    columns_sql = ", ".join(f"`{c}`" for c in DRUG_COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in DRUG_COLUMNS)
    insert_sql = f"INSERT INTO `drugs` ({columns_sql}) VALUES ({placeholders})"

    df_mapped = df.rename(columns=DRUG_FIELD_MAP)
    for col in DRUG_COLUMNS:
        if col not in df_mapped.columns:
            df_mapped[col] = None

    df_mapped = df_mapped[DRUG_COLUMNS].where(pd.notna(df_mapped), None)

    records = df_mapped.to_dict(orient="records")
    skipped = 0
    valid_records = []
    for r in records:
        for k, v in r.items():
            if isinstance(v, float) and pd.isna(v):
                r[k] = None
        if not r.get("drug_name"):
            skipped += 1
            continue
        # 批准文号为空时生成占位值
        if not r.get("approval_number"):
            r["approval_number"] = f"AUTO-{abs(hash(str(r.get('drug_name', '')))) % 10**8:08d}"
        valid_records.append(r)

    logger.info(f"预处理: {len(valid_records)} 条有效药品记录, {skipped} 条跳过")

    count = 0
    for i in range(0, len(valid_records), BATCH_SIZE):
        batch = valid_records[i:i + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            count += len(batch)
            pct = min(count, len(valid_records)) / len(valid_records) * 100
            logger.info(f"  药品导入进度: {min(count, len(valid_records))}/{len(valid_records)} ({pct:.1f}%)")
        except pymysql.Error as e:
            logger.error(f"  批量插入出错 (offset={i}): {e}")
            for rec in batch:
                try:
                    cursor.execute(insert_sql, rec)
                    conn.commit()
                    count += 1
                except pymysql.Error as e2:
                    logger.warning(f"  跳过单条: {rec.get('drug_name', '?')} - {e2}")

    cursor.close()
    logger.info(f"药品导入完成: 共 {count} 条")
    return count


# ======================== 构建关联关系 ========================

def build_relations(conn) -> int:
    cursor = conn.cursor()

    cursor.execute("SELECT `id`, `disease_name` FROM `diseases` WHERE `disease_name` IS NOT NULL")
    diseases = cursor.fetchall()
    logger.info(f"加载 {len(diseases)} 种疾病")

    ignore_words = {"病", "症", "炎", "癌", "瘤", "热", "痛", "毒", "菌"}
    valid_diseases = [(d["id"], d["disease_name"].strip()) for d in diseases
                      if len(d["disease_name"].strip()) >= 2 and d["disease_name"].strip() not in ignore_words]
    logger.info(f"有效匹配疾病: {len(valid_diseases)} 种")

    cursor.execute("SELECT `id`, `drug_name`, `indication` FROM `drugs` WHERE `indication` IS NOT NULL AND `indication` != ''")
    drugs = cursor.fetchall()
    logger.info(f"加载 {len(drugs)} 种有适应症的药品")

    relations = []
    for drug in drugs:
        drug_id = drug["id"]
        indication = drug["indication"]
        if not indication:
            continue
        indication_lower = indication.lower()

        for disease_id, disease_name in valid_diseases:
            match = False
            if disease_name in indication or disease_name.lower() in indication_lower:
                match = True
            else:
                cursor.execute("SELECT `symptoms` FROM `diseases` WHERE `id` = %s", (disease_id,))
                row = cursor.fetchone()
                if row and row.get("symptoms"):
                    for term in re.split(r"[，,\s\|；;]+", str(row["symptoms"])):
                        term = term.strip()
                        if len(term) >= 2 and (term in indication or term.lower() in indication_lower):
                            match = True
                            break
            if match:
                relations.append((disease_id, drug_id))

    logger.info(f"匹配到 {len(relations)} 条疾病-药品关联")

    if not relations:
        cursor.close()
        return 0

    insert_sql = "INSERT IGNORE INTO `disease_drug_relation` (`disease_id`, `drug_id`, `match_source`) VALUES (%s, %s, 'indication')"
    count = 0
    for i in range(0, len(relations), BATCH_SIZE):
        batch = relations[i:i + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            count += cursor.rowcount
        except pymysql.Error as e:
            logger.error(f"关联插入出错: {e}")
            for rel in batch:
                try:
                    cursor.execute(insert_sql, rel)
                    conn.commit()
                    count += 1
                except pymysql.Error:
                    pass

    cursor.close()
    logger.info(f"关联关系导入完成: 共 {count} 条")
    return count


# ======================== 统计报告 ========================

def print_statistics(conn):
    cursor = conn.cursor()
    stats = {}
    for table in ["diseases", "drugs", "disease_drug_relation"]:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
        stats[table] = cursor.fetchone()["cnt"]

    print("\n" + "=" * 60)
    print("  📊 XLSX → MySQL 导入统计报告")
    print("=" * 60)
    print(f"  疾病记录:          {stats['diseases']:>6} 条")
    print(f"  药品记录:          {stats['drugs']:>6} 条")
    print(f"  疾病-药品关联:     {stats['disease_drug_relation']:>6} 条")
    print("=" * 60)

    cursor.execute(
        "SELECT d.disease_name, dr.drug_name, dr.approval_number "
        "FROM disease_drug_relation r "
        "JOIN diseases d ON r.disease_id = d.id "
        "JOIN drugs dr ON r.drug_id = dr.id "
        "ORDER BY d.disease_name LIMIT 15"
    )
    samples = cursor.fetchall()
    cursor.close()

    if samples:
        print("\n  🔗 关联关系样例:")
        print(f"  {'疾病名称':<20} {'药品名称':<22} {'批准文号'}")
        print(f"  {'-'*20} {'-'*22} {'-'*20}")
        for s in samples:
            name = (s["disease_name"] or "")[:18]
            drug = (s["drug_name"] or "")[:20]
            code = (s["approval_number"] or "")[:18]
            print(f"  {name:<20} {drug:<22} {code}")
        print()


# ======================== 主入口 ========================

def main():
    print("=" * 60)
    print("  XLSX → MySQL 数据导入工具（扩展版）")
    print("=" * 60)
    start_time = time.time()

    # 1. 读取 XLSX
    print("\n[1/4] 读取 XLSX 文件...")
    disease_df = pd.read_excel(XLSX_FILES["diseases"])
    drug_df = pd.read_excel(XLSX_FILES["drugs"])
    logger.info(f"diseases.xlsx: {disease_df.shape[0]} 行 x {disease_df.shape[1]} 列")
    logger.info(f"drugs.xlsx:    {drug_df.shape[0]} 行 x {drug_df.shape[1]} 列")

    # 2. 连接 MySQL & 建表
    print("\n[2/4] 连接 MySQL 并创建表结构...")
    conn = get_connection()
    execute_init_sql(conn)

    # 3. 导入数据
    print(f"\n[3/4] 导入数据 (疾病 {len(disease_df)} 条, 药品 {len(drug_df)} 条)...")
    disease_count = import_diseases(conn, disease_df)
    drug_count = import_drugs(conn, drug_df)

    # 4. 构建关联
    print("\n[4/4] 构建疾病-药品关联关系...")
    relation_count = build_relations(conn)

    print_statistics(conn)

    elapsed = time.time() - start_time
    logger.info(f"总耗时: {elapsed:.1f} 秒")
    conn.close()
    logger.info("数据库连接已关闭")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断。")
    except Exception as e:
        logger.error(f"运行异常: {e}", exc_info=True)
