import http from './http.js'

export const listSplits   = (itemId)         => http.get(`/items/${itemId}/splits`)
export const createSplit  = (itemId, data)   => http.post(`/items/${itemId}/splits`, data)
export const returnSplit  = (itemId, id, data = {}) => http.post(`/items/${itemId}/splits/${id}/return`, data)
export const deleteSplit  = (itemId, id)     => http.delete(`/items/${itemId}/splits/${id}`)
