<template>
  <div class="page">
    <h2><el-icon style="vertical-align: middle;"><MedicineBox /></el-icon> 药品查询</h2>
    <el-card class="search-card">
      <!-- 搜索栏 -->
      <el-row :gutter="10" style="margin-bottom:16px">
        <el-col :span="9">
          <el-input v-model="keyword" placeholder="搜索药品名称/英文名/适应症" clearable @keyup.enter="loadAll" />
        </el-col>
        <el-col :span="5">
          <el-select v-model="drugCategory" placeholder="药品分类" clearable @change="loadAll">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="loadAll">搜索</el-button>
          <el-button @click="resetFilters" style="margin-left:4px">重置</el-button>
        </el-col>
      </el-row>

      <!-- ========== 炫酷数据可视化大屏 ========== -->
      <div class="dashboard" v-show="allStatsData.length > 0">
        <div class="particles-bg"></div>

        <!-- 数字卡片组 -->
        <div class="stats-row">
          <div class="stat-card stat-total">
            <div class="stat-icon-wrap"><el-icon :size="28"><Collection /></el-icon></div>
            <div class="stat-body">
              <div class="stat-value">{{ displayStats.total }}</div>
              <div class="stat-label">符合筛选药品总数</div>
            </div>
            <div class="stat-card-glow"></div>
          </div>
          <div class="stat-card stat-prescription">
            <div class="stat-icon-wrap prescription-icon"><el-icon :size="28"><Document /></el-icon></div>
            <div class="stat-body">
              <div class="stat-value">{{ displayStats.prescription }}</div>
              <div class="stat-label">处方药</div>
            </div>
            <div class="stat-card-glow"></div>
          </div>
          <div class="stat-card stat-otc">
            <div class="stat-icon-wrap otc-icon"><el-icon :size="28"><ShoppingBag /></el-icon></div>
            <div class="stat-body">
              <div class="stat-value">{{ displayStats.otc }}</div>
              <div class="stat-label">非处方药(OTC)</div>
            </div>
            <div class="stat-card-glow"></div>
          </div>
        </div>

        <!-- 图表区 -->
        <div class="chart-row">
          <div class="chart-card chart-card-wide">
            <div class="chart-card-header">
              <span class="chart-dot dot-blue"></span>
              <span class="chart-label">剂型分布统计</span>
            </div>
            <div ref="formChartRef" class="chart-box"></div>
          </div>
          <div class="chart-card chart-card-wide">
            <div class="chart-card-header">
              <span class="chart-dot dot-cyan"></span>
              <span class="chart-label">药品分类分布</span>
            </div>
            <div ref="categoryChartRef" class="chart-box"></div>
          </div>
        </div>
      </div>
      <!-- ========== 可视化大屏 END ========== -->

      <!-- 药品列表 -->
      <el-table :data="tableData" border stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="drugName" label="药品名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="englishName" label="英文名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="dosageForm" label="剂型" min-width="110" show-overflow-tooltip />
        <el-table-column prop="specification" label="规格" min-width="140" show-overflow-tooltip />
        <el-table-column prop="indication" label="适应症" min-width="240" show-overflow-tooltip />
        <el-table-column prop="manufacturer" label="生产单位" min-width="180" show-overflow-tooltip />
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDrugs } from '../../api/drug'

const tableData = ref([])
const loading = ref(false)
const keyword = ref('')
const drugCategory = ref('')
const page = ref(1)
const size = ref(10)
const total = ref(0)

const categories = ref([])

// ===== 可视化大屏数据 =====
const allStatsData = ref([])
const displayStats = reactive({ total: 0, prescription: 0, otc: 0 })
const rawStats = reactive({ total: 0, prescription: 0, otc: 0 })
let animFrame = null

const formChartRef = ref(null)
const categoryChartRef = ref(null)
let formChart = null
let categoryChart = null
let chartResizeHandler = null

// ===== 数字滚动动画 =====
const animateStats = () => {
  const keys = ['total', 'prescription', 'otc']
  const duration = 800
  const startTime = Date.now()
  const starts = { ...displayStats }
  const animLoop = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    keys.forEach(k => {
      displayStats[k] = Math.round(starts[k] + (rawStats[k] - starts[k]) * eased)
    })
    if (progress < 1) {
      animFrame = requestAnimationFrame(animLoop)
    }
  }
  if (animFrame) cancelAnimationFrame(animFrame)
  animFrame = requestAnimationFrame(animLoop)
}

