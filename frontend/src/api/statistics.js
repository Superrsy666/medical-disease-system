import request from '../utils/request'

export const predict = (data) => request.post('/prediction', data)
export const predictDemo = (data) => request.post('/prediction/demo', data)
export const getStatisticsOverview = () => request.get('/statistics/overview')
