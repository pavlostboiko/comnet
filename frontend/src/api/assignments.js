import http from './http.js'

export const getAssignments   = (whId)      => http.get(`/assignments?warehouse_id=${whId}&active=true`)
export const createAssignment = (data)      => http.post('/assignments', data)
export const returnAssignment = (id, data = {}) => http.post(`/assignments/${id}/return`, data)
export const groupHoldings    = (groupId)   => http.get(`/assignments/group/${groupId}`)
