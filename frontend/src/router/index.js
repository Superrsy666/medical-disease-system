import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue')
  },
  // ========== 管理员 ==========
  {
    path: '/admin',
    component: () => import('../views/layout/AdminLayout.vue'),
    meta: { role: 1 },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'AdminDashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'users', name: 'UserManage', component: () => import('../views/admin/UserManage.vue') },
      { path: 'doctors/verify', name: 'DoctorVerify', component: () => import('../views/admin/DoctorVerify.vue') },
      { path: 'self-tests', name: 'AdminSelfTests', component: () => import('../views/shared/SelfTestRecords.vue') },
      { path: 'diseases', name: 'DiseaseManage', component: () => import('../views/admin/DiseaseManage.vue') },
      { path: 'drugs', name: 'DrugManage', component: () => import('../views/admin/DrugManage.vue') }
    ]
  },
  // ========== 医生 ==========
  {
    path: '/doctor',
    component: () => import('../views/layout/DoctorLayout.vue'),
    meta: { role: 2 },
    children: [
      { path: '', redirect: '/doctor/patients' },
      { path: 'patients', name: 'MyPatients', component: () => import('../views/doctor/MyPatients.vue') },
      { path: 'write-record', name: 'WriteRecord', component: () => import('../views/doctor/WriteRecord.vue') },
      { path: 'records', name: 'HistoryRecords', component: () => import('../views/doctor/HistoryRecords.vue') },
      { path: 'self-tests', name: 'DoctorSelfTests', component: () => import('../views/shared/SelfTestRecords.vue') },
      { path: 'disease-search', name: 'DoctorDiseaseSearch', component: () => import('../views/doctor/DiseaseSearch.vue') },
      { path: 'drug-search', name: 'DoctorDrugSearch', component: () => import('../views/doctor/DrugSearch.vue') }
    ]
  },
  // ========== 患者 ==========
  {
    path: '/patient',
    component: () => import('../views/layout/PatientLayout.vue'),
    meta: { role: 3 },
    children: [
      { path: '', redirect: '/patient/records' },
      { path: 'records', name: 'MyRecords', component: () => import('../views/patient/MyRecords.vue') },
      { path: 'self-test', name: 'SelfTest', component: () => import('../views/patient/SelfTest.vue') },
      { path: 'disease-search', name: 'PatientDiseaseSearch', component: () => import('../views/patient/DiseaseSearch.vue') },
      { path: 'drug-search', name: 'PatientDrugSearch', component: () => import('../views/patient/DrugSearch.vue') }
    ]
  },
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.path === '/login' || to.path === '/register') {
    if (auth.token && auth.role) {
      // 已登录，跳转对应工作台
      const homeMap = { 1: '/admin', 2: '/doctor', 3: '/patient' }
      next(homeMap[auth.role] || '/login')
    } else {
      next()
    }
    return
  }

  if (!auth.token) {
    next('/login')
    return
  }

  // 角色权限校验
  const requiredRole = to.matched.find(r => r.meta.role)?.meta.role
  if (requiredRole && requiredRole !== auth.role) {
    auth.logout()
    next('/login')
    return
  }

  next()
})

export default router
