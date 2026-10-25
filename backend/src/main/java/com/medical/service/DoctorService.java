package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.Doctor;
import com.medical.mapper.DoctorMapper;
import org.springframework.stereotype.Service;

@Service
public class DoctorService extends ServiceImpl<DoctorMapper, Doctor> {
}
