import request from '../utils/request'

export const getRecords = (params) => request.get('/records', { params })
export const getRecord = (id) => request.get(`/records/${id}`)
export const createRecord = (data) => request.post('/records', data)
