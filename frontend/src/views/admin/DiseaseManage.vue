<template>
  <div class="page">
    <h2>疾病管理</h2>
    <el-card class="search-card">
      <!-- 搜索栏 -->
      <el-row :gutter="12" style="margin-bottom:16px">
        <el-col :span="4">
          <el-input v-model="keyword" placeholder="搜索疾病名称" clearable @keyup.enter="loadAll" />
        </el-col>
        <el-col :span="4">
          <el-input v-model="symptomKeyword" placeholder="按症状搜索" clearable @keyup.enter="loadAll" />
        </el-col>
        <el-col :span="3">
          <el-select v-model="department" placeholder="科室" clearable @change="loadAll">
            <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-select v-model="infectiousness" placeholder="传染性" clearable @change="loadAll">
            <el-option label="有传染性" value="传染性" />
            <el-option label="无传染性" value="无传染性" />
          </el-select>
        </el-col>
        <el-col :span="7" style="white-space: nowrap;">
          <el-button type="primary" @click="loadAll">搜索</el-button>
          <el-button @click="resetFilters" style="margin-left:4px">重置</el-button>
          <el-button type="success" @click="loadDepartments" style="margin-left:4px">刷新科室</el-button>
        </el-col>
      </el-row>

      <!-- ========== 炫酷数据可视化大屏 ========== -->
      <div class="dashboard" v-show="allStatsData.length > 0">
        <div class="particles-bg"></div>
        <div class="stats-row">
          <div class="stat-card stat-total">
            <div class="stat-icon-wrap"><el-icon :size="28"><DataAnalysis /></el-icon></div>
            <div class="stat-body">
              <div class="stat-value">{{ displayStats.total }}</div>
              <div class="stat-label">符合筛选疾病总数</div>
            </div>
            <div class="stat-card-glow"></div>
          </div>
          <div class="stat-card stat-infectious">
            <div class="stat-icon-wrap infectious-icon"><el-icon :size="28"><WarningFilled /></el-icon></div>
            <div class="stat-body">
              <div class="stat-value">{{ displayStats.infectious }}</div>
              <div class="stat-label">传染性疾病</div>
            </div>
            <div class="stat-card-glow"></div>
          </div>
          <div class="stat-card stat-safe">
            <div class="stat-icon-wrap safe-icon"><el-icon :size="28"><CircleCheckFilled /></el-icon></div>
            <div class="stat-body">
              <div class="stat-value">{{ displayStats.noninfectious }}</div>
              <div class="stat-label">无传染性疾病</div>
            </div>
            <div class="stat-card-glow"></div>
          </div>
        </div>
        <div class="chart-row">
          <div class="chart-card">
            <div class="chart-card-header">
              <span class="chart-dot dot-blue"></span>
              <span class="chart-label">科室疾病分布</span>
            </div>
            <div ref="deptChartRef" class="chart-box"></div>
          </div>
          <div class="chart-card">
            <div class="chart-card-header">
              <span class="chart-dot dot-cyan"></span>
              <span class="chart-label">高发疾病 TOP5</span>
            </div>
            <div ref="topChartRef" class="chart-box"></div>
          </div>
          <div class="chart-card">
            <div class="chart-card-header">
              <span class="chart-dot dot-green"></span>
              <span class="chart-label">发病部位分布</span>
            </div>
            <div ref="areaChartRef" class="chart-box"></div>
          </div>
        </div>
      </div>
      <!-- ========== 可视化大屏 END ========== -->

      <!-- 疾病列表 -->
      <el-table :data="tableData" border stripe v-loading="loading"
        highlight-current-row @row-click="showDetail">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="diseaseName" label="疾病名称" min-width="140" />
        <el-table-column prop="englishName" label="英文名" min-width="140" show-overflow-tooltip />
        <el-table-column prop="department" label="就诊科室" width="120" />
        <el-table-column prop="icdCode" label="ICD编码" width="110" />
        <el-table-column prop="affectedArea" label="发病部位" width="100" />
        <el-table-column prop="infectiousness" label="传染性" width="85">
          <template #default="{row}">
            <el-tag v-if="row.infectiousness" size="small"
              :type="row.infectiousness.includes('传染') ? 'danger' : 'info'" effect="plain">
              {{ row.infectiousness }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="symptoms" label="典型症状" show-overflow-tooltip min-width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{row}">
            <el-button type="primary" link size="small" @click.stop="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>

    <!-- 疾病详情弹窗 -->
    <el-dialog v-model="dialogVisible" :title="currentDisease?.diseaseName || '疾病详情'" width="850px" top="5vh" destroy-on-close>
      <template v-if="currentDisease">
        <div class="info-grid">
          <div class="info-item" v-if="currentDisease.department">
            <span class="info-label">就诊科室：</span>
            <el-tag size="small" effect="plain">{{ currentDisease.department }}</el-tag>
          </div>
          <div class="info-item" v-if="currentDisease.icdCode">
            <span class="info-label">ICD编码：</span>
            <code>{{ currentDisease.icdCode }}</code>
          </div>
          <div class="info-item" v-if="currentDisease.englishName">
            <span class="info-label">英文名称：</span>
            <code>{{ currentDisease.englishName }}</code>
          </div>
          <div class="info-item" v-if="currentDisease.affectedArea">
            <span class="info-label">发病部位：</span>
            <span>{{ currentDisease.affectedArea }}</span>
          </div>
          <div class="info-item" v-if="currentDisease.infectiousness">
            <span class="info-label">传染性：</span>
            <el-tag size="small" :type="currentDisease.infectiousness.includes('传染') ? 'danger' : 'info'" effect="plain">
              {{ currentDisease.infectiousness }}
            </el-tag>
          </div>
          <div class="info-item" v-if="currentDisease.hereditary">
            <span class="info-label">遗传性：</span>
            <span>{{ currentDisease.hereditary }}</span>
          </div>
          <div class="info-item" v-if="currentDisease.medicalInsurance">
            <span class="info-label">医保：</span>
            <el-tag size="small" type="success" effect="plain">{{ currentDisease.medicalInsurance }}</el-tag>
          </div>
          <div class="info-item" v-if="currentDisease.incidenceRate">
            <span class="info-label">发病率：</span>
            <span>{{ currentDisease.incidenceRate }}</span>
          </div>
        </div>
        <div class="text-block" v-if="currentDisease.description">
          <div class="block-title">疾病描述</div>
          <div class="block-text">{{ currentDisease.description }}</div>
        </div>
        <el-collapse v-if="hasSymptom" class="detail-collapse">
          <el-collapse-item title="🩺 典型症状与详述" name="symptoms">
            <div class="text-block" v-if="currentDisease.symptoms">
              <div class="block-title">典型症状</div>
              <div class="block-text">{{ currentDisease.symptoms }}</div>
            </div>
            <div class="text-block" v-if="currentDisease.symptomsOverview">
              <div class="block-title">症状总述</div>
              <div class="block-text">{{ currentDisease.symptomsOverview }}</div>
            </div>
            <div class="text-block" v-if="currentDisease.symptomsDetail">
              <div class="block-title">症状详述</div>
              <div class="block-text">{{ currentDisease.symptomsDetail }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="hasEtiology" class="detail-collapse">
          <el-collapse-item title="🔬 病因与危险因素" name="etiology">
            <div class="text-block" v-if="currentDisease.etiology">
              <div class="block-title">主要病因</div>
              <div class="block-text">{{ currentDisease.etiology }}</div>
            </div>
            <div class="text-block" v-if="currentDisease.riskFactors">
              <div class="block-title">危险因素</div>
              <div class="block-text">{{ currentDisease.riskFactors }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="hasExam" class="detail-collapse">
          <el-collapse-item title="🏥 检查与诊断" name="exam">
            <div class="text-block" v-if="currentDisease.examination">
              <div class="block-title">检查项目</div>
              <div class="block-text">{{ currentDisease.examination }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="hasTreatment" class="detail-collapse">
          <el-collapse-item title="💊 治疗与预后" name="treatment">
            <div class="text-block" v-if="currentDisease.drugTreatment">
              <div class="block-title">药物治疗方案</div>
              <div class="block-text">{{ currentDisease.drugTreatment }}</div>
            </div>
            <div class="text-block" v-if="currentDisease.prevention">
              <div class="block-title">预防措施</div>
              <div class="block-text">{{ currentDisease.prevention }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <div class="warning-block" v-if="currentDisease.importantNote">
          <strong>⚠️ 重要提醒：</strong>{{ currentDisease.importantNote }}
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDiseases } from '../../api/disease'

const tableData = ref([])
const loading = ref(false)
const keyword = ref('')
const symptomKeyword = ref('')
const department = ref('')
const infectiousness = ref('')
const page = ref(1)
const size = ref(10)
const total = ref(0)
const departments = ref([])
const dialogVisible = ref(false)
const currentDisease = ref(null)

// ===== 可视化大屏数据 =====
const allStatsData = ref([])
const displayStats = reactive({ total: 0, infectious: 0, noninfectious: 0 })
const rawStats = reactive({ total: 0, infectious: 0, noninfectious: 0 })
let animFrame = null

const deptChartRef = ref(null)
const topChartRef = ref(null)
const areaChartRef = ref(null)
let deptChart = null, topChart = null, areaChart = null
let chartResizeHandler = null

const animateStats = () => {
  const keys = ['total', 'infectious', 'noninfectious']
  const duration = 800, startTime = Date.now()
  const starts = { ...displayStats }
  const animLoop = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    keys.forEach(k => { displayStats[k] = Math.round(starts[k] + (rawStats[k] - starts[k]) * eased) })
    if (progress < 1) { animFrame = requestAnimationFrame(animLoop) }
  }
  if (animFrame) cancelAnimationFrame(animFrame)
  animFrame = requestAnimationFrame(animLoop)
}

const computeStats = (data) => {
  rawStats.total = data.length
  rawStats.infectious = data.filter(d => d.infectiousness && d.infectiousness.includes('传染')).length
  rawStats.noninfectious = rawStats.total - rawStats.infectious
  animateStats()
}

const renderDeptChart = (data) => {
  if (!deptChart) return
  const deptMap = {}
  data.forEach(d => { const dept = d.department || '其他'; deptMap[dept] = (deptMap[dept] || 0) + 1 })

  // 排序：数量多的靠前
  let chartData = Object.entries(deptMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  // 过多小科室合并为“其他”，避免标签挤成一团
  const TOP_N = 7
  if (chartData.length > TOP_N) {
    const topItems = chartData.slice(0, TOP_N)
    const otherValue = chartData.slice(TOP_N).reduce((sum, item) => sum + item.value, 0)
    chartData = [...topItems, { name: '其他', value: otherValue }]
  }

  deptChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(6,30,60,0.92)',
      borderColor: '#0ea5e9',
      textStyle: { color: '#e0f2fe' },
      formatter: '{b}: {c}例 ({d}%)'
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#94a3b8', fontSize: 10 },
      pageIconColor: '#0ea5e9',
      pageTextStyle: { color: '#94a3b8' }
    },
    series: [{
      type: 'pie',
      radius: '58%',
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 6,
        borderColor: 'rgba(6,30,60,0.85)',
        borderWidth: 2
      },
      label: {
        show: true,
        position: 'outside',
        color: '#e2e8f0',
        fontSize: 11,
        formatter: '{b}\n{d}%',
        lineHeight: 14
      },
      labelLine: {
        show: true,
        length: 12,
        length2: 8,
        smooth: 0.2
      },
      emphasis: {
        scale: true,
        scaleSize: 10,
        label: { fontSize: 13, fontWeight: 'bold' },
        itemStyle: { shadowBlur: 20, shadowColor: 'rgba(14,165,233,0.6)' }
      },
      data: chartData,
      color: ['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e', '#84cc16', '#14b8a6', '#a855f7', '#f59e0b', '#6366f1', '#10b981']
    }]
  }, true)
}

