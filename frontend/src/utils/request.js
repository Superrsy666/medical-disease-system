import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      if (res.code === 401) {
        localStorage.clear()
        router.push('/login')
      }
      return Promise.reject(new Error(res.message))
    }
    return res
  },
  error => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.clear()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error(error.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

export default request
