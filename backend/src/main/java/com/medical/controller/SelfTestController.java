package com.medical.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.medical.common.Result;
import com.medical.common.SecurityUser;
import com.medical.entity.Patient;
import com.medical.entity.SelfTest;
import com.medical.entity.User;
import com.medical.service.PatientService;
import com.medical.service.SelfTestService;
import com.medical.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/self-tests")
@RequiredArgsConstructor
public class SelfTestController {
    private final SelfTestService selfTestService;
    private final PatientService patientService;
    private final UserService userService;

    @GetMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'DOCTOR')")
    public Result<Page<SelfTest>> list(@RequestParam(defaultValue = "1") Integer page,
                                       @RequestParam(defaultValue = "10") Integer size,
                                       @AuthenticationPrincipal SecurityUser currentUser) {
        LambdaQueryWrapper<SelfTest> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByDesc(SelfTest::getCreatedAt);
        Page<SelfTest> result = selfTestService.page(new Page<>(page, size), wrapper);
        result.getRecords().forEach(test -> {
            Patient patient = patientService.getById(test.getPatientId());
            if (patient != null) {
                User user = userService.getById(patient.getUserId());
                if (user != null) {
                    test.setPatientName(user.getRealName());
                    test.setPatientUsername(user.getUsername());
                }
            }
        });
        return Result.ok(result);
    }
}