const renderTopChart = (data) => {
  if (!topChart) return
  const sorted = [...data].filter(d => d.incidenceRate).sort((a, b) => {
    return (parseFloat(b.incidenceRate) || 0) - (parseFloat(a.incidenceRate) || 0)
  }).slice(0, 5)
  if (sorted.length === 0) sorted.push(...data.slice(0, 5))
  const names = sorted.map(d => d.diseaseName.length > 6 ? d.diseaseName.slice(0, 6) + '...' : d.diseaseName)
  const values = sorted.map(d => { const v = parseFloat(d.incidenceRate); return isNaN(v) ? 1 : v })
  const dataMax = Math.max(...values, 1)
  const yMax = Math.ceil(dataMax / 0.9)
  topChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(6,30,60,0.92)', borderColor: '#06b6d4', textStyle: { color: '#e0f2fe' } },
    grid: { left: 65, right: 30, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: names, axisLine: { lineStyle: { color: '#1e5068' } }, axisTick: { show: false }, axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 15 } },
    yAxis: { type: 'value', name: '发病率', max: yMax, minInterval: 0.1, nameTextStyle: { color: '#94a3b8', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(14,165,233,0.08)' } }, axisLabel: { color: '#94a3b8', fontSize: 10, margin: 12 } },
    series: [{
      type: 'bar', barWidth: '55%',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: i % 2 === 0 ? '#06b6d4' : '#0ea5e9' },
            { offset: 1, color: i % 2 === 0 ? '#0891b2' : '#0284c7' }
          ])
        }
      })),
      emphasis: { itemStyle: { shadowBlur: 20, shadowColor: 'rgba(6,182,212,0.6)' } },
      animationDuration: 1200, animationEasing: 'elasticOut'
    }]
  }, true)
}

