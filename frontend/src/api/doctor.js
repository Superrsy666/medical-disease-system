import request from '../utils/request'

export const getDoctors = (params) => request.get('/doctors', { params })
export const verifyDoctor = (id, data) => request.put(`/doctors/${id}/verify`, data)
