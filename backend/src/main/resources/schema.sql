-- ============================================================
--  医疗疾病数据分析系统 - 新增表 + 测试数据
--  引擎: InnoDB  |  字符集: utf8mb4
-- ============================================================

USE `medical_data`;

-- ============================================================
--  药典知识片段（用户提供的整理文档，供 AI 检索）
-- ============================================================
CREATE TABLE IF NOT EXISTS `pharmacopoeia_chunks` (
    `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `source_key`    CHAR(64)        NOT NULL                COMMENT '来源与条目组合的SHA-256，供幂等导入',
    `source_title`  VARCHAR(255)    NOT NULL                COMMENT '来源文档标题',
    `edition`       VARCHAR(100)    NOT NULL                COMMENT '药典版本',
    `volume`        VARCHAR(100)    NOT NULL                COMMENT '药典部次',
    `section`       VARCHAR(150)    NOT NULL                COMMENT '知识片段类型',
    `entry_name`    VARCHAR(255)    NOT NULL                COMMENT '条目名称',
    `content`       MEDIUMTEXT      NOT NULL                COMMENT '整理后的知识内容',
    `keywords`      TEXT            DEFAULT NULL            COMMENT '检索主题词，以分号分隔',
    `source_pages`  VARCHAR(100)    DEFAULT NULL            COMMENT '药典印刷页码',
    `source_note`   TEXT            DEFAULT NULL            COMMENT '来源可靠性与使用边界',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_pharmacopoeia_source_key` (`source_key`),
    KEY `idx_pharmacopoeia_entry` (`entry_name`),
    KEY `idx_pharmacopoeia_volume_section` (`volume`, `section`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='药典AI检索知识片段';

-- ============================================================
--  1. 用户表
-- ============================================================
DROP TABLE IF EXISTS `patient_doctor`;
DROP TABLE IF EXISTS `medical_records`;
DROP TABLE IF EXISTS `self_tests`;
DROP TABLE IF EXISTS `patients`;
DROP TABLE IF EXISTS `doctors`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
    `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `username`    VARCHAR(50)     NOT NULL                COMMENT '用户名',
    `password`    VARCHAR(255)    NOT NULL                COMMENT 'BCrypt加密密码',
    `role`        TINYINT         NOT NULL DEFAULT 3      COMMENT '1管理员 2医生 3患者',
    `real_name`   VARCHAR(50)     DEFAULT NULL            COMMENT '真实姓名',
    `phone`       VARCHAR(20)     DEFAULT NULL            COMMENT '手机号',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================================
--  2. 患者表
-- ============================================================
CREATE TABLE `patients` (
    `id`              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `user_id`         INT UNSIGNED    NOT NULL              COMMENT '关联用户ID',
    `gender`          TINYINT         DEFAULT 0             COMMENT '0未知 1男 2女',
    `birth_date`      DATE            DEFAULT NULL          COMMENT '出生日期',
    `height`          DECIMAL(5,1)    DEFAULT NULL          COMMENT '身高cm',
    `weight`          DECIMAL(5,1)    DEFAULT NULL          COMMENT '体重kg',
    `allergy_history` TEXT            DEFAULT NULL          COMMENT '过敏史',
    `address`         VARCHAR(255)    DEFAULT NULL          COMMENT '地址',
    `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_id` (`user_id`),
    CONSTRAINT `fk_patient_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者信息表';

-- ============================================================
--  3. 医生表
-- ============================================================
CREATE TABLE `doctors` (
    `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `user_id`     INT UNSIGNED    NOT NULL              COMMENT '关联用户ID',
    `department`  VARCHAR(100)    DEFAULT NULL           COMMENT '科室',
    `title`       VARCHAR(50)     DEFAULT NULL           COMMENT '职称',
    `hospital`    VARCHAR(200)    DEFAULT NULL           COMMENT '所属医院',
    `is_verified` TINYINT         NOT NULL DEFAULT 0     COMMENT '0待审核 1已通过',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_doctor_user` (`user_id`),
    CONSTRAINT `fk_doctor_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='医生信息表';

-- ============================================================
--  4. 患者-医生关联表
-- ============================================================
CREATE TABLE `patient_doctor` (
    `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `patient_id`  INT UNSIGNED    NOT NULL,
    `doctor_id`   INT UNSIGNED    NOT NULL,
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_patient_doctor` (`patient_id`, `doctor_id`),
    CONSTRAINT `fk_pd_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pd_doctor`  FOREIGN KEY (`doctor_id`)  REFERENCES `doctors`(`id`)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者-医生关联';

-- ============================================================
--  5. 病历表
-- ============================================================
CREATE TABLE `medical_records` (
    `id`                INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `patient_id`        INT UNSIGNED    NOT NULL,
    `doctor_id`         INT UNSIGNED    NOT NULL,
    `visit_date`        DATE            NOT NULL            COMMENT '就诊日期',
    `chief_complaint`   TEXT            DEFAULT NULL        COMMENT '主诉',
    `diagnosis`         VARCHAR(255)    DEFAULT NULL        COMMENT '诊断(疾病名称)',
    `diagnosis_detail`  TEXT            DEFAULT NULL        COMMENT '诊断详情',
    `prescription`      JSON            DEFAULT NULL        COMMENT '处方JSON [{drugId,dosage}]',
    `status`            TINYINT         NOT NULL DEFAULT 1  COMMENT '1初诊 2复诊 3痊愈',
    `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_patient` (`patient_id`),
    KEY `idx_doctor` (`doctor_id`),
    CONSTRAINT `fk_record_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`),
    CONSTRAINT `fk_record_doctor`  FOREIGN KEY (`doctor_id`)  REFERENCES `doctors`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='病历表';

-- ============================================================
--  6. 自测表
-- ============================================================
CREATE TABLE `self_tests` (
    `id`              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `patient_id`      INT UNSIGNED    NOT NULL,
    `input_symptoms`  TEXT            NOT NULL             COMMENT '输入的症状',
    `matched_disease` VARCHAR(255)    DEFAULT NULL         COMMENT '匹配的疾病',
    `confidence`      DECIMAL(5,2)    DEFAULT NULL         COMMENT '匹配度%',
    `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_test_patient` (`patient_id`),
    CONSTRAINT `fk_test_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者自测记录';


-- ============================================================
--  测试数据 (密码均为 123456 的BCrypt值)
-- ============================================================

-- 用户: admin/123456, doctor_zhang/123456, doctor_li/123456, patient1~5/123456
INSERT INTO `users` (`id`, `username`, `password`, `role`, `real_name`, `phone`) VALUES
(1,  'admin',         '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 1, '系统管理员',  '13800000000'),
(2,  'doctor_zhang',  '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 2, '张医生',     '13800000001'),
(3,  'doctor_li',     '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 2, '李医生',     '13800000002'),
(4,  'patient_wang',  '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 3, '王小明',     '13900000001'),
(5,  'patient_li',    '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 3, '李小红',     '13900000002'),
(6,  'patient_zhao',  '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 3, '赵大勇',     '13900000003'),
(7,  'patient_chen',  '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 3, '陈美丽',     '13900000004'),
(8,  'patient_liu',   '$2b$12$FQ2816j23h5PF0qZC6VQ3.Pt8dh1OCwmP0pLRK9ncNM8oL8yBIt1S', 3, '刘健康',     '13900000005');

-- 患者信息
INSERT INTO `patients` (`id`, `user_id`, `gender`, `birth_date`, `height`, `weight`, `allergy_history`, `address`) VALUES
(1, 4, 1, '1990-05-15', 175.0, 70.0, '青霉素过敏',    '北京市朝阳区'),
(2, 5, 2, '1985-08-20', 162.0, 55.0, NULL,           '上海市浦东新区'),
(3, 6, 1, '1978-03-10', 180.0, 85.0, '磺胺类药物过敏', '广州市天河区'),
(4, 7, 2, '1995-11-25', 158.0, 48.0, NULL,           '深圳市南山区'),
(5, 8, 1, '2000-01-08', 172.0, 65.0, '花粉过敏',      '成都市武侯区');

-- 医生信息
INSERT INTO `doctors` (`id`, `user_id`, `department`, `title`, `hospital`, `is_verified`) VALUES
(1, 2, '内科',   '主任医师',   '北京协和医院',   1),
(2, 3, '心血管内科', '副主任医师', '上海瑞金医院', 1);

-- 患者-医生关联
INSERT INTO `patient_doctor` (`patient_id`, `doctor_id`) VALUES
(1, 1), (2, 1), (3, 1), (4, 2), (5, 2);

-- 病历
INSERT INTO `medical_records` (`patient_id`, `doctor_id`, `visit_date`, `chief_complaint`, `diagnosis`, `diagnosis_detail`, `prescription`, `status`) VALUES
(1, 1, '2025-12-01', '发热咳嗽3天，体温38.5°C', '流行性感冒', '甲型流感病毒检测阳性',
    '[{"drugId":320,"dosage":"口服 每次4粒 每日3次"}]', 1),
(2, 1, '2025-12-05', '头晕头痛一周，血压偏高', '高血压', '血压160/100mmHg',
    '[{"drugId":73,"dosage":"口服 每次1片(5mg) 每日1次"}]', 1),
(3, 1, '2025-12-10', '胸闷气短，活动后加重', '冠心病', '心电图示ST段压低',
    '[{"drugId":66,"dosage":"口服 每次1片(100mg) 每日1次"},{"drugId":58,"dosage":"口服 每次1片(10mg) 每晚1次"}]', 2),
(4, 2, '2025-12-15', '心悸气促，下肢水肿', '高血压', '血压150/95mmHg，心功能II级',
    '[{"drugId":73,"dosage":"口服 每次1片(5mg) 每日1次"}]', 1),
(5, 2, '2026-01-03', '关节疼痛晨僵2月', '类风湿性关节炎', '类风湿因子阳性，ESR升高',
    '[{"drugId":67,"dosage":"口服 每次1粒(0.2g) 每日1次"}]', 1),
(1, 1, '2026-01-10', '感冒复诊，症状好转', '流行性感冒', '体温正常，咳嗽减轻',
    '[{"drugId":320,"dosage":"口服 每次4粒 每日3次"}]', 3),
(2, 1, '2026-01-15', '血压控制复查', '高血压', '血压130/85mmHg，控制良好',
    '[{"drugId":73,"dosage":"口服 每次1片(5mg) 每日1次"}]', 2),
(3, 1, '2026-01-20', '胃部不适，上腹隐痛', '胃炎', '胃镜示浅表性胃炎',
    '[{"drugId":140,"dosage":"口服 每次1粒 每日1次"}]', 1);

-- 自测记录
INSERT INTO `self_tests` (`patient_id`, `input_symptoms`, `matched_disease`, `confidence`) VALUES
(1, '发热 咳嗽 头痛 肌肉酸痛', '流行性感冒', 85.50),
(2, '头晕 头痛 视力模糊', '高血压', 78.30),
(4, '关节疼痛 晨僵 疲乏', '类风湿性关节炎', 72.00);
