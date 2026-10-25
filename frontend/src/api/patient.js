import request from '../utils/request'

export const getPatients = (params) => request.get('/patients', { params })
export const getPatient = (id) => request.get(`/patients/${id}`)
export const updatePatient = (id, data) => request.put(`/patients/${id}`, data)
