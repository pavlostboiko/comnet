import http from './http.js'

export const getMovements    = ()           => http.get('/movements').then(r => r.data)
export const getMovement     = (id)         => http.get(`/movements/${id}`).then(r => r.data)
export const createMovement  = (data)       => http.post('/movements', data).then(r => r.data)
export const updateMovement  = (id, data)   => http.put(`/movements/${id}`, data).then(r => r.data)
export const deleteMovement  = (id)         => http.delete(`/movements/${id}`)
