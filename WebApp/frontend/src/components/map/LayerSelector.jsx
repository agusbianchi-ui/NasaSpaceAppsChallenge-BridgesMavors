import { Layers } from 'lucide-react'

function resolutionLabel(layer) {
  if (layer.resolution == null) {
    return 'Resolution not published'
  }
  return `${layer.resolution} ${layer.resolution_unit ?? ''}`.trim()
}

export default function LayerSelector({
  layers,
  selectedId,
  onSelect,
  disabled = false,
}) {
  return (
    <div className="layer-selector" role="group" aria-label="NASA map layer">
      <div className="layer-selector__heading">
        <Layers size={14} aria-hidden="true" />
        <span>Orbital layer</span>
      </div>
      <div className="layer-selector__options">
        {layers.length === 0 && (
          <p className="layer-selector__empty">
            No visualizable NASA layers are registered.
          </p>
        )}
        {layers.map((layer) => {
          const active = layer.id === selectedId
          return (
            <button
              key={layer.id}
              type="button"
              className={`layer-option${active ? ' is-active' : ''}`}
              aria-pressed={active}
              disabled={disabled}
              onClick={() => onSelect(layer.id)}
            >
              <span className="layer-option__instrument">
                {layer.instrument}
              </span>
              <span className="layer-option__name">{layer.name}</span>
              <span className="layer-option__meta">
                {resolutionLabel(layer)} · {layer.mission}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
