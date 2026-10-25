<template>
  <div class="login-page">
    <div class="login-container">
      <el-card class="login-card">
        <template #header>
          <h2 class="login-title">医疗疾病数据分析系统</h2>
        </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item label="登录身份" prop="role">
          <el-select v-model="form.role" placeholder="请选择登录身份" style="width:100%">
            <el-option label="管理员" :value="1" />
            <el-option label="医生" :value="2" />
            <el-option label="患者" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"
            prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" style="width:100%">
            登录
          </el-button>
        </el-form-item>
        <div class="register-link">
          <el-link type="info" @click="showForgotDialog = true">忘记密码？</el-link>
          <span style="margin: 0 8px">|</span>
          还没有账号？<el-link type="primary" @click="$router.push('/register')">立即注册</el-link>
        </div>
      </el-form>
      </el-card>
    </div>

    <!-- 忘记密码对话框 -->
    <el-dialog v-model="showForgotDialog" title="找回密码" width="400px" :close-on-click-modal="false">
      <el-steps :active="forgotStep" finish-status="success" align-center style="margin-bottom: 20px">
        <el-step title="验证身份" />
        <el-step title="重置密码" />
      </el-steps>

      <!-- 步骤1：验证身份 -->
      <el-form v-if="forgotStep === 0" :model="forgotForm" :rules="forgotRules" ref="forgotFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="forgotForm.username" placeholder="请输入用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="forgotForm.phone" placeholder="请输入注册时的手机号" prefix-icon="Phone" />
        </el-form-item>
      </el-form>

      <!-- 步骤2：重置密码 -->
      <el-form v-else :model="resetForm" :rules="resetRules" ref="resetFormRef" label-width="80px">
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetForm.newPassword" type="password" placeholder="请输入新密码" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="resetForm.confirmPassword" type="password" placeholder="请再次输入新密码" prefix-icon="Lock" show-password />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showForgotDialog = false">取消</el-button>
        <el-button v-if="forgotStep === 0" type="primary" @click="handleVerify" :loading="verifying">下一步</el-button>
        <el-button v-else type="primary" @click="handleReset" :loading="resetting">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { login, forgotPassword, resetPassword } from '../api/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)

const savedLogin = JSON.parse(localStorage.getItem('savedLogin') || '{}')
const form = reactive({
  username: savedLogin.username || '',
  password: '',
  role: savedLogin.role || 3
})
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择登录身份', trigger: 'change' }]
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await login(form)
    auth.setLogin(res.data)
    localStorage.setItem('savedLogin', JSON.stringify({
      username: form.username,
      role: form.role
    }))
    ElMessage.success('登录成功')
    const homeMap = { 1: '/admin', 2: '/doctor', 3: '/patient' }
    router.push(homeMap[res.data.role] || '/login')
  } finally {
    loading.value = false
  }
}

// 忘记密码相关
const showForgotDialog = ref(false)
const forgotStep = ref(0)
const forgotFormRef = ref()
const resetFormRef = ref()
const verifying = ref(false)
const resetting = ref(false)

const forgotForm = reactive({ username: '', phone: '' })
const forgotRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }]
}

const resetForm = reactive({ newPassword: '', confirmPassword: '' })
const resetRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== resetForm.newPassword) {
          callback(new Error('两次密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleVerify = async () => {
  const valid = await forgotFormRef.value.validate().catch(() => false)
  if (!valid) return
  verifying.value = true
  try {
    const res = await forgotPassword(forgotForm)
    if (res.code === 200) {
      ElMessage.success('验证成功，请设置新密码')
      forgotStep.value = 1
    } else {
      ElMessage.error(res.message || '验证失败')
    }
  } finally {
    verifying.value = false
  }
}

const handleReset = async () => {
  const valid = await resetFormRef.value.validate().catch(() => false)
  if (!valid) return
  resetting.value = true
  try {
    const res = await resetPassword({
      username: forgotForm.username,
      phone: forgotForm.phone,
      newPassword: resetForm.newPassword
    })
    if (res.code === 200) {
      ElMessage.success('密码重置成功，请使用新密码登录')
      showForgotDialog.value = false
      // 重置表单
      forgotStep.value = 0
      forgotForm.username = ''
      forgotForm.phone = ''
      resetForm.newPassword = ''
      resetForm.confirmPassword = ''
    } else {
      ElMessage.error(res.message || '重置失败')
    }
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: clamp(90px, 14vw, 220px);
  background-color: #eef3f8;
  background-image: url('/login-bg.jpg');
  background-size: cover;
  background-position: 35% center;
  background-attachment: fixed;
  background-repeat: no-repeat;
}
.login-container {
  width: 100%;
  max-width: 460px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.login-card {
  width: 420px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 18px;
  box-shadow: 0 20px 60px rgba(15, 45, 90, 0.12);
}
.login-title {
  text-align: center;
  margin: 0;
  color: #303133;
  font-size: 22px;
}
.register-link {
  text-align: center;
  margin-top: -10px;
  font-size: 14px;
  color: #606266;
}
@media (max-width: 768px) {
  .login-page {
    padding: 24px 16px;
    justify-content: center;
    background-position: center;
    background-attachment: scroll;
  }
  .login-container { max-width: 100%; justify-content: center; }
  .login-card { width: 100%; }
}
</style>
