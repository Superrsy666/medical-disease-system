<template>
  <div class="page">
    <h2>医生审核</h2>
    <el-card>
      <el-table :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="realName" label="姓名" />
        <el-table-column prop="hospital" label="医院" />
        <el-table-column prop="department" label="科室" />
        <el-table-column prop="title" label="职称" />
        <el-table-column prop="isVerified" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.isVerified === 1 ? 'success' : 'warning'">
              {{ row.isVerified === 1 ? '已通过' : '待审核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" type="success" :disabled="row.isVerified === 1"
              @click="handleVerify(row, 1)">通过</el-button>
            <el-button size="small" type="danger" :disabled="row.isVerified === 0"
              @click="handleVerify(row, 0)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDoctors, verifyDoctor } from '../../api/doctor'

const tableData = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)

const loadData = async () => {
  const res = await getDoctors({ page: page.value, size: size.value })
  tableData.value = res.data.records || []
  total.value = res.data.total || 0
}

const handleVerify = async (row, status) => {
  await verifyDoctor(row.id, { isVerified: status })
  ElMessage.success(status === 1 ? '已通过' : '已驳回')
  row.isVerified = status
}

onMounted(loadData)
</script>

<style scoped>
.page { padding: 20px; }
</style>
