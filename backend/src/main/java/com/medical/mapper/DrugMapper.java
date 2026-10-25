package com.medical.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.medical.entity.Drug;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface DrugMapper extends BaseMapper<Drug> {
}
