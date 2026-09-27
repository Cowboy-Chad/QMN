import { request } from './client.js'

export function startRumbleAnalysis(data) {
  return request('/rumble/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function checkRumbleResult(videoUrl, pattern) {
  const params = new URLSearchParams({ video_url: videoUrl, pattern })
  return request(`/rumble/check-result?${params.toString()}`)
}

export function getChannelVideos(limit = 100) {
  return request(`/channel/videos?limit=${limit}`)
}