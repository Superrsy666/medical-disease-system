package com.medical.controller;

import com.medical.common.Result;
import com.medical.common.SecurityUser;
import com.medical.dto.PredictionRequest;
import com.medical.dto.PredictionResponse;
import com.medical.entity.Disease;
import com.medical.entity.DiseaseDrugRelation;
import com.medical.entity.Drug;
import com.medical.entity.Patient;
import com.medical.entity.SelfTest;
import com.medical.service.*;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URI;
import java.net.http.HttpClient;
import java.time.Duration;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/prediction")
@RequiredArgsConstructor
public class PredictionController {

    private static final Logger log = LoggerFactory.getLogger(PredictionController.class);
        private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();
    private static final String OPENAI_URL = "https://api.openai.com/v1/chat/completions";
    /** 口语化症状 → 规范医学表达（可多词，用空格分隔）。同一词典同时用于关键词扩展与疾病文本归一化，保证两侧可互匹配。 */
    private static final Map<String, String> SYMPTOM_SYNONYMS = Map.ofEntries(
            // 腹部与消化道
            Map.entry("肚子痛", "腹痛"),
            Map.entry("肚子疼", "腹痛"),
            Map.entry("肚痛", "腹痛"),
            Map.entry("肚子胀", "腹胀"),
            Map.entry("胀气", "腹胀"),
            Map.entry("拉肚子", "腹泻"),
            Map.entry("拉稀", "腹泻"),
            Map.entry("闹肚子", "腹泻"),
            Map.entry("胃疼", "胃痛 腹痛"),
            Map.entry("胃痛", "胃痛 腹痛"),
            Map.entry("上腹疼", "上腹疼痛 腹痛"),
            Map.entry("想吐", "恶心 呕吐"),
            Map.entry("犯恶心", "恶心"),
            Map.entry("反胃", "恶心 呕吐"),
            Map.entry("干呕", "呕吐"),
            Map.entry("烧心", "反酸"),
            Map.entry("打饱嗝", "嗳气"),
            Map.entry("没胃口", "食欲不振"),
            Map.entry("吃不下", "食欲不振"),
            Map.entry("不想吃饭", "食欲不振"),
            Map.entry("便秘", "便秘"),
            Map.entry("拉不出", "便秘"),
            Map.entry("大便干结", "便秘"),
            Map.entry("便血", "便血"),
            Map.entry("大便带血", "便血"),
            Map.entry("拉血", "便血"),
            // 呼吸道
            Map.entry("咳嗽", "咳嗽"),
            Map.entry("干咳", "咳嗽"),
            Map.entry("咳嗽有痰", "咳痰"),
            Map.entry("有痰", "咳痰"),
            Map.entry("发烧", "发热"),
            Map.entry("发高烧", "发热"),
            Map.entry("发低烧", "发热"),
            Map.entry("打喷嚏", "喷嚏"),
            Map.entry("流鼻涕", "流涕"),
            Map.entry("流鼻水", "流涕"),
            Map.entry("淌鼻涕", "流涕"),
            Map.entry("鼻子不通", "鼻塞"),
            Map.entry("鼻塞", "鼻塞"),
            Map.entry("嗓子疼", "咽痛 喉咙痛"),
            Map.entry("嗓子痛", "咽痛 喉咙痛"),
            Map.entry("嗓子干", "咽干"),
            Map.entry("嗓子哑", "声音嘶哑"),
            Map.entry("说话嘶哑", "声音嘶哑"),
            Map.entry("喉咙疼", "咽痛 喉咙痛"),
            Map.entry("喉咙痛", "咽痛 喉咙痛"),
            Map.entry("咽喉疼", "咽痛 喉咙痛"),
            Map.entry("咽喉痛", "咽痛 喉咙痛"),
            Map.entry("咽喉疼痛", "咽痛 喉咙痛"),
            Map.entry("喘不上气", "气短 呼吸困难"),
            Map.entry("喘不过气", "气短 呼吸困难"),
            Map.entry("上不来气", "气短 呼吸困难"),
            Map.entry("呼吸不畅", "气短 呼吸困难"),
            Map.entry("流鼻血", "鼻出血"),
            Map.entry("鼻子出血", "鼻出血"),
            Map.entry("咽不下去", "吞咽困难"),
            Map.entry("吃东西噎", "吞咽困难"),
            // 头面部与神经
            Map.entry("头疼", "头痛"),
            Map.entry("头晕眼花", "头晕 眩晕"),
            Map.entry("头发晕", "头晕"),
            Map.entry("天旋地转", "眩晕"),
            Map.entry("晕眩", "眩晕"),
            Map.entry("晕倒", "晕厥 昏迷"),
            Map.entry("晕过去", "晕厥 昏迷"),
            Map.entry("抽风", "抽搐"),
            Map.entry("牙疼", "牙痛"),
            Map.entry("耳朵疼", "耳痛"),
            Map.entry("耳朵响", "耳鸣"),
            Map.entry("听不见", "耳聋"),
            Map.entry("眼睛干", "眼干"),
            Map.entry("眼睛痒", "眼痒"),
            Map.entry("看不清东西", "视力模糊"),
            Map.entry("看东西模糊", "视力模糊"),
            Map.entry("视物模糊", "视力模糊"),
            Map.entry("视力下降", "视力模糊"),
            Map.entry("爱流泪", "流泪"),
            Map.entry("掉眼泪", "流泪"),
            Map.entry("眼睛发黄", "黄疸"),
            Map.entry("皮肤发黄", "黄疸"),
            // 心胸
            Map.entry("心口疼", "胸痛"),
            Map.entry("心口痛", "胸痛"),
            Map.entry("胸口疼", "胸痛"),
            Map.entry("胸口痛", "胸痛"),
            Map.entry("胸口闷", "胸闷"),
            Map.entry("心慌", "心悸"),
            Map.entry("心跳快", "心悸"),
            Map.entry("心跳加速", "心悸"),
            // 全身与四肢
            Map.entry("没力气", "乏力"),
            Map.entry("浑身没劲", "乏力"),
            Map.entry("没精神", "乏力"),
            Map.entry("疲惫", "乏力 疲乏"),
            Map.entry("腰疼", "腰痛"),
            Map.entry("肩膀疼", "肩痛"),
            Map.entry("膝盖疼", "膝关节痛"),
            Map.entry("腿疼", "腿痛"),
            Map.entry("关节疼", "关节痛"),
            Map.entry("关节酸痛", "关节痛"),
            Map.entry("手麻", "麻木"),
            Map.entry("脚麻", "麻木"),
            Map.entry("手脚麻", "麻木"),
            Map.entry("腿抽筋", "痉挛"),
            Map.entry("抽筋", "痉挛"),
            Map.entry("水肿", "水肿"),
            Map.entry("浮肿", "水肿"),
            Map.entry("脚肿", "水肿"),
            Map.entry("腿肿", "水肿"),
            Map.entry("脸肿", "水肿"),
            // 皮肤
            Map.entry("起疹子", "皮疹"),
            Map.entry("出疹子", "皮疹"),
            Map.entry("长红疹", "皮疹"),
            Map.entry("皮肤痒", "瘙痒"),
            Map.entry("身上痒", "瘙痒"),
            Map.entry("淋巴肿大", "淋巴结肿大"),
            Map.entry("脖子有疙瘩", "淋巴结肿大"),
            // 汗、寒、代谢
            Map.entry("出冷汗", "出汗"),
            Map.entry("冒冷汗", "出汗"),
            Map.entry("出虚汗", "出汗 盗汗"),
            Map.entry("爱出汗", "出汗"),
            Map.entry("夜里出汗", "盗汗"),
            Map.entry("睡觉出汗", "盗汗"),
            Map.entry("怕冷", "畏寒"),
            Map.entry("发冷", "畏寒"),
            Map.entry("打寒战", "寒战"),
            Map.entry("浑身发抖", "寒战"),
            Map.entry("瘦了", "体重下降"),
            Map.entry("变瘦", "体重下降"),
            Map.entry("喝水多", "多饮"),
            Map.entry("总饿", "多食"),
            // 睡眠与口腔
            Map.entry("睡不着", "失眠"),
            Map.entry("失眠多梦", "失眠"),
            Map.entry("嘴干", "口干"),
            Map.entry("口气重", "口臭"),
            Map.entry("刷牙出血", "牙龈出血"),
            // 泌尿
            Map.entry("尿疼", "尿痛"),
            Map.entry("小便疼", "尿痛"),
            Map.entry("小便痛", "尿痛"),
            Map.entry("老想上厕所", "尿频"),
            Map.entry("小便次数多", "尿频"),
            Map.entry("尿血", "血尿"),
            Map.entry("眼睛胀", "眼胀"),
            // ===== 第二轮：日常口语化表达（普通人说法） =====
            // 腹部与消化
            Map.entry("肚子不舒服", "腹痛 腹部不适"),
            Map.entry("肚子难受", "腹痛"),
            Map.entry("肚子不得劲", "腹痛"),
            Map.entry("胃不舒服", "胃痛 胃部不适"),
            Map.entry("胃难受", "胃痛"),
            Map.entry("胃里难受", "胃痛"),
            Map.entry("不消化", "消化不良"),
            Map.entry("消化不好", "消化不良"),
            Map.entry("积食", "消化不良"),
            Map.entry("打嗝", "呃逆"),
            Map.entry("老打嗝", "呃逆"),
            Map.entry("放屁多", "腹胀"),
            Map.entry("屁多", "腹胀"),
            Map.entry("肚子咕咕叫", "肠鸣"),
            Map.entry("大便稀", "腹泻"),
            Map.entry("大便不成形", "腹泻"),
            Map.entry("大便干", "便秘"),
            Map.entry("拉不出来", "便秘"),
            Map.entry("反酸水", "反酸"),
            Map.entry("嘴里反酸", "反酸"),
            Map.entry("呕血", "呕血"),
            Map.entry("吐出血", "呕血"),
            Map.entry("厌食", "食欲不振"),
            Map.entry("吃不下饭", "食欲不振"),
            Map.entry("饿得快", "多食"),
            Map.entry("总想吃", "多食"),
            // 咽喉与呼吸道
            Map.entry("嗓子不舒服", "咽痛 喉咙痛"),
            Map.entry("嗓子难受", "咽痛 喉咙痛"),
            Map.entry("喉咙不舒服", "咽痛 喉咙痛"),
            Map.entry("喉咙难受", "咽痛 喉咙痛"),
            Map.entry("嗓子发炎", "咽痛"),
            Map.entry("喉咙发炎", "咽痛"),
            Map.entry("喉咙有痰", "咳痰"),
            Map.entry("痰多", "咳痰"),
            Map.entry("痰黄", "咳痰"),
            Map.entry("痰白", "咳痰"),
            Map.entry("鼻子干", "鼻干"),
            Map.entry("流清涕", "流涕"),
            Map.entry("流黄涕", "流涕"),
            Map.entry("流浓涕", "流涕"),
            Map.entry("憋气", "气短 呼吸困难"),
            Map.entry("气不够用", "气短 呼吸困难"),
            Map.entry("咳血", "咳血"),
            Map.entry("咳嗽带血", "咳血"),
            Map.entry("着凉", "感冒 畏寒"),
            Map.entry("受凉", "感冒 畏寒"),
            Map.entry("感冒了", "感冒 鼻塞 流涕"),
            Map.entry("上火", "咽痛 口干 口腔溃疡"),
            Map.entry("口干舌燥", "口干"),
            Map.entry("说话费劲", "声音嘶哑"),
            Map.entry("嗓子发干", "咽干"),
            Map.entry("声音沙哑", "声音嘶哑"),
            // 心胸
            Map.entry("心口堵", "胸闷 胸痛"),
            Map.entry("心里堵", "胸闷"),
            Map.entry("心前区疼", "胸痛"),
            Map.entry("胸口发紧", "胸闷"),
            Map.entry("心里发慌", "心悸"),
            Map.entry("心发慌", "心悸"),
            Map.entry("心跳得厉害", "心悸"),
            Map.entry("心脏跳得快", "心悸"),
            Map.entry("前胸疼", "胸痛"),
            // 头面与神经
            Map.entry("眼前发黑", "头晕 晕厥"),
            Map.entry("发黑晕", "头晕"),
            Map.entry("站不稳", "眩晕"),
            Map.entry("走路发飘", "头晕 眩晕"),
            Map.entry("头重脚轻", "头晕 眩晕"),
            Map.entry("昏昏沉沉", "头晕"),
            Map.entry("头昏", "头晕"),
            Map.entry("犯困", "嗜睡 乏力"),
            Map.entry("总想睡", "嗜睡"),
            Map.entry("睡不醒", "嗜睡"),
            Map.entry("睡不踏实", "失眠"),
            Map.entry("容易醒", "失眠"),
            Map.entry("多梦", "失眠"),
            Map.entry("打呼噜", "打鼾"),
            Map.entry("记忆力差", "记忆力减退"),
            Map.entry("记性差", "记忆力减退"),
            Map.entry("忘事", "记忆力减退"),
            Map.entry("脑袋嗡嗡", "头晕"),
            Map.entry("头晕脑胀", "头晕"),
            Map.entry("后脑勺疼", "头痛"),
            Map.entry("太阳穴疼", "头痛"),
            Map.entry("偏头疼", "偏头痛 头痛"),
            // 四肢关节肌肉
            Map.entry("腰酸", "腰痛"),
            Map.entry("腰酸背痛", "腰痛"),
            Map.entry("腰不得劲", "腰痛"),
            Map.entry("背疼", "背痛"),
            Map.entry("后背疼", "背痛"),
            Map.entry("脖子疼", "颈痛"),
            Map.entry("脖颈疼", "颈痛"),
            Map.entry("落枕", "颈痛"),
            Map.entry("肩膀酸", "肩痛"),
            Map.entry("肩周疼", "肩痛"),
            Map.entry("胳膊疼", "臂痛"),
            Map.entry("手臂疼", "臂痛"),
            Map.entry("手抖", "震颤"),
            Map.entry("手发麻", "麻木"),
            Map.entry("腿发麻", "麻木"),
            Map.entry("腿软", "下肢无力 乏力"),
            Map.entry("腿没劲", "乏力"),
            Map.entry("脚底疼", "足跟痛"),
            Map.entry("脚后跟疼", "足跟痛"),
            Map.entry("膝盖酸", "关节痛"),
            Map.entry("骨头疼", "骨痛"),
            Map.entry("浑身疼", "肌肉酸痛"),
            Map.entry("全身疼", "肌肉酸痛"),
            Map.entry("浑身难受", "乏力 不适"),
            Map.entry("全身没劲", "乏力"),
            Map.entry("没劲", "乏力"),
            // 皮肤
            Map.entry("长痘痘", "痤疮 皮疹"),
            Map.entry("长痘", "痤疮 皮疹"),
            Map.entry("起痘", "痤疮 皮疹"),
            Map.entry("脸上长痘", "痤疮 皮疹"),
            Map.entry("脱皮", "脱屑"),
            Map.entry("掉皮", "脱屑"),
            Map.entry("起水泡", "水疱"),
            Map.entry("长水泡", "水疱"),
            Map.entry("皮肤干", "皮肤干燥"),
            Map.entry("皮肤发红", "红斑"),
            Map.entry("红疹", "皮疹"),
            Map.entry("身上有红点", "皮疹"),
            Map.entry("头皮痒", "瘙痒"),
            Map.entry("掉头发", "脱发"),
            Map.entry("掉发", "脱发"),
            Map.entry("头发掉得厉害", "脱发"),
            Map.entry("皮肤过敏", "皮疹 瘙痒"),
            // 泌尿生殖
            Map.entry("起夜多", "夜尿增多"),
            Map.entry("夜尿多", "夜尿增多"),
            Map.entry("晚上老上厕所", "夜尿增多"),
            Map.entry("尿不出来", "排尿困难"),
            Map.entry("尿不出", "排尿困难"),
            Map.entry("排尿费劲", "排尿困难"),
            Map.entry("尿少", "少尿"),
            Map.entry("尿频尿急", "尿频 尿急"),
            Map.entry("痛经", "痛经"),
            Map.entry("月经疼", "痛经"),
            Map.entry("月经不调", "月经不调"),
            Map.entry("月经乱", "月经不调"),
            Map.entry("白带多", "白带异常"),
            Map.entry("私处痒", "瘙痒"),
            Map.entry("下面痒", "瘙痒"),
            // 眼耳口
            Map.entry("眼睛红", "眼红"),
            Map.entry("眼睛有红血丝", "眼红"),
            Map.entry("眼睛肿", "眼肿"),
            Map.entry("眼皮肿", "眼肿"),
            Map.entry("眼睛疼", "眼痛"),
            Map.entry("眼屎多", "眼分泌物增多"),
            Map.entry("眼花", "视力模糊"),
            Map.entry("重影", "复视"),
            Map.entry("看东西重影", "复视"),
            Map.entry("怕光", "畏光"),
            Map.entry("眼睛怕光", "畏光"),
            Map.entry("耳朵嗡嗡响", "耳鸣"),
            Map.entry("耳朵有回声", "耳鸣"),
            Map.entry("耳朵流水", "耳流脓"),
            Map.entry("耳朵流脓", "耳流脓"),
            Map.entry("牙龈肿", "牙龈肿胀"),
            Map.entry("牙床肿", "牙龈肿胀"),
            Map.entry("牙齿松动", "牙松动"),
            Map.entry("口腔溃疡", "口腔溃疡"),
            Map.entry("嘴里长溃疡", "口腔溃疡"),
            Map.entry("嘴上长溃疡", "口腔溃疡"),
            Map.entry("长溃疡", "口腔溃疡"),
            Map.entry("起溃疡", "口腔溃疡"),
            Map.entry("口疮", "口腔溃疡"),
            Map.entry("嘴歪", "面瘫"),
            Map.entry("流口水", "流涎"),
            Map.entry("睡觉流口水", "流涎"),
            // 其他全身
            Map.entry("手脚冰凉", "手足冰冷 畏寒"),
            Map.entry("手脚发凉", "手足冰冷 畏寒"),
            Map.entry("发冷发热", "畏寒 发热"),
            Map.entry("忽冷忽热", "畏寒 发热"),
            Map.entry("低烧", "发热"),
            Map.entry("午后发热", "发热"),
            Map.entry("体温高", "发热"),
            Map.entry("发烧不退", "发热"),
            Map.entry("淋巴结疼", "淋巴结肿大"),
            Map.entry("长包块", "肿块"),
            Map.entry("摸到肿块", "肿块"),
            Map.entry("消瘦", "体重下降")
    );
    /** 用于从"我最近一直咳嗽、还有点发热"这类自然语言中提取症状（口语与规范表达均收录）。 */
    private static final List<String> COMMON_SYMPTOMS = List.of(
            "发热", "发烧", "发高烧", "发低烧", "咳嗽", "干咳", "咳痰", "咳嗽有痰", "有痰", "咽痛", "喉咙痛", "喉咙疼", "咽喉痛", "咽喉疼", "嗓子疼", "嗓子痛", "嗓子哑",
            "头痛", "头疼", "头晕", "头晕眼花", "天旋地转", "眩晕", "乏力", "疲乏", "没力气", "浑身没劲", "没精神", "疲惫", "肌肉酸痛", "关节痛", "关节疼", "关节酸痛",
            "胸痛", "胸口疼", "胸口痛", "心口疼", "胸闷", "胸口闷", "气短", "喘不上气", "喘不过气", "呼吸困难", "心悸", "心慌", "心跳快", "出汗", "冒冷汗", "出冷汗", "出虚汗", "盗汗", "夜里出汗",
            "腹痛", "肚子痛", "肚子疼", "肚痛", "上腹疼痛", "腹胀", "肚子胀", "胀气", "腹泻", "拉肚子", "拉稀", "闹肚子", "恶心", "犯恶心", "想吐", "反胃", "呕吐", "干呕", "食欲不振", "没胃口", "吃不下", "便秘", "拉不出", "便血", "大便带血",
            "多饮", "喝水多", "多尿", "多食", "总饿", "体重下降", "瘦了", "视力模糊", "看东西模糊", "看不清东西", "耳鸣", "耳朵响", "耳聋", "喷嚏", "打喷嚏", "鼻痒",
            "鼻塞", "鼻子不通", "流涕", "流鼻涕", "眼痒", "眼睛痒", "皮疹", "起疹子", "出疹子", "瘙痒", "皮肤痒", "身上痒", "水肿", "浮肿", "脚肿", "失眠", "睡不着", "腰痛", "腰疼", "尿频", "老想上厕所", "尿痛", "小便疼", "尿急",
            "胸骨后疼痛", "牙疼", "牙痛", "肩膀疼", "膝盖疼", "腿疼", "腿痛", "麻木", "手麻", "脚麻", "抽搐", "抽筋", "痉挛", "昏迷", "晕倒", "晕厥", "血尿", "尿血", "口苦", "口干", "嘴干", "口臭", "牙龈出血", "刷牙出血",
            "淋巴结肿大", "淋巴肿大", "畏寒", "怕冷", "寒战", "发热伴寒战", "黄疸", "眼干", "眼睛干", "流泪", "爱流泪", "眼胀", "声音嘶哑", "吞咽困难", "咽不下去", "鼻出血", "流鼻血", "反酸", "烧心", "嗳气", "打饱嗝", "胃痛", "胃疼", "胃灼热"
    );

