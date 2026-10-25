package com.medical.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.medical.entity.SelfTest;
import com.medical.mapper.SelfTestMapper;
import org.springframework.stereotype.Service;

@Service
public class SelfTestService extends ServiceImpl<SelfTestMapper, SelfTest> {
}
