import { request } from './client.js'

export function getHistory(params = {}) {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v) qs.set(k, v)
  }
  return request(`/history?${qs.toString()}`)
}