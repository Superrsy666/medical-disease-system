package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("patient_doctor")
public class PatientDoctor {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer patientId;
    private Integer doctorId;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
