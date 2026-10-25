package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.Patient;
import com.medical.mapper.PatientMapper;
import org.springframework.stereotype.Service;

@Service
public class PatientService extends ServiceImpl<PatientMapper, Patient> {
}
