package com.medical.common;

import com.medical.entity.User;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.List;

@Getter
public class SecurityUser implements UserDetails {
    private Integer id;
    private String username;
    private String password;
    private Integer role;

    public SecurityUser(User user) {
        this.id = user.getId();
        this.username = user.getUsername();
        this.password = user.getPassword();
        this.role = user.getRole();
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        String roleName = switch (role) {
            case 1 -> "ROLE_ADMIN";
            case 2 -> "ROLE_DOCTOR";
            case 3 -> "ROLE_PATIENT";
            default -> "ROLE_PATIENT";
        };
        return List.of(new SimpleGrantedAuthority(roleName));
    }

    @Override
    public boolean isAccountNonExpired() { return true; }
    @Override
    public boolean isAccountNonLocked() { return true; }
    @Override
    public boolean isCredentialsNonExpired() { return true; }
    @Override
    public boolean isEnabled() { return true; }
}
