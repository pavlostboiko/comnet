import http from './http.js'

function upload(url, file) {
  const fd = new FormData()
  fd.append('file', file)
  return http.post(url, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const importItems       = (file) => upload('/admin/v2/import/items', file)
export const importMovements   = (file) => upload('/admin/v2/import/movements', file)
export const importAssignments = (file) => upload('/admin/v2/import/assignments', file)
export const wipeV2            = ()     => http.post('/admin/v2/wipe')
export const wipePersonsV2     = ()     => http.post('/admin/v2/wipe-persons')
