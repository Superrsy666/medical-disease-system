package com.medical.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class RegisterRequest {
    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 50, message = "用户名长度3-50")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, message = "密码至少6位")
    private String password;

    private String realName;
    private String phone;
    private Integer gender;
    private LocalDate birthDate;
    private BigDecimal height;
    private BigDecimal weight;
    private String allergyHistory;
    private String address;
    private Integer role;
    private String department;
    private String title;
    private String hospital;
}
