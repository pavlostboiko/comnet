import http from './http'

export const getDocuments   = (docType)    => http.get('/documents', { params: docType ? { doc_type: docType } : {} }).then(r => r.data)
export const getDocument    = (id)         => http.get(`/documents/${id}`).then(r => r.data)
export const createDocument = (data)       => http.post('/documents', data).then(r => r.data)
export const updateDocument = (id, data)   => http.put(`/documents/${id}`, data).then(r => r.data)
export const deleteDocument = (id)         => http.delete(`/documents/${id}`)
export const signDocument   = (id)         => http.post(`/documents/${id}/sign`).then(r => r.data)
export const unsignDocument = (id)         => http.post(`/documents/${id}/unsign`).then(r => r.data)
export const exportDocumentXlsx = (id)     => http.get(`/documents/${id}/export/xlsx`, { responseType: 'blob' })
