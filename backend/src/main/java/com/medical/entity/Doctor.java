package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("doctors")
public class Doctor {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer userId;
    private String department;
    private String title;
    private String hospital;
    private Integer isVerified;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableField(exist = false)
    private String username;
    @TableField(exist = false)
    private String realName;
}
