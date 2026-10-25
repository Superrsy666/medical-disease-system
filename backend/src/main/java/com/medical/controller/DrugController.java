package com.medical.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.medical.common.Result;
import com.medical.entity.Drug;
import com.medical.service.DrugService;
import lombok.RequiredArgsConstructor;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/drugs")
@RequiredArgsConstructor
public class DrugController {

    private final DrugService drugService;

    @GetMapping
    public Result<Page<Drug>> list(@RequestParam(defaultValue = "1") Integer page,
                                    @RequestParam(defaultValue = "10") Integer size,
                                    @RequestParam(required = false) String keyword,
                                    @RequestParam(required = false) String drugCategory) {
        LambdaQueryWrapper<Drug> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(keyword)) {
            wrapper.and(w -> w.like(Drug::getDrugName, keyword)
                    .or().like(Drug::getEnglishName, keyword)
                    .or().like(Drug::getIndication, keyword));
        }
        if (StringUtils.hasText(drugCategory)) {
            wrapper.like(Drug::getDrugCategory, drugCategory);
        }
        wrapper.orderByDesc(Drug::getId);
        return Result.ok(drugService.page(new Page<>(page, size), wrapper));
    }

    @GetMapping("/{id}")
    public Result<Drug> getById(@PathVariable Integer id) {
        Drug drug = drugService.getById(id);
        if (drug == null) return Result.error("药品不存在");
        return Result.ok(drug);
    }
}
