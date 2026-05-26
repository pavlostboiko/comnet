import http from './http.js'

export const getUsers       = ()              => http.get('/users')
export const createUser     = (data)          => http.post('/users', data)
export const updateUser     = (id, data)      => http.put(`/users/${id}`, data)
export const setUserPassword = (id, password) => http.post(`/users/${id}/password`, { password })
export const deleteUser     = (id)            => http.delete(`/users/${id}`)
