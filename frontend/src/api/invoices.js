import http from './http'

export const getInvoices    = ()          => http.get('/invoices').then(r => r.data)
export const getInvoice     = (id)        => http.get(`/invoices/${id}`).then(r => r.data)
export const createInvoice  = (data)      => http.post('/invoices', data).then(r => r.data)
export const updateInvoice  = (id, data)  => http.put(`/invoices/${id}`, data).then(r => r.data)
export const deleteInvoice  = (id)        => http.delete(`/invoices/${id}`)
export const exportInvoiceXlsx = (id)     => http.get(`/invoices/${id}/export/xlsx`, { responseType: 'blob' })
