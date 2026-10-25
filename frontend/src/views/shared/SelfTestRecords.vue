<template>
  <div class="page">
    <h2>患者症状自测记录</h2>
    <el-card>
      <el-table :data="records" border stripe v-loading="loading">
        <el-table-column prop="patientName" label="患者姓名" width="120" />
        <el-table-column prop="patientUsername" label="患者账号" width="140" />
        <el-table-column prop="inputSymptoms" label="症状描述" min-width="260" show-overflow-tooltip />
        <el-table-column prop="matchedDisease" label="匹配结果" min-width="180" />
        <el-table-column prop="confidence" label="匹配度" width="100">
          <template #default="{ row }">{{ row.confidence ?? 0 }}%</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="提交时间" width="180" />
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getSelfTests } from '../../api/selfTest'

const records = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const loading = ref(false)

const loadData = async () => {
  loading.value = true
  try {
    const res = await getSelfTests({ page: page.value, size: size.value })
    records.value = res.data.records || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page { padding: 20px; }
</style>
