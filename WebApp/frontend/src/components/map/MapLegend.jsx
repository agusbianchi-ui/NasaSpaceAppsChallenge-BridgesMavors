import { Ruler } from 'lucide-react'
import { MARS_RADIUS_METERS } from '../../services/marsGeo.js'

function formatDistance(meters) {
  if (!Number.isFinite(meters) || meters <= 0) {
    return 'n/a'
  }
  if (meters >= 1000) {
    const km = meters / 1000
    return `${km >= 10 ? km.toFixed(0) : km.toFixed(1)} km`
  }
  if (meters >= 1) {
    return `${meters >= 10 ? meters.toFixed(0) : meters.toFixed(1)} m`
  }
  return `${(meters * 100).toFixed(0)} cm`
}

function formatResolution(metersPerPixel) {
  if (!Number.isFinite(metersPerPixel) || metersPerPixel <= 0) {
    return 'n/a'
  }
  return `${formatDistance(metersPerPixel)}/px`
}

export default function MapLegend({ layer, metersPerPixel, showRoute = false }) {
  return (
    <section className="map-card" aria-label="Map legend">
      <header className="map-card__header">
        <Ruler size={14} aria-hidden="true" />
        <h3>Map legend</h3>
      </header>

      <ul className="map-legend">
        <li>
          <span className="map-legend__swatch map-legend__swatch--imagery" />
          <span>{layer ? `${layer.instrument} basemap` : 'Orbital basemap'}</span>
        </li>
        <li>
          <span className="map-legend__swatch map-legend__swatch--frame" />
          <span>Published WMTS footprint</span>
        </li>
        <li>
          <span className="map-legend__swatch map-legend__swatch--nodata" />
          <span>Transparent / no data</span>
        </li>
        {showRoute && (
          <>
            <li>
              <span className="map-legend__swatch map-legend__swatch--route" />
              <span>Simulated route</span>
            </li>
            <li>
              <span className="map-legend__swatch map-legend__swatch--waypoint" />
              <span>Route waypoints</span>
            </li>
          </>
        )}
      </ul>

      <div className="map-scale">
        <div className="map-scale__bar" aria-hidden="true" />
        <p>
          100 px ≈ {formatDistance((metersPerPixel ?? 0) * 100)}
        </p>
        <p className="map-note">
          Current view scale: {formatResolution(metersPerPixel)}. Approximate,
          derived from the WMTS matrix resolution using a Mars radius of{' '}
          {MARS_RADIUS_METERS.toLocaleString('en-US')} m.
        </p>
      </div>
    </section>
  )
}