const renderAreaChart = (data) => {
  if (!areaChart) return
  const areaGroups = { '皮肤': 0, '全身': 0, '腹部': 0, '肺部': 0, '其他': 0 }
  data.forEach(d => {
    const area = (d.affectedArea || '').trim()
    if (area.includes('皮肤')) areaGroups['皮肤']++
    else if (area.includes('全身') || area.includes('全身性')) areaGroups['全身']++
    else if (area.includes('腹部') || area.includes('腹腔') || area.includes('肠胃')) areaGroups['腹部']++
    else if (area.includes('肺') || area.includes('呼吸') || area.includes('胸部')) areaGroups['肺部']++
    else areaGroups['其他']++
  })
  const indicator = Object.keys(areaGroups).map(k => ({ name: k, max: Math.max(...Object.values(areaGroups), 1) * 1.3 }))
  areaChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(6,30,60,0.92)', borderColor: '#14b8a6', textStyle: { color: '#e0f2fe' } },
    radar: {
      center: ['50%', '52%'], radius: '65%', indicator,
      axisName: { color: '#94a3b8', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(14,165,233,0.02)', 'rgba(14,165,233,0.06)'] } },
      splitLine: { lineStyle: { color: 'rgba(14,165,233,0.15)' } },
      axisLine: { lineStyle: { color: 'rgba(14,165,233,0.3)' } }
    },
    series: [{
      type: 'radar',
      data: [{ value: Object.values(areaGroups), name: '发病部位' }],
      symbol: 'circle', symbolSize: 5,
      lineStyle: { color: '#2dd4bf', width: 2 },
      itemStyle: { color: '#2dd4bf', borderColor: '#ccfbf1', borderWidth: 1 },
      areaStyle: { color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [{ offset: 0, color: 'rgba(45,212,191,0.4)' }, { offset: 1, color: 'rgba(20,184,166,0.05)' }]) },
      emphasis: { itemStyle: { shadowBlur: 20, shadowColor: 'rgba(45,212,191,0.6)' } }
    }]
  }, true)
}

