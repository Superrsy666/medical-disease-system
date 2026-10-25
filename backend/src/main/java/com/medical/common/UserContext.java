package com.medical.common;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

public class UserContext {

    public static SecurityUser getCurrentUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof SecurityUser) {
            return (SecurityUser) auth.getPrincipal();
        }
        return null;
    }

    public static Integer getUserId() {
        SecurityUser user = getCurrentUser();
        return user != null ? user.getId() : null;
    }

    public static Integer getRole() {
        SecurityUser user = getCurrentUser();
        return user != null ? user.getRole() : null;
    }

    public static String getUsername() {
        SecurityUser user = getCurrentUser();
        return user != null ? user.getUsername() : null;
    }
}
