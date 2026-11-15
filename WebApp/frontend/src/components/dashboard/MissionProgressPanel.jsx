import { TrendingUp } from 'lucide-react'
import { missionProgress } from '../../services/missionData.js'
import Panel from '../Panel.jsx'
import MissionProgressChart from '../charts/MissionProgressChart.jsx'

export default function MissionProgressPanel() {
  return (
    <Panel
      title="Mission Progress"
      eyebrow="Planning phase"
      icon={TrendingUp}
      action={<span className="panel__tag">Simulated</span>}
    >
      <MissionProgressChart />

      <ul className="progress-phases">
        {missionProgress.phases.map((phase) => (
          <li key={phase.id}>
            <div className="progress-phase__top">
              <span>{phase.label}</span>
              <span>{phase.value}%</span>
            </div>
            <div
              className="progress-phase__track"
              role="progressbar"
              aria-label={`${phase.label} simulated progress`}
              aria-valuenow={phase.value}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <span
                className="progress-phase__fill"
                style={{ width: `${phase.value}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  )
}
