import { Compass, MapPin } from 'lucide-react'
import { exploration } from '../../services/missionData.js'
import Panel from '../Panel.jsx'

export default function ExplorationPanel() {
  return (
    <Panel
      title="Exploration Area"
      eyebrow="Surface reference"
      icon={Compass}
      action={<span className="panel__tag">Simulated</span>}
    >
      <div className="exploration">
        <div
          className="mars-visual"
          role="img"
          aria-label="Illustrative representation of Mars with a marker for Jezero Crater"
        >
          <div className="mars-visual__globe">
            <span
              className="mars-visual__crater mars-visual__crater--1"
              aria-hidden="true"
            />
            <span
              className="mars-visual__crater mars-visual__crater--2"
              aria-hidden="true"
            />
            <span
              className="mars-visual__crater mars-visual__crater--3"
              aria-hidden="true"
            />
            {exploration.points.map((point) => (
              <span
                key={point.id}
                className="mars-visual__marker"
                style={{ left: `${point.x}%`, top: `${point.y}%` }}
                title={`${point.id} · ${point.label}`}
              >
                <span className="mars-visual__pulse" aria-hidden="true" />
              </span>
            ))}
            <span className="mars-visual__location">
              <MapPin size={12} aria-hidden="true" />
              Jezero
            </span>
          </div>
        </div>

        <div className="exploration__info">
          <div>
            <p className="exploration__area">{exploration.area}</p>
            <p className="exploration__region">{exploration.region}</p>
          </div>

          <dl className="coordinate-list">
            {exploration.coordinates.map((item) => (
              <div key={item.label}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>

          <dl className="point-summary">
            {exploration.pointSummary.map((item) => (
              <div key={item.label}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>

          <p className="panel__note">{exploration.note}</p>
        </div>
      </div>
    </Panel>
  )
}
