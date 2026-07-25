import http from './http.js'

export const getMovements   = ()       => http.get('/custody/movements')
export const createMovement = (data)   => http.post('/custody/movements', data)
export const createDocument  = (data)  => http.post('/custody/document', data)
export const getBalances    = (whId)   => http.get(`/custody/balances?warehouse_id=${whId}`)
export const getSerialAt     = (whId)  => http.get(`/custody/serial?warehouse_id=${whId}`)
export const whereIs         = (nomId) => http.get(`/custody/where?nomenclature_id=${nomId}`)
export const getTotals       = ()      => http.get('/custody/totals')

// v2 documents (накладна/акт над рухами)
export const getDocs      = (params) => http.get('/custody/documents', { params })
export const getDoc       = (id)     => http.get(`/custody/documents/${id}`)
export const createDoc    = (data)   => http.post('/custody/documents', data)
export const updateDoc    = (id, d)  => http.put(`/custody/documents/${id}`, d)
export const signDoc      = (id)     => http.post(`/custody/documents/${id}/sign`)
export const unsignDoc    = (id)     => http.post(`/custody/documents/${id}/unsign`)
export const deleteDoc    = (id)     => http.delete(`/custody/documents/${id}`)
export const exportDocXlsx = (id)    => http.get(`/custody/documents/${id}/export/xlsx`, { responseType: 'blob' })
