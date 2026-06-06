import http from './http.js'

export const getRecipients    = ()         => http.get('/recipients')
export const createRecipient  = (data)     => http.post('/recipients', data)
export const updateRecipient  = (id, data) => http.put(`/recipients/${id}`, data)
export const deleteRecipient  = (id)       => http.delete(`/recipients/${id}`)
