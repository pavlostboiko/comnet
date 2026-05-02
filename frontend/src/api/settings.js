import http from './http.js'

// Unit
export const getUnit = () => http.get('/settings/unit')
export const updateUnit = (data) => http.put('/settings/unit', data)

// Op Types
export const getOpTypes = () => http.get('/settings/op-types')
export const createOpType = (data) => http.post('/settings/op-types', data)
export const updateOpType = (id, data) => http.put(`/settings/op-types/${id}`, data)
export const deleteOpType = (id) => http.delete(`/settings/op-types/${id}`)

// Op Type Details
export const getOpTypeDetails = () => http.get('/settings/op-types-detail')
export const createOpTypeDetail = (data) => http.post('/settings/op-types-detail', data)
export const updateOpTypeDetail = (id, data) => http.put(`/settings/op-types-detail/${id}`, data)
export const deleteOpTypeDetail = (id) => http.delete(`/settings/op-types-detail/${id}`)

// Persons
export const getPersons = () => http.get('/settings/persons')
export const createPerson = (data) => http.post('/settings/persons', data)
export const updatePerson = (id, data) => http.put(`/settings/persons/${id}`, data)
export const deletePerson = (id) => http.delete(`/settings/persons/${id}`)
