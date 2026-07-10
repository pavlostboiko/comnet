import http from './http.js'

export const getResiduesByUnit       = ()     => http.get('/residues/by-unit')
export const getResiduesByUnitDetail = (unit) => http.get(`/residues/by-unit/${encodeURIComponent(unit)}`)
export const getResiduesByRecipient       = ()    => http.get('/residues/by-recipient')
export const getResiduesByRecipientDetail = (rid) => http.get(`/residues/by-recipient/${rid}`)
