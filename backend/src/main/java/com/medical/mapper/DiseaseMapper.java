package com.medical.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.medical.entity.Disease;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface DiseaseMapper extends BaseMapper<Disease> {
}
