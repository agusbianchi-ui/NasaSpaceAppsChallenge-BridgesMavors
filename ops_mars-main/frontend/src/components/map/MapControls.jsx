import { Maximize2, Minus, Plus } from 'lucide-react'

export default function MapControls({ mapRef, disabled = false }) {
  return (
    <div className="map-controls" role="group" aria-label="Map controls">
      <button
        type="button"
        className="map-control"
        aria-label="Zoom in"
        title="Zoom in"
        onClick={() => mapRef.current?.zoomIn()}
        disabled={disabled}
      >
        <Plus size={16} aria-hidden="true" />
      </button>
      <button
        type="button"
        className="map-control"
        aria-label="Zoom out"
        title="Zoom out"
        onClick={() => mapRef.current?.zoomOut()}
        disabled={disabled}
      >
        <Minus size={16} aria-hidden="true" />
      </button>
      <button
        type="button"
        className="map-control"
        aria-label="Fit to published footprint"
        title="Fit to published footprint"
        onClick={() => mapRef.current?.fitToLayer()}
        disabled={disabled}
      >
        <Maximize2 size={16} aria-hidden="true" />
      </button>
    </div>
  )
}
