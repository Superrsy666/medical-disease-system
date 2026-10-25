# -*- coding: utf-8 -*-
"""导入用户提供的药典要点 DOCX，生成可重复执行的知识库导入。"""
import argparse
import hashlib
import re
from pathlib import Path

import pymysql
from docx import Document

from config import DB_CONFIG


SOURCE_TITLE = "《中国药典》2025年版（一部·三部）类风湿关节炎相关要点提取"
EDITION = "2025年版"
SOURCE_NOTE = (
    "来源为用户提供的类风湿关节炎要点提取 DOCX；文档注明部分内容来自扫描件 OCR "
    "且部分内容由 AI 生成。该摘要仅供知识检索，正式引用前须复核药典原页；"
    "不构成诊断或个体化用药建议，生物制品适应证与用法以现行说明书和医生意见为准。"
)

HERB_KEYWORDS = {
    "制川乌": "类风湿关节炎;RA;寒湿痹;关节冷痛;遇寒加重;风寒湿痹;有毒;孕妇慎用",
    "木瓜": "类风湿关节炎;RA;湿痹;关节酸重疼痛;拘挛;舒筋活络",
    "威灵仙": "类风湿关节炎;RA;风湿痹痛;关节冷痛;遇寒加重;肢体麻木;筋脉拘挛;屈伸不利",
    "独活": "类风湿关节炎;RA;寒湿痹;关节冷痛;遇寒加重;腰膝疼痛;风寒湿痹",
    "穿山龙": "类风湿关节炎;RA;风湿痹病;关节肿胀;关节红肿;疼痛麻木",
    "络石藤": "类风湿关节炎;RA;湿热痹;关节红肿热痛;关节热痛;筋脉拘挛;腰膝酸痛",
    "秦艽": "类风湿关节炎;RA;风湿痹痛;关节红肿热痛;关节热痛;筋脉拘挛;骨节酸痛",
    "徐长卿": "类风湿关节炎;RA;风湿痹痛;关节冷痛;遇寒加重;腰痛;止痛",
    "桑枝": "类风湿关节炎;RA;风湿痹病;肩臂关节酸痛麻木",
    "桑寄生": "类风湿关节炎;RA;肝肾亏虚;腰膝酸软;筋骨无力",
    "豨莶草": "类风湿关节炎;RA;风湿痹痛;腰膝酸软;四肢麻痹",
    "蕲蛇": "类风湿关节炎;RA;风湿顽痹;麻木拘挛;有毒",
}

PRODUCTS = (
    ("注射用阿达木单抗", "阿达木单抗", "三部", "生物制品品种正文", "353–356",
     "类风湿关节炎;RA;TNF-α;阿达木单抗;生物制品;生物学活性;储藏"),
    ("注射用英夫利西单抗", "英夫利西单抗", "三部", "生物制品品种正文", "353–356",
     "类风湿关节炎;RA;TNF-α;英夫利西单抗;生物制品;生物学活性;储藏"),
    ("利妥昔单抗注射液", "利妥昔单抗", "三部", "生物制品品种正文", "365–368",
     "类风湿关节炎;RA;CD20;利妥昔单抗;难治性;生物制品;生物学活性;储藏"),
)


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS pharmacopoeia_chunks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_key CHAR(64) NOT NULL,
    source_title VARCHAR(255) NOT NULL,
    edition VARCHAR(100) NOT NULL,
    volume VARCHAR(100) NOT NULL,
    section VARCHAR(150) NOT NULL,
    entry_name VARCHAR(255) NOT NULL,
    content MEDIUMTEXT NOT NULL,
    keywords TEXT DEFAULT NULL,
    source_pages VARCHAR(100) DEFAULT NULL,
    source_note TEXT DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_pharmacopoeia_source_key (source_key),
    KEY idx_pharmacopoeia_entry (entry_name),
    KEY idx_pharmacopoeia_volume_section (volume, section)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='药典AI检索知识片段'
"""

UPSERT = """
INSERT INTO pharmacopoeia_chunks
    (source_key, source_title, edition, volume, section, entry_name,
     content, keywords, source_pages, source_note)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    source_title = VALUES(source_title),
    edition = VALUES(edition),
    volume = VALUES(volume),
    section = VALUES(section),
    entry_name = VALUES(entry_name),
    content = VALUES(content),
    keywords = VALUES(keywords),
    source_pages = VALUES(source_pages),
    source_note = VALUES(source_note)