const computeStats = (data) => {
  rawStats.total = data.length
  rawStats.prescription = data.filter(d => d.prescriptionType && d.prescriptionType.includes('处方')).length
  rawStats.otc = rawStats.total - rawStats.prescription
  animateStats()
}

// ===== 剂型分布饼图 =====
// 剂型标准化： dosage_form 为空时从药品名称智能识别
const normalizeDosageForm = (name, rawForm) => {
  if (rawForm && String(rawForm).trim()) return String(rawForm).trim()
  if (!name) return '其他'
  const n = String(name)
  const rules = [
    ['泡腾片', /泡腾片/], ['咀嚼片', /咀嚼片/], ['缓释片', /缓释片/],
    ['控释片', /控释片/], ['肠溶片', /肠溶片/], ['分散片', /分散片/],
    ['含片', /含片/], ['舌下片', /舌下片/], ['口腔崩解片', /口腔崩解片|口崩片/],
    ['注射液', /注射液/], ['注射用', /注射用/], ['粉针剂', /粉针|冻干粉针/],
    ['输液', /输液/], ['胶囊', /胶囊/], ['口服液', /口服液/],
    ['口服溶液', /口服溶液/], ['混悬液', /混悬液/], ['干混悬剂', /干混悬剂/],
    ['糖浆剂', /糖浆/], ['合剂', /合剂/], ['滴丸', /滴丸/], ['丸剂', /丸/],
    ['颗粒', /颗粒/], ['散剂', /散|粉$|粉末/], ['软膏', /软膏/],
    ['乳膏', /乳膏/], ['凝胶', /凝胶/], ['贴剂', /贴|贴膏/], ['栓剂', /栓/],
    ['滴眼液', /滴眼液/], ['眼膏', /眼膏/], ['滴鼻液', /滴鼻液/],
    ['喷雾剂', /喷雾剂|气雾剂/], ['吸入剂', /吸入/], ['洗剂', /洗剂/],
    ['搽剂', /搽剂/], ['酊剂', /酊/], ['煎膏剂', /煎膏|膏滋/],
    ['膏药', /膏药/], ['锭剂', /锭/], ['露剂', /露/],
    ['酒剂', /酒$|酒剂/], ['茶剂', /茶剂/], ['曲剂', /曲剂/],
    ['膜剂', /膜剂/], ['片剂', /片$|片剂/]
  ]
  for (const [form, re] of rules) {
    if (re.test(n)) return form
  }
  return '其他'
}

const renderFormChart = (data) => {
  if (!formChart) return
  const formMap = {}
  data.forEach(d => {
    const form = normalizeDosageForm(d.drugName, d.dosageForm)
    formMap[form] = (formMap[form] || 0) + 1
  })
  let chartData = Object.entries(formMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  // 过多小剂型合并为“其他”
  const TOP_N = 8
  const otherIdx = chartData.findIndex(d => d.name === '其他')
  let otherItem = otherIdx >= 0 ? chartData.splice(otherIdx, 1)[0] : { name: '其他', value: 0 }
  if (chartData.length > TOP_N) {
    const topItems = chartData.slice(0, TOP_N)
    const otherValue = chartData.slice(TOP_N).reduce((sum, item) => sum + item.value, 0) + otherItem.value
    chartData = [...topItems, { name: '其他', value: otherValue }]
  } else if (otherItem.value > 0) {
    chartData.push(otherItem)
  }

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(6,30,60,0.92)',
      borderColor: '#0ea5e9',
      textStyle: { color: '#e0f2fe' },
      formatter: '{b}: {c}种 ({d}%)'
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
  }
  formChart.setOption(option, true)
}

// ===== 药品分类柱状图 =====
// 一级分类聚合：把 drug_category 首字母代码聚合到一级分类
const CATEGORY_LEVEL1_MAP = {
  'A': 'A 消化系统用药',
  'B': 'B 呼吸系统用药',
  'C': 'C 心血管系统用药',
  'D': 'D 神经系统用药',
  'E': 'E 抗感染用药',
  'F': 'F 内分泌与代谢用药',
  'G': 'G 血液系统用药',
  'H': 'H 泌尿生殖系统用药',
  'I': 'I 骨骼肌肉系统用药',
  'J': 'J 皮肤科用药',
  'K': 'K 五官科用药',
  'L': 'L 中成药',
  'M': 'M 抗肿瘤与免疫用药',
  'N': 'N 营养与维生素',
  'O': 'O 其他'
}
const getLevel1Category = (cat) => {
  if (!cat) return 'O 其他'
  const code = String(cat).trim().charAt(0).toUpperCase()
  return CATEGORY_LEVEL1_MAP[code] || 'O 其他'
}

