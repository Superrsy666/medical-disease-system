#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV → MySQL 数据导入脚本
读取 diseases.csv 和 drugs.csv，导入到 MySQL 数据库，
并自动构建疾病-药品关联关系。

依赖安装:
    pip install pymysql

运行方式:
    python import_to_mysql.py
"""

import os
import sys
import csv
import time
import logging
import re
from typing import List, Dict, Tuple

import pymysql
from pymysql.cursors import DictCursor

# ======================== 配置区域 ========================
# ⚠️ 请根据你的实际环境修改以下参数

MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",            # ← 修改为你的用户名
    "password": os.getenv("DB_PASSWORD", "CHANGE_ME"),  # 通过环境变量 DB_PASSWORD 提供
    "database": "medical_data",   # ← 数据库名（与 init_database.sql 一致）
    "charset": "utf8mb4",
}

# CSV 文件路径
CSV_DIR = "data"
DISEASES_CSV = os.path.join(CSV_DIR, "diseases.csv")
DRUGS_CSV = os.path.join(CSV_DIR, "drugs.csv")

# 批量插入大小
BATCH_SIZE = 100

# ======================== 日志配置 ========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("import_mysql.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ======================== 工具函数 ========================

def read_csv(filepath: str) -> List[Dict]:
    """读取 CSV 文件，返回字典列表"""
    if not os.path.exists(filepath):
        logger.error(f"CSV 文件不存在: {filepath}")
        return []

    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 去除 BOM 和多余空白
            cleaned = {}
            for key, value in row.items():
                clean_key = key.strip().lstrip("\ufeff")
                clean_val = value.strip() if value else ""
                cleaned[clean_key] = clean_val
            rows.append(cleaned)

    logger.info(f"✓ 读取 CSV: {filepath} ({len(rows)} 行)")
    return rows


def get_connection() -> pymysql.Connection:
    """创建 MySQL 连接，如果数据库不存在则自动创建"""
    db_name = MYSQL_CONFIG.get("database", "medical_data")

    # 先不带数据库名连接，确保数据库存在
    try:
        base_config = {k: v for k, v in MYSQL_CONFIG.items() if k != "database"}
        conn = pymysql.connect(**base_config, cursorclass=DictCursor)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()
    except pymysql.Error as e:
        logger.error(f"✗ MySQL 连接失败: {e}")
        sys.exit(1)

    # 再连接到目标数据库
    try:
        conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=DictCursor)
        logger.info(f"✓ MySQL 连接成功: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{db_name}")
        return conn
    except pymysql.Error as e:
        logger.error(f"✗ MySQL 连接失败: {e}")
        sys.exit(1)


def execute_init_sql(conn: pymysql.Connection):
    """
    自动执行建表 SQL（如果表不存在）。
    你也可以手动执行 init_database.sql 后跳过此步骤。
    """
    sql_file = "init_database.sql"
    if not os.path.exists(sql_file):
        logger.warning(f"未找到 {sql_file}，请手动执行建表 SQL")
        return

    with open(sql_file, "r", encoding="utf-8") as f:
        sql_text = f.read()

    # 去掉注释行，按分号拆分
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
            # DROP TABLE IF EXISTS 和 CREATE 相关的错误可以忽略
            if "already exists" not in str(e).lower():
                logger.debug(f"SQL 执行提示: {e}")
    conn.commit()
    cursor.close()
    logger.info("✓ 数据库表结构已就绪")


# ======================== 疾病导入 ========================

def import_diseases(conn: pymysql.Connection, csv_rows: List[Dict]) -> int:
    """
    导入疾病数据到 diseases 表
    返回: 实际插入/更新的条数
    """
    if not csv_rows:
        logger.warning("无疾病数据可导入")
        return 0

    cursor = conn.cursor()

    # 先清空表
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE `disease_drug_relation`")
    cursor.execute("TRUNCATE TABLE `diseases`")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    logger.info("✓ 已清空 diseases 和 disease_drug_relation 表")

    # 插入 SQL（使用 ON DUPLICATE KEY UPDATE 实现去重）
    insert_sql = """
        INSERT INTO `diseases`
            (`disease_name`, `icd_code`, `category_path`, `description`, `symptoms`, `excludes`)
        VALUES
            (%(disease_name)s, %(icd_code)s, %(category_path)s, %(description)s, %(symptoms)s, %(excludes)s)
        ON DUPLICATE KEY UPDATE
            `icd_code`      = VALUES(`icd_code`),
            `category_path` = VALUES(`category_path`),
            `description`   = VALUES(`description`),
            `symptoms`      = VALUES(`symptoms`),
            `excludes`      = VALUES(`excludes`)
    """

    # 字段映射: CSV 列名 → SQL 参数名
    field_map = {
        "疾病名称": "disease_name",
        "ICD-11编码": "icd_code",
        "上级分类路径": "category_path",
        "疾病描述": "description",
        "疾病定义/描述": "description",
        "临床体征/症状": "symptoms",
        "排除项": "excludes",
    }

    # 预处理数据
    records = []
    skipped = 0
    for row in csv_rows:
        # 映射字段（同一目标字段取第一个非空值）
        record = {}
        for csv_key, sql_key in field_map.items():
            val = row.get(csv_key, "").strip() if row.get(csv_key) else ""
            if val and not record.get(sql_key):  # 只取第一个非空值
                record[sql_key] = val

        # 至少要有疾病名称
        if not record.get("disease_name"):
            skipped += 1
            continue

        records.append(record)

    logger.info(f"预处理: {len(records)} 条有效记录, {skipped} 条跳过（无名称）")

    # 批量插入
    count = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            count += len(batch)
            progress = min(count, len(records))
            pct = progress / len(records) * 100
            logger.info(f"  疾病导入进度: {progress}/{len(records)} ({pct:.1f}%)")
        except pymysql.Error as e:
            logger.error(f"  批量插入出错 (offset={i}): {e}")
            # 逐条重试
            for rec in batch:
                try:
                    cursor.execute(insert_sql, rec)
                    conn.commit()
                    count += 1
                except pymysql.Error as e2:
                    logger.warning(f"  跳过单条: {rec.get('disease_name', '?')} - {e2}")

    cursor.close()
    logger.info(f"✓ 疾病导入完成: 共 {count} 条")
    return count


# ======================== 药品导入 ========================

def import_drugs(conn: pymysql.Connection, csv_rows: List[Dict]) -> int:
    """
    导入药品数据到 drugs 表
    返回: 实际插入/更新的条数
    """
    if not csv_rows:
        logger.warning("无药品数据可导入")
        return 0

    cursor = conn.cursor()

    # 清空药品表（先关外键）
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE `disease_drug_relation`")
    cursor.execute("TRUNCATE TABLE `drugs`")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    logger.info("✓ 已清空 drugs 表")

    insert_sql = """
        INSERT INTO `drugs`
            (`drug_name`, `english_name`, `approval_number`, `manufacturer`,
             `dosage_form`, `specification`, `indication`, `drug_category`,
             `approval_date`, `validity_period`)
        VALUES
            (%(drug_name)s, %(english_name)s, %(approval_number)s, %(manufacturer)s,
             %(dosage_form)s, %(specification)s, %(indication)s, %(drug_category)s,
             %(approval_date)s, %(validity_period)s)
        ON DUPLICATE KEY UPDATE
            `english_name`    = VALUES(`english_name`),
            `manufacturer`    = VALUES(`manufacturer`),
            `dosage_form`     = VALUES(`dosage_form`),
            `specification`   = VALUES(`specification`),
            `indication`      = VALUES(`indication`),
            `drug_category`   = VALUES(`drug_category`),
            `approval_date`   = VALUES(`approval_date`),
            `validity_period` = VALUES(`validity_period`)
    """

    field_map = {
        "产品名称": "drug_name",
        "药品名称": "drug_name",
        "英文名称": "english_name",
        "批准文号": "approval_number",
        "生产单位": "manufacturer",
        "生产厂家": "manufacturer",
        "剂型": "dosage_form",
        "规格": "specification",
        "适应症": "indication",
        "药品分类": "drug_category",
        "产品类别": "drug_category",
        "批准日期": "approval_date",
        "有效期": "validity_period",
    }

    # 预处理
    records = []
    skipped = 0
    for row in csv_rows:
        record = {}
        for csv_key, sql_key in field_map.items():
            val = row.get(csv_key, "").strip() if row.get(csv_key) else ""
            if val and not record.get(sql_key):  # 只取第一个非空值
                record[sql_key] = val

        # 至少要有药品名称和批准文号
        if not record.get("drug_name"):
            skipped += 1
            continue
        # 如果批准文号为空，给一个占位值
        if not record.get("approval_number"):
            record["approval_number"] = f"AUTO-{hash(record['drug_name']) % 10**8:08d}"

        # 处理日期格式
        if record.get("approval_date"):
            date_str = record["approval_date"].strip()
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y.%m.%d"]:
                try:
                    record["approval_date"] = time.strftime("%Y-%m-%d", time.strptime(date_str, fmt))
                    break
                except ValueError:
                    continue
            else:
                record["approval_date"] = None  # 无法解析则置空

        # 确保所有 SQL 占位符都有值，避免批量插入时 KeyError
        for field in [
            "english_name", "manufacturer", "dosage_form", "specification",
            "indication", "drug_category", "approval_date", "validity_period"
        ]:
            record.setdefault(field, None)

        records.append(record)

    logger.info(f"预处理: {len(records)} 条有效记录, {skipped} 条跳过")

    # 批量插入
    count = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            count += len(batch)
            progress = min(count, len(records))
            pct = progress / len(records) * 100
            logger.info(f"  药品导入进度: {progress}/{len(records)} ({pct:.1f}%)")
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
    logger.info(f"✓ 药品导入完成: 共 {count} 条")
    return count


# ======================== 构建关联关系 ========================

def build_relations(conn: pymysql.Connection) -> int:
    """
    根据药品的「适应症」文本，自动匹配疾病名称，建立多对多关联。

    匹配策略:
    1. 精确包含匹配: 适应症文本中包含疾病名称
    2. 仅匹配名称长度 >= 2 的疾病（避免单字误匹配）
    3. 排除过于宽泛的词（如"病"、"症"单独出现时）
    """
    cursor = conn.cursor()

    # 1. 获取所有疾病 (id, disease_name)
    cursor.execute("SELECT `id`, `disease_name` FROM `diseases` WHERE `disease_name` IS NOT NULL")
    diseases = cursor.fetchall()
    logger.info(f"从数据库加载 {len(diseases)} 种疾病")

    # 过滤掉名称过短或过于宽泛的疾病
    ignore_words = {"病", "症", "炎", "癌", "瘤", "热", "痛", "毒", "菌"}
    valid_diseases = []
    for d in diseases:
        name = d["disease_name"].strip()
        if len(name) >= 2 and name not in ignore_words:
            valid_diseases.append((d["id"], name))
    logger.info(f"有效匹配疾病: {len(valid_diseases)} 种（已过滤短名称）")

    # 2. 获取所有药品 (id, drug_name, indication)
    cursor.execute(
        "SELECT `id`, `drug_name`, `indication` FROM `drugs` "
        "WHERE `indication` IS NOT NULL AND `indication` != ''"
    )
    drugs = cursor.fetchall()
    logger.info(f"从数据库加载 {len(drugs)} 种有适应症的药品")

    # 3. 匹配
    relations = []  # [(disease_id, drug_id)]
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
                # 兼容症状关键词匹配，增强关联覆盖
                cursor.execute(
                    "SELECT `symptoms` FROM `diseases` WHERE `id` = %s",
                    (disease_id,)
                )
                disease_row = cursor.fetchone()
                if disease_row:
                    symptoms_text = disease_row.get("symptoms") or ""
                    for term in re.split(r"[，,\s\|；;]+", symptoms_text):
                        term = term.strip()
                        if len(term) >= 2 and (term in indication or term.lower() in indication_lower):
                            match = True
                            break

            if match:
                relations.append((disease_id, drug_id))

    logger.info(f"匹配到 {len(relations)} 条疾病-药品关联")

    # 4. 批量插入关联表
    if not relations:
        logger.warning("未匹配到任何关联关系")
        cursor.close()
        return 0

    insert_sql = """
        INSERT IGNORE INTO `disease_drug_relation`
            (`disease_id`, `drug_id`, `match_source`)
        VALUES
            (%s, %s, 'indication')
    """

    count = 0
    for i in range(0, len(relations), BATCH_SIZE):
        batch = relations[i:i + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            count += cursor.rowcount
            progress = min(i + BATCH_SIZE, len(relations))
            logger.info(f"  关联导入进度: {progress}/{len(relations)}")
        except pymysql.Error as e:
            logger.error(f"  关联批量插入出错: {e}")
            # 逐条重试
            for rel in batch:
                try:
                    cursor.execute(insert_sql, rel)
                    conn.commit()
                    count += 1
                except pymysql.Error:
                    pass

    cursor.close()
    logger.info(f"✓ 关联关系导入完成: 共 {count} 条")
    return count


# ======================== 统计报告 ========================

def print_statistics(conn: pymysql.Connection):
    """打印最终统计信息"""
    cursor = conn.cursor()

    stats = {}
    for table in ["diseases", "drugs", "disease_drug_relation"]:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
        stats[table] = cursor.fetchone()["cnt"]

    cursor.close()

    print("\n" + "=" * 60)
    print("  📊 导入统计报告")
    print("=" * 60)
    print(f"  疾病记录:          {stats['diseases']:>6} 条")
    print(f"  药品记录:          {stats['drugs']:>6} 条")
    print(f"  疾病-药品关联:     {stats['disease_drug_relation']:>6} 条")
    print("=" * 60)

    # 展示一些关联样例
    cursor2 = conn.cursor()
    cursor2.execute(
        "SELECT d.disease_name, dr.drug_name, dr.approval_number "
        "FROM disease_drug_relation r "
        "JOIN diseases d ON r.disease_id = d.id "
        "JOIN drugs dr ON r.drug_id = dr.id "
        "ORDER BY d.disease_name "
        "LIMIT 10"
    )
    samples = cursor2.fetchall()
    cursor2.close()

    if samples:
        print("\n  🔗 关联关系样例（前 10 条）:")
        print(f"  {'疾病名称':<20} {'药品名称':<20} {'批准文号'}")
        print(f"  {'-'*20} {'-'*20} {'-'*20}")
        for s in samples:
            name = s["disease_name"][:18]
            drug = s["drug_name"][:18] if s["drug_name"] else "N/A"
            code = s["approval_number"][:18] if s["approval_number"] else "N/A"
            print(f"  {name:<20} {drug:<20} {code}")
        print()


# ======================== 主入口 ========================

def main():
    print("=" * 60)
    print("  CSV → MySQL 数据导入工具")
    print("=" * 60)
    start_time = time.time()

    # 1. 读取 CSV
    print("\n[1/5] 读取 CSV 文件...")
    disease_rows = read_csv(DISEASES_CSV)
    drug_rows = read_csv(DRUGS_CSV)

    if not disease_rows and not drug_rows:
        logger.error("两个 CSV 文件均为空或不存在，退出")
        return

    # 2. 连接 MySQL
    print("\n[2/5] 连接 MySQL 数据库...")
    conn = get_connection()

    # 3. 确保表结构存在
    print("\n[3/5] 检查数据库表结构...")
    execute_init_sql(conn)

    # 4. 导入数据
    print(f"\n[4/5] 导入数据 (疾病 {len(disease_rows)} 条, 药品 {len(drug_rows)} 条)...")

    disease_count = import_diseases(conn, disease_rows)
    drug_count = import_drugs(conn, drug_rows)

    # 5. 构建关联关系
    print("\n[5/5] 构建疾病-药品关联关系...")
    relation_count = build_relations(conn)

    # 打印统计
    print_statistics(conn)

    elapsed = time.time() - start_time
    print(f"  ⏱ 总耗时: {elapsed:.1f} 秒")
    print("=" * 60)

    conn.close()
    logger.info("数据库连接已关闭")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，退出。")
    except Exception as e:
        logger.error(f"运行异常: {e}", exc_info=True)
