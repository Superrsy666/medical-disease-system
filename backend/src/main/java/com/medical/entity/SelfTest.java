package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("self_tests")
public class SelfTest {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer patientId;
    private String inputSymptoms;
    private String matchedDisease;
    private BigDecimal confidence;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    @TableField(exist = false)
    private String patientName;
    @TableField(exist = false)
    private String patientUsername;
}
