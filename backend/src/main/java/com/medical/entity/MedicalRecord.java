package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@TableName(value = "medical_records", autoResultMap = true)
public class MedicalRecord {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer patientId;
    private Integer doctorId;
    private LocalDate visitDate;
    private String chiefComplaint;
    private String diagnosis;
    private String diagnosisDetail;
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> prescription;
    private Integer status;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableField(exist = false)
    private String patientName;
    @TableField(exist = false)
    private String doctorName;
}
