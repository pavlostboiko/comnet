import http from './http.js'

export const getNomenclature    = ()         => http.get('/nomenclature')
export const createNomenclature = (data)     => http.post('/nomenclature', data)
export const updateNomenclature = (id, data) => http.put(`/nomenclature/${id}`, data)
export const deleteNomenclature = (id)       => http.delete(`/nomenclature/${id}`)

export const getInstances   = (nid)       => http.get(`/nomenclature/${nid}/instances`)
export const createInstance = (nid, data) => http.post(`/nomenclature/${nid}/instances`, data)
export const updateInstance = (nid, iid, data) => http.put(`/nomenclature/${nid}/instances/${iid}`, data)
export const deleteInstance = (nid, iid)  => http.delete(`/nomenclature/${nid}/instances/${iid}`)
