package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("drugs")
public class Drug {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private String drugName;
    private String englishName;
    private String pinyin;
    private String approvalNumber;
    private String manufacturer;
    private String dosageForm;
    private String specification;
    private String drugCategory;
    private String prescriptionType;
    private String medicalInsurance;
    private String referencePrice;
    private String ingredients;
    private String indication;
    private String usageDosage;
    private String adverseReactions;
    private String contraindications;
    private String precautions;
    private String drugInteractions;
    private String pharmacologicalAction;
    private String storage;
    private String validityPeriod;
    private String executiveStandard;
    private String drugIntro;
    private LocalDate approvalDate;
    private String detailUrl;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