    private final DiseaseService diseaseService;
    private final DiseaseDrugRelationService relationService;
    private final DrugService drugService;
    private final SelfTestService selfTestService;
    private final PatientService patientService;
    private final PredictionService predictionService;

    @Value("${openai.api-key:}")
    private String openAiApiKey;

    @Value("${deepseek.api.url:}")
    private String deepseekApiUrl;

    @Value("${deepseek.api.key:}")
    private String deepseekApiKey;

    @Value("${deepseek.api.model:deepseek-chat}")
    private String deepseekModel;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostMapping
    public Result<List<PredictionResponse>> predict(@RequestBody PredictionRequest req,
                                                     @AuthenticationPrincipal SecurityUser currentUser) {
        String symptoms = req.getSymptoms();
        if (symptoms == null || symptoms.isBlank()) {
            return Result.error("请输入症状描述");
        }

        List<PredictionResponse> results;

        if (useDeepseek()) {
            results = predictionService.predict(symptoms);
        } else {
            Set<String> keywords = extractSymptomKeywords(symptoms);
            if (keywords.isEmpty()) {
                return Result.error("请输入有效的症状描述");
            }
            keywords = expandKeywordsWithSynonyms(keywords);
            results = matchDiseasesByKeywords(keywords, symptoms);

            if (results.isEmpty() && (openAiApiKey != null && !openAiApiKey.isBlank())) {
                List<String> aiKeywords = extractKeywordsWithAI(symptoms);
                if (!aiKeywords.isEmpty() && !keywords.containsAll(aiKeywords)) {
                    keywords.addAll(aiKeywords);
                    results = matchDiseasesByKeywords(keywords, symptoms);
                }
            }

            if (results.isEmpty()) {
                // 兜底：即使未匹配到明确疾病，也尽量给出与症状相关的参考药品
                List<Drug> refDrugs = findReferenceDrugs(keywords);
                String advice = createFallbackAdvice(symptoms, refDrugs);
                results.add(PredictionResponse.builder()
                        .matchedDisease("未匹配到明确疾病")
                        .confidence(BigDecimal.ZERO)
                        .disease(null)
                        .recommendedDrugs(refDrugs)
                        .advice(advice)
                        .build());
            }
        }

        results.sort((a, b) -> b.getConfidence().compareTo(a.getConfidence()));

        if (currentUser != null && currentUser.getRole() == 3 && !results.isEmpty()) {
            Patient patient = patientService.lambdaQuery()
                    .eq(Patient::getUserId, currentUser.getId()).one();
            if (patient != null) {
                SelfTest test = new SelfTest();
                test.setPatientId(patient.getId());
                test.setInputSymptoms(symptoms);
                test.setMatchedDisease(results.get(0).getMatchedDisease());
                test.setConfidence(results.get(0).getConfidence());
                selfTestService.save(test);
            }
        }

        return Result.ok(results);
    }

