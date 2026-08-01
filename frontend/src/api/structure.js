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

// Warehouses (auto-created; only name is editable)
export const getWarehouses   = ()         => http.get('/structure/warehouses')
export const renameWarehouse = (id, name) => http.put(`/structure/warehouses/${id}`, { name })

// Точки зберігання (фізичне розміщення всередині складу)
export const getStoragePoints   = (whId) => http.get('/structure/storage-points', { params: { warehouse_id: whId || undefined } })
export const createStoragePoint = (data) => http.post('/structure/storage-points', data)
export const renameStoragePoint = (id, name) => http.put(`/structure/storage-points/${id}`, { name })
export const deleteStoragePoint = (id)   => http.delete(`/structure/storage-points/${id}`)

// МВО
export const getMvo    = ()         => http.get('/structure/mvo')
export const createMvo = (data)     => http.post('/structure/mvo', data)
export const updateMvo = (id, data) => http.put(`/structure/mvo/${id}`, data)
export const deleteMvo = (id)       => http.delete(`/structure/mvo/${id}`)
