import { ShieldAlert } from 'lucide-react'
import { SIMULATION_NOTICE } from '../services/missionData.js'

export default function SimulationNotice({ compact = false }) {
  return (
    <div
      className={`simulation-notice${compact ? ' simulation-notice--compact' : ''}`}
      role="note"
    >
      <ShieldAlert size={16} aria-hidden="true" />
      <p>
        <span>Simulation environment.</span> {SIMULATION_NOTICE}
      </p>
    </div>
  )
}
