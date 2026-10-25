package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("diseases")
public class Disease {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private String diseaseName;
    private String englishName;
    private String aliases;
    private String icdCode;
    private String department;
    private String categoryPath;
    private String description;
    private String affectedArea;
    private String symptoms;
    private String symptomsOverview;
    private String symptomsDetail;
    private String etiology;
    private String etiologyOverview;
    private String riskFactors;
    private String examination;
    private String expectedExamination;
    private String labExamination;
    private String imagingExamination;
    private String diagnosticBasis;
    private String diagnosticCriteria;
    private String differentialDiagnosis;
    private String excludes;
    private String infectiousness;
    private String infectionSource;
    private String transmissionRoute;
    private String incidenceRate;
    private String incidenceTrend;
    private String susceptiblePopulation;
    private String hereditary;
    private String medicalInsurance;
    private String tcmRelated;
    private String treatmentPrognosis;
    private String generalTreatment;
    private String drugTreatment;
    private String prevention;
    private String importantNote;
    private String detailUrl;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
