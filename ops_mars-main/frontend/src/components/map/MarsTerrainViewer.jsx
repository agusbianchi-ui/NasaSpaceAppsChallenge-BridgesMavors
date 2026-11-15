import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import '../../styles/terrain.css'
import { useTerrainPlanning } from '../../hooks/useTerrainPlanning.js'
import TerrainPlanningControls from './TerrainPlanningControls.jsx'
import ScientificInspectionPanel from '../dashboard/ScientificInspectionPanel.jsx'
import { useApi } from '../hooks/useApi.jsx'

const BASE_URL = `${import.meta.env.BASE_URL}terrain`

const MarsTerrainViewer = forwardRef(function MarsTerrainViewer({ onInspect, onPlaceMarker }, ref) {
  const container = useRef(null), host = useRef(null), engine = useRef(null)
  const callbacks = useRef(null)
  const [grid, setGrid] = useState(null)
  const planning = useTerrainPlanning(grid, BASE_URL)
  const [attempt, setAttempt] = useState(0)
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState('')
  const [quality, setQuality] = useState('medium')
  const [fullscreen, setFullscreen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [notice, setNotice] = useState('')
  const [stats, setStats] = useState(null)
  const { api, setApi } = useApi()

  // Scientific inspection state
  const [inspectionPosition, setInspectionPosition] = useState(null)
  const [inspectionVariables, setInspectionVariables] = useState({})
  const [terrainMetadata, setTerrainMetadata] = useState({})
  const [showInspectionPanel, setShowInspectionPanel] = useState(false)

  // Close panel on unmount / re-render
  useEffect(() => {
    return () => {
      setShowInspectionPanel(false)
    }
  }, [])

  // Handle right-click inspection for scientific data
  useEffect(() => {
    const handleInspect = async (hit) => {
      if (!hit || !hit.x || !hit.z) return

      setShowInspectionPanel(true)
      setInspectionPosition({ x: hit.x, z: hit.z })
      setInspectionVariables({})
      setTerrainMetadata({})

      try {
        const params = new URLSearchParams()
        params.set('x', String(hit.x))
        params.set('z', String(hit.z))
        params.set('mars_year', '36')
        params.set('sol', '1')

        const response = await fetch(
          `${api}/api/v1/terrain/point?${params}`,
          { headers: { Accept: 'application/json' } }
        )
        const data = await response.json()

        if (data && data.data && data.data.variables) {
          setInspectionVariables(data.data.variables)
          setTerrainMetadata({
            availability: data.data.coverage,
            notice: data.data.notice,
          })
        } else {
          setTerrainMetadata({
            availability: data.data?.coverage || 'Unavailable',
            reason: data.error?.message || 'No scientific data available at this position',
          })
        }
      } catch (err) {
        console.error('Scientific inspection error:', err)
        setTerrainMetadata({
          availability: 'Error',
          reason: err.message || 'Could not reach science API',
        })
      }
    }

    // Attach inspection handler to the terrain engine's onInspect callback
    // This is set up in the engine initialization below
    callbacks.current = { inspect: hit => { planning.inspect(hit); onInspect?.(hit) } }
  }, [api, planning, onInspect])

  // Initialize the terrain engine with scientific inspection support
  useEffect(() => {
    if (!attempt) return undefined
    let active = true, current = null, lastProgress = 0
    import('../../terrain/createTerrainEngine.js').then(({ createTerrainEngine }) => {
      if (!active) return
      current = createTerrainEngine(host.current, {
        baseUrl: BASE_URL,
        onProgress: value => { if (active && (performance.now() - lastProgress > 100 || value.complete === value.count)) { lastProgress = performance.now(); setProgress(value) } },
        onReady: () => { if (active) setStatus('ready') },
        onError: message => { if (active) { setError(message); setStatus('error') } },
        onStats: value => { if (active) setStats(value) },
        onGeometry: value => { if (active) setGrid(value) },
        onInspect: hit => {
          callbacks.current?.inspect(hit)
          // Trigger scientific inspection on valid hits
          if (hit && hit.x !== undefined && hit.z !== undefined) {
            scientificInspect(hit)
          }
        },
        onPlace: hit => callbacks.current?.place(hit),
      })
    }).catch(err => { if (active) { setError(`3D graphics could not start: ${err.message}`); setStatus('error') } })
    return () => { active = false; current?.dispose(); engine.current = null }
  }, [attempt, api])

  // Scientific inspection handler - queries backend for variables
  const scientificInspect = async (hit) => {
    setShowInspectionPanel(true)
    setInspectionPosition({ x: hit.x, z: hit.z })
    setInspectionVariables({})
    setTerrainMetadata({})

    if (!hit.x || !hit.z) return

    try {
      const params = new URLSearchParams()
      params.set('x', String(hit.x))
      params.set('z', String(hit.z))
      params.set('mars_year', '36')
      params.set('sol', '1')

      const response = await fetch(
        `${api}/api/v1/terrain/point?${params}`,
        { headers: { Accept: 'application/json' } }
      )
      const data = await response.json()

      if (data && data.data && data.data.variables) {
        setInspectionVariables(data.data.variables)
        setTerrainMetadata({
          availability: data.data.coverage,
          notice: data.data.notice,
        })
      } else {
        setTerrainMetadata({
          availability: data.data?.coverage || 'Unavailable',
          reason: data.error?.message || 'No scientific data available at this position',
        })
      }
    } catch (err) {
      console.error('Scientific inspection error:', err)
      setTerrainMetadata({
        availability: 'Error',
        reason: err.message || 'Could not reach science API',
      })
    }
  }

  // Panel visibility effect
  useEffect(() => {
    return () => {
      setShowInspectionPanel(false)
    }
  }, [])

  const active = status !== 'idle' && Boolean(attempt)
  const percent = progress ? Math.min(100, Math.floor(progress.bytes / progress.total * 100)) : null

  return (
    <div ref={container} className={`terrain-viewer${expanded ? ' terrain-viewer--expanded' : ''}`}>
      <div className="terrain-toolbar" role="toolbar" aria-label="3D camera controls">
        <button type="button" disabled={!active} onClick={() => engine.current?.reset()}>Reset View</button>
        <button type="button" disabled={!active} onClick={() => engine.current?.top()}>Top View</button>
        <button type="button" disabled={!active} onClick={() => engine.current?.perspective()}>Perspective View</button>
        <label>Quality <select disabled={status !== 'ready'} aria-label="Graphics quality" value={quality} onChange={e => { setQuality(e.target.value); engine.current?.setQuality(e.target.value) }}>
          <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
        </select></label>
        <button type="button" onClick={toggleFullscreen}>{fullscreen ? 'Exit Fullscreen' : expanded ? 'Exit Expanded View' : 'Fullscreen'}</button>
      </div>
      <div className="terrain-stage">
        <div className="terrain-canvas" ref={host} />
        <div className="terrain-orientation" title="Local model axes; not geographic north"><span aria-hidden="true">↑</span>Local −Z</div>
        {status === 'idle' && <div className="terrain-overlay"><h3>Explore the surface</h3><p>Navigate the original voxel terrain in 3D.</p><button type="button" onClick={start}>Load 3D terrain</button><small>Approximately 52 MiB · loads progressively</small></div>}
        {status === 'loading' && <div className="terrain-loading" role="status">
          <span>{percent === null ? 'Preparing terrain…' : percent < 100 ? `Downloading terrain · ${percent}%` : 'Preparing final sectors…'}</span>
          <progress aria-label="Terrain download" max="100" {...(percent === null ? {} : { value: percent })} />
          {progress && <small>{progress.complete} / {progress.count} sectors ready · partial terrain}</small>
        </div>}
        {status === 'error' && <div className="terrain-overlay" role="alert"><h3>Terrain unavailable</h3><p>{error}</p><p>Any visible sectors are incomplete.</p><button type="button" onClick={start}>Retry terrain</button></div>}
        {active && <div className="terrain-camera-buttons" role="group" aria-label="Accessible terrain navigation">
          <button aria-label="Zoom in terrain" onClick={() => engine.current?.zoom(0.8)}>+</button>
          <button aria-label="Zoom out terrain" onClick={() => engine.current?.zoom(1.25)}>−</button>
          <button aria-label="Pan left" onClick={() => engine.current?.pan(60, 0)}>←</button>
          <button aria-label="Pan right" onClick={() => engine.current?.pan(-60, 0)}>→</button>
          <button aria-label="Pan forward" onClick={() => engine.current?.pan(0, -60)}>↑</button>
          <button aria-label="Pan backward" onClick={() => engine.current?.pan(0, 60)}>↓</button>
          <button aria-label="Rotate left" onClick={() => engine.current?.orbit(-0.2, 0)}>↶</button>
          <button aria-label="Rotate right" onClick={() => engine.current?.orbit(0.2, 0)}>↷</button>
          <button aria-label="Tilt up" onClick={() => engine.current?.orbit(0, -0.1)}>Tilt +</button>
          <button aria-label="Tilt down" onClick={() => engine.current?.orbit(0, 0.1)}>Tilt −</button>
        </div>}
      </div>

      {showInspectionPanel && inspectionPosition && (
        <ScientificInspectionPanel
          position={inspectionPosition}
          variables={inspectionVariables}
          terrainMetadata={terrainMetadata}
          onClose={() => setShowInspectionPanel(false)}
          onConvertToMarker={() => {
            // Convert the inspected point to a marker
            onPlaceMarker?.(inspectionPosition)
            setShowInspectionPanel(false)
          }}
          onUseAsOrigin={() => {
            // Use as route origin - implement route planning
            setShowInspectionPanel(false)
          }}
          onUseAsDestination={() => {
            // Use as route destination - implement route planning
            setShowInspectionPanel(false)
          }}
          onUseAsWaypoint={() => {
            // Use as waypoint - implement route planning
            setShowInspectionPanel(false)
          }}
        />
      )}

      <TerrainPlanningControls planning={planning} enabled={status === 'ready'} focus={position => engine.current?.focus(position)} />
      <div className="terrain-caption">
        <p>Left drag: pan · Right drag: orbit · Wheel: zoom<br />Touch: drag to pan · Pinch to zoom · Twist to rotate · Two-finger vertical drag to tilt</p>
        <p>Local orientation only. Geographic reference and distance units are not verified. Original vertical scale retained.</p>
        {status === 'ready' && <span role="status">Terrain ready · 44 sectors</span>}
        {notice && <p role="status">{notice}</p>}
      </div>
      {stats && <details className="terrain-diagnostics"><summary>Rendering diagnostics</summary><output>
        {JSON.stringify(stats)}
      </output></details>}
    </div>
  )
})
export default MarsTerrainViewer