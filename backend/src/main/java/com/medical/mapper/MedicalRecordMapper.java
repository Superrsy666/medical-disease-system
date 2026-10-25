package com.medical.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.medical.entity.MedicalRecord;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface MedicalRecordMapper extends BaseMapper<MedicalRecord> {
}
