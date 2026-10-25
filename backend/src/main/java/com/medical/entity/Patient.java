package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("patients")
public class Patient {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer userId;
    private Integer gender;
    private LocalDate birthDate;
    private BigDecimal height;
    private BigDecimal weight;
    private String allergyHistory;
    private String address;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    /** 非数据库字段：用户名 */
    @TableField(exist = false)
    private String username;
    @TableField(exist = false)
    private String realName;
}
