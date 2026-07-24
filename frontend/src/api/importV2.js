import http from './http.js'

export function importItems(file) {
  const fd = new FormData()
  fd.append('file', file)
  return http.post('/admin/v2/import/items', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
