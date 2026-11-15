import { useEffect, useState, useRef, AbortController } from 'react'

export function useApi() {
  const [apiBaseUrl, setApiBaseUrl] = useState(
    typeof window !== 'undefined'
      ? (window.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
      : 'http://127.0.0.1:8000'
  )
  const controllerRef = useRef(null)

  const fetch = async (endpoint, options = {}) => {
    const controller = new AbortController()
    controllerRef.current = controller

    const signal = options.signal || controller.signal

    try {
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        headers: { Accept: 'application/json' },
        signal,
        ...options,
      })

      let payload
      try {
        payload = await response.json()
      } catch {
        payload = null
      }

      if (!response.ok) {
        const errorMsg = payload?.error?.message ??
          `API request failed with status ${response.status}.`
        throw new Error(errorMsg)
      }

      return payload?.data || payload
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error
      }
      throw error
    } finally {
      // Auto-abort when component unmounts or fetch completes
      if (!options.keepAlive && controllerRef.current === controller) {
        controller.abort()
        controllerRef.current = null
      }
    }
  }

  const cancel = () => {
    if (controllerRef.current) {
      controllerRef.current.abort()
      controllerRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      cancel()
    }
  }, [])

  return { apiBaseUrl, setApiBaseUrl, fetch, cancel }
}