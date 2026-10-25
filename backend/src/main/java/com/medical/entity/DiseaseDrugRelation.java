package com.medical.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

@Data
@TableName("disease_drug_relation")
public class DiseaseDrugRelation {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer diseaseId;
    private Integer drugId;
    private String matchSource;
}
