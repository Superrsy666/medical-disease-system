<template>
  <div class="page">
    <h2>我的患者</h2>
    <el-card>
      <el-table :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="realName" label="姓名" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="gender" label="性别">
          <template #default="{ row }">{{ ['未知','男','女'][row.gender] }}</template>
        </el-table-column>
        <el-table-column prop="birthDate" label="出生日期" width="120" />
        <el-table-column prop="allergyHistory" label="过敏史" show-overflow-tooltip />
        <el-table-column prop="address" label="地址" show-overflow-tooltip />
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPatients } from '../../api/patient'

const tableData = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)

const loadData = async () => {
  const res = await getPatients({ page: page.value, size: size.value })
  tableData.value = res.data.records || []
  total.value = res.data.total || 0
}

onMounted(loadData)
</script>

<style scoped>
.page { padding: 20px; }
</style>
