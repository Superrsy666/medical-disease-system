import request from '../utils/request'

export const login = (data) => request.post('/auth/login', data)
export const register = (data) => request.post('/auth/register', data)
export const getMe = () => request.get('/auth/me')
export const forgotPassword = (data) => request.post('/auth/forgot-password', data)
export const resetPassword = (data) => request.post('/auth/reset-password', data)
