import SimulationNotice from '../components/SimulationNotice.jsx'
import ScientificTargetsPanel from '../components/dashboard/ScientificTargetsPanel.jsx'
import { scientificTargets } from '../services/missionData.js'

const STATUS_ORDER = ['Analyzed', 'In review', 'Pending']

const statusCounts = STATUS_ORDER.map((status) => ({
  status,
  count: scientificTargets.filter((target) => target.status === status).length,
}))

export default function ScientificTargets() {
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">Target catalogue</p>
          <h1>Scientific Targets</h1>
          <p className="page-heading__description">
            Simulated catalogue of points of interest in the Jezero Crater
            planning area, including analysis status and confidence labels.
          </p>
        </div>
        <span className="page-heading__phase">
          {scientificTargets.length} TARGETS
        </span>
      </div>

      <SimulationNotice compact />

      <div className="metric-grid">
        {statusCounts.map((item) => (
          <div className="metric-card" key={item.status}>
            <span className="metric-card__label">{item.status}</span>
            <strong className="metric-card__value">{item.count}</strong>
            <span className="metric-card__detail">
              Simulated target count
            </span>
          </div>
        ))}
      </div>

      <ScientificTargetsPanel />
    </div>
  )
}
