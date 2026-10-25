<template>
  <div class="page">
    <h2>我的病历</h2>
    <el-card>
      <el-table :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="visitDate" label="就诊日期" width="120" />
        <el-table-column prop="diagnosis" label="诊断" />
        <el-table-column prop="chiefComplaint" label="主诉" show-overflow-tooltip />
        <el-table-column prop="doctorName" label="接诊医生" width="120" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="['','','warning','success'][row.status]">
              {{ ['','初诊','复诊','痊愈'][row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="diagnosisDetail" label="诊断详情" show-overflow-tooltip />
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRecords } from '../../api/record'

const tableData = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)

const loadData = async () => {
  const res = await getRecords({ page: page.value, size: size.value })
  tableData.value = res.data.records || []
  total.value = res.data.total || 0
}

onMounted(loadData)
</script>

<style scoped>
.page { padding: 20px; }
</style>