    private String buildAdvice(Disease disease, List<Drug> drugs, BigDecimal confidence) {
        String diseaseName = disease.getDiseaseName();
        StringBuilder sb = new StringBuilder();
        sb.append("可能匹配疾病：").append(diseaseName);

        if (disease.getDepartment() != null && !disease.getDepartment().isBlank()) {
            sb.append("（建议就诊科室：").append(disease.getDepartment()).append("）");
        }
        sb.append("。");

        if (disease.getDrugTreatment() != null && !disease.getDrugTreatment().isBlank()) {
            String dt = disease.getDrugTreatment();
            sb.append("治疗方案参考：").append(dt, 0, Math.min(200, dt.length())).append("。");
        }

        if (drugs != null && !drugs.isEmpty()) {
            List<String> drugNames = new ArrayList<>();
            for (Drug drug : drugs) {
                if (drug != null && drug.getDrugName() != null && !drug.getDrugName().isBlank()) {
                    drugNames.add(drug.getDrugName());
                }
            }
            if (!drugNames.isEmpty()) {
                sb.append("推荐参考药品：").append(String.join("、", drugNames.stream().limit(8).toList()));
                sb.append("。");
            }
        }
        sb.append("本结果仅为自测参考，请结合症状及时就医，遵医嘱用药。");
        return sb.toString();
    }