const initAllCharts = () => {
  deptChart = echarts.init(deptChartRef.value)
  topChart = echarts.init(topChartRef.value)
  areaChart = echarts.init(areaChartRef.value)
  refreshCharts()
}

const refreshCharts = () => { const data = allStatsData.value; if (!data.length) return; computeStats(data); renderDeptChart(data); renderTopChart(data); renderAreaChart(data) }
const disposeCharts = () => { if (deptChart) { deptChart.dispose(); deptChart = null } if (topChart) { topChart.dispose(); topChart = null } if (areaChart) { areaChart.dispose(); areaChart = null } }

const loadAllStats = async () => {
  try {
    const params = { page: 1, size: 1000 }
    if (keyword.value) params.keyword = keyword.value
    if (symptomKeyword.value) params.symptom = symptomKeyword.value
    if (department.value) params.department = department.value
    if (infectiousness.value) params.infectiousness = infectiousness.value
    const res = await getDiseases(params)
    allStatsData.value = res.data.records || []
    await nextTick()
    if (deptChartRef.value && topChartRef.value && areaChartRef.value) {
      if (!deptChart) initAllCharts(); else refreshCharts()
    }
  } catch (e) { allStatsData.value = [] }
}

const resetFilters = () => { keyword.value = ''; symptomKeyword.value = ''; department.value = ''; infectiousness.value = ''; page.value = 1; loadAll() }
const loadAll = () => { page.value = 1; loadData(); loadAllStats() }

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    if (keyword.value) params.keyword = keyword.value
    if (symptomKeyword.value) params.symptom = symptomKeyword.value
    if (department.value) params.department = department.value
    if (infectiousness.value) params.infectiousness = infectiousness.value
    const res = await getDiseases(params)
    tableData.value = res.data.records || []
    total.value = res.data.total || 0
  } catch (e) { console.error('加载疾病数据失败', e) } finally { loading.value = false }
}

