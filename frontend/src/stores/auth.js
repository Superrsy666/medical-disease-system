import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMe } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const role = ref(Number(localStorage.getItem('role')) || 0)
  const username = ref(localStorage.getItem('username') || '')
  const realName = ref(localStorage.getItem('realName') || '')
  const userId = ref(Number(localStorage.getItem('userId')) || 0)

  function setLogin(data) {
    token.value = data.token
    role.value = data.role
    username.value = data.username
    realName.value = data.realName || ''
    userId.value = data.userId
    localStorage.setItem('token', data.token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('username', data.username)
    localStorage.setItem('realName', data.realName || '')
    localStorage.setItem('userId', data.userId)
  }

  function logout() {
    token.value = ''
    role.value = 0
    username.value = ''
    realName.value = ''
    userId.value = 0
    localStorage.clear()
  }

  async function fetchUserInfo() {
    try {
      const res = await getMe()
      if (res.code === 200) {
        realName.value = res.data.realName || ''
        localStorage.setItem('realName', realName.value)
      }
    } catch (e) {
      console.error('获取用户信息失败', e)
    }
  }

  return { token, role, username, realName, userId, setLogin, logout, fetchUserInfo }
})
