package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.DiseaseDrugRelation;
import com.medical.mapper.DiseaseDrugRelationMapper;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DiseaseDrugRelationService extends ServiceImpl<DiseaseDrugRelationMapper, DiseaseDrugRelation> {
    @Cacheable(cacheNames = "prediction:relations", key = "#diseaseId")
    public List<DiseaseDrugRelation> getForPrediction(Integer diseaseId) {
        return lambdaQuery().eq(DiseaseDrugRelation::getDiseaseId, diseaseId).list();
    }
}
