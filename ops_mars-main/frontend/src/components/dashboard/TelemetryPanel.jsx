import { Activity, Gauge, Mountain, Thermometer, Wind } from 'lucide-react'
import { telemetryMetrics } from '../../services/missionData.js'
import Panel from '../Panel.jsx'
import TelemetryChart from '../charts/TelemetryChart.jsx'

const METRIC_ICONS = {
  temperature: Thermometer,
  pressure: Gauge,
  wind: Wind,
  elevation: Mountain,
}

export default function TelemetryPanel() {
  return (
    <Panel
      title="Telemetry"
      eyebrow="Simulated surface feed"
      icon={Activity}
      action={<span className="panel__tag">Simulated</span>}
    >
      <div className="telemetry-grid">
        {telemetryMetrics.map((metric) => {
          const Icon = METRIC_ICONS[metric.id]

          return (
            <div className="telemetry-metric" key={metric.id}>
              <div className="telemetry-metric__header">
                <span>{metric.label}</span>
                {Icon && <Icon size={15} aria-hidden="true" />}
              </div>
              <p className="telemetry-metric__value">
                {metric.value}
                <span>{metric.unit}</span>
              </p>
              <p className="telemetry-metric__trend">{metric.trend}</p>
            </div>
          )
        })}
      </div>

      <div className="chart-block">
        <div className="chart-block__heading">
          <span>Temperature trend</span>
          <span className="mono">SIM · 24H</span>
        </div>
        <TelemetryChart />
      </div>
    </Panel>
  )
}
