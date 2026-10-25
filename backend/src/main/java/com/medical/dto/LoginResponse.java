package com.medical.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class LoginResponse {
    private String token;
    private Integer role;
    private String username;
    private String realName;
    private Integer userId;
}