    private List<PredictionResponse> matchDiseasesByKeywords(Set<String> keywords, String symptoms) {
        List<Disease> allDiseases = diseaseService.getAllForPrediction();
        List<PredictionResponse> results = new ArrayList<>();
        if (allDiseases == null || allDiseases.isEmpty()) {
            return results;
        }

        Set<String> normalizedKeywords = expandKeywordsWithSynonyms(keywords).stream()
                .map(keyword -> normalizeKeyword(keyword))
                .filter(s -> s != null && !s.isBlank())
                .collect(Collectors.toCollection(LinkedHashSet::new));

        for (Disease disease : allDiseases) {
            String diseaseName = defaultString(disease.getDiseaseName());
            String desc = defaultString(disease.getDescription());
            String symptomField = defaultString(disease.getSymptoms());
            String symptomsOverview = defaultString(disease.getSymptomsOverview());
            String symptomsDetail = defaultString(disease.getSymptomsDetail());
            String etiology = defaultString(disease.getEtiology());
            String etiologyOverview = defaultString(disease.getEtiologyOverview());
            String department = defaultString(disease.getDepartment());
            String affectedArea = defaultString(disease.getAffectedArea());
            String drugTreatment = defaultString(disease.getDrugTreatment());
            String examination = defaultString(disease.getExamination());
            String differentialDiagnosis = defaultString(disease.getDifferentialDiagnosis());
            // 双向归一化：疾病侧文本与输入关键词统一经过同义词替换，口语表达可匹配规范字段
            String normalizedName = normalizeTextForSearch(diseaseName);
            String combined = normalizeTextForSearch((diseaseName + " " + desc + " " + symptomField + " "
                    + symptomsOverview + " " + symptomsDetail + " " + etiology + " "
                    + etiologyOverview + " " + department + " " + affectedArea + " "
                    + drugTreatment + " " + examination + " " + differentialDiagnosis).toLowerCase());

            int exactMatchCount = 0;
            int weightedScore = 0;
            for (String kw : normalizedKeywords) {
                String normalizedKw = kw.toLowerCase();
                if (normalizedKw.length() < 2) {
                    continue;
                }
                boolean inDiseaseName = containsSymptom(normalizedName, normalizedKw);
                boolean inSymptoms = containsSymptom(symptomField, normalizedKw)
                        || containsSymptom(symptomsOverview, normalizedKw)
                        || containsSymptom(symptomsDetail, normalizedKw);
                boolean inDesc = containsSymptom(desc, normalizedKw)
                        || containsSymptom(etiology, normalizedKw)
                        || containsSymptom(etiologyOverview, normalizedKw)
                        || containsSymptom(department, normalizedKw)
                        || containsSymptom(affectedArea, normalizedKw);
                if (inDiseaseName || inSymptoms || inDesc) {
                    exactMatchCount++;
                    weightedScore += inDiseaseName ? 3 : 1;
                    weightedScore += inSymptoms ? 2 : 0;
                    weightedScore += inDesc ? 1 : 0;
                }
            }

            if (exactMatchCount == 0) {
                // 兜底：关键词在归一化全文中命中，但未命中上述核心字段时仍按弱匹配处理
                int combinedHits = 0;
                for (String kw : normalizedKeywords) {
                    if (kw.length() >= 2 && containsSymptom(combined, kw.toLowerCase())) {
                        combinedHits++;
                    }
                }
                if (combinedHits == 0) {
                    continue;
                }
                exactMatchCount = combinedHits;
            }

            double scoreRatio = Math.min(1.0, exactMatchCount / Math.max(1.0, normalizedKeywords.size()));
            // 置信度 = 匹配质量(症状/病名/描述加权) × 70% + 关键词覆盖率 × 30%，归一化到 0-0.98
            // 避免"仅描述提及一个常见症状"的弱匹配也封顶 98%，提升医学判断区分度
            double qualityRatio = Math.min(1.0, weightedScore / (6.0 * normalizedKeywords.size()));
            int confidenceValue = (int) Math.round(100 * Math.min(0.98, qualityRatio * 0.7 + scoreRatio * 0.3));
            confidenceValue = Math.max(20, Math.min(98, confidenceValue));
            BigDecimal confidence = BigDecimal.valueOf(confidenceValue).setScale(2, RoundingMode.HALF_UP);

            List<DiseaseDrugRelation> relations = relationService.getForPrediction(disease.getId());
            List<Drug> drugs = relations.stream()
                    .map(r -> drugService.getById(r.getDrugId()))
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());

            // 如果关系表药品不足，通过疾病名称和症状智能补充搜索药品
            if (drugs.size() < 3) {
                List<Drug> smartMatchedDrugs = smartMatchDrugsForDisease(disease, normalizedKeywords);
                for (Drug smartDrug : smartMatchedDrugs) {
                    boolean alreadyExists = drugs.stream().anyMatch(d -> d.getId().equals(smartDrug.getId()));
                    if (!alreadyExists) {
                        drugs.add(smartDrug);
                    }
                }
            }
            // 统一限制推荐药品数量，避免页面渲染过长的药品列表
            if (drugs.size() > 8) {
                drugs = drugs.subList(0, 8);
            }

            String advice = buildAdvice(disease, drugs, confidence);

            results.add(PredictionResponse.builder()
                    .matchedDisease(diseaseName)
                    .confidence(confidence)
                    .disease(disease)
                    .recommendedDrugs(drugs)
                    .advice(advice)
                    .build());
        }

