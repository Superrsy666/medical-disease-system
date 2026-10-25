package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.Disease;
import com.medical.mapper.DiseaseMapper;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DiseaseService extends ServiceImpl<DiseaseMapper, Disease> {
    @Cacheable(cacheNames = "prediction:diseases", key = "'all'")
    public List<Disease> getAllForPrediction() {
        return list();
    }
}