const loadDepartments = async () => {
  try {
    const res = await getDiseases({ page: 1, size: 1000 })
    const records = res.data.records || []
    const deptSet = new Set()
    records.forEach(r => { if (r.department) deptSet.add(r.department) })
    departments.value = [...deptSet].sort()
  } catch (e) { /* 静默 */ }
}

const showDetail = (row) => { currentDisease.value = row; dialogVisible.value = true }

const hasSymptom = computed(() => { const d = currentDisease.value; return d && (d.symptoms || d.symptomsOverview || d.symptomsDetail) })
const hasEtiology = computed(() => { const d = currentDisease.value; return d && (d.etiology || d.etiologyOverview || d.riskFactors || d.susceptiblePopulation) })
const hasExam = computed(() => { const d = currentDisease.value; return d && d.examination })
const hasTreatment = computed(() => { const d = currentDisease.value; return d && (d.drugTreatment || d.prevention || d.treatmentPrognosis) })

onMounted(async () => {
  await loadData()
  await loadDepartments()
  await loadAllStats()
  chartResizeHandler = () => { deptChart?.resize(); topChart?.resize(); areaChart?.resize() }
  window.addEventListener('resize', chartResizeHandler)
})

onBeforeUnmount(() => {
  disposeCharts()
  if (animFrame) cancelAnimationFrame(animFrame)
  if (chartResizeHandler) window.removeEventListener('resize', chartResizeHandler)
})
</script>

