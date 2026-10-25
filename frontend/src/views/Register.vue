<template>
  <div class="register-page">
    <div class="register-container">
      <el-card class="register-card">
        <template #header>
          <h2 class="register-title">账号注册</h2>
        </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="3-50个字符" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="注册身份" prop="role">
          <el-select v-model="form.role" placeholder="请选择注册身份" style="width:100%">
            <el-option label="医生" :value="2" />
            <el-option label="患者" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.realName" placeholder="真实姓名（可选）" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="手机号（可选）" />
        </el-form-item>
        <template v-if="form.role === 3">
          <el-form-item label="出生日期">
            <el-date-picker v-model="form.birthDate" type="date" value-format="YYYY-MM-DD"
              placeholder="选择出生日期" style="width:100%" />
          </el-form-item>
          <el-form-item label="性别">
            <el-radio-group v-model="form.gender">
              <el-radio :value="1">男</el-radio>
              <el-radio :value="2">女</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="身高(cm)">
            <el-input v-model="form.height" placeholder="如 170" />
          </el-form-item>
          <el-form-item label="体重(kg)">
            <el-input v-model="form.weight" placeholder="如 60" />
          </el-form-item>
          <el-form-item label="过敏史">
            <el-input v-model="form.allergyHistory" placeholder="如：青霉素过敏（可选）" />
          </el-form-item>
          <el-form-item label="地址">
            <el-input v-model="form.address" placeholder="家庭地址（可选）" />
          </el-form-item>
        </template>
        <template v-if="form.role === 2">
          <el-form-item label="科室"><el-input v-model="form.department" placeholder="所属科室" /></el-form-item>
          <el-form-item label="职称"><el-input v-model="form.title" placeholder="职称（可选）" /></el-form-item>
          <el-form-item label="医院"><el-input v-model="form.hospital" placeholder="所属医院" /></el-form-item>
        </template>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleRegister" style="width:100%">
            注册
          </el-button>
        </el-form-item>
        <div class="login-link">
          已有账号？<el-link type="primary" @click="$router.push('/login')">返回登录</el-link>
        </div>
      </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '../api/auth'

const router = useRouter()
const formRef = ref()
const loading = ref(false)

// 仅保留非敏感信息（用户名、身份）到本地，姓名/手机号/地址等个人隐私不落盘
const savedForm = JSON.parse(localStorage.getItem('savedRegisterForm') || '{}')
const form = reactive({
  username: savedForm.username || '',
  password: '',
  role: savedForm.role || 3,
  realName: '',
  phone: '',
  gender: 1,
  birthDate: '',
  height: '',
  weight: '',
  allergyHistory: '',
  address: '',
  department: '',
  title: '',
  hospital: ''
})
const rules = {
  username: [{ required: true, min: 3, max: 50, message: '用户名长度3-50', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
  role: [{ required: true, message: '请选择注册身份', trigger: 'change' }]
}

watch(
  () => ({ username: form.username, role: form.role }),
  (val) => {
    localStorage.setItem('savedRegisterForm', JSON.stringify(val))
  },
  { deep: true }
)

const handleRegister = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await register(form)
    localStorage.removeItem('savedRegisterForm')
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: clamp(90px, 14vw, 220px);
  background-color: #eef3f8;
  background-image: url('/login-bg.jpg');
  background-size: cover;
  background-size: cover;
  background-position: 35% center;
  background-attachment: fixed;
  background-repeat: no-repeat;
}
.register-container {
  width: 100%;
  max-width: 500px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.register-card {
  width: 460px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 18px;
  box-shadow: 0 20px 60px rgba(15, 45, 90, 0.12);
}
.register-title {
  text-align: center;
  margin: 0;
  font-size: 22px;
  color: #303133;
}
.login-link {
  text-align: center;
  font-size: 14px;
  color: #606266;
}
@media (max-width: 768px) {
  .register-page {
    padding: 24px 16px;
    justify-content: center;
    background-position: center;
    background-attachment: scroll;
  }
  .register-container { max-width: 100%; justify-content: center; }
  .register-card { width: 100%; }
}
</style>
