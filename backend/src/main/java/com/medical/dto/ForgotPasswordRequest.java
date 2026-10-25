package com.medical.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ForgotPasswordRequest {
    @NotBlank(message = "用户名不能为空")
    private String username;
    @NotBlank(message = "手机号不能为空")
    private String phone;
}
