import request from '../utils/request'
import axios from 'axios'

export const getSelfTests = (params) => request.get('/self-tests', { params })

// ===== AI 智能问诊（Python FastAPI 深度学习 + Agent 服务）=====
// 不走统一拦截器（AI 服务返回结构与 Spring 不同），超时放宽到 90s
const aiClient = axios.create({
  baseURL: '/ai',
  timeout: 90000
})

export const aiConsult = (data) => aiClient.post('/agent/chat', data)

export const aiHealth = () => aiClient.get('/health')
