package com.medical.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.medical.dto.PredictionResponse;
import com.medical.entity.Disease;
import com.medical.entity.Drug;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PredictionService {

    private static final Logger log = LoggerFactory.getLogger(PredictionService.class);

    private final RestTemplate restTemplate;
    private final DiseaseService diseaseService;
    private final DrugService drugService;
    private final DiseaseDrugRelationService relationService;

    @Value("${deepseek.api.key}")
    private String apiKey;

    @Value("${deepseek.api.url}")
    private String apiUrl;

    @Value("${deepseek.api.model:deepseek-chat}")
    private String model;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<PredictionResponse> predict(String symptoms) {
        if (symptoms == null || symptoms.isBlank()) {
            return Collections.emptyList();
        }

        try {
            return callDeepSeekForPrediction(symptoms);
        } catch (Exception e) {
            log.error("DeepSeek API 调用失败，降级处理", e);
            return buildFallbackResult(symptoms, e);
        }
    }

    private List<PredictionResponse> callDeepSeekForPrediction(String symptoms) {
        String prompt = buildPrompt(symptoms);

        Map<String, Object> requestBody = Map.of(
                "model", model,
                "messages", List.of(
                        Map.of("role", "system", "content",
                                "你是一个经验丰富的全科医学专家AI助手。请根据用户的症状描述进行专业的疾病诊断分析。" +
                                "回答必须严格按照指定的JSON格式返回，不要包含任何其他说明文字，只输出纯JSON。"),
                        Map.of("role", "user", "content", prompt)
                ),
                "temperature", 0.3,
                "max_tokens", 2000
        );

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + apiKey);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    apiUrl, HttpMethod.POST, entity, String.class
            );

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                JsonNode root = objectMapper.readTree(response.getBody());
                JsonNode contentNode = root.at("/choices/0/message/content");
                if (!contentNode.isMissingNode() && contentNode.isTextual()) {
                    String jsonResult = extractJson(contentNode.asText());
                    return parseDeepSeekResult(jsonResult);
                }
            }
            throw new RuntimeException("DeepSeek API 返回格式异常");

        } catch (HttpClientErrorException.Unauthorized e) {
            log.error("DeepSeek API 鉴权失败 (401): {}", e.getMessage());
            throw new RuntimeException("API 密钥无效或已过期", e);
        } catch (HttpClientErrorException.Forbidden e) {
            log.error("DeepSeek API 权限不足 (403): {}", e.getMessage());
            throw new RuntimeException("API 访问被拒绝", e);
        } catch (HttpClientErrorException.TooManyRequests e) {
            log.error("DeepSeek API 调用频率超限 (429): {}", e.getMessage());
            throw new RuntimeException("API 调用过于频繁，请稍后再试", e);
        } catch (ResourceAccessException e) {
            log.error("DeepSeek API 网络连接超时: {}", e.getMessage());
            throw new RuntimeException("网络连接超时，请检查网络", e);
        } catch (Exception e) {
            log.error("DeepSeek API 调用异常: {}", e.getMessage());
            throw new RuntimeException("AI 诊断服务暂时不可用", e);
        }
    }

    private String buildPrompt(String symptoms) {
        StringBuilder context = new StringBuilder();

        List<Disease> allDiseases = diseaseService.getAllForPrediction();
        if (allDiseases != null && !allDiseases.isEmpty()) {
            context.append("\n\n【本地疾病知识库参考（供你匹配时参考）：\n");
            int count = 0;
            for (Disease d : allDiseases) {
                if (count >= 80) break;
                context.append("- ").append(d.getDiseaseName());
                if (d.getDepartment() != null && !d.getDepartment().isBlank()) {
                    context.append(" [科室: ").append(d.getDepartment()).append("]");
                }
                if (d.getSymptoms() != null && !d.getSymptoms().isBlank()) {
                    String s = d.getSymptoms();
                    context.append(" [症状: ").append(s, 0, Math.min(120, s.length())).append("]");
                }
                if (d.getEtiology() != null && !d.getEtiology().isBlank()) {
                    String e = d.getEtiology();
                    context.append(" [病因: ").append(e, 0, Math.min(80, e.length())).append("]");
                }
                if (d.getDrugTreatment() != null && !d.getDrugTreatment().isBlank()) {
                    String t = d.getDrugTreatment();
                    context.append(" [药物: ").append(t, 0, Math.min(80, t.length())).append("]");
                }
                if (d.getDescription() != null && !d.getDescription().isBlank()) {
                    context.append(" [描述: ").append(d.getDescription(), 0, Math.min(100, d.getDescription().length())).append("]");
                }
                context.append("\n");
                count++;
            }
            context.append("】\n");
        }

        List<Drug> allDrugs = drugService.list();
        if (allDrugs != null && !allDrugs.isEmpty()) {
            context.append("\n【本地药品知识库参考（供推荐时参考）：\n");
            int count = 0;
            for (Drug d : allDrugs) {
                if (count >= 80) break;
                context.append("- ").append(d.getDrugName());
                if (d.getDrugCategory() != null && !d.getDrugCategory().isBlank()) {
                    context.append(" [分类: ").append(d.getDrugCategory()).append("]");
                }
                if (d.getIndication() != null && !d.getIndication().isBlank()) {
                    context.append(" [适应症: ").append(d.getIndication(), 0, Math.min(80, d.getIndication().length())).append("]");
                }
                if (d.getPrescriptionType() != null && !d.getPrescriptionType().isBlank()) {
                    context.append(" [处方: ").append(d.getPrescriptionType()).append("]");
                }
                if (d.getAdverseReactions() != null && !d.getAdverseReactions().isBlank()) {
                    String a = d.getAdverseReactions();
                    context.append(" [不良反应: ").append(a, 0, Math.min(50, a.length())).append("]");
                }
                context.append("\n");
                count++;
            }
            context.append("】\n");
        }

        return "你是一个经验丰富的全科医学专家AI助手。请根据以下用户的症状描述进行专业的疾病诊断分析。\n\n"
                + "【用户症状描述】\n" + symptoms + "\n"
                + context
                + "\n请严格按照以下JSON格式返回分析结果（只返回JSON，不要任何其他文字）：\n"
                + "{\n"
                + "  \"results\": [\n"
                + "    {\n"
                + "      \"diseaseName\": \"疾病名称（中文）\",\n"
                + "      \"confidence\": 85,\n"
                + "      \"briefDescription\": \"简要说明（1-2句话，为什么考虑这个疾病）\",\n"
                + "      \"recommendedDrugs\": [\"药品1\", \"药品2\"],\n"
                + "      \"advice\": \"就医和用药建议（1-2句话）\"\n"
                + "    }\n"
                + "  ]\n"
                + "}\n\n"
                + "要求：\n"
                + "1. 返回1-5个最可能的疾病，按匹配度（confidence）从高到低排序\n"
                + "2. confidence为0-100的整数，越可能数值越高\n"
                + "3. 推荐药品请从参考药品库中选择最匹配的，也可补充医学常识中的常用药\n"
                + "4. 如果症状非常不典型，可返回多个可能性，匹配度依次递减\n"
                + "5. 务必在advice中强调：本结果仅为AI参考，不能替代医生诊断，患病请及时就医\n"
                + "6. 必须输出纯JSON格式，不要Markdown代码块，不要解释文字";
    }

    private String extractJson(String text) {
        if (text == null || text.isBlank()) return "";
        int firstBrace = text.indexOf('{');
        int lastBrace = text.lastIndexOf('}');
        if (firstBrace >= 0 && lastBrace > firstBrace) {
            return text.substring(firstBrace, lastBrace + 1);
        }
        return text.trim();
    }

    private List<PredictionResponse> parseDeepSeekResult(String jsonStr) {
        List<PredictionResponse> results = new ArrayList<>();
        try {
            JsonNode root = objectMapper.readTree(jsonStr);
            JsonNode resultsNode = root.get("results");
            if (resultsNode == null || !resultsNode.isArray()) {
                throw new RuntimeException("AI 返回结果格式错误：缺少 results 数组");
            }

            for (JsonNode item : resultsNode) {
                String diseaseName = item.has("diseaseName") ? item.get("diseaseName").asText("") : "";
                if (diseaseName.isBlank()) continue;

                int confidenceVal = item.has("confidence") ? item.get("confidence").asInt(50) : 50;
                confidenceVal = Math.max(10, Math.min(98, confidenceVal));
                BigDecimal confidence = BigDecimal.valueOf(confidenceVal).setScale(2, RoundingMode.HALF_UP);

                String briefDescription = item.has("briefDescription") ? item.get("briefDescription").asText("") : "";
                String advice = item.has("advice") ? item.get("advice").asText("") : "";

                Disease matchedDisease = findDiseaseByName(diseaseName);

                List<String> drugNames = new ArrayList<>();
                JsonNode drugsNode = item.get("recommendedDrugs");
                if (drugsNode != null && drugsNode.isArray()) {
                    for (JsonNode dn : drugsNode) {
                        if (dn.isTextual()) drugNames.add(dn.asText());
                    }
                }
                List<Drug> matchedDrugs = findDrugsByNames(drugNames);

                if (matchedDisease != null && matchedDrugs.isEmpty()) {
                    matchedDrugs = findDrugsByDiseaseRelation(matchedDisease.getId());
                }

                PredictionResponse.PredictionResponseBuilder builder = PredictionResponse.builder()
                        .matchedDisease(diseaseName)
                        .confidence(confidence)
                        .disease(matchedDisease)
                        .recommendedDrugs(matchedDrugs)
                        .advice(advice.isBlank() ? buildDefaultAdvice(diseaseName, matchedDrugs) : advice)
                        .diseaseOverview(briefDescription)
                        .aiAnalysisSummary(briefDescription);

                results.add(builder.build());
            }

            if (results.isEmpty()) {
                throw new RuntimeException("AI 未返回任何有效诊断结果");
            }

            results.sort((a, b) -> b.getConfidence().compareTo(a.getConfidence()));
            return results;

        } catch (Exception e) {
            log.error("解析 DeepSeek 返回结果失败: {}", e.getMessage());
            throw new RuntimeException("AI 返回结果解析失败", e);
        }
    }

    private Disease findDiseaseByName(String name) {
        if (name == null || name.isBlank()) return null;
        try {
            List<Disease> diseases = diseaseService.lambdaQuery()
                    .like(Disease::getDiseaseName, name)
                    .last("LIMIT 1")
                    .list();
            if (diseases != null && !diseases.isEmpty()) return diseases.get(0);

            List<Disease> all = diseaseService.getAllForPrediction();
            if (all != null) {
                for (Disease d : all) {
                    if (d.getDiseaseName() != null
                            && (d.getDiseaseName().contains(name) || name.contains(d.getDiseaseName()))) {
                        return d;
                    }
                }
            }
        } catch (Exception e) {
            log.warn("查找疾病失败: {}", name, e);
        }
        return null;
    }

    private List<Drug> findDrugsByNames(List<String> drugNames) {
        List<Drug> result = new ArrayList<>();
        if (drugNames == null || drugNames.isEmpty()) return result;
        try {
            for (String name : drugNames) {
                if (name == null || name.isBlank()) continue;
                List<Drug> drugs = drugService.lambdaQuery()
                        .like(Drug::getDrugName, name.trim())
                        .last("LIMIT 1")
                        .list();
                if (drugs != null && !drugs.isEmpty()) {
                    boolean exists = result.stream().anyMatch(r -> r.getId().equals(drugs.get(0).getId()));
                    if (!exists) result.add(drugs.get(0));
                }
            }
        } catch (Exception e) {
            log.warn("按名称查找药品失败", e);
        }
        return result;
    }

    private List<Drug> findDrugsByDiseaseRelation(Integer diseaseId) {
        if (diseaseId == null) return Collections.emptyList();
        try {
            return relationService.getForPrediction(diseaseId).stream()
                    .map(r -> drugService.getById(r.getDrugId()))
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.warn("按疾病关系查找药品失败", e);
            return Collections.emptyList();
        }
    }

    private String buildDefaultAdvice(String diseaseName, List<Drug> drugs) {
        StringBuilder sb = new StringBuilder();
        sb.append("本结果仅为AI智能参考，可能匹配疾病：").append(diseaseName).append("。");
        if (drugs != null && !drugs.isEmpty()) {
            sb.append("推荐参考药品：");
            sb.append(drugs.stream().map(Drug::getDrugName)
                    .filter(Objects::nonNull).collect(Collectors.joining("、")));
            sb.append("。");
        }
        sb.append("请结合症状及时就医，遵医嘱用药。⚠️本结果不能替代医生诊断。");
        return sb.toString();
    }

    private List<PredictionResponse> buildFallbackResult(String symptoms, Exception e) {
        String errorMsg = (e != null && e.getMessage() != null) ? e.getMessage() : "服务异常";
        String advice = "⚠️AI诊断服务暂时不可用（" + errorMsg + "）。"
                + "您描述的症状为：" + symptoms + "。"
                + "建议您关注身体变化，如症状持续或加重，请及时前往医院就诊，遵医嘱治疗。"
                + "本系统所有内容仅供参考，不能替代专业医疗诊断。";

        return List.of(PredictionResponse.builder()
                .matchedDisease("AI服务暂不可用")
                .confidence(BigDecimal.ZERO)
                .disease(null)
                .recommendedDrugs(Collections.emptyList())
                .advice(advice)
                .aiAnalysisSummary("服务降级提示：" + errorMsg)
                .build());
    }
}
