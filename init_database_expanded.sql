-- ============================================================
--  医疗疾病系统 - 扩展版数据库建表脚本
--  新增字段以容纳 xlsx 中的丰富数据
-- ============================================================

CREATE DATABASE IF NOT EXISTS `medical_data`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `medical_data`;

-- ============================================================
--  1. 疾病表 (diseases) — 扩展版
-- ============================================================

DROP TABLE IF EXISTS `disease_drug_relation`;
DROP TABLE IF EXISTS `diseases`;

CREATE TABLE `diseases` (
    `id`                       INT UNSIGNED    NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `disease_name`             VARCHAR(255)    NOT NULL                 COMMENT '疾病名称',
    `english_name`             VARCHAR(500)    DEFAULT NULL             COMMENT '英文名称',
    `aliases`                  VARCHAR(500)    DEFAULT NULL             COMMENT '其它名称/别名',
    `icd_code`                 VARCHAR(50)     DEFAULT NULL             COMMENT 'ICD编码',
    `department`               VARCHAR(255)    DEFAULT NULL             COMMENT '所属科室',
    `category_path`            VARCHAR(500)    DEFAULT NULL             COMMENT '上级分类路径',
    `description`              TEXT            DEFAULT NULL             COMMENT '疾病描述/定义',
    `affected_area`            VARCHAR(255)    DEFAULT NULL             COMMENT '发病部位',
    `symptoms`                 TEXT            DEFAULT NULL             COMMENT '典型症状',
    `symptoms_overview`        TEXT            DEFAULT NULL             COMMENT '症状总述',
    `symptoms_detail`          TEXT            DEFAULT NULL             COMMENT '症状详述',
    `etiology`                 TEXT            DEFAULT NULL             COMMENT '主要病因',
    `etiology_overview`        TEXT            DEFAULT NULL             COMMENT '病因概述',
    `risk_factors`             TEXT            DEFAULT NULL             COMMENT '危险因素',
    `examination`              TEXT            DEFAULT NULL             COMMENT '检查项目',
    `expected_examination`     TEXT            DEFAULT NULL             COMMENT '预计检查',
    `lab_examination`          TEXT            DEFAULT NULL             COMMENT '实验室检查',
    `imaging_examination`      TEXT            DEFAULT NULL             COMMENT '影像学检查',
    `diagnostic_basis`         TEXT            DEFAULT NULL             COMMENT '诊断依据',
    `diagnostic_criteria`      TEXT            DEFAULT NULL             COMMENT '诊断标准',
    `differential_diagnosis`   TEXT            DEFAULT NULL             COMMENT '鉴别诊断',
    `excludes`                 TEXT            DEFAULT NULL             COMMENT '排除项',
    `infectiousness`           TEXT            DEFAULT NULL             COMMENT '传染性',
    `infection_source`         TEXT            DEFAULT NULL             COMMENT '传染源',
    `transmission_route`       TEXT            DEFAULT NULL             COMMENT '传播途径',
    `incidence_rate`           TEXT            DEFAULT NULL             COMMENT '发病率',
    `incidence_trend`          VARCHAR(500)    DEFAULT NULL             COMMENT '发病趋势',
    `susceptible_population`   TEXT            DEFAULT NULL             COMMENT '易感人群',
    `hereditary`               VARCHAR(100)    DEFAULT NULL             COMMENT '遗传性',
    `medical_insurance`        VARCHAR(100)    DEFAULT NULL             COMMENT '是否医保',
    `tcm_related`              VARCHAR(500)    DEFAULT NULL             COMMENT '相关中医疾病',
    `treatment_prognosis`      TEXT            DEFAULT NULL             COMMENT '治疗预后',
    `general_treatment`        TEXT            DEFAULT NULL             COMMENT '一般治疗',
    `drug_treatment`           TEXT            DEFAULT NULL             COMMENT '药物治疗',
    `prevention`               TEXT            DEFAULT NULL             COMMENT '预防治疗',
    `important_note`           TEXT            DEFAULT NULL             COMMENT '重要提醒',
    `detail_url`               VARCHAR(500)    DEFAULT NULL             COMMENT '详情链接',
    `created_at`               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP         COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_disease_name` (`disease_name`),
    KEY `idx_icd_code` (`icd_code`),
    KEY `idx_department` (`department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='疾病信息表（扩展版）';


-- ============================================================
--  2. 药品表 (drugs) — 扩展版
-- ============================================================

DROP TABLE IF EXISTS `drugs`;

CREATE TABLE `drugs` (
    `id`                      INT UNSIGNED    NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `drug_name`               VARCHAR(255)    NOT NULL                 COMMENT '药品通用名',
    `english_name`            VARCHAR(500)    DEFAULT NULL             COMMENT '英文名称',
    `pinyin`                  VARCHAR(500)    DEFAULT NULL             COMMENT '汉语拼音',
    `approval_number`         VARCHAR(100)    NOT NULL                 COMMENT '批准文号',
    `manufacturer`            VARCHAR(500)    DEFAULT NULL             COMMENT '生产厂家',
    `dosage_form`             VARCHAR(100)    DEFAULT NULL             COMMENT '剂型',
    `specification`           TEXT            DEFAULT NULL             COMMENT '规格',
    `drug_category`           VARCHAR(100)    DEFAULT NULL             COMMENT '药品分类',
    `prescription_type`       VARCHAR(100)    DEFAULT NULL             COMMENT '处方类型',
    `medical_insurance`       VARCHAR(100)    DEFAULT NULL             COMMENT '医保类型',
    `reference_price`         VARCHAR(255)    DEFAULT NULL             COMMENT '参考价格',
    `ingredients`             TEXT            DEFAULT NULL             COMMENT '成分',
    `indication`              TEXT            DEFAULT NULL             COMMENT '适应症',
    `usage_dosage`            TEXT            DEFAULT NULL             COMMENT '用法用量',
    `adverse_reactions`       TEXT            DEFAULT NULL             COMMENT '不良反应',
    `contraindications`       TEXT            DEFAULT NULL             COMMENT '禁忌',
    `precautions`             TEXT            DEFAULT NULL             COMMENT '注意事项',
    `drug_interactions`       TEXT            DEFAULT NULL             COMMENT '药物相互作用',
    `pharmacological_action`  TEXT            DEFAULT NULL             COMMENT '药理作用',
    `storage`                 VARCHAR(500)    DEFAULT NULL             COMMENT '贮藏方法',
    `validity_period`         VARCHAR(100)    DEFAULT NULL             COMMENT '有效期',
    `executive_standard`      VARCHAR(500)    DEFAULT NULL             COMMENT '执行标准',
    `drug_intro`              TEXT            DEFAULT NULL             COMMENT '药品简介',
    `approval_date`           DATE            DEFAULT NULL             COMMENT '批准日期',
    `detail_url`              VARCHAR(500)    DEFAULT NULL             COMMENT '详情链接',
    `created_at`              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP         COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_drug_name` (`drug_name`),
    UNIQUE KEY `uk_approval_number` (`approval_number`),
    KEY `idx_manufacturer` (`manufacturer`(100)),
    KEY `idx_drug_category` (`drug_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='药品信息表（扩展版）';


-- ============================================================
--  3. 疾病-药品关联中间表
-- ============================================================

DROP TABLE IF EXISTS `disease_drug_relation`;

CREATE TABLE `disease_drug_relation` (
    `id`            INT UNSIGNED    NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `disease_id`    INT UNSIGNED    NOT NULL                 COMMENT '疾病ID',
    `drug_id`       INT UNSIGNED    NOT NULL                 COMMENT '药品ID',
    `match_source`  VARCHAR(50)     DEFAULT 'indication'     COMMENT '关联来源',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_disease_drug` (`disease_id`, `drug_id`),
    KEY `idx_disease_id` (`disease_id`),
    KEY `idx_drug_id` (`drug_id`),
    CONSTRAINT `fk_relation_disease`
        FOREIGN KEY (`disease_id`) REFERENCES `diseases` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_relation_drug`
        FOREIGN KEY (`drug_id`) REFERENCES `drugs` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='疾病-药品关联表（多对多）';
