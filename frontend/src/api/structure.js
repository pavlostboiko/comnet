import http from './http.js'

// Units
export const getUnits   = ()         => http.get('/structure/units')
export const createUnit = (data)     => http.post('/structure/units', data)
export const updateUnit = (id, data) => http.put(`/structure/units/${id}`, data)
export const deleteUnit = (id)       => http.delete(`/structure/units/${id}`)

// Groups
export const getGroups   = ()         => http.get('/structure/groups')
export const createGroup = (data)     => http.post('/structure/groups', data)
export const updateGroup = (id, data) => http.put(`/structure/groups/${id}`, data)
export const deleteGroup = (id)       => http.delete(`/structure/groups/${id}`)

// Warehouses (read-only, auto-created)
export const getWarehouses = () => http.get('/structure/warehouses')

// МВО
export const getMvo    = ()         => http.get('/structure/mvo')
export const createMvo = (data)     => http.post('/structure/mvo', data)
export const updateMvo = (id, data) => http.put(`/structure/mvo/${id}`, data)
