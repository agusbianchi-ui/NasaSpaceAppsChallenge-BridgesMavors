import { Route } from 'lucide-react'
import { surfaceVisualization } from '../../services/missionData.js'
import Panel from '../Panel.jsx'

export default function SurfaceExplorationPanel() {
  return (
    <Panel
      title="SURFACE EXPLORATION"
      eyebrow="Terrain visualization"
      icon={Route}
      action={<span className="panel__tag">Simulated</span>}
      className="surface-exploration-panel"
    >
      <figure className="surface-exploration">
        <div className="surface-exploration__media">
          <img
            className="surface-exploration__image"
            src="/assets/mars-surface-route.gif"
            alt={surfaceVisualization.alt}
          />
          <div
            className="surface-exploration__shade"
            aria-hidden="true"
          />
          <div className="surface-exploration__top">
            <div>
              <p className="surface-exploration__title">
                {surfaceVisualization.title}
              </p>
              <p className="surface-exploration__subtitle">
                {surfaceVisualization.subtitle}
              </p>
            </div>
            <span className="surface-exploration__indicator">
              <span
                className="surface-exploration__indicator-dot"
                aria-hidden="true"
              />
              {surfaceVisualization.indicator}
            </span>
          </div>
          <figcaption className="surface-exploration__caption">
            <p>{surfaceVisualization.description}</p>
            <span className="surface-exploration__note">
              {surfaceVisualization.note}
            </span>
          </figcaption>
        </div>
      </figure>
    </Panel>
  )
}
