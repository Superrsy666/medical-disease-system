package com.medical.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.medical.common.Result;
import com.medical.entity.Doctor;
import com.medical.entity.User;
import com.medical.service.DoctorService;
import com.medical.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/doctors")
@RequiredArgsConstructor
public class DoctorController {

    private final DoctorService doctorService;
    private final UserService userService;

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Page<Doctor>> list(@RequestParam(defaultValue = "1") Integer page,
                                      @RequestParam(defaultValue = "10") Integer size) {
        Page<Doctor> result = doctorService.page(new Page<>(page, size));
        result.getRecords().forEach(d -> {
            User user = userService.getById(d.getUserId());
            if (user != null) {
                d.setUsername(user.getUsername());
                d.setRealName(user.getRealName());
            }
        });
        return Result.ok(result);
    }

    @PutMapping("/{id}/verify")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<?> verify(@PathVariable Integer id, @RequestBody Map<String, Integer> body) {
        Doctor doctor = doctorService.getById(id);
        if (doctor == null) return Result.error("医生不存在");
        Integer isVerified = body.get("isVerified");
        if (isVerified == null) return Result.error("参数错误");
        doctor.setIsVerified(isVerified);
        doctorService.updateById(doctor);
        return Result.ok();
    }
}
