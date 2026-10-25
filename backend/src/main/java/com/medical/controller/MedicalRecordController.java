package com.medical.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.medical.common.Result;
import com.medical.common.SecurityUser;
import com.medical.dto.RecordCreateRequest;
import com.medical.entity.Doctor;
import com.medical.entity.MedicalRecord;
import com.medical.entity.Patient;
import com.medical.service.DoctorService;
import com.medical.service.MedicalRecordService;
import com.medical.service.PatientService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/records")
@RequiredArgsConstructor
public class MedicalRecordController {

    private final MedicalRecordService recordService;
    private final DoctorService doctorService;
    private final PatientService patientService;

    @GetMapping
    public Result<Page<MedicalRecord>> list(@RequestParam(defaultValue = "1") Integer page,
                                             @RequestParam(defaultValue = "10") Integer size,
                                             @AuthenticationPrincipal SecurityUser currentUser) {
        LambdaQueryWrapper<MedicalRecord> wrapper = new LambdaQueryWrapper<>();

        if (currentUser.getRole() == 2) {
            // 医生看自己的
            Doctor doctor = doctorService.lambdaQuery().eq(Doctor::getUserId, currentUser.getId()).one();
            if (doctor != null) {
                wrapper.eq(MedicalRecord::getDoctorId, doctor.getId());
            }
        } else if (currentUser.getRole() == 3) {
            // 患者看自己的
            Patient patient = patientService.lambdaQuery().eq(Patient::getUserId, currentUser.getId()).one();
            if (patient != null) {
                wrapper.eq(MedicalRecord::getPatientId, patient.getId());
            }
        }
        wrapper.orderByDesc(MedicalRecord::getVisitDate);
        Page<MedicalRecord> result = recordService.page(new Page<>(page, size), wrapper);

        // 填充患者和医生姓名
        result.getRecords().forEach(r -> {
            Patient p = patientService.getById(r.getPatientId());
            if (p != null) {
                r.setPatientName(p.getRealName() != null ? p.getRealName() : String.valueOf(p.getId()));
            }
            Doctor d = doctorService.getById(r.getDoctorId());
            if (d != null) {
                r.setDoctorName(d.getRealName() != null ? d.getRealName() : String.valueOf(d.getId()));
            }
        });
        return Result.ok(result);
    }

    @PostMapping
    public Result<?> create(@RequestBody RecordCreateRequest req,
                             @AuthenticationPrincipal SecurityUser currentUser) {
        Doctor doctor = doctorService.lambdaQuery().eq(Doctor::getUserId, currentUser.getId()).one();
        if (doctor == null) return Result.error("医生信息不存在");

        MedicalRecord record = new MedicalRecord();
        record.setPatientId(req.getPatientId());
        record.setDoctorId(doctor.getId());
        record.setVisitDate(req.getVisitDate());
        record.setChiefComplaint(req.getChiefComplaint());
        record.setDiagnosis(req.getDiagnosis());
        record.setDiagnosisDetail(req.getDiagnosisDetail());
        record.setPrescription(req.getPrescription());
        record.setStatus(req.getStatus() != null ? req.getStatus() : 1);
        recordService.save(record);
        return Result.ok();
    }

    @GetMapping("/{id}")
    public Result<MedicalRecord> getById(@PathVariable Integer id,
                                          @AuthenticationPrincipal SecurityUser currentUser) {
        MedicalRecord record = recordService.getById(id);
        if (record == null) return Result.error("病历不存在");

        // 权限校验
        if (currentUser.getRole() == 3) {
            Patient patient = patientService.lambdaQuery().eq(Patient::getUserId, currentUser.getId()).one();
            if (patient == null || !record.getPatientId().equals(patient.getId())) {
                return Result.error(403, "无权访问");
            }
        } else if (currentUser.getRole() == 2) {
            Doctor doctor = doctorService.lambdaQuery().eq(Doctor::getUserId, currentUser.getId()).one();
            if (doctor == null || !record.getDoctorId().equals(doctor.getId())) {
                return Result.error(403, "无权访问");
            }
        }
        return Result.ok(record);
    }
}
