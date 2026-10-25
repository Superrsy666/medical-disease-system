<template>
  <div class="dashboard">
    <h2>数据看板</h2>
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="item in stats" :key="item.key">
        <el-card class="stat-card" :style="{ borderTop: `4px solid ${item.color}` }">
          <div class="stat-body">
            <div class="stat-num" :style="{ color: item.color }">{{ item.value }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
          <el-icon :size="40" :style="{ color: item.color, opacity: 0.3 }">
            <component :is="item.icon" />
          </el-icon>
        </el-card>
      </el-col>
    </el-row>
    <!-- ECharts 图表 -->
    <el-card style="margin-top:20px">
      <template #header><span>数据总览</span></template>
      <div ref="chartRef" style="height:320px"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { getStatisticsOverview } from '../../api/statistics'

const chartRef = ref()
let chart = null
const stats = ref([
  { key: 'patientCount', label: '患者总数', value: 0, color: '#409EFF', icon: 'UserFilled' },
  { key: 'doctorCount',  label: '医生总数', value: 0, color: '#67C23A', icon: 'Avatar' },
  { key: 'drugCount',    label: '药品总数', value: 0, color: '#E6A23C', icon: 'MagicStick' },
  { key: 'diseaseCount', label: '疾病总数', value: 0, color: '#F56C6C', icon: 'FirstAidKit' }
])

const handleResize = () => { chart && chart.resize() }

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  try {
    const res = await getStatisticsOverview()
    stats.value.forEach(s => { s.value = res.data[s.key] || 0 })
    initChart(res.data)
  } catch (e) {}
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart && chart.dispose()
  chart = null
})

function initChart(data) {
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['数量'] },
    xAxis: {
      type: 'category',
      data: ['患者', '医生', '药品', '疾病']
    },
    yAxis: { type: 'value' },
    series: [{
      name: '数量',
      type: 'bar',
      data: [data.patientCount, data.doctorCount, data.drugCount, data.diseaseCount],
      itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] }
    }]
  })
}
</script>

<style scoped>
.dashboard { padding: 20px; }
.stat-row { margin-top: 10px; }
.stat-card { cursor: default; }
.stat-body { flex: 1; }
.stat-num { font-size: 36px; font-weight: bold; margin-bottom: 4px; }
.stat-label { color: #909399; font-size: 14px; }
:deep(.el-card__body) { display: flex; align-items: center; justify-content: space-between; padding: 20px; }
</style>
