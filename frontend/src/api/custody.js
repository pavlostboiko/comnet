import http from './http.js'

export const getMovements   = ()       => http.get('/custody/movements')
export const createMovement = (data)   => http.post('/custody/movements', data)
export const getBalances    = (whId)   => http.get(`/custody/balances?warehouse_id=${whId}`)
export const getSerialAt     = (whId)  => http.get(`/custody/serial?warehouse_id=${whId}`)
export const whereIs         = (nomId) => http.get(`/custody/where?nomenclature_id=${nomId}`)