        results.sort((a, b) -> b.getConfidence().compareTo(a.getConfidence()));
        return results;
    }

    private List<String> extractKeywordsWithAI(String symptoms) {
        try {
            String prompt = "你是一个专业中文医疗助手。请从下面的症状描述中提取 3-5 个最可能的关键词，关键词应简短、精确，仅返回词语，使用逗号分隔，不要包含解释。\n症状描述：" + symptoms;
            String resultText = callAiService(prompt);
            if (resultText == null || resultText.isBlank()) {
                return localExtractKeywords(symptoms);
            }
            return Arrays.stream(resultText.split("[，,;；\n]+"))
                    .map(String::trim)
                    .filter(s -> !s.isBlank())
                    .map(s -> s.replaceAll("^\\W+|\\W+$", ""))
                    .filter(s -> s.length() >= 2)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.warn("AI keyword extraction exception", e);
            return localExtractKeywords(symptoms);
        }
    }

    private List<String> localExtractKeywords(String symptoms) {
        if (symptoms == null || symptoms.isBlank()) return Collections.emptyList();
        return extractSymptomKeywords(symptoms).stream()
                .map(String::trim)
                .filter(s -> s.length() >= 2)
                .distinct()
                .limit(5)
                .collect(Collectors.toList());
    }

    private Set<String> extractSymptomKeywords(String symptoms) {
        Set<String> extracted = new LinkedHashSet<>();
        if (symptoms == null || symptoms.isBlank()) {
            return extracted;
        }

        // 保留用户输入中以标点分隔的词，兼容原有输入方式。
        Arrays.stream(symptoms.split("[，,\\s、;；。！？!?：:]+"))
                .map(String::trim)
                .filter(s -> s.length() >= 2)
                .forEach(extracted::add);

        // "部位+不舒服/难受/不得劲" 类开放表达（如"胃里不舒服""嗓子有点难受"）按部位映射到规范症状
        for (String token : symptoms.split("[，,\\s、;；。！？!?：:]+")) {
            addDiscomfortMappings(token, extracted);
        }

        // 再从整句中查找症状词，支持自然语言描述。
        for (String symptom : COMMON_SYMPTOMS) {
            if (symptoms.contains(symptom)) {
                extracted.add(symptom);
            }
        }
        // 词典中收录的口语变体同样参与整句扫描，新增词自动生效，无需再同步 COMMON_SYMPTOMS
        for (String symptom : SYMPTOM_SYNONYMS.keySet()) {
            if (symptom.length() >= 2 && symptoms.contains(symptom)) {
                extracted.add(symptom);
            }
        }
        return expandKeywordsWithSynonyms(extracted);
    }

    /** 处理"肚子不舒服""胃里难受""腰也酸""腿发麻"等日常说法：按出现部位+症状后缀映射到规范症状词。 */
    private void addDiscomfortMappings(String token, Set<String> extracted) {
        if (token == null || token.isBlank()) {
            return;
        }
        String[] longSuffixes = {"不舒服", "难受", "不得劲", "发麻", "发酸", "发痒", "发胀", "发晕", "发闷"};
        String suffix = null;
        for (String s : longSuffixes) {
            if (token.endsWith(s)) {
                suffix = s;
                break;
            }
        }
        if (suffix == null) {
            char last = token.charAt(token.length() - 1);
            if ("痛疼酸胀麻痒晕闷肿".indexOf(last) >= 0) {
                suffix = String.valueOf(last);
            }
        }
        if (suffix == null) {
            return;
        }
        String body = token.substring(0, token.length() - suffix.length()).trim();
        String[][] locations = {
                {"肚子", "腹痛"}, {"胃", "胃痛"}, {"嗓子", "咽痛 喉咙痛"}, {"喉咙", "咽痛 喉咙痛"},
                {"咽喉", "咽痛 喉咙痛"}, {"胸口", "胸闷 胸痛"}, {"心口", "胸闷 胸痛"},
                {"后背", "背痛"}, {"背", "背痛"}, {"腰", "腰痛"}, {"头", "头痛"},
                {"眼睛", "眼干 眼痛"}, {"耳朵", "耳痛 耳鸣"}, {"肩膀", "肩痛"},
                {"脖子", "颈痛"}, {"膝盖", "关节痛"}, {"胳膊", "臂痛"}, {"手臂", "臂痛"},
                {"腿", "腿痛"}, {"脚", "足痛"}, {"浑身", "乏力"}, {"全身", "乏力"}
        };
        for (String[] loc : locations) {
            if (body.contains(loc[0])) {
                String mapped;
                char c = suffix.charAt(suffix.length() - 1);
                if (c == '麻') {
                    mapped = "麻木";
                } else if (c == '酸') {
                    mapped = "膝盖".equals(loc[0]) ? "关节痛" : "酸痛";
                } else if (c == '痒') {
                    mapped = "瘙痒";
                } else if (c == '胀') {
                    mapped = "腹胀";
                } else if (c == '晕') {
                    mapped = "头晕";
                } else if (c == '闷') {
                    mapped = "胸闷";
                } else if (c == '肿') {
                    mapped = "水肿";
                } else {
                    mapped = loc[1];
                }
                for (String part : mapped.split("\\s+")) {
                    if (part.length() >= 2) {
                        extracted.add(part);
                    }
                }
                break;
            }
        }
    }

    private Set<String> expandKeywordsWithSynonyms(Set<String> keywords) {
        Set<String> expanded = new LinkedHashSet<>(keywords);
        for (String key : keywords) {
            String normalized = normalizeKeyword(key);
            if (normalized.isBlank()) {
                continue;
            }
            // 多词归一结果（如"嗓子疼"→"咽痛 喉咙痛"）拆成独立关键词参与匹配
            for (String part : normalized.split("\\s+")) {
                if (!part.isBlank() && !expanded.contains(part)) {
                    expanded.add(part);
                }
            }
        }
        return expanded;
    }

    /**
     * 口语化症状文本 → 规范医学表达。按词长降序替换，避免短词先替换破坏长词。
     * 用于输入关键词与疾病文本两侧，保证"嗓子疼"与"咽痛/喉咙痛"可互相匹配。
     */
    private String normalizeTextForSearch(String text) {
        if (text == null || text.isBlank()) {
            return text == null ? "" : text;
        }
        String normalized = text;
        List<Map.Entry<String, String>> entries = new ArrayList<>(SYMPTOM_SYNONYMS.entrySet());
        entries.sort((a, b) -> Integer.compare(b.getKey().length(), a.getKey().length()));
        for (Map.Entry<String, String> entry : entries) {
            normalized = normalized.replace(entry.getKey(), entry.getValue());
        }
        return normalized;
    }

    private String normalizeKeyword(String keyword) {
        if (keyword == null) {
            return "";
        }
        return normalizeTextForSearch(keyword.trim());
    }

    private boolean containsSymptom(String text, String keyword) {
        if (text == null || keyword == null || keyword.isBlank()) {
            return false;
        }
        String source = text.toLowerCase();
        String target = keyword.toLowerCase();
        if (source.contains(target)) {
            return true;
        }
        // 数据中常见"上腹疼痛"，用户常说"腹痛"；去掉"疼"后进行兼容匹配。
        if (source.replace("疼", "").contains(target.replace("疼", ""))) {
            return true;
        }
        // 进一步去除痛/痒/胀/酸/麻等后缀后做包含匹配，核心词至少保留2字，避免单字误匹配。
        String srcStem = source.replace("疼", "").replace("痛", "").replace("痒", "")
                .replace("胀", "").replace("酸", "").replace("麻", "");
        String tgtStem = target.replace("疼", "").replace("痛", "").replace("痒", "")
                .replace("胀", "").replace("酸", "").replace("麻", "");
        return tgtStem.length() >= 2 && srcStem.contains(tgtStem);
    }

    private String createFallbackAdvice(String symptoms, List<Drug> drugs) {
        StringBuilder advice = new StringBuilder();
        if (drugs != null && !drugs.isEmpty()) {
            advice.append("本结果为智能参考，以下药品为推荐参考。请结合症状及时就医并遵医嘱用药。");
        } else {
            advice.append("本结果为智能参考，当前药品数据库未命中具体推荐，建议咨询医生或药师。 ");
        }
        String aiSuggestion = generateAiSuggestion(symptoms);
        if (!aiSuggestion.isBlank()) {
            advice.append("AI智能建议：").append(aiSuggestion);
        } else {
            advice.append("如症状持续或加重，建议到医院进一步检查。");
        }
        return advice.toString();
    }

    private List<Drug> findReferenceDrugs(Set<String> keywords) {
        if (keywords == null || keywords.isEmpty()) {
            return Collections.emptyList();
        }
        List<String> usableKeywords = keywords.stream()
                .map(keyword -> normalizeKeyword(keyword))
                .filter(k -> k != null && k.length() >= 2)
                .distinct()
                .limit(8)
                .toList();
        if (usableKeywords.isEmpty()) {
            return Collections.emptyList();
        }
        return drugService.lambdaQuery()
                .and(wrapper -> {
                    for (String keyword : usableKeywords) {
                        wrapper.or().like(Drug::getIndication, keyword)
                                .or().like(Drug::getDrugName, keyword)
                                .or().like(Drug::getDrugCategory, keyword);
                    }
                })
                .last("LIMIT 6")
                .list();
    }

    private PredictionResponse buildUncertainPrediction(String symptoms, Set<String> keywords) {
        List<Drug> drugs = findReferenceDrugs(keywords);
        String advice = createFallbackAdvice(symptoms, drugs);
        return PredictionResponse.builder()
                .matchedDisease("症状相关参考（待进一步判断）")
                .confidence(BigDecimal.valueOf(20).setScale(2, RoundingMode.HALF_UP))
                .disease(null)
                .recommendedDrugs(drugs)
                .advice(advice)
                .build();
    }

    private List<Drug> smartMatchDrugsForDisease(Disease disease, Set<String> symptomKeywords) {
        List<Drug> matchedDrugs = new ArrayList<>();
        try {
            List<String> searchKeywords = new ArrayList<>();

            if (disease.getDiseaseName() != null && !disease.getDiseaseName().isBlank()) {
                searchKeywords.add(disease.getDiseaseName().trim());
            }

            if (symptomKeywords != null && !symptomKeywords.isEmpty()) {
                int count = 0;
                for (String kw : symptomKeywords) {
                    if (count >= 5) break;
                    if (kw != null && kw.length() >= 2) {
                        searchKeywords.add(kw.trim());
                        count++;
                    }
                }
            }

            if (disease.getSymptoms() != null && !disease.getSymptoms().isBlank()) {
                String[] parts = disease.getSymptoms().split("[，,。、；;\\s]+");
                int count = 0;
                for (String p : parts) {
                    if (count >= 3) break;
                    p = p.trim();
                    // 归一化后再用于药品适应症检索，提高命中率
                    String normalizedPart = normalizeTextForSearch(p);
                    for (String sub : normalizedPart.split("\\s+")) {
                        if (sub.length() >= 2 && !searchKeywords.contains(sub)) {
                            searchKeywords.add(sub);
                            count++;
                        }
                    }
                }
            }

            if (searchKeywords.isEmpty()) {
                return matchedDrugs;
            }

            for (String keyword : searchKeywords) {
                if (keyword == null || keyword.length() < 2) continue;

                List<Drug> byIndication = drugService.lambdaQuery()
                        .like(Drug::getIndication, keyword)
                        .last("LIMIT 3")
                        .list();
                if (byIndication != null) {
                    for (Drug d : byIndication) {
                        boolean exists = matchedDrugs.stream().anyMatch(m -> m.getId().equals(d.getId()));
                        if (!exists) matchedDrugs.add(d);
                    }
                }

                List<Drug> byCategory = drugService.lambdaQuery()
                        .like(Drug::getDrugCategory, keyword)
                        .last("LIMIT 2")
                        .list();
                if (byCategory != null) {
                    for (Drug d : byCategory) {
                        boolean exists = matchedDrugs.stream().anyMatch(m -> m.getId().equals(d.getId()));
                        if (!exists) matchedDrugs.add(d);
                    }
                }

                List<Drug> byName = drugService.lambdaQuery()
                        .like(Drug::getDrugName, keyword)
                        .last("LIMIT 2")
                        .list();
                if (byName != null) {
                    for (Drug d : byName) {
                        boolean exists = matchedDrugs.stream().anyMatch(m -> m.getId().equals(d.getId()));
                        if (!exists) matchedDrugs.add(d);
                    }
                }

                if (matchedDrugs.size() >= 6) break;
            }

            if (matchedDrugs.size() > 6) {
                matchedDrugs = matchedDrugs.subList(0, 6);
            }

        } catch (Exception e) {
            log.warn("Smart drug matching error for disease: {}", disease.getDiseaseName(), e);
        }
        return matchedDrugs;
    }

    private String generateAiSuggestion(String symptoms) {
        if (!useDeepseek() && (openAiApiKey == null || openAiApiKey.isBlank())) {
            return "当前症状未匹配到明确疾病或关联药品，不建议自行用药；如症状持续、加重或出现危险信号，请及时就医。";
        }
        try {
            String prompt = "你是一个专业中文医疗助手。根据以下症状描述，给出 2-3 句具体对症建议，说明症状对应的治疗方向或缓解措施，避免过于笼统，并不要只说休息和多喝水。\n症状描述：" + symptoms;
            String resultText = callAiService(prompt);
            if (resultText == null || resultText.isBlank()) {
                return "当前症状未匹配到明确疾病或关联药品，不建议自行用药；如症状持续、加重或出现危险信号，请及时就医。";
            }
            return resultText.trim();
        } catch (Exception e) {
            log.warn("AI suggestion exception", e);
            return "当前症状未匹配到明确疾病或关联药品，不建议自行用药；如症状持续、加重或出现危险信号，请及时就医。";
        }
    }

    private String callAiService(String prompt) throws IOException, InterruptedException {
        if (useDeepseek()) {
            String body = objectMapper.writeValueAsString(Map.of(
                    "model", deepseekModel,
                    "messages", List.of(
                            Map.of("role", "system", "content", "你是一个中文医疗助手。"),
                            Map.of("role", "user", "content", prompt)
                    ),
                    "temperature", 0.4,
                    "max_tokens", 160
            ));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(deepseekApiUrl))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + deepseekApiKey)
                    .timeout(Duration.ofSeconds(4))
                    .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() == 200) {
                JsonNode root = objectMapper.readTree(response.body());
                JsonNode textNode = root.at("/choices/0/message/content");
                if (!textNode.isMissingNode() && textNode.isTextual()) {
                    return textNode.asText();
                }
            }
            log.warn("DeepSeek AI request failed: {}", response.body());
            if (openAiApiKey != null && !openAiApiKey.isBlank()) {
                return callOpenAi(prompt);
            }
            return null;
        }
        return callOpenAi(prompt);
    }

    private String callOpenAi(String prompt) throws IOException, InterruptedException {
        String body = objectMapper.writeValueAsString(Map.of(
                "model", "gpt-3.5-turbo",
                "messages", List.of(
                        Map.of("role", "system", "content", "你是一个中文医疗助手。"),
                        Map.of("role", "user", "content", prompt)
                ),
                "temperature", 0.4,
                "max_tokens", 160
        ));
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(OPENAI_URL))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + openAiApiKey)
                .timeout(Duration.ofSeconds(4))
                .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() == 200) {
            JsonNode root = objectMapper.readTree(response.body());
            JsonNode textNode = root.at("/choices/0/message/content");
            if (!textNode.isMissingNode() && textNode.isTextual()) {
                return textNode.asText();
            }
        }
        log.warn("OpenAI request failed: {}", response.body());
        return null;
    }

    private boolean useDeepseek() {
        return deepseekApiUrl != null && !deepseekApiUrl.isBlank()
                && deepseekApiKey != null && !deepseekApiKey.isBlank();
    }

    private String defaultString(String value) {
        return value != null ? value : "";
    }

    @PostMapping("/demo")
    public Result<Map<String, Object>> predictDemo(@RequestBody PredictionRequest req,
                                                    @AuthenticationPrincipal SecurityUser currentUser) {
        String symptoms = req.getSymptoms();
        Map<String, Object> resp = new HashMap<>();
        if (symptoms == null || symptoms.isBlank()) {
            resp.put("drugNames", Collections.emptyList());
            resp.put("advice", "请输入症状描述。 ⚠️本内容仅为毕业设计演示，不具备临床诊疗作用，不能作为用药依据，患病请前往医院遵医嘱");
            return Result.ok(resp);
        }

        Set<String> keywords = extractSymptomKeywords(symptoms);
        if (useDeepseek() || (openAiApiKey != null && !openAiApiKey.isBlank())) {
            keywords.addAll(extractKeywordsWithAI(symptoms));
            keywords = expandKeywordsWithSynonyms(keywords);
        }

        List<PredictionResponse> matchedResults = matchDiseasesByKeywords(keywords, symptoms);
        if (matchedResults.isEmpty()) {
            matchedResults = new ArrayList<>();
            matchedResults.add(buildUncertainPrediction(symptoms, keywords));
        }
        List<Drug> matchedDrugs = matchedResults.isEmpty()
                ? Collections.emptyList()
                : matchedResults.get(0).getRecommendedDrugs();
        List<String> drugNames = matchedDrugs.stream()
                .map(Drug::getDrugName)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
        if (drugNames.size() > 6) drugNames = drugNames.subList(0, 6);

        String advice = matchedResults.isEmpty()
                ? createFallbackAdvice(symptoms, Collections.emptyList())
                : matchedResults.get(0).getAdvice();
        advice = advice + "\n\n⚠️本内容仅为毕业设计演示，不具备临床诊疗作用，不能作为用药依据，患病请前往医院遵医嘱";

        resp.put("drugNames", drugNames);
        resp.put("matchedResults", matchedResults);
        resp.put("advice", advice);

        saveSelfTest(currentUser, symptoms, matchedResults.get(0));
        return Result.ok(resp);
    }

    private void saveSelfTest(SecurityUser currentUser, String symptoms, PredictionResponse result) {
        if (currentUser == null || currentUser.getRole() != 3) {
            return;
        }
        Patient patient = patientService.lambdaQuery()
                .eq(Patient::getUserId, currentUser.getId()).one();
        if (patient == null) {
            log.warn("Patient profile not found for self-test user {}", currentUser.getId());
            return;
        }
        SelfTest test = new SelfTest();
        test.setPatientId(patient.getId());
        test.setInputSymptoms(symptoms);
        test.setMatchedDisease(result.getMatchedDisease());
        test.setConfidence(result.getConfidence());
        selfTestService.save(test);
    }

    private String generateDemoAdvice(String symptoms, List<String> drugNames) {
        if (!useDeepseek() && (openAiApiKey == null || openAiApiKey.isBlank())) {
            return "如出现发热或咳嗽，可优先考虑退热、止咳或祛痰类对症治疗；若症状严重或持续，请及时就医。";
        }
        try {
            String drugText = drugNames == null || drugNames.isEmpty() ? "" : "推荐药品：" + String.join("、", drugNames) + "。";
            String prompt = "你是一个专业中文医疗助手。根据以下症状描述和推荐药品名称，给出 2-3 句具体的对症缓解建议，说明症状对应的用药方向或缓解措施，避免过于笼统，不要给出具体药品剂量。\n症状描述：" + symptoms + "\n" + drugText;
            String resultText = callAiService(prompt);
            if (resultText == null || resultText.isBlank()) {
                return "如出现发热或咳嗽，可优先考虑退热、止咳或祛痰类对症治疗；若症状严重或持续，请及时就医。";
            }
            return resultText.trim();
        } catch (Exception e) {
            log.warn("Demo AI advice exception", e);
            return "如出现发热或咳嗽，可优先考虑退热、止咳或祛痰类对症治疗；若症状严重或持续，请及时就医。";
        }
    }

    private List<PredictionResponse> enhanceWithDeepSeekAnalysis(String symptoms, List<PredictionResponse> existingResults, Set<String> keywords) {
        try {
            List<Disease> allDiseases = diseaseService.getAllForPrediction();
            List<Drug> allDrugs = drugService.list();

            StringBuilder diseaseContext = new StringBuilder();
            if (allDiseases != null && !allDiseases.isEmpty()) {
                diseaseContext.append("【参考疾病库（部分）：\n");
                int count = 0;
                for (Disease d : allDiseases) {
                    if (count >= 50) break;
                    diseaseContext.append("- ").append(d.getDiseaseName());
                    if (d.getSymptoms() != null && !d.getSymptoms().isBlank()) {
                        diseaseContext.append("（症状：").append(d.getSymptoms(), 0, Math.min(100, d.getSymptoms().length())).append("）");
                    }
                    if (d.getDescription() != null && !d.getDescription().isBlank()) {
                        diseaseContext.append(" [描述：").append(d.getDescription(), 0, Math.min(100, d.getDescription().length())).append("]");
                    }
                    diseaseContext.append("\n");
                    count++;
                }
            }

            StringBuilder drugContext = new StringBuilder();
            if (allDrugs != null && !allDrugs.isEmpty()) {
                drugContext.append("【参考药品库（部分）：\n");
                int count = 0;
                for (Drug d : allDrugs) {
                    if (count >= 50) break;
                    drugContext.append("- ").append(d.getDrugName());
                    if (d.getIndication() != null && !d.getIndication().isBlank()) {
                        drugContext.append("（适应症：").append(d.getIndication(), 0, Math.min(80, d.getIndication().length())).append("）");
                    }
                    if (d.getDrugCategory() != null && !d.getDrugCategory().isBlank()) {
                        drugContext.append(" [分类：").append(d.getDrugCategory()).append("]");
                    }
                    drugContext.append("\n");
                    count++;
                }
            }

            StringBuilder existingResultContext = new StringBuilder();
            if (existingResults != null && !existingResults.isEmpty()) {
                existingResultContext.append("【本地关键词匹配结果（供参考，可修正或补充）：\n");
                for (int i = 0; i < Math.min(5, existingResults.size()); i++) {
                    PredictionResponse r = existingResults.get(i);
                    existingResultContext.append("- ").append(r.getMatchedDisease())
                            .append("（置信度：").append(r.getConfidence()).append("）");
                    if (r.getRecommendedDrugs() != null && !r.getRecommendedDrugs().isEmpty()) {
                        existingResultContext.append(" [推荐药：");
                        for (int j = 0; j < Math.min(3, r.getRecommendedDrugs().size()); j++) {
                            if (j > 0) existingResultContext.append("、");
                            existingResultContext.append(r.getRecommendedDrugs().get(j).getDrugName());
                        }
                        existingResultContext.append("]");
                    }
                    existingResultContext.append("\n");
                }
            }

            String prompt = "你是一个经验丰富的全科医学专家AI助手。请根据用户的症状描述，结合提供的疾病和药品知识库，进行专业的医学分析。\n\n"
                    + "【用户症状描述】\n" + symptoms + "\n\n"
                    + "【提取的症状关键词】\n" + String.join("、", keywords) + "\n\n"
                    + diseaseContext.toString() + "\n"
                    + drugContext.toString() + "\n"
                    + existingResultContext.toString() + "\n"
                    + "请严格按以下JSON格式返回分析结果（不要包含任何其他文字，只返回纯JSON）：\n"
                    + "{\n"
                    + "  \"analyses\": [\n"
                    + "    {\n"
                    + "      \"diseaseName\": \"疾病名称\",\n"
                    + "      \"confidence\": 85,\n"
                    + "      \"diseaseOverview\": \"疾病概述（1-2句）\",\n"
                    + "      \"possibleCauses\": \"可能病因（列举2-3个可能原因）\",\n"
                    + "      \"typicalSymptoms\": \"典型症状描述\",\n"
                    + "      \"diagnosticSuggestions\": \"诊断建议（建议做什么检查）\",\n"
                    + "      \"treatmentDirections\": \"治疗方向（药物治疗、非药物治疗）\",\n"
                    + "      \"recommendedDrugs\": [\"药品1\", \"药品2\"],\n"
                    + "      \"lifestyleAdvice\": \"生活方式建议\",\n"
                    + "      \"riskWarnings\": \"风险警示（什么情况需要立即就医）\",\n"
                    + "      \"differentialDiagnoses\": [\"鉴别诊断1\", \"鉴别诊断2\"]\n"
                    + "    }\n"
                    + "  ],\n"
                    + "  \"overallSummary\": \"整体分析总结（2-3句话概括用户可能的健康状况和就医建议）\"\n"
                    + "}\n\n"
                    + "要求：\n"
                    + "1. 返回1-3个最可能的疾病诊断，按可能性从高到低排序\n"
                    + "2. 每个诊断的置信度为0-100的整数\n"
                    + "3. 推荐药品请从参考药品库中选择最匹配的，也可补充常见药品\n"
                    + "4. 所有内容务必专业但避免具体剂量\n"
                    + "5. 必须强调：本分析仅供参考，不能替代医生诊断，患病请及时就医";

            String resultText = callAiServiceWithExtendedTimeout(prompt);
            if (resultText == null || resultText.isBlank()) {
                return existingResults;
            }

            return parseDeepSeekAnalysisResult(resultText, existingResults, symptoms);
        } catch (Exception e) {
            log.warn("DeepSeek enhanced analysis exception", e);
            return existingResults;
        }
    }

    private List<PredictionResponse> parseDeepSeekAnalysisResult(String aiText, List<PredictionResponse> existingResults, String symptoms) {
        try {
            String jsonStr = extractJsonFromText(aiText);
            if (jsonStr == null || jsonStr.isBlank()) {
                return existingResults;
            }

            JsonNode root = objectMapper.readTree(jsonStr);
            JsonNode analysesNode = root.get("analyses");
            String overallSummary = root.has("overallSummary") ? root.get("overallSummary").asText("") : "";

            List<PredictionResponse> enhancedResults = new ArrayList<>();

            if (analysesNode != null && analysesNode.isArray()) {
                for (JsonNode analysis : analysesNode) {
                    try {
                        String diseaseName = analysis.has("diseaseName") ? analysis.get("diseaseName").asText("") : "";
                        if (diseaseName.isBlank()) continue;

                        int confidenceVal = analysis.has("confidence") ? analysis.get("confidence").asInt(50) : 50;
                        confidenceVal = Math.max(20, Math.min(98, confidenceVal));
                        BigDecimal confidence = BigDecimal.valueOf(confidenceVal).setScale(2, RoundingMode.HALF_UP);

                        Disease matchedDisease = findDiseaseByName(diseaseName);

                        List<String> drugNames = new ArrayList<>();
                        JsonNode drugsNode = analysis.get("recommendedDrugs");
                        if (drugsNode != null && drugsNode.isArray()) {
                            for (JsonNode dn : drugsNode) {
                                if (dn.isTextual()) {
                                    drugNames.add(dn.asText());
                                }
                            }
                        }
                        List<Drug> matchedDrugs = findDrugsByNames(drugNames);

                        String diseaseOverview = analysis.has("diseaseOverview") ? analysis.get("diseaseOverview").asText("") : "";
                        String possibleCauses = analysis.has("possibleCauses") ? analysis.get("possibleCauses").asText("") : "";
                        String typicalSymptoms = analysis.has("typicalSymptoms") ? analysis.get("typicalSymptoms").asText("") : "";
                        String diagnosticSuggestions = analysis.has("diagnosticSuggestions") ? analysis.get("diagnosticSuggestions").asText("") : "";
                        String treatmentDirections = analysis.has("treatmentDirections") ? analysis.get("treatmentDirections").asText("") : "";
                        String lifestyleAdvice = analysis.has("lifestyleAdvice") ? analysis.get("lifestyleAdvice").asText("") : "";
                        String riskWarnings = analysis.has("riskWarnings") ? analysis.get("riskWarnings").asText("") : "";

                        List<String> differentialDiagnoses = new ArrayList<>();
                        JsonNode ddNode = analysis.get("differentialDiagnoses");
                        if (ddNode != null && ddNode.isArray()) {
                            for (JsonNode d : ddNode) {
                                if (d.isTextual()) differentialDiagnoses.add(d.asText());
                            }
                        }

                        String advice = buildAdvice(matchedDisease, matchedDrugs, confidence);


                        PredictionResponse.PredictionResponseBuilder builder = PredictionResponse.builder()
                                .matchedDisease(diseaseName)
                                .confidence(confidence)
                                .disease(matchedDisease)
                                .recommendedDrugs(matchedDrugs)
                                .advice(advice)
                                .diseaseOverview(diseaseOverview)
                                .possibleCauses(possibleCauses)
                                .typicalSymptoms(typicalSymptoms)
                                .diagnosticSuggestions(diagnosticSuggestions)
                                .treatmentDirections(treatmentDirections)
                                .lifestyleAdvice(lifestyleAdvice)
                                .riskWarnings(riskWarnings)
                                .differentialDiagnoses(differentialDiagnoses)
                                .aiAnalysisSummary(overallSummary);

                        enhancedResults.add(builder.build());
                    } catch (Exception e) {
                        log.warn("Parse single analysis error", e);
                    }
                }
            }

            if (enhancedResults.isEmpty()) {
                return existingResults;
            }

            if (existingResults != null) {
                for (PredictionResponse er : existingResults) {
                    boolean alreadyIn = enhancedResults.stream().anyMatch(e -> e.getMatchedDisease().equals(er.getMatchedDisease()));
                    if (!alreadyIn) {
                        enhancedResults.add(er);
                    }
                }
            }

            return enhancedResults;
        } catch (Exception e) {
            log.warn("Parse DeepSeek result error", e);
            return existingResults;
        }
    }

    private String extractJsonFromText(String text) {
        if (text == null || text.isBlank()) return null;
        int firstBrace = text.indexOf('{');
        int lastBrace = text.lastIndexOf('}');
        if (firstBrace >= 0 && lastBrace > firstBrace) {
            return text.substring(firstBrace, lastBrace + 1);
        }
        return text.trim();
    }

    private Disease findDiseaseByName(String name) {
        if (name == null || name.isBlank()) return null;
        try {
            List<Disease> diseases = diseaseService.lambdaQuery()
                    .like(Disease::getDiseaseName, name)
                    .last("LIMIT 1")
                    .list();
            if (diseases != null && !diseases.isEmpty()) {
                return diseases.get(0);
            }
            List<Disease> all = diseaseService.getAllForPrediction();
            if (all != null) {
                for (Disease d : all) {
                    if (d.getDiseaseName() != null && (d.getDiseaseName().contains(name) || name.contains(d.getDiseaseName()))) {
                        return d;
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Find disease by name error", e);
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
                    result.add(drugs.get(0));
                }
            }
        } catch (Exception e) {
            log.warn("Find drugs by names error", e);
        }
        return result;
    }

    private String generateDeepSeekComprehensiveAdvice(String symptoms, List<String> drugNames, List<String> keywords) {
        try {
            String prompt = "你是一个专业的全科医学AI助手。请根据用户的以下症状描述，给出一份详细的健康分析和建议。\n\n"
                    + "【用户症状】：" + symptoms + "\n"
                    + (keywords != null && !keywords.isEmpty() ? "【关键词】：" + String.join("、", keywords) + "\n" : "")
                    + (drugNames != null && !drugNames.isEmpty() ? "【相关药品参考】：" + String.join("、", drugNames) + "\n" : "")
                    + "\n请从以下几个方面给出建议（每方面1-2句话，简洁专业）：\n"
                    + "1. 可能的健康状况分析\n"
                    + "2. 建议的就医或检查方向\n"
                    + "3. 日常护理和注意事项\n"
                    + "4. 什么情况下必须立即就医\n\n"
                    + "请务必在最后加上：⚠️本分析仅供参考，不能替代医生诊断";
            return callAiServiceWithExtendedTimeout(prompt);
        } catch (Exception e) {
            log.warn("Generate comprehensive advice error", e);
            return "";
        }
    }

    private String callAiServiceWithExtendedTimeout(String prompt) throws IOException, InterruptedException {
        if (useDeepseek()) {
            String body = objectMapper.writeValueAsString(Map.of(
                    "model", deepseekModel,
                    "messages", List.of(
                            Map.of("role", "system", "content", "你是一个经验丰富的中文全科医学专家AI助手，擅长疾病诊断分析和用药建议。回答要专业、准确、详细，同时注意医学严谨，避免给出具体药品剂量。始终强调本分析仅供参考，不能替代医生诊断。"),
                            Map.of("role", "user", "content", prompt)
                    ),
                    "temperature", 0.3,
                    "max_tokens", 2000
            ));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(deepseekApiUrl))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + deepseekApiKey)
                    .timeout(Duration.ofSeconds(30))
                    .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() == 200) {
                JsonNode root = objectMapper.readTree(response.body());
                JsonNode textNode = root.at("/choices/0/message/content");
                if (!textNode.isMissingNode() && textNode.isTextual()) {
                    return textNode.asText();
                }
            }
            log.warn("DeepSeek extended AI request failed: {}", response.body());
            if (openAiApiKey != null && !openAiApiKey.isBlank()) {
                return callOpenAiExtended(prompt);
            }
            return null;
        }
        return callOpenAiExtended(prompt);
    }

    private String callOpenAiExtended(String prompt) throws IOException, InterruptedException {
        String body = objectMapper.writeValueAsString(Map.of(
                "model", "gpt-3.5-turbo",
                "messages", List.of(
                        Map.of("role", "system", "content", "你是一个经验丰富的中文全科医学专家AI助手。"),
                        Map.of("role", "user", "content", prompt)
                ),
                "temperature", 0.3,
                "max_tokens", 2000
        ));
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(OPENAI_URL))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + openAiApiKey)
                .timeout(Duration.ofSeconds(30))
                .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() == 200) {
            JsonNode root = objectMapper.readTree(response.body());
            JsonNode textNode = root.at("/choices/0/message/content");
            if (!textNode.isMissingNode() && textNode.isTextual()) {
                return textNode.asText();
            }
        }
        log.warn("OpenAI extended request failed: {}", response.body());
        return null;
    }
}
