import { Activity, AlertTriangle, Map, Target, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import SimulationNotice from '../components/SimulationNotice.jsx'
import ExplorationPanel from '../components/dashboard/ExplorationPanel.jsx'
import MissionActivityPanel from '../components/dashboard/MissionActivityPanel.jsx'
import MissionProgressPanel from '../components/dashboard/MissionProgressPanel.jsx'
import ScientificTargetsPanel from '../components/dashboard/ScientificTargetsPanel.jsx'
import StatCard from '../components/dashboard/StatCard.jsx'
import SurfaceExplorationPanel from '../components/dashboard/SurfaceExplorationPanel.jsx'
import TelemetryPanel from '../components/dashboard/TelemetryPanel.jsx'
import { overviewMetrics } from '../services/missionData.js'

const OVERVIEW_ICONS = {
  status: Activity,
  area: Map,
  targets: Target,
  risk: AlertTriangle,
  progress: TrendingUp,
}

export default function MissionOverview() {
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">
            Mission control · Simulated environment
          </p>
          <h1>Mission Overview</h1>
          <p className="page-heading__description">
            Operational summary for the Jezero Crater exploration planning
            scenario. Every metric and event on this screen is generated for
            interface demonstration.
          </p>
        </div>
        <span className="page-heading__phase">PHASE · PRE-MISSION</span>
      </div>

      <SimulationNotice />

      <section className="stat-grid" aria-label="Mission summary metrics">
        {overviewMetrics.map((metric) => (
          <StatCard
            key={metric.id}
            icon={OVERVIEW_ICONS[metric.id]}
            label={metric.label}
            value={metric.value}
            meta={metric.meta}
            tone={metric.tone}
          />
        ))}
      </section>

      <SurfaceExplorationPanel />

      <div className="dashboard-grid dashboard-grid--primary">
        <ExplorationPanel />
        <MissionProgressPanel />
      </div>

      <TelemetryPanel />

      <div className="dashboard-grid dashboard-grid--secondary">
        <ScientificTargetsPanel
          limit={4}
          action={
            <Link className="text-link" to="/targets">
              View all targets
            </Link>
          }
        />
        <MissionActivityPanel />
      </div>
    </div>
  )
}