<style scoped>
.page { padding: 20px; background: #f0f4f8; min-height: 100vh; }
.search-card { margin-top: 16px; }

/* ========== 可视化大屏 ========== */
.dashboard {
  position: relative; margin: 20px 0; padding: 24px 20px 18px; border-radius: 16px;
  background: linear-gradient(135deg, rgba(6,30,60,0.92) 0%, rgba(15,52,96,0.94) 40%, rgba(6,40,70,0.93) 100%);
  border: 1px solid rgba(14,165,233,0.25);
  box-shadow: 0 0 40px rgba(14,165,233,0.08), inset 0 0 60px rgba(14,165,233,0.03);
  overflow: hidden; animation: dashFadeIn 0.8s ease-out;
}
@keyframes dashFadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.particles-bg {
  position: absolute; inset: 0; pointer-events: none; overflow: hidden; z-index: 0;
  background-image:
    radial-gradient(2px 2px at 20% 30%, rgba(14,165,233,0.5), transparent),
    radial-gradient(2px 2px at 50% 70%, rgba(6,182,212,0.4), transparent),
    radial-gradient(1px 1px at 80% 20%, rgba(45,212,191,0.5), transparent),
    radial-gradient(1px 1px at 40% 60%, rgba(56,189,248,0.4), transparent),
    radial-gradient(2px 2px at 70% 50%, rgba(14,165,233,0.3), transparent),
    radial-gradient(1px 1px at 10% 80%, rgba(6,182,212,0.4), transparent),
    radial-gradient(1px 1px at 90% 90%, rgba(45,212,191,0.3), transparent),
    radial-gradient(2px 2px at 30% 15%, rgba(14,165,233,0.35), transparent),
    radial-gradient(1px 1px at 60% 85%, rgba(56,189,248,0.3), transparent),
    radial-gradient(1px 1px at 85% 45%, rgba(6,182,212,0.35), transparent);
  animation: particleFloat 8s ease-in-out infinite;
}
@keyframes particleFloat { 0%, 100% { transform: translateY(0); opacity: 0.8; } 50% { transform: translateY(-8px); opacity: 1; } }
.stats-row { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
.stat-card {
  position: relative; display: flex; align-items: center; gap: 16px;
  padding: 22px 24px; min-height: 100px; border-radius: 14px;
  background: rgba(255,255,255,0.04); backdrop-filter: blur(10px);
  border: 1px solid rgba(14,165,233,0.18);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1); cursor: default;
}
.stat-card:hover { transform: translateY(-4px); border-color: rgba(14,165,233,0.5); box-shadow: 0 8px 30px rgba(14,165,233,0.15); }
.stat-card:hover .stat-card-glow { opacity: 1; }
.stat-card-glow { position: absolute; inset: -1px; border-radius: 14px; background: radial-gradient(circle at 50% 50%, rgba(14,165,233,0.15), transparent 60%); opacity: 0; transition: opacity 0.35s; pointer-events: none; }
.stat-icon-wrap { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; border-radius: 12px; background: rgba(14,165,233,0.12); color: #38bdf8; flex-shrink: 0; }
.infectious-icon { background: rgba(239,68,68,0.12); color: #f87171; }
.safe-icon { background: rgba(34,197,94,0.12); color: #4ade80; }
.stat-body { flex: 1; }
.stat-value { font-size: 36px; font-weight: 700; color: #e0f2fe; font-family: 'DIN Alternate', 'Helvetica Neue', sans-serif; line-height: 1.3; text-shadow: 0 0 20px rgba(14,165,233,0.3); }
.stat-label { font-size: 13px; color: #94a3b8; margin-top: 2px; letter-spacing: 0.5px; }
.chart-row { position: relative; z-index: 1; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; }
.chart-card { background: rgba(255,255,255,0.03); backdrop-filter: blur(6px); border: 1px solid rgba(14,165,233,0.15); border-radius: 14px; padding: 14px 16px 10px; transition: all 0.35s; }
.chart-card:hover { border-color: rgba(14,165,233,0.4); box-shadow: 0 0 28px rgba(14,165,233,0.12); transform: translateY(-2px); }
.chart-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.chart-dot { width: 8px; height: 8px; border-radius: 50%; animation: dotPulse 2s ease-in-out infinite; }
.dot-blue { background: #0ea5e9; box-shadow: 0 0 8px rgba(14,165,233,0.6); }
.dot-cyan { background: #06b6d4; box-shadow: 0 0 8px rgba(6,182,212,0.6); }
.dot-green { background: #14b8a6; box-shadow: 0 0 8px rgba(20,184,166,0.6); }
@keyframes dotPulse { 0%, 100% { box-shadow: 0 0 4px currentColor; } 50% { box-shadow: 0 0 14px currentColor, 0 0 24px currentColor; } }
.chart-label { color: #cbd5e1; font-size: 13px; font-weight: 500; letter-spacing: 0.5px; }
.chart-box { width: 100%; height: 280px; }

/* ========== 原有样式 ========== */
.info-grid { display: flex; flex-wrap: wrap; gap: 8px; background: #fafafa; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.info-item { display: flex; align-items: center; gap: 4px; font-size: 13px; }
.info-label { color: #909399; white-space: nowrap; }
.info-item code { background: #ecf5ff; color: #409eff; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
.text-block { margin-top: 12px; }
.block-title { font-weight: 600; color: #409eff; font-size: 13px; margin-bottom: 4px; }
.block-text { color: #606266; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.detail-collapse { margin-top: 8px; }
.warning-block { background: #fef0f0; border: 1px solid #fde2e2; border-radius: 6px; padding: 12px; margin-top: 12px; color: #F56C6C; font-size: 14px; line-height: 1.6; }
</style>
