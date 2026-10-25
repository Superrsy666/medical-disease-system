package com.medical.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.medical.common.Result;
import com.medical.common.SecurityUser;
import com.medical.entity.Patient;
import com.medical.entity.User;
import com.medical.service.PatientService;
import com.medical.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/patients")
@RequiredArgsConstructor
public class PatientController {

    private final PatientService patientService;
    private final UserService userService;

    @GetMapping
    @PreAuthorize("hasAnyRole('ADMIN','DOCTOR')")
    public Result<Page<Patient>> list(@RequestParam(defaultValue = "1") Integer page,
                                       @RequestParam(defaultValue = "10") Integer size) {
        Page<Patient> result = patientService.page(new Page<>(page, size));
        // 填充用户名和姓名
        result.getRecords().forEach(p -> {
            User user = userService.getById(p.getUserId());
            if (user != null) {
                p.setUsername(user.getUsername());
                p.setRealName(user.getRealName());
            }
        });
        return Result.ok(result);
    }

    @GetMapping("/{id}")
    public Result<Patient> getById(@PathVariable Integer id,
                                    @AuthenticationPrincipal SecurityUser currentUser) {
        Patient patient = patientService.getById(id);
        if (patient == null) return Result.error("患者不存在");
        // 患者只能看自己
        if (currentUser.getRole() == 3) {
            if (!patient.getUserId().equals(currentUser.getId())) {
                return Result.error(403, "无权访问");
            }
        }
        User user = userService.getById(patient.getUserId());
        if (user != null) {
            patient.setUsername(user.getUsername());
            patient.setRealName(user.getRealName());
        }
        return Result.ok(patient);
    }

    @PutMapping("/{id}")
    public Result<?> update(@PathVariable Integer id,
                             @RequestBody Patient patient,
                             @AuthenticationPrincipal SecurityUser currentUser) {
        Patient existing = patientService.getById(id);
        if (existing == null) return Result.error("患者不存在");
        // 患者只能改自己
        if (currentUser.getRole() == 3 && !existing.getUserId().equals(currentUser.getId())) {
            return Result.error(403, "无权修改");
        }
        patient.setId(id);
        patient.setUserId(null); // 禁止修改userId
        patientService.updateById(patient);
        return Result.ok();
    }
}
