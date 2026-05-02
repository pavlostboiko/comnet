import http from './http.js'

export const getItems  = ()        => http.get('/items').then(r => r.data)
export const getItem   = (id)      => http.get(`/items/${id}`).then(r => r.data)
export const createItem = (data)   => http.post('/items', data).then(r => r.data)
export const updateItem = (id, data) => http.put(`/items/${id}`, data).then(r => r.data)
export const deleteItem = (id)     => http.delete(`/items/${id}`)