"""


def _paragraphs(document):
    return [paragraph.text.strip() for paragraph in document.paragraphs]


def _find_paragraph(paragraphs, marker):
    for index, text in enumerate(paragraphs):
        if marker in text:
            return index, text
    raise ValueError(f"DOCX is missing expected section: {marker}")


def _record(volume, section, entry_name, content, keywords, source_pages=None):
    source_key = hashlib.sha256(
        f"{SOURCE_TITLE}|{volume}|{section}|{entry_name}".encode("utf-8")
    ).hexdigest()
    return (
        source_key, SOURCE_TITLE, EDITION, volume, section, entry_name,
        content, keywords, source_pages, SOURCE_NOTE,
    )


def extract_chunks(path):
    document = Document(path)
    paragraphs = _paragraphs(document)
    chunks = []

    if len(document.tables) < 3:
        raise ValueError("DOCX is missing the verified materia-medica table")

    herb_table = document.tables[2]
    for row in herb_table.rows[1:]:
        cells = [cell.text.strip() for cell in row.cells]
        if len(cells) < 5:
            raise ValueError("Unexpected materia-medica table row")
        match = re.fullmatch(r"(.+?)（(\d+)）", cells[0])
        if not match:
            raise ValueError(f"Unexpected materia-medica entry: {cells[0]}")
        name, page = match.groups()
        content = (
            f"性味归经：{cells[1]}；功能主治：{cells[2]}；"
            f"用法用量：{cells[3]}；关键质控/注意：{cells[4]}"
        )
        chunks.append(_record(
            "一部", "中药材及饮片", name, content,
            HERB_KEYWORDS.get(name, "类风湿关节炎;RA;风湿痹痛"), page,
        ))

    for entry_name, marker, volume, section, pages, keywords in PRODUCTS:
        index, heading = _find_paragraph(paragraphs, marker)
        details = paragraphs[index + 1:index + 5]
        if len(details) != 4 or not all(details):
            raise ValueError(f"Incomplete pharmacopoeia monograph: {entry_name}")
        content = "；".join([heading, *details])
        chunks.append(_record(
            volume, section, entry_name, content, keywords, pages,
        ))

    _, monograph = _find_paragraph(paragraphs, "人用重组单克隆抗体制品总论")
    chunks.append(_record(
        "三部", "相关总论", "人用重组单克隆抗体制品总论",
        monograph,
        "类风湿关节炎;RA;单克隆抗体;重组抗体;质量控制;CQA",
        "14–16",
    ))

    _, mapping = _find_paragraph(paragraphs, "表型→标准映射")
    chunks.append(_record(
        "一部·三部", "RA检索映射", "类风湿关节炎相关表型映射",
        mapping,
        "类风湿关节炎;RA;寒湿痹;湿热痹;肝肾亏虚;关节冷痛;"
        "关节红肿热痛;腰膝酸软;TNF-α;CD20",
    ))

    _, scope = _find_paragraph(paragraphs, "知识库口径")
    chunks.append(_record(
        "一部·三部", "收载范围说明", "文档收载范围与未收载内容",
        scope,
        "类风湿关节炎;RA;收载范围;雷公藤;白芍总苷;托珠单抗;依那西普",
    ))

    _, verification = _find_paragraph(paragraphs, "定位复核")
    chunks.append(_record(
        "一部·三部", "来源与复核提示", "OCR识别与正式引用复核",
        verification,
        "类风湿关节炎;RA;OCR;识别误差;原文核对;正式引用",
    ))

    if len(document.tables) >= 4 and document.tables[3].rows:
        boundary = document.tables[3].rows[0].cells[0].text.strip()
        chunks.append(_record(
            "一部·三部", "使用边界", "药典知识使用边界",
            boundary,
            "药典;诊疗建议;药品说明书;医生意见;用药安全",
        ))

    return chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path, help="要导入的药典要点 DOCX 文件")
    args = parser.parse_args()
    if not args.document.is_file():
        parser.error(f"DOCX file not found: {args.document}")

    chunks = extract_chunks(args.document)
    connection = pymysql.connect(**DB_CONFIG, autocommit=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE)
            cursor.executemany(UPSERT, chunks)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(f"Imported {len(chunks)} pharmacopoeia knowledge chunks from {args.document.name}")


if __name__ == "__main__":
    main()
