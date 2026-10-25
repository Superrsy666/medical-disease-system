package com.medical.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LoginRequest {
    @NotBlank(message = "用户名不能为空")
    private String username;
    @NotBlank(message = "密码不能为空")
    private String password;

    /** 1管理员，2医生，3患者；为空时兼容旧客户端 */
    private Integer role;
}
