package com.medical.controller;

import com.medical.common.Result;
import com.medical.service.DiseaseService;
import com.medical.service.DoctorService;
import com.medical.service.DrugService;
import com.medical.service.PatientService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/statistics")
@RequiredArgsConstructor
public class StatisticsController {

    private final PatientService patientService;
    private final DoctorService doctorService;
    private final DrugService drugService;
    private final DiseaseService diseaseService;

    @GetMapping("/overview")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Map<String, Long>> overview() {
        Map<String, Long> data = new HashMap<>();
        data.put("patientCount", patientService.count());
        data.put("doctorCount", doctorService.count());
        data.put("drugCount", drugService.count());
        data.put("diseaseCount", diseaseService.count());
        return Result.ok(data);
    }
}
