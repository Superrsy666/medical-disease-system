import request from '../utils/request'

export const getDiseases = (params) => request.get('/diseases', { params })
export const getDisease = (id) => request.get(`/diseases/${id}`)
export const getDiseaseDrugs = (id) => request.get(`/diseases/${id}/drugs`)
export const createDisease = (data) => request.post('/diseases', data)
export const updateDisease = (id, data) => request.put(`/diseases/${id}`, data)
export const deleteDisease = (id) => request.delete(`/diseases/${id}`)
