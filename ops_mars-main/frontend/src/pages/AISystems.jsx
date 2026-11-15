import { BrainCircuit, Cpu } from 'lucide-react'
import SimulationNotice from '../components/SimulationNotice.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { aiSystems } from '../services/missionData.js'

const STATUS_TONES = {
  Prototype: 'accent',
  Design: 'warning',
  Concept: 'muted',
}

export default function AISystems() {
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">Autonomy roadmap</p>
          <h1>AI Systems</h1>
          <p className="page-heading__description">
            Planned analysis and planning modules for MARS OPS. No machine
            learning model is implemented or connected in this version.
          </p>
        </div>
        <span className="page-heading__phase">AI · NOT CONNECTED</span>
      </div>

      <SimulationNotice compact />

      <div className="page-grid">
        {aiSystems.map((system) => (
          <article className="ai-card" key={system.id}>
            <div className="ai-card__header">
              <span className="ai-card__icon">
                <Cpu size={18} aria-hidden="true" />
              </span>
              <StatusPill tone={STATUS_TONES[system.status]}>
                {system.status}
              </StatusPill>
            </div>
            <p className="ai-card__id">{system.id}</p>
            <h3>{system.name}</h3>
            <p>{system.description}</p>
            <div className="ai-card__footer">
              <span>{system.mode}</span>
              <span>SIMULATED</span>
            </div>
          </article>
        ))}
      </div>

      <div className="coming-soon">
        <span className="coming-soon__icon">
          <BrainCircuit size={22} aria-hidden="true" />
        </span>
        <h3>Model integration pending</h3>
        <p>
          These modules describe the intended autonomy layer. A later stage will
          connect models, datasets, and evaluation workflows from the
          independent <code>mars_ml/</code> workspace.
        </p>
      </div>
    </div>
  )
}
