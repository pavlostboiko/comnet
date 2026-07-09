import http from './http.js'

export const wipeInventory   = () => http.post('/admin/wipe-inventory')

function uploadXlsx(path, file) {
  const fd = new FormData()
  fd.append('file', file)
  return http.post(path, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const importItems     = (file) => uploadXlsx('/admin/import/items',     file)
export const importMovements = (file) => uploadXlsx('/admin/import/movements', file)

export const mergeNonserialPreview = () => http.get('/admin/merge-nonserial-duplicates/preview')
export const mergeNonserialApply   = () => http.post('/admin/merge-nonserial-duplicates')
