<template>
  <div class="page">
    <h2>用户管理</h2>
    <el-card>
      <el-table :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="realName" label="姓名" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="role" label="角色">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="注册时间" width="180" />
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="size"
        :total="total" layout="prev,pager,next,total" @change="loadData" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../../utils/request'

const tableData = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)

const roleLabel = (role) => ['', '管理员', '医生', '患者'][role] || '未知'
const roleType = (role) => [, 'danger', 'warning', 'success'][role] || 'info'

const loadData = async () => {
  const res = await request.get('/auth/users', { params: { page: page.value, size: size.value } })
  if (res.code === 200) {
    tableData.value = res.data.records || []
    total.value = res.data.total || 0
  }
}

onMounted(loadData)
</script>

<style scoped>
.page { padding: 20px; }
</style>