const renderCategoryChart = (data) => {
  if (!categoryChart) return
  const catMap = {}
  data.forEach(d => {
    const cat = getLevel1Category(d.drugCategory)
    catMap[cat] = (catMap[cat] || 0) + 1
  })
  const sorted = Object.entries(catMap).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
  const names = sorted.map(d => d.name.length > 14 ? d.name.slice(0, 14) + '...' : d.name)
  const values = sorted.map(d => d.value)

  const dataMax = Math.max(...values, 1)
  const yMax = Math.ceil(dataMax / 0.9)
  const option = {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(6,30,60,0.92)', borderColor: '#06b6d4', textStyle: { color: '#e0f2fe' } },
    grid: { left: 65, right: 30, top: 20, bottom: 60 },
    xAxis: {
      type: 'category', data: names,
      axisLine: { lineStyle: { color: '#1e5068' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 9, rotate: 25 }
    },
    yAxis: {
      type: 'value', name: '数量',
      max: yMax,
      minInterval: 1,
      nameTextStyle: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(14,165,233,0.08)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, margin: 12 }
    },
    series: [{
      type: 'bar', barWidth: '50%',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: i % 2 === 0 ? '#0ea5e9' : '#06b6d4' },
            { offset: 1, color: i % 2 === 0 ? '#0369a1' : '#0891b2' }
          ])
        }
      })),
      emphasis: {
        itemStyle: { shadowBlur: 20, shadowColor: 'rgba(14,165,233,0.6)' }
      },
      animationDuration: 1200,
      animationEasing: 'elasticOut'
    }]
  }
  categoryChart.setOption(option, true)
}

// ===== 初始化图表 =====
const initAllCharts = () => {
  formChart = echarts.init(formChartRef.value)
  categoryChart = echarts.init(categoryChartRef.value)
  refreshCharts()
}

const refreshCharts = () => {
  const data = allStatsData.value
  if (!data.length) return
  computeStats(data)
  renderFormChart(data)
  renderCategoryChart(data)
}

const disposeCharts = () => {
  if (formChart) { formChart.dispose(); formChart = null }
  if (categoryChart) { categoryChart.dispose(); categoryChart = null }
}

// ===== 加载统计数据 =====
const loadAllStats = async () => {
  try {
    const params = { page: 1, size: 1000 }
    if (keyword.value) params.keyword = keyword.value
    if (drugCategory.value) params.drugCategory = drugCategory.value
    const res = await getDrugs(params)
    allStatsData.value = res.data.records || []
    await nextTick()
    if (formChartRef.value && categoryChartRef.value) {
      if (!formChart) initAllCharts()
      else refreshCharts()
    }
  } catch (e) {
    allStatsData.value = []
  }
}

// ===== 加载分类下拉 =====
const loadCategories = async () => {
  try {
    const res = await getDrugs({ page: 1, size: 1000 })
    const records = res.data.records || []
    const catSet = new Set()
    records.forEach(r => { if (r.drugCategory) catSet.add(r.drugCategory) })
    categories.value = [...catSet].sort()
  } catch (e) { /* 静默 */ }
}

// ===== 交互函数 =====
const resetFilters = () => {
  keyword.value = ''
  drugCategory.value = ''
  page.value = 1
  loadAll()
}

const loadAll = () => {
  page.value = 1
  loadData()
  loadAllStats()
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value, keyword: keyword.value }
    if (drugCategory.value) params.drugCategory = drugCategory.value
    const res = await getDrugs(params)
    tableData.value = res.data.records || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('加载药品数据失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadData()
  await loadCategories()
  await loadAllStats()
  chartResizeHandler = () => {
    formChart?.resize()
    categoryChart?.resize()
  }
  window.addEventListener('resize', chartResizeHandler)
})

onBeforeUnmount(() => {
  disposeCharts()
  if (animFrame) cancelAnimationFrame(animFrame)
  if (chartResizeHandler) window.removeEventListener('resize', chartResizeHandler)
})
</script>

