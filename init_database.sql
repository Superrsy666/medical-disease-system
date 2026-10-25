-- ============================================================
--  医疗疾病系统 - 数据库建表脚本
--  引擎: InnoDB  |  字符集: utf8mb4
-- ============================================================

-- 如果数据库不存在则创建
CREATE DATABASE IF NOT EXISTS `medical_data`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `medical_data`;


-- ============================================================
--  1. 疾病表 (diseases)
-- ============================================================

DROP TABLE IF EXISTS `diseases`;

CREATE TABLE `diseases` (
    `id`            INT UNSIGNED    NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `disease_name`  VARCHAR(255)    NOT NULL                 COMMENT '疾病名称（中文）',
    `icd_code`      VARCHAR(50)     DEFAULT NULL             COMMENT 'ICD-11 编码',
    `category_path` VARCHAR(500)    DEFAULT NULL             COMMENT '上级分类路径，如: 肿瘤 > 乳腺肿瘤 > 乳腺癌',
    `description`   TEXT            DEFAULT NULL             COMMENT '疾病定义/描述',
    `symptoms`      VARCHAR(1000)   DEFAULT NULL             COMMENT '症状关键词，多个用逗号分隔',
    `excludes`      TEXT            DEFAULT NULL             COMMENT '排除项（需要区分的相似疾病）',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                            COMMENT '创建时间',
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP
                                                            COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_disease_name` (`disease_name`),
    KEY `idx_icd_code` (`icd_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='疾病信息表（WHO ICD-11）';


-- ============================================================
--  2. 药品表 (drugs)
-- ============================================================

DROP TABLE IF EXISTS `drugs`;

CREATE TABLE `drugs` (
    `id`               INT UNSIGNED    NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `drug_name`        VARCHAR(255)    NOT NULL                 COMMENT '药品名称（中文通用名）',
    `english_name`     VARCHAR(500)    DEFAULT NULL             COMMENT '英文名称',
    `approval_number`  VARCHAR(100)    NOT NULL                 COMMENT '批准文号，如: 国药准字H10983027',
    `manufacturer`     VARCHAR(500)    DEFAULT NULL             COMMENT '生产单位（企业名称）',
    `dosage_form`      VARCHAR(100)    DEFAULT NULL             COMMENT '剂型，如: 片剂、胶囊、注射液',
    `specification`    VARCHAR(255)    DEFAULT NULL             COMMENT '规格，如: 0.5g、10mg*20片',
    `indication`       TEXT            DEFAULT NULL             COMMENT '适应症（用于治疗什么疾病）',
    `drug_category`    VARCHAR(100)    DEFAULT NULL             COMMENT '药品分类，如: 化学药品、中成药',
    `approval_date`    DATE            DEFAULT NULL             COMMENT '批准日期',
    `validity_period`  VARCHAR(100)    DEFAULT NULL             COMMENT '有效期',
    `created_at`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                                COMMENT '创建时间',
    `updated_at`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP
                                                                COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_drug_name` (`drug_name`),
    UNIQUE KEY `uk_approval_number` (`approval_number`),
    KEY `idx_manufacturer` (`manufacturer`(100)),
    KEY `idx_drug_category` (`drug_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='药品信息表（NMPA 国家药监局）';


-- ============================================================
--  3. 疾病-药品关联中间表 (disease_drug_relation)
--     多对多关系: 一种疾病可对应多种推荐药品,
--                 一种药品也可适用于多种疾病
-- ============================================================

DROP TABLE IF EXISTS `disease_drug_relation`;

CREATE TABLE `disease_drug_relation` (
    `id`            INT UNSIGNED    NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `disease_id`    INT UNSIGNED    NOT NULL                 COMMENT '疾病 ID（关联 diseases 表）',
    `drug_id`       INT UNSIGNED    NOT NULL                 COMMENT '药品 ID（关联 drugs 表）',
    `match_source`  VARCHAR(50)     DEFAULT 'indication'     COMMENT '关联来源: indication=适应症匹配',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                            COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_disease_drug` (`disease_id`, `drug_id`),
    KEY `idx_disease_id` (`disease_id`),
    KEY `idx_drug_id` (`drug_id`),

    -- 外键约束
    CONSTRAINT `fk_relation_disease`
        FOREIGN KEY (`disease_id`) REFERENCES `diseases` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT `fk_relation_drug`
        FOREIGN KEY (`drug_id`) REFERENCES `drugs` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='疾病-药品关联表（多对多）';


-- ============================================================
--  4. 常用查询视图（可选）
-- ============================================================

-- 查看某种疾病的所有推荐药品
-- SELECT d.disease_name, dr.drug_name, dr.approval_number, dr.manufacturer
-- FROM diseases d
-- JOIN disease_drug_relation r ON d.id = r.disease_id
-- JOIN drugs dr ON r.drug_id = dr.id
-- WHERE d.disease_name = '高血压';

-- 查看某种药品适用于哪些疾病
-- SELECT dr.drug_name, d.disease_name, d.icd_code
-- FROM drugs dr
-- JOIN disease_drug_relation r ON dr.id = r.drug_id
-- JOIN diseases d ON r.disease_id = d.id
-- WHERE dr.drug_name LIKE '%阿莫西林%';
