import request from '../utils/request'

export const getDrugs = (params) => request.get('/drugs', { params })
export const getDrug = (id) => request.get(`/drugs/${id}`)
export const createDrug = (data) => request.post('/drugs', data)
export const updateDrug = (id, data) => request.put(`/drugs/${id}`, data)
export const deleteDrug = (id) => request.delete(`/drugs/${id}`)
