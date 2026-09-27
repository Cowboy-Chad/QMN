import { request } from './client.js'

export function startYouTubeAnalysis(data) {
  return request('/youtube/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function checkYouTubeResult(videoUrl, pattern) {
  const params = new URLSearchParams({ video_url: videoUrl, pattern })
  return request(`/youtube/check-result?${params.toString()}`)
}