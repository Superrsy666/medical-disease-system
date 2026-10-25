package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.Drug;
import com.medical.mapper.DrugMapper;
import org.springframework.stereotype.Service;

@Service
public class DrugService extends ServiceImpl<DrugMapper, Drug> {
}
