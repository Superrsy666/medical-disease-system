<template>
  <el-container class="layout-container">
    <!-- 桌面端侧边栏 -->
    <el-aside width="220px" class="aside">
      <div class="logo">患者中心</div>
      <el-menu :default-active="$route.path" router background-color="#2d6a4f" text-color="#b7e4c7" active-text-color="#ffffff">
        <el-menu-item v-for="m in menus" :key="m.index" :index="m.index">
          <el-icon><component :is="m.icon" /></el-icon><span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button class="menu-btn" text @click="drawerOpen = true">
            <el-icon size="22"><Menu /></el-icon>
          </el-button>
          <span class="welcome">欢迎，{{ auth.realName || auth.username }}（患者）</span>
        </div>
        <el-button type="danger" size="small" @click="handleLogout">退出</el-button>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>

    <!-- 移动端抽屉菜单 -->
    <el-drawer v-model="drawerOpen" direction="ltr" size="220px" :with-header="false" class="menu-drawer">
      <div class="logo drawer-logo">患者中心</div>
      <el-menu :default-active="$route.path" router background-color="#2d6a4f" text-color="#b7e4c7" active-text-color="#ffffff" @select="drawerOpen = false">
        <el-menu-item v-for="m in menus" :key="m.index" :index="m.index">
          <el-icon><component :is="m.icon" /></el-icon><span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useRouter } from 'vue-router'
const auth = useAuthStore()
const router = useRouter()
const handleLogout = () => { auth.logout(); router.push('/login') }

const menus = [
  { index: '/patient/records', icon: 'Document', label: '我的病历' },
  { index: '/patient/self-test', icon: 'FirstAidKit', label: '症状自测' },
  { index: '/patient/disease-search', icon: 'Search', label: '疾病查询' },
  { index: '/patient/drug-search', icon: 'MedicineBox', label: '药品查询' }
]
const drawerOpen = ref(false)
</script>

<style scoped>
.layout-container { height: 100vh; }
.aside { background: #2d6a4f; }
.logo { height: 60px; line-height: 60px; text-align: center; color: #fff; font-size: 16px; font-weight: bold; background: #1b4332; }
.header { background: #fff; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.header-left { display: flex; align-items: center; gap: 6px; min-width: 0; }
.welcome { color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.main { background: #f0f2f5; overflow-y: auto; }
.menu-btn { display: none; }
.drawer-logo { background: #1b4332; }

@media (max-width: 768px) {
  .aside { display: none; }
  .menu-btn { display: inline-flex; }
  .header { padding: 0 10px; }
  .welcome { font-size: 14px; }
}
</style>
