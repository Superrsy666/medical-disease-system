package com.medical.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class ResetPasswordRequest {
    @NotBlank(message = "用户名不能为空")
    private String username;
    @NotBlank(message = "手机号不能为空")
    private String phone;
    @NotBlank(message = "新密码不能为空")
    @Size(min = 6, message = "密码至少6位")
    private String newPassword;
}
