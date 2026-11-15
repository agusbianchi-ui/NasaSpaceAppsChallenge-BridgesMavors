const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '')

export class MarsApiError extends Error {
  constructor(message, { code = 'api_error', status = 0 } = {}) {
    super(message)
    this.name = 'MarsApiError'
    this.code = code
    this.status = status
  }
}

async function request(path, { signal, method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw error
    }
    throw new MarsApiError(
      'Could not reach the MARS OPS API. Check that the backend is running.',
      { code: 'network_error' },
    )
  }

  let payload
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok || payload?.success === false) {
    throw new MarsApiError(
      payload?.error?.message ??
        `MARS OPS API request failed with status ${response.status}.`,
      {
        code: payload?.error?.code ?? 'api_error',
        status: response.status,
      },
    )
  }

  return payload?.data
}

export function fetchMarsLayers({ signal } = {}) {
  return request('/api/v1/mars/layers', { signal })
}

export function fetchMarsLayerCapabilities(
  layerId,
  { live = false, signal } = {},
) {
  const query = live ? '?live=true' : ''
  return request(
    `/api/v1/mars/layers/${encodeURIComponent(layerId)}/capabilities${query}`,
    { signal },
  )
}

export function fetchJezeroLocation({ signal } = {}) {
  return request('/api/v1/mars/locations/jezero', { signal })
}

export function fetchAeolianDatasets({ signal } = {}) {
  return request('/api/v1/aeolian/datasets', { signal })
}

export function analyzeAeolian(payload, { signal } = {}) {
  return request('/api/v1/aeolian/analyze', {
    method: 'POST',
    body: payload,
    signal,
  })
}

export function fetchAeolianResult(analysisId, { signal } = {}) {
  return request(
    `/api/v1/aeolian/results/${encodeURIComponent(analysisId)}`,
    { signal },
  )
}

// Scientific queries share the transport and support cancellation. No forecast default.
export function fetchTerrainMetadata({ signal } = {}) {
  return request('/api/v1/terrain/metadata', { signal })
}
export function fetchTerrainPoint(position, { marsYear, sol, signal } = {}) {
  const query = new URLSearchParams()
  for (const key of ['x', 'z', 'latitude', 'longitude']) {
    if (position[key] !== undefined) query.set(key, String(position[key]))
  }
  if (marsYear !== undefined) query.set('mars_year', String(marsYear))
  if (sol !== undefined) query.set('sol', String(sol))
  return request(`/api/v1/terrain/point?${query}`, { signal })
}
export function fetchScienceSources({ signal } = {}) {
  return request('/api/v1/science/sources', { signal })
}
export function fetchScienceVariables({ signal } = {}) {
  return request('/api/v1/science/variables', { signal })
}
export function fetchMissionScenarios({ signal } = {}) {
  return request('/api/v1/mission/scenarios', { signal })
}

export function inspectMissionPoint(position, mission, { signal } = {}) {
  return request('/api/v1/science/inspect', { method:'POST', body:{points:[position,position],mission}, signal })
}
export function fetchHazardRegions(mission, { signal } = {}) {
  return request('/api/v1/hazard/regions', { method:'POST', body:{mission}, signal })
}
export function startPlanning(body, { signal } = {}) {
  return request('/api/v1/plan/route', { method:'POST', body, signal })
}
export function fetchPlanningJob(id, { signal } = {}) {
  return request(`/api/v1/plan/jobs/${id}`, { signal })
}
export function cancelPlanningJob(id) {
  return request(`/api/v1/plan/jobs/${id}`, { method:'DELETE' })
}
