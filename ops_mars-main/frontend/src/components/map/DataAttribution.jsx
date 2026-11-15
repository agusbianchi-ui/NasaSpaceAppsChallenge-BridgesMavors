import { ExternalLink, Satellite } from 'lucide-react'

const SOURCES = [
  {
    label: 'NASA Mars Trek',
    href: 'https://trek.nasa.gov/mars/',
    detail: 'WMTS tile service and orbital mosaics',
  },
  {
    label: 'USGS Astrogeology',
    href: 'https://astrogeology.usgs.gov/',
    detail: 'Planetary cartography and mosaic production',
  },
  {
    label: 'NASA PDS',
    href: 'https://pds.nasa.gov/',
    detail: 'Archived mission data and product metadata',
  },
]

export default function DataAttribution({ layer }) {
  return (
    <section className="map-card" aria-label="Data attribution">
      <header className="map-card__header">
        <Satellite size={14} aria-hidden="true" />
        <h3>Data attribution</h3>
      </header>

      <p className="map-note">
        Orbital imagery is streamed directly from NASA Mars Trek. No tiles are
        cached or modified by this dashboard. Attribution and usage terms
        remain with the original providers.
      </p>

      {layer?.attribution && (
        <p className="map-attribution">{layer.attribution}</p>
      )}

      <ul className="map-sources">
        {SOURCES.map((source) => (
          <li key={source.label}>
            <a
              className="map-link"
              href={source.href}
              target="_blank"
              rel="noreferrer"
            >
              {source.label}
              <ExternalLink size={12} aria-hidden="true" />
            </a>
            <span>{source.detail}</span>
          </li>
        ))}
      </ul>

      <p className="map-note">
        Mission telemetry, progress, risks, and events shown elsewhere in this
        dashboard are simulated. Only the orbital map layers and the metadata
        fetched from the backend describe real NASA products.
      </p>
    </section>
  )
}
