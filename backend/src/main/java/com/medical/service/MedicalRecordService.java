package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.MedicalRecord;
import com.medical.mapper.MedicalRecordMapper;
import org.springframework.stereotype.Service;

@Service
public class MedicalRecordService extends ServiceImpl<MedicalRecordMapper, MedicalRecord> {
}
