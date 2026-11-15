import SimulationNotice from '../components/SimulationNotice.jsx'
import ScientificTargetsPanel from '../components/dashboard/ScientificTargetsPanel.jsx'
import { scientificTargets, missionActivity } from '../services/missionData.js'
import MissionActivityPanel from '../components/dashboard/MissionActivityPanel.jsx'

const STATUS_ORDER = ['Analyzed', 'In review', 'Pending']

const statusCounts = STATUS_ORDER.map((status) => ({
  status,
  count: scientificTargets.filter((target) => target.status === status).length,
}))

// Map scientific target IDs to their objects for quick lookup
const targetMap = scientificTargets.reduce((map, target) => {
  map[target.id] = target
  return map
}, {})

// Enhance mission activity with scientific target relationships
const enhancedMissionActivity = missionActivity.map((event) => {
  const relatedTargets = []
  // Check if the event detail or title mentions a scientific target ID
  const targetIdMatch = event.detail.match(/JZ-\d{3}/) || event.title.match(/JZ-\d{3}/)
  if (targetIdMatch) {
    const target = targetMap[targetIdMatch[0]]
    if (target) {
      relatedTargets.push(target)
    }
  }
  return { ...event, relatedTargets }
})

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

      <MissionActivityPanel enhancedActivity={enhancedMissionActivity} targetMap={targetMap} />

      <ScientificTargetsPanel />
    </div>
  )
}