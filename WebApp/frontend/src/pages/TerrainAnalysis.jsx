import MarsTerrainViewer from '../components/map/MarsTerrainViewer.jsx'
import {
  CheckCircle2,
  Mountain,
  Radar,
  Route,
  ShieldAlert,
} from 'lucide-react'
import Panel from '../components/Panel.jsx'
import SimulationNotice from '../components/SimulationNotice.jsx'
import StatCard from '../components/dashboard/StatCard.jsx'
import TerrainRiskChart from '../components/charts/TerrainRiskChart.jsx'
import { terrainMetrics, terrainRiskSeries } from '../services/missionData.js'

const TERRAIN_ICONS = {
  slope: Mountain,
  hazard: ShieldAlert,
  corridor: Route,
  rocks: Radar,
}

export default function TerrainAnalysis() {
  return (
    <div className="page">
      <h1>Terrain Analysis</h1>
      <p>Shared mission, points, scientific hazards and route comparison. The same terrain and assumptions are used in Mars Explorer.</p>
      <MarsTerrainViewer />
      <details><summary>Previous simulated demonstration / 2D reference</summary>
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">Surface assessment</p>
          <h1>Terrain Analysis</h1>
          <p className="page-heading__description">
            Synthetic terrain indicators for the Jezero Crater planning
            scenario. These values do not represent scientific measurements.
          </p>
        </div>
        <span className="page-heading__phase">MODEL · SIMULATED</span>
      </div>

      <SimulationNotice compact />

      <section className="stat-grid" aria-label="Simulated terrain metrics">
        {terrainMetrics.map((metric) => (
          <StatCard
            key={metric.id}
            icon={TERRAIN_ICONS[metric.id]}
            label={metric.label}
            value={metric.value}
            meta={metric.detail}
          />
        ))}
      </section>

      <div className="dashboard-grid dashboard-grid--primary">
        <Panel
          title="Hazard Profile"
          eyebrow="Simulated terrain model"
          icon={ShieldAlert}
          action={<span className="panel__tag">Simulated</span>}
        >
          <TerrainRiskChart />
          <p className="panel__note">{terrainRiskSeries.note}</p>
        </Panel>

        <Panel
          title="Analysis Pipeline"
          eyebrow="Planned capabilities"
          icon={Radar}
          action={<span className="panel__tag">Pending</span>}
        >
          <div className="coming-soon">
            <span className="coming-soon__icon">
              <Mountain size={24} aria-hidden="true" />
            </span>
            <h3>Terrain processing modules</h3>
            <p>
              Slope, rock-density, and traversability processing will be wired
              to real analysis services in a future stage. This page currently
              presents the visual structure with synthetic values.
            </p>
            <ul className="check-list">
              <li>
                <CheckCircle2 size={14} aria-hidden="true" />
                Surface hazard summary
              </li>
              <li>
                <CheckCircle2 size={14} aria-hidden="true" />
                Compact risk distribution chart
              </li>
              <li>
                <CheckCircle2 size={14} aria-hidden="true" />
                Reserved integration point for analysis services
              </li>
            </ul>
          </div>
        </Panel>
      </div>
      </details>
    </div>
  )
}
