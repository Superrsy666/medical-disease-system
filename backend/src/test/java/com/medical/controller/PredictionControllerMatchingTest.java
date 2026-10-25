package com.medical.controller;

import com.medical.entity.Disease;
import com.medical.entity.Drug;
import com.medical.service.DiseaseService;
import com.medical.service.DiseaseDrugRelationService;
import com.medical.service.DrugService;
import com.medical.service.PatientService;
import com.medical.service.SelfTestService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class PredictionControllerMatchingTest {

    @Mock
    private DiseaseService diseaseService;

    @Mock
    private DiseaseDrugRelationService relationService;

    @Mock
    private DrugService drugService;

    @Mock
    private SelfTestService selfTestService;

    @Mock
    private PatientService patientService;

    @InjectMocks
    private PredictionController controller;

    @Test
    void shouldPreferRespiratoryInfectionForFeverAndCoughSymptoms() {
        Disease influenza = new Disease();
        influenza.setId(1);
        influenza.setDiseaseName("流行性感冒");
        influenza.setDescription("由流感病毒引起的急性呼吸道传染病");
        influenza.setSymptoms("发热,咳嗽,咽痛,肌肉酸痛,头痛,乏力");

        Disease pneumonia = new Disease();
        pneumonia.setId(2);
        pneumonia.setDiseaseName("肺炎");
        pneumonia.setDescription("终末气道、肺泡和肺间质炎症");
        pneumonia.setSymptoms("发热,咳嗽,咳痰,胸痛,呼吸困难");

        when(diseaseService.getAllForPrediction()).thenReturn(List.of(influenza, pneumonia));
        when(drugService.getById(anyInt())).thenReturn(new Drug());

        var results = invokeMatchMethod("发热 咳嗽", "发热 咳嗽");

        assertFalse(results.isEmpty());
        assertTrue(results.get(0).getMatchedDisease().contains("流行性感冒"));
    }

    @SuppressWarnings("unchecked")
    private List<com.medical.dto.PredictionResponse> invokeMatchMethod(String keywords, String symptoms) {
        try {
            var method = PredictionController.class.getDeclaredMethod("matchDiseasesByKeywords", Set.class, String.class);
            method.setAccessible(true);
            Set<String> keywordSet = new LinkedHashSet<>(Arrays.asList(keywords.split("[，,\\s、]+")));
            return (List<com.medical.dto.PredictionResponse>) method.invoke(controller, keywordSet, symptoms);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
