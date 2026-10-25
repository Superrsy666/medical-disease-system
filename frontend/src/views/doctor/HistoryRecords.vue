<template>
  <div class="page">
    <h2>历史病历</h2>
    <el-card>
      <el-table :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="patientName" label="患者" />
        <el-table-column prop="visitDate" label="就诊日期" width="120" />
        <el-table-column prop="diagnosis" label="诊断" />
        <el-table-column prop="chiefComplaint" label="主诉" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="['','','warning','success'][row.status]">
              {{ ['','初诊','复诊','痊愈'][row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="处方" width="80">
          <template #default="{ row }">
            <el-button size="small" @click="showPrescription(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="处方详情" width="400px">
      <div v-if="currentRecord?.prescription">
        <div v-for="(item, i) in currentRecord.prescription" :key="i" class="presc-item">
          <el-tag>药品ID: {{ item.drugId }}</el-tag>
          <span style="margin-left:8px">{{ item.dosage }}</span>
        </div>
      </div>
      <span v-else>无处方</span>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRecords } from '../../api/record'

const tableData = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const currentRecord = ref(null)

const loadData = async () => {
  const res = await getRecords({ page: page.value, size: size.value })
  tableData.value = res.data.records || []
  total.value = res.data.total || 0
}

const showPrescription = (row) => {
  currentRecord.value = row
  dialogVisible.value = true
}

onMounted(loadData)
</script>

<style scoped>
.page { padding: 20px; }
.presc-item { padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
</style>
