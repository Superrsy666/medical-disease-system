package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.PatientDoctor;
import com.medical.mapper.PatientDoctorMapper;
import org.springframework.stereotype.Service;

@Service
public class PatientDoctorService extends ServiceImpl<PatientDoctorMapper, PatientDoctor> {
}
