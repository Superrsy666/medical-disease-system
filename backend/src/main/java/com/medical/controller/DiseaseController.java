package com.medical.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.medical.common.Result;
import com.medical.entity.Disease;
import com.medical.entity.DiseaseDrugRelation;
import com.medical.entity.Drug;
import com.medical.service.DiseaseDrugRelationService;
import com.medical.service.DiseaseService;
import com.medical.service.DrugService;
import lombok.RequiredArgsConstructor;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Objects;

@RestController
@RequestMapping("/api/diseases")
@RequiredArgsConstructor
public class DiseaseController {

    private final DiseaseService diseaseService;
    private final DiseaseDrugRelationService relationService;
    private final DrugService drugService;

    @GetMapping
    public Result<Page<Disease>> list(@RequestParam(defaultValue = "1") Integer page,
                                       @RequestParam(defaultValue = "10") Integer size,
                                       @RequestParam(required = false) String keyword,
                                       @RequestParam(required = false) String symptom,
                                       @RequestParam(required = false) String department,
                                       @RequestParam(required = false) String categoryPath) {
        LambdaQueryWrapper<Disease> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(keyword)) {
            wrapper.and(w -> w.like(Disease::getDiseaseName, keyword)
                    .or().like(Disease::getDescription, keyword)
                    .or().like(Disease::getSymptoms, keyword));
        }
        if (StringUtils.hasText(symptom)) {
            wrapper.and(w -> w.like(Disease::getSymptoms, symptom)
                    .or().like(Disease::getSymptomsOverview, symptom)
                    .or().like(Disease::getSymptomsDetail, symptom));
        }
        if (StringUtils.hasText(department)) {
            wrapper.like(Disease::getDepartment, department);
        }
        if (StringUtils.hasText(categoryPath)) {
            wrapper.eq(Disease::getCategoryPath, categoryPath);
        }
        return Result.ok(diseaseService.page(new Page<>(page, size), wrapper));
    }

    @GetMapping("/{id}")
    public Result<Disease> getById(@PathVariable Integer id) {
        Disease disease = diseaseService.getById(id);
        if (disease == null) return Result.error("疾病不存在");
        return Result.ok(disease);
    }

    @GetMapping("/{id}/drugs")
    public Result<List<Drug>> getDiseaseDrugs(@PathVariable Integer id) {
        List<DiseaseDrugRelation> relations = relationService.lambdaQuery()
                .eq(DiseaseDrugRelation::getDiseaseId, id).list();
        List<Drug> drugs = relations.stream()
                .map(r -> drugService.getById(r.getDrugId()))
                .filter(Objects::nonNull)
                .toList();
        return Result.ok(drugs);
    }
}
