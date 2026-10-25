package com.medical.dto;

import lombok.Builder;
import lombok.Data;
import com.medical.entity.Disease;
import com.medical.entity.Drug;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class PredictionResponse {
    private String matchedDisease;
    private BigDecimal confidence;
    private Disease disease;
    private List<Drug> recommendedDrugs;
    private String advice;

    private String diseaseOverview;
    private String possibleCauses;
    private String typicalSymptoms;
    private String diagnosticSuggestions;
    private String treatmentDirections;
    private String lifestyleAdvice;
    private String riskWarnings;
    private List<String> differentialDiagnoses;
    private String aiAnalysisSummary;
}
