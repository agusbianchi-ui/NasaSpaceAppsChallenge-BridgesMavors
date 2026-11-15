import { useState } from 'react'
import { Activity, Map, Target, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import TimeFilters from '../components/telemetry/TimeFilters.jsx'
import MissionStatus from '../components/dashboard/MissionStatus.jsx'
import EnvironmentalTelemetry from '../components/dashboard/EnvironmentalTelemetry.jsx'
import RoverTelemetry from '../components/dashboard/RoverTelemetry.jsx'
import ScientificTargetsPanel from '../components/dashboard/ScientificTargetsPanel.jsx'
import StatCard from '../components/dashboard/StatCard.jsx'
import TelemetryMetricsSelector from '../components/telemetry/TelemetryMetricsSelector.jsx'
import SimulationNotice from '../components/SimulationNotice.jsx'

import { useMarsClock } from '../hooks/useMarsClock'

const OVERVIEW_ICONS = {
  status: Activity,
  area: Map,
  targets: Target,
  risk: TrendingUp,
  progress: TrendingUp,
}

function MissionClock({ landingDate }) {
  const { sol, lmst, terrestrialEquivalent, landingDate: ld } = useMarsClock(landingDate)

  const formatLMST = (hours) => {
    const h = Math.floor(hours)
    const m = Math.floor((hours - h) * 60)
    return `${h.toString().padStart(2, '0')}:${m
      .toString()
      .padStart(2, '0')}`
  }

  return (
    <div className="mission-clock">
      <div className="clock-row">
        <span className="clock-label">Sol</span>
        <strong className="clock-value">{sol}</strong>
        <span className="clock-meta">· Landing: {ld.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        })}</span>
      </div>
      <div className="clock-row">
        <span className="clock-label">LMST</span>
        <strong className="clock-value">{formatLMST(lmst)}</strong>
        <span className="clock-meta">Mean Solar Time · Jezero Crater</span>
      </div>
      <div className="clock-row">
        <span className="clock-label">Earth date</span>
        <strong className="clock-value">{terrestrialEquivalent.toLocaleDateString(
          'en-US',
        )}</strong>
        <span className="clock-meta">· {terrestrialEquivalent.toLocaleTimeString(
          'en-US',
        )}</span>
      </div>
    </div>
  )
}

export default function MissionOverview() {
  const landingDate = new Date('2021-02-18')
  const { sol, mtc } = useMarsClock(landingDate)
  const [visibleMetrics, setVisibleMetrics] = useState(['temperature', 'battery'])

  const [selectedPeriod, setSelectedPeriod] = useState('24h')

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

      <TimeFilters
        onSelect={(period) => setSelectedPeriod(period)}
        selectedPeriod={selectedPeriod}
      />

      <SimulationNotice />

      <MissionClock landingDate={landingDate} />

      <section className="stat-grid" aria-label="Mission summary metrics">
        {['status', 'area', 'targets', 'risk', 'progress'].map((metric) => (
          <StatCard
            key={metric}
            icon={OVERVIEW_ICONS[metric]}
            label={metric}
            value={metric === 'status' ? 'Online' : metric === 'area' ? 'Jezero Crater' : metric === 'targets' ? '8' : metric === 'risk' ? 'Moderate' : '42%'}
            meta={metric === 'progress' ? 'Planning phase · simulated' : 'Simulated operations profile'}
            tone={metric === 'risk' ? 'warning' : 'accent'}
          />
        ))}

        <StatCard
          id="sol"
          icon={Activity}
          label="Current Sol"
          value={sol}
          meta={mtc > 0 ? `LMST ${mtc.toFixed(1)}h` : 'Mars time'}
          tone="accent"
        />
      </section>

      <MissionStatus />

      <TelemetryMetricsSelector
        visibleMetrics={visibleMetrics}
        onToggleMetric={(metric) => setVisibleMetrics(
          visibleMetrics.includes(metric)
            ? visibleMetrics.filter((m) => m !== metric)
            : [...visibleMetrics, metric]
        )}
      />

      <EnvironmentalTelemetry visibleMetrics={visibleMetrics} />

      <RoverTelemetry visibleMetrics={visibleMetrics} />

      <div className="dashboard-grid dashboard-grid--secondary">
        <ScientificTargetsPanel
          limit={4}
          action={
            <Link className="text-link" to="/targets">
              View all targets
            </Link>
          }
        />
      </div>
    </div>
  )
}