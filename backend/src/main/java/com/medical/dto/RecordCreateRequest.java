package com.medical.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Data
public class RecordCreateRequest {
    private Integer patientId;
    private LocalDate visitDate;
    private String chiefComplaint;
    private String diagnosis;
    private String diagnosisDetail;
    private List<Map<String, Object>> prescription;
    private Integer status;
}
