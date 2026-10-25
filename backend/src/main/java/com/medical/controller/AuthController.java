package com.medical.controller;

import com.medical.common.Result;
import com.medical.common.SecurityUser;
import com.medical.dto.ForgotPasswordRequest;
import com.medical.dto.LoginRequest;
import com.medical.dto.LoginResponse;
import com.medical.dto.RegisterRequest;
import com.medical.dto.ResetPasswordRequest;
import com.medical.entity.Patient;
import com.medical.entity.Doctor;
import com.medical.service.DoctorService;
import com.medical.entity.User;
import com.medical.service.PatientService;
import com.medical.service.UserService;
import com.medical.util.JwtUtils;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import org.springframework.transaction.annotation.Transactional;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;
    private final PatientService patientService;
    private final DoctorService doctorService;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtils jwtUtils;

    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest req) {
        User user = userService.getByUsername(req.getUsername());
        if (user == null || !passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            return Result.error(401, "用户名或密码错误");
        }
        if (req.getRole() != null && !req.getRole().equals(user.getRole())) {
            return Result.error(401, "登录身份与账号不匹配");
        }
        String token = jwtUtils.generateToken(user.getId(), user.getUsername(), user.getRole());
        return Result.ok(LoginResponse.builder()
                .token(token)
                .role(user.getRole())
                .username(user.getUsername())
                .realName(user.getRealName())
                .userId(user.getId())
                .build());
    }

    @PostMapping("/register")
    @Transactional
    public Result<?> register(@Valid @RequestBody RegisterRequest req) {
        if (userService.getByUsername(req.getUsername()) != null) {
            return Result.error(400, "用户名已存在");
        }
        User user = new User();
        user.setUsername(req.getUsername());
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        int role = req.getRole() == null ? 3 : req.getRole();
        // 安全限制：仅允许自助注册医生或患者账号，管理员账号由系统内置，避免越权注册
        if (role != 2 && role != 3) {
            return Result.error(400, "仅支持注册医生或患者账号，管理员账号由系统内置");
        }
        user.setRole(role);
        user.setRealName(req.getRealName());
        user.setPhone(req.getPhone());
        userService.save(user);

        if (role == 3) {
            Patient patient = new Patient();
            patient.setUserId(user.getId());
            patient.setGender(req.getGender() != null ? req.getGender() : 0);
            patient.setBirthDate(req.getBirthDate());
            patient.setHeight(req.getHeight());
            patient.setWeight(req.getWeight());
            patient.setAllergyHistory(req.getAllergyHistory());
            patient.setAddress(req.getAddress());
            patientService.save(patient);
        } else if (role == 2) {
            Doctor doctor = new Doctor();
            doctor.setUserId(user.getId());
            doctor.setDepartment(req.getDepartment());
            doctor.setTitle(req.getTitle());
            doctor.setHospital(req.getHospital());
            doctor.setIsVerified(0);
            doctorService.save(doctor);
        }

        return Result.ok();
    }

    @GetMapping("/me")
    public Result<Map<String, Object>> me(@AuthenticationPrincipal SecurityUser currentUser) {
        User user = userService.getById(currentUser.getId());
        Map<String, Object> map = new HashMap<>();
        map.put("id", user.getId());
        map.put("username", user.getUsername());
        map.put("role", user.getRole());
        map.put("realName", user.getRealName());
        map.put("phone", user.getPhone());

        // 如果是患者，附加患者信息
        if (user.getRole() == 3) {
            Patient patient = patientService.lambdaQuery()
                    .eq(Patient::getUserId, user.getId()).one();
            if (patient != null) {
                map.put("patientId", patient.getId());
                map.put("gender", patient.getGender());
                map.put("birthDate", patient.getBirthDate());
                map.put("height", patient.getHeight());
                map.put("weight", patient.getWeight());
                map.put("allergyHistory", patient.getAllergyHistory());
                map.put("address", patient.getAddress());
            }
        }
        return Result.ok(map);
    }

    /**
     * 忘记密码 - 验证身份
     */
    @PostMapping("/forgot-password")
    public Result<?> forgotPassword(@Valid @RequestBody ForgotPasswordRequest req) {
        User user = userService.getByUsername(req.getUsername());
        if (user == null) {
            return Result.error(400, "用户不存在");
        }
        if (user.getPhone() == null || !user.getPhone().equals(req.getPhone())) {
            return Result.error(400, "手机号与注册信息不匹配");
        }
        return Result.ok("验证通过");
    }

    /**
     * 重置密码
     */
    @PostMapping("/reset-password")
    public Result<?> resetPassword(@Valid @RequestBody ResetPasswordRequest req) {
        User user = userService.getByUsername(req.getUsername());
        if (user == null) {
            return Result.error(400, "用户不存在");
        }
        if (user.getPhone() == null || !user.getPhone().equals(req.getPhone())) {
            return Result.error(400, "手机号与注册信息不匹配");
        }
        user.setPassword(passwordEncoder.encode(req.getNewPassword()));
        userService.updateById(user);
        return Result.ok("密码重置成功");
    }
}