<style scoped>
.page { padding: 20px; background: #f0f4f8; min-height: 100vh; max-width: 1440px; margin: 0 auto; }
.search-card { margin-top: 16px; }
.search-card :deep(.el-table) { width: 100%; }

/* ========== 可视化大屏 ========== */
.dashboard {
  position: relative;
  margin: 20px 0;
  padding: 24px 20px 18px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(6,30,60,0.92) 0%, rgba(15,52,96,0.94) 40%, rgba(6,40,70,0.93) 100%);
  border: 1px solid rgba(14,165,233,0.25);
  box-shadow: 0 0 40px rgba(14,165,233,0.08), inset 0 0 60px rgba(14,165,233,0.03);
  overflow: hidden;
  animation: dashFadeIn 0.8s ease-out;
}
@keyframes dashFadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.particles-bg {
  position: absolute; inset: 0; pointer-events: none; overflow: hidden; z-index: 0;
  background-image:
    radial-gradient(2px 2px at 15% 25%, rgba(14,165,233,0.5), transparent),
    radial-gradient(2px 2px at 45% 65%, rgba(6,182,212,0.4), transparent),
    radial-gradient(1px 1px at 75% 30%, rgba(45,212,191,0.5), transparent),
    radial-gradient(1px 1px at 55% 55%, rgba(56,189,248,0.4), transparent),
    radial-gradient(2px 2px at 65% 45%, rgba(14,165,233,0.3), transparent),
    radial-gradient(1px 1px at 20% 75%, rgba(6,182,212,0.4), transparent),
    radial-gradient(1px 1px at 85% 80%, rgba(45,212,191,0.3), transparent),
    radial-gradient(2px 2px at 35% 10%, rgba(14,165,233,0.35), transparent),
    radial-gradient(1px 1px at 80% 15%, rgba(56,189,248,0.3), transparent),
    radial-gradient(1px 1px at 10% 55%, rgba(6,182,212,0.35), transparent);
  animation: particleFloat 8s ease-in-out infinite;
}
@keyframes particleFloat {
  0%, 100% { transform: translateY(0); opacity: 0.8; }
  50% { transform: translateY(-8px); opacity: 1; }
}

.stats-row {
  position: relative; z-index: 1;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px;
}
.stat-card {
  position: relative;
  display: flex; align-items: center; gap: 16px;
  padding: 22px 24px;
  min-height: 100px;
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(14,165,233,0.18);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: default;
}
.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(14,165,233,0.5);
  box-shadow: 0 8px 30px rgba(14,165,233,0.15);
}
.stat-card:hover .stat-card-glow { opacity: 1; }
.stat-card-glow {
  position: absolute; inset: -1px;
  border-radius: 14px;
  background: radial-gradient(circle at 50% 50%, rgba(14,165,233,0.15), transparent 60%);
  opacity: 0;
  transition: opacity 0.35s;
  pointer-events: none;
}
.stat-icon-wrap {
  width: 52px; height: 52px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 12px;
  background: rgba(14,165,233,0.12);
  color: #38bdf8;
  flex-shrink: 0;
}
.prescription-icon { background: rgba(239,68,68,0.12); color: #f87171; }
.otc-icon { background: rgba(34,197,94,0.12); color: #4ade80; }
.stat-body { flex: 1; }
.stat-value {
  font-size: 36px; font-weight: 700; color: #e0f2fe;
  font-family: 'DIN Alternate', 'Helvetica Neue', sans-serif;
  line-height: 1.3;
  text-shadow: 0 0 20px rgba(14,165,233,0.3);
}
.stat-label {
  font-size: 13px; color: #94a3b8; margin-top: 2px; letter-spacing: 0.5px;
}

.chart-row {
  position: relative; z-index: 1;
  display: grid; grid-template-columns: 1fr 1fr; gap: 18px;
}
.chart-card-wide {
  background: rgba(255,255,255,0.03);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(14,165,233,0.15);
  border-radius: 14px;
  padding: 14px 16px 10px;
  transition: all 0.35s;
}
.chart-card-wide:hover {
  border-color: rgba(14,165,233,0.4);
  box-shadow: 0 0 28px rgba(14,165,233,0.12);
  transform: translateY(-2px);
}
.chart-card-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}
.chart-dot {
  width: 8px; height: 8px; border-radius: 50%;
  animation: dotPulse 2s ease-in-out infinite;
}
.dot-blue { background: #0ea5e9; box-shadow: 0 0 8px rgba(14,165,233,0.6); }
.dot-cyan { background: #06b6d4; box-shadow: 0 0 8px rgba(6,182,212,0.6); }
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 4px currentColor; }
  50% { box-shadow: 0 0 14px currentColor, 0 0 24px currentColor; }
}
.chart-label {
  color: #cbd5e1; font-size: 13px; font-weight: 500; letter-spacing: 0.5px;
}
.chart-box {
  width: 100%; height: 270px;
}
</style>
