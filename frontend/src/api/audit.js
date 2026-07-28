import http from './http.js'

export const getAudit = (params) => http.get('/audit', { params })
export const getAuditMeta = () => http.get('/audit/meta')
