<template>
  <div class="page">
    <div class="page-header">
      <h2>症状自测</h2>
      <p class="subtitle">基于 977 种疾病和 1000 种药品的智能匹配引擎 + AI 智能问诊</p>
    </div>

    <!-- ===== AI 智能问诊（深度学习 + Agent）===== -->
    <el-card class="input-card ai-card">
      <template #header>
        <div class="ai-card-header">
          <span class="ai-card-title">
            <el-icon class="ai-card-icon"><ChatLineSquare /></el-icon>
            AI 智能问诊
          </span>
          <div>
            <el-tag type="danger" size="small" class="ai-tag">深度学习语义匹配</el-tag>
            <el-tag type="warning" size="small" class="ai-tag">DeepSeek Agent 多轮问诊</el-tag>
          </div>
        </div>
      </template>

      <el-form @submit.prevent="handleAiConsult">
        <el-form-item label="症状描述">
          <el-input v-model="aiSymptoms" type="textarea" :rows="3"
            placeholder="用大白话说就行，例如：我这两天嗓子疼，咳嗽，还有点发烧，浑身没劲" />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" size="large" :loading="aiLoading" @click="handleAiConsult">
            <el-icon><ChatLineSquare /></el-icon> 开始 AI 问诊
          </el-button>
          <el-button size="large" @click="resetAi">重置问诊</el-button>
        </el-form-item>
      </el-form>

      <!-- Agent 思考步骤 -->
      <div v-if="aiSteps.length > 0" class="ai-steps">
        <div class="ai-steps-title">AI 分析过程</div>
        <div v-for="(s, i) in aiSteps" :key="i" class="ai-step">
          <el-icon class="ai-step-icon" :class="{ 'is-loading': i === aiSteps.length - 1 && aiLoading }">
            <Loading v-if="i === aiSteps.length - 1 && aiLoading" />
            <MagicStick v-else />
          </el-icon>
          <div class="ai-step-body">
            <div class="ai-step-name">{{ s.name }}</div>
            <div class="ai-step-detail">{{ s.detail }}</div>
          </div>
        </div>
      </div>

      <!-- AI 诊断结果 -->
      <div v-if="aiResult && aiResult.diagnoses && aiResult.diagnoses.length > 0" class="ai-result">
        <div class="ai-result-title">AI 鉴别诊断（{{ aiResult.source === 'rule' ? '规则兜底' : '深度分析' }}）</div>
        <div v-for="(d, i) in aiResult.diagnoses" :key="i" class="ai-diag">
          <div class="ai-diag-head">
            <span class="ai-diag-name">{{ d.name }}</span>
            <span class="ai-diag-conf">{{ d.confidence }}%</span>
          </div>
          <el-progress :percentage="Math.min(100, Math.max(0, Number(d.confidence) || 0))"
            :color="confidenceColor(d.confidence)" :stroke-width="6" />
          <div v-if="d.summary" class="ai-diag-line"><b>概述：</b>{{ d.summary }}</div>
          <div v-if="d.causes" class="ai-diag-line"><b>可能病因：</b>{{ d.causes }}</div>
          <div v-if="d.checks" class="ai-diag-line"><b>建议检查：</b>{{ d.checks }}</div>
          <div v-if="d.treatment" class="ai-diag-line"><b>治疗方向：</b>{{ d.treatment }}</div>
          <div v-if="d.drugs && d.drugs.length" class="ai-diag-line">
            <b>推荐用药：</b>
            <el-tag v-for="(drugName, di) in d.drugs" :key="di" type="success" size="small"
              class="ai-drug-tag" @click="showDrugDetail({ drugName })">
              {{ drugName }}
            </el-tag>
          </div>
          <div v-if="d.risk" class="ai-risk">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ d.risk }}</span>
          </div>
        </div>

        <!-- 整体建议 -->
        <div v-if="aiResult.advice" class="ai-advice">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ aiResult.advice }}</span>
        </div>

        <!-- AI 追问（多轮） -->
        <div v-if="aiResult.next_questions && aiResult.next_questions.length" class="ai-followup">
          <div class="ai-followup-title">AI 医生追问</div>
          <ul class="ai-question-list">
            <li v-for="(q, qi) in aiResult.next_questions" :key="qi">{{ q }}</li>
          </ul>
          <div class="ai-followup-input">
            <el-input v-model="aiAnswer" placeholder="补充回答，例如：体温38度多，咳嗽有黄痰" />
            <el-button type="primary" :loading="aiLoading" @click="continueAiConsult">继续问诊</el-button>
          </div>
        </div>
      </div>

      <div class="ai-disclaimer">本结果由 AI 生成，仅供健康参考，不能替代医生面诊。出现高热不退、呼吸困难、胸痛、意识改变等危险信号请立即就医。</div>
    </el-card>

    <!-- ===== 规则引擎匹配（备用）===== -->
    <el-card class="input-card">
      <template #header>
        <div class="ai-card-header">
          <span class="ai-card-title">
            <el-icon class="ai-card-icon"><Search /></el-icon>
            规则引擎快速匹配
          </span>
          <el-tag size="small" type="info">本地引擎 · 秒级返回</el-tag>
        </div>
      </template>
      <el-form @submit.prevent="handlePredict">
        <el-form-item label="症状描述">
          <el-input v-model="symptoms" type="textarea" :rows="3"
            placeholder="请输入您的症状，如：发热 咳嗽 头痛 肌肉酸痛（可用空格或逗号分隔）" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handlePredict">
            <el-icon><Search /></el-icon> 开始匹配
          </el-button>
          <el-button size="large" @click="symptoms = ''; results = []">清空</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="hint-box">
      <el-icon><InfoFilled /></el-icon>
      <span>已启用 AI 增强匹配 + 海量医疗知识库。匹配引擎会自动扩展同义词、滑动窗口关键词，并在疾病名称、症状详述、病因概述、治疗方案等多个维度进行智能搜索。</span>
    </div>

    <!-- 疾病结果列表 -->
    <div v-if="results.length > 0" class="results-section">
      <h3>匹配结果（{{ results.length }} 条）</h3>

      <el-card v-for="(item, i) in sortedResults" :key="i" class="result-card" shadow="hover">
        <!-- 头部 -->
        <div class="result-header">
          <div class="result-header-left">
            <span class="disease-name">{{ item.matchedDisease }}</span>
            <el-tag :type="item.disease ? 'primary' : 'success'" size="small" class="tag">
              {{ item.disease ? '疾病匹配' : '相关药品' }}
            </el-tag>
          </div>
          <div class="result-header-right">
            <span class="confidence-label">匹配度</span>
            <span class="confidence-badge" :class="confidenceClass(item.confidence)">
              {{ item.confidence }}%
            </span>
          </div>
        </div>
        <el-progress :percentage="parseFloat(item.confidence)" :color="confidenceColor(item.confidence)"
          :stroke-width="8" style="margin-top: 8px" />

        <!-- 疾病详情（展开版） -->
        <div v-if="item.disease" class="disease-detail">
          <!-- 基本信息行 -->
          <div class="info-grid">
            <div v-if="item.disease.department" class="info-item">
              <span class="info-label">就诊科室</span>
              <el-tag size="small" effect="plain" type="info">{{ item.disease.department }}</el-tag>
            </div>
            <div v-if="item.disease.icdCode" class="info-item">
              <span class="info-label">ICD编码</span>
              <code>{{ item.disease.icdCode }}</code>
            </div>
            <div v-if="item.disease.affectedArea" class="info-item">
              <span class="info-label">发病部位</span>
              <span class="info-value">{{ item.disease.affectedArea }}</span>
            </div>
            <div v-if="item.disease.infectiousness" class="info-item">
              <span class="info-label">传染性</span>
              <span class="info-value">{{ item.disease.infectiousness }}</span>
            </div>
            <div v-if="item.disease.hereditary" class="info-item">
              <span class="info-label">遗传性</span>
              <span class="info-value">{{ item.disease.hereditary }}</span>
            </div>
            <div v-if="item.disease.medicalInsurance" class="info-item">
              <span class="info-label">医保</span>
              <span class="info-value">{{ item.disease.medicalInsurance }}</span>
            </div>
          </div>

          <!-- description -->
          <div v-if="item.disease.description" class="text-block">
            <p class="block-title">疾病描述</p>
            <p class="block-text">{{ item.disease.description }}</p>
          </div>

          <!-- 症状详情 -->
          <el-collapse v-if="hasSymptomsDetail(item.disease)" class="detail-collapse">
            <el-collapse-item name="symptoms">
              <template #title>
                <span class="collapse-title">典型症状与详述</span>
              </template>
              <div v-if="item.disease.symptoms" class="text-block">
                <p class="block-title">典型症状</p>
                <p class="block-text">{{ item.disease.symptoms }}</p>
              </div>
              <div v-if="item.disease.symptomsOverview" class="text-block">
                <p class="block-title">症状总述</p>
                <p class="block-text">{{ item.disease.symptomsOverview }}</p>
              </div>
              <div v-if="item.disease.symptomsDetail" class="text-block">
                <p class="block-title">症状详述</p>
                <p class="block-text">{{ item.disease.symptomsDetail }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>

          <!-- 病因详情 -->
          <el-collapse v-if="hasEtiologyDetail(item.disease)" class="detail-collapse">
            <el-collapse-item name="etiology">
              <template #title>
                <span class="collapse-title">病因与危险因素</span>
              </template>
              <div v-if="item.disease.etiology" class="text-block">
                <p class="block-title">主要病因</p>
                <p class="block-text">{{ item.disease.etiology }}</p>
              </div>
              <div v-if="item.disease.etiologyOverview" class="text-block">
                <p class="block-title">病因概述</p>
                <p class="block-text">{{ item.disease.etiologyOverview }}</p>
              </div>
              <div v-if="item.disease.riskFactors" class="text-block">
                <p class="block-title">危险因素</p>
                <p class="block-text">{{ item.disease.riskFactors }}</p>
              </div>
              <div v-if="item.disease.susceptiblePopulation" class="text-block">
                <p class="block-title">易感人群</p>
                <p class="block-text">{{ item.disease.susceptiblePopulation }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>

          <!-- 检查诊断详情 -->
          <el-collapse v-if="hasExamDetail(item.disease)" class="detail-collapse">
            <el-collapse-item name="exam">
              <template #title>
                <span class="collapse-title">检查与诊断</span>
              </template>
              <div v-if="item.disease.examination" class="text-block">
                <p class="block-title">检查项目</p>
                <p class="block-text">{{ item.disease.examination }}</p>
              </div>
              <div v-if="item.disease.expectedExamination" class="text-block">
                <p class="block-title">预计检查</p>
                <p class="block-text">{{ item.disease.expectedExamination }}</p>
              </div>
              <div v-if="item.disease.labExamination" class="text-block">
                <p class="block-title">实验室检查</p>
                <p class="block-text">{{ item.disease.labExamination }}</p>
              </div>
              <div v-if="item.disease.imagingExamination" class="text-block">
                <p class="block-title">影像学检查</p>
                <p class="block-text">{{ item.disease.imagingExamination }}</p>
              </div>
              <div v-if="item.disease.diagnosticBasis" class="text-block">
                <p class="block-title">诊断依据</p>
                <p class="block-text">{{ item.disease.diagnosticBasis }}</p>
              </div>
              <div v-if="item.disease.diagnosticCriteria" class="text-block">
                <p class="block-title">诊断标准</p>
                <p class="block-text">{{ item.disease.diagnosticCriteria }}</p>
              </div>
              <div v-if="item.disease.differentialDiagnosis" class="text-block">
                <p class="block-title">鉴别诊断</p>
                <p class="block-text">{{ item.disease.differentialDiagnosis }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>

          <!-- 治疗详情 -->
          <el-collapse v-if="hasTreatmentDetail(item.disease)" class="detail-collapse">
            <el-collapse-item name="treatment">
              <template #title>
                <span class="collapse-title">治疗与预后</span>
              </template>
              <div v-if="item.disease.generalTreatment" class="text-block">
                <p class="block-title">一般治疗</p>
                <p class="block-text">{{ item.disease.generalTreatment }}</p>
              </div>
              <div v-if="item.disease.drugTreatment" class="text-block">
                <p class="block-title">药物治疗</p>
                <p class="block-text">{{ item.disease.drugTreatment }}</p>
              </div>
              <div v-if="item.disease.prevention" class="text-block">
                <p class="block-title">预防治疗</p>
                <p class="block-text">{{ item.disease.prevention }}</p>
              </div>
              <div v-if="item.disease.treatmentPrognosis" class="text-block">
                <p class="block-title">治疗预后</p>
                <p class="block-text">{{ item.disease.treatmentPrognosis }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>

          <!-- 重要提醒 -->
          <div v-if="item.disease.importantNote" class="warning-block">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ item.disease.importantNote }}</span>
          </div>
        </div>

        <!-- 推荐药品 -->
        <div v-if="item.recommendedDrugs && item.recommendedDrugs.length > 0" class="drugs-section">
          <div class="section-divider">
            <span class="section-title">推荐药品</span>
            <span class="drug-count">共 {{ item.recommendedDrugs.length }} 种</span>
          </div>
          <div class="drug-tags">
            <el-tag v-for="drug in item.recommendedDrugs" :key="drug.id || drug.drugName"
              type="success" size="large" class="drug-tag" @click="showDrugDetail(drug)">
              <span class="drug-tag-name">{{ drug.drugName }}</span>
              <span v-if="drug.prescriptionType" class="drug-tag-meta">[{{ drug.prescriptionType }}]</span>
            </el-tag>
          </div>
        </div>

        <!-- 建议 -->
        <div v-if="item.advice" class="advice-section">
          <el-icon><ChatLineSquare /></el-icon>
          <span>{{ item.advice }}</span>
        </div>
      </el-card>
    </div>

    <el-empty v-else-if="searched" description="未找到匹配的疾病，请尝试补充更多症状"></el-empty>

    <!-- 药品详情弹窗（增强版） -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" destroy-on-close>
      <div v-if="drugDetail" class="drug-detail-dialog">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small" class="drug-desc">
          <el-descriptions-item label="药品通用名" :span="2">
            <strong>{{ drugDetail.drugName }}</strong>
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.englishName" label="英文名称" :span="2">
            {{ drugDetail.englishName }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.pinyin" label="汉语拼音" :span="2">
            {{ drugDetail.pinyin }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.approvalNumber" label="批准文号">
            {{ drugDetail.approvalNumber }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.manufacturer" label="生产厂家">
            {{ drugDetail.manufacturer }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.drugCategory" label="药品分类">
            <el-tag size="small">{{ drugDetail.drugCategory }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.prescriptionType" label="处方类型">
            <el-tag :type="drugDetail.prescriptionType.includes('处方') ? 'danger' : 'success'" size="small">
              {{ drugDetail.prescriptionType }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.medicalInsurance" label="医保类型">
            {{ drugDetail.medicalInsurance }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.referencePrice" label="参考价格">
            {{ drugDetail.referencePrice }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.specification" label="规格" :span="2">
            {{ drugDetail.specification }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.validityPeriod" label="有效期">
            {{ drugDetail.validityPeriod }}
          </el-descriptions-item>
          <el-descriptions-item v-if="drugDetail.executiveStandard" label="执行标准">
            {{ drugDetail.executiveStandard }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 适应症 -->
        <div v-if="drugDetail.indication" class="dialog-section">
          <h4>适应症</h4>
          <p class="dialog-text">{{ drugDetail.indication }}</p>
        </div>

        <!-- 成分 -->
        <div v-if="drugDetail.ingredients" class="dialog-section">
          <h4>成分</h4>
          <p class="dialog-text">{{ drugDetail.ingredients }}</p>
        </div>

        <!-- 用法用量 -->
        <div v-if="drugDetail.usageDosage" class="dialog-section">
          <h4>用法用量</h4>
          <p class="dialog-text">{{ drugDetail.usageDosage }}</p>
        </div>

        <!-- 不良反应 -->
        <div v-if="drugDetail.adverseReactions" class="dialog-section">
          <h4>不良反应</h4>
          <p class="dialog-text warning-text">{{ drugDetail.adverseReactions }}</p>
        </div>

        <!-- 禁忌 -->
        <div v-if="drugDetail.contraindications" class="dialog-section">
          <h4>禁忌</h4>
          <p class="dialog-text danger-text">{{ drugDetail.contraindications }}</p>
        </div>

        <!-- 注意事项 -->
        <div v-if="drugDetail.precautions" class="dialog-section">
          <h4>注意事项</h4>
          <p class="dialog-text">{{ drugDetail.precautions }}</p>
        </div>

        <!-- 药物相互作用 -->
        <div v-if="drugDetail.drugInteractions" class="dialog-section">
          <h4>药物相互作用</h4>
          <p class="dialog-text">{{ drugDetail.drugInteractions }}</p>
        </div>

        <!-- 药理作用 -->
        <div v-if="drugDetail.pharmacologicalAction" class="dialog-section">
          <h4>药理作用</h4>
          <p class="dialog-text">{{ drugDetail.pharmacologicalAction }}</p>
        </div>

        <!-- 贮藏 -->
        <div v-if="drugDetail.storage" class="dialog-section">
          <h4>贮藏方法</h4>
          <p class="dialog-text">{{ drugDetail.storage }}</p>
        </div>

        <!-- 药品简介 -->
        <div v-if="drugDetail.drugIntro" class="dialog-section">
          <h4>药品简介</h4>
          <p class="dialog-text">{{ drugDetail.drugIntro }}</p>
        </div>
      </div>
      <div v-else style="text-align:center;padding:40px">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p style="margin-top:10px;color:#999">加载中...</p>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, InfoFilled, WarningFilled, ChatLineSquare, Loading, MagicStick } from '@element-plus/icons-vue'
import { predictDemo } from '../../api/statistics'
import { getDrug, getDrugs } from '../../api/drug'
import { aiConsult } from '../../api/selfTest'

// ===== AI 智能问诊状态 =====
const aiSymptoms = ref('')
const aiLoading = ref(false)
const aiSteps = ref([])
const aiResult = ref(null)
const aiHistory = ref([])       // 多轮对话记录
const aiAnswer = ref('')        // 追问回答输入
const aiSearched = ref(false)

const aiErrorMessage = (err) => {
  const detail = err?.response?.data?.detail || err?.response?.data?.message
  if (detail) return typeof detail === 'string' ? detail : JSON.stringify(detail)
  if (!err?.response) {
    return '无法连接 Python AI 问诊服务，请在 backend_py 目录启动 8000 端口服务后重试'
  }
  return `AI 问诊服务返回 HTTP ${err.response.status}，请查看 backend_py 控制台日志`
}

const resetAi = () => {
  aiSymptoms.value = ''
  aiAnswer.value = ''
  aiSteps.value = []
  aiResult.value = null
  aiHistory.value = []
  aiSearched.value = false
}

// 开始/继续 AI 问诊
const handleAiConsult = async () => {
  if (!aiSymptoms.value.trim()) {
    ElMessage.warning('请输入症状描述')
    return
  }
  aiLoading.value = true
  aiSteps.value = []
  aiResult.value = null
  aiSearched.value = false
  try {
    const res = await aiConsult({
      symptoms: aiSymptoms.value,
      history: aiHistory.value
    })
    const payload = res.data || res
    aiSteps.value = payload.steps || []
    aiResult.value = payload.result || null
    aiSearched.value = true
    // 记录 AI 追问，等待用户补充
    if (aiResult.value && aiResult.value.next_questions && aiResult.value.next_questions.length) {
      aiHistory.value.push({ role: 'assistant', content: aiResult.value.next_questions.join('；') })
    }
  } catch (err) {
    console.error('ai consult error', err)
    ElMessage.error(aiErrorMessage(err))
  } finally {
    aiLoading.value = false
  }
}

// 多轮：把用户的补充回答加入对话，再次调用 AI
const continueAiConsult = async () => {
  if (!aiAnswer.value.trim()) {
    ElMessage.warning('请先补充回答')
    return
  }
  aiHistory.value.push({ role: 'user', content: aiAnswer.value })
  aiSymptoms.value = aiAnswer.value
  aiAnswer.value = ''
  aiLoading.value = true
  aiSteps.value = []
  try {
    const res = await aiConsult({
      symptoms: aiSymptoms.value,
      history: aiHistory.value
    })
    const payload = res.data || res
    aiSteps.value = payload.steps || []
    aiResult.value = payload.result || null
    if (aiResult.value && aiResult.value.next_questions && aiResult.value.next_questions.length) {
      aiHistory.value.push({ role: 'assistant', content: aiResult.value.next_questions.join('；') })
    }
  } catch (err) {
    console.error('ai continue error', err)
    ElMessage.error(aiErrorMessage(err))
  } finally {
    aiLoading.value = false
  }
}

// ===== 规则引擎匹配 =====
const symptoms = ref('')
const results = ref([])
const loading = ref(false)
const searched = ref(false)

const sortedResults = computed(() => {
  return [...results.value].sort((a, b) => {
    const aPriority = a.disease ? 1 : 0
    const bPriority = b.disease ? 1 : 0
    if (aPriority !== bPriority) return bPriority - aPriority
    return parseFloat(b.confidence) - parseFloat(a.confidence)
  })
})

const handlePredict = async () => {
  if (!symptoms.value.trim()) {
    ElMessage.warning('请输入症状描述')
    return
  }
  loading.value = true
  searched.value = false
  try {
    const res = await predictDemo({ symptoms: symptoms.value })
    const payload = res.data || res
    const matchedResults = payload.matchedResults || []
    const drugNames = payload.drugNames || []
    const advice = payload.advice || ''
    if (matchedResults.length > 0) {
      results.value = matchedResults
    } else {
      results.value = [{
        matchedDisease: '未匹配到明确疾病',
        confidence: 0,
        disease: null,
        recommendedDrugs: drugNames.map(n => ({ drugName: n })),
        advice
      }]
    }
    searched.value = true
  } catch (err) {
    console.error('predict error', err)
    ElMessage.error(err?.message || '请求失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const confidenceClass = (val) => {
  if (val >= 70) return 'conf-high'
  if (val >= 40) return 'conf-medium'
  return 'conf-low'
}
const confidenceColor = (val) => {
  if (val >= 70) return '#F56C6C'
  if (val >= 40) return '#E6A23C'
  return '#909399'
}

// 辅助判断函数
const hasSymptomsDetail = (d) => d?.symptoms || d?.symptomsOverview || d?.symptomsDetail
const hasEtiologyDetail = (d) => d?.etiology || d?.etiologyOverview || d?.riskFactors || d?.susceptiblePopulation
const hasExamDetail = (d) => d?.examination || d?.expectedExamination || d?.labExamination || d?.imagingExamination || d?.diagnosticBasis || d?.diagnosticCriteria || d?.differentialDiagnosis
const hasTreatmentDetail = (d) => d?.generalTreatment || d?.drugTreatment || d?.prevention || d?.treatmentPrognosis

// 药品详情弹窗
const dialogVisible = ref(false)
const drugDetail = ref(null)
const dialogTitle = computed(() => drugDetail.value ? '药品详情 - ' + drugDetail.value.drugName : '药品详情')

const showDrugDetail = async (drug) => {
  try {
    drugDetail.value = null
    if (drug.id) {
      const res = await getDrug(drug.id)
      drugDetail.value = res.data || res
    } else if (drug.drugName) {
      const listRes = await getDrugs({ page: 1, size: 1, keyword: drug.drugName })
      const page = listRes.data
      if (page && page.records && page.records.length > 0) {
        drugDetail.value = page.records[0]
      } else {
        drugDetail.value = { drugName: drug.drugName, indication: '未找到详细信息' }
      }
    }
    dialogVisible.value = true
  } catch (err) {
    console.error('showDrugDetail error', err)
    ElMessage.error('获取药品详情失败')
  }
}
</script>

<style scoped>
.page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}
.page-header .subtitle {
  margin: 4px 0 0;
  color: #909399;
  font-size: 14px;
}
.input-card {
  max-width: 800px;
  margin-bottom: 20px;
}

/* ===== AI 智能问诊样式 ===== */
.ai-card {
  border-top: 3px solid #f56c6c;
}
.ai-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ai-card-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.ai-card-icon {
  margin-right: 6px;
  color: #f56c6c;
}
.ai-tag {
  margin-left: 6px;
}
.ai-steps {
  margin-top: 8px;
  padding: 14px 16px;
  background: #fdf6f6;
  border: 1px solid #fde2e2;
  border-radius: 8px;
}
.ai-steps-title {
  font-size: 13px;
  font-weight: 600;
  color: #c0392b;
  margin-bottom: 10px;
}
.ai-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
}
.ai-step-icon {
  margin-top: 3px;
  color: #f56c6c;
  flex-shrink: 0;
}
.ai-step-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.ai-step-detail {
  font-size: 13px;
  color: #606266;
  margin-top: 2px;
  line-height: 1.6;
}
.ai-result {
  margin-top: 16px;
}
.ai-result-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}
.ai-diag {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: #fff;
}
.ai-diag-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.ai-diag-name {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
}
.ai-diag-conf {
  font-size: 14px;
  font-weight: 700;
  color: #f56c6c;
}
.ai-diag-line {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  margin-top: 6px;
}
.ai-drug-tag {
  margin: 2px 4px 2px 0;
  cursor: pointer;
}
.ai-drug-tag:hover {
  transform: translateY(-1px);
}
.ai-risk {
  margin-top: 10px;
  padding: 10px 12px;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  color: #c0392b;
  font-size: 13px;
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.ai-risk .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}
.ai-advice {
  margin-top: 12px;
  padding: 12px 14px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 6px;
  color: #529b2e;
  font-size: 13px;
  line-height: 1.7;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.ai-advice .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}
.ai-followup {
  margin-top: 16px;
  padding: 14px 16px;
  background: #f4f4f5;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.ai-followup-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
.ai-question-list {
  margin: 0 0 12px;
  padding-left: 20px;
  color: #606266;
  font-size: 13px;
  line-height: 1.9;
}
.ai-followup-input {
  display: flex;
  gap: 8px;
}
.ai-disclaimer {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
.hint-box {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f0f5ff;
  border: 1px solid #d6e4ff;
  border-radius: 8px;
  color: #495060;
  font-size: 13px;
  line-height: 1.7;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.hint-box .el-icon {
  margin-top: 2px;
  color: #409eff;
  flex-shrink: 0;
}

.results-section {
  margin-top: 24px;
}
.results-section h3 {
  margin: 0 0 16px;
  font-size: 18px;
  color: #303133;
}

.result-card {
  margin-bottom: 16px;
  border-radius: 10px;
}

/* result header */
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.result-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.disease-name {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}
.tag {
  font-size: 12px;
}
.result-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.confidence-label {
  font-size: 13px;
  color: #909399;
}
.confidence-badge {
  padding: 3px 12px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: bold;
  color: #fff;
}
.conf-high { background: #F56C6C; }
.conf-medium { background: #E6A23C; }
.conf-low { background: #909399; }

/* info grid */
.info-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}
.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}
.info-label {
  color: #909399;
  white-space: nowrap;
}
.info-item code {
  background: #ecf5ff;
  color: #409eff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.info-value {
  color: #606266;
}

/* text blocks */
.text-block {
  margin-top: 8px;
}
.block-title {
  font-weight: 600;
  color: #409eff;
  font-size: 13px;
  margin: 0 0 4px;
}
.block-text {
  color: #606266;
  font-size: 14px;
  line-height: 1.7;
  margin: 0;
  white-space: pre-wrap;
}

/* collapse */
.detail-collapse {
  margin-top: 8px;
}
.collapse-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

/* warning */
.warning-block {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 8px;
  font-size: 13px;
  color: #F56C6C;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.6;
}
.warning-block .el-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

/* drugs section */
.drugs-section {
  margin-top: 12px;
}
.section-divider {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.section-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.drug-count {
  font-size: 12px;
  color: #909399;
}
.drug-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.drug-tag {
  cursor: pointer;
  transition: transform 0.15s;
}
.drug-tag:hover {
  transform: translateY(-1px);
}
.drug-tag-name {
  font-weight: 500;
}
.drug-tag-meta {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.8;
}

/* advice */
.advice-section {
  margin-top: 14px;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
  color: #606266;
  font-size: 14px;
  line-height: 1.7;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.advice-section .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: #409eff;
}

/* drug detail dialog */
.drug-detail-dialog {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;
}
.drug-desc {
  margin-bottom: 16px;
}
.dialog-section {
  margin-top: 14px;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
}
.dialog-section h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: #303133;
}
.dialog-text {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}
.warning-text {
  color: #E6A23C;
}
.danger-text {
  color: #F56C6C;
}
</style>
