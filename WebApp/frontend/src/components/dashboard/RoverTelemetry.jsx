import { Line } from 'react-chartjs-2'
import { Activity } from 'lucide-react'
import { Panel } from '../Panel.jsx'

const batteryColor = '#10b981'
const tempColor = '#ef4444'
const commColor = '#3b82f6'

const roverChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: '#111824',
      borderColor: 'rgba(130, 144, 163, 0.24)',
      borderWidth: 1,
      titleColor: '#e8edf4',
      bodyColor: '#8290a3',
      padding: 6,
      displayColors: false,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
      border: {
        display: false,
      },
      ticks: {
        color: '#8290a3',
        maxRotation: 0,
      },
    },
    y: {
      grid: {
        color: 'rgba(130, 144, 163, 0.12)',
      },
      border: {
        display: false,
      },
      ticks: {
        color: '#8290a3',
      },
    },
  },
}

const batteryDataset = {
  label: 'Battery Level',
  data: [87, 82, 85, 87, 84, 88],
  borderColor: batteryColor,
  backgroundColor: 'rgba(16, 185, 129, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const roverTempDataset = {
  label: 'Rover Temperature',
  data: [-40, -38, -35, -33, -36, -34],
  borderColor: tempColor,
  backgroundColor: 'rgba(239, 68, 68, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const commLatencyDataset = {
  label: 'Communication Latency',
  data: [10, 8, 12, 9, 7, 11],
  borderColor: commColor,
  backgroundColor: 'rgba(59, 130, 246, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

export default function RoverTelemetry({ visibleMetrics }) {
  const showBattery = visibleMetrics.includes('battery')
  const showRoverTemp = visibleMetrics.includes('roverTemp')
  const showCommLatency = visibleMetrics.includes('commLatency')

  return (
    <Panel
      title="Rover Telemetry"
      eyebrow="Vehicle systems monitoring"
      icon={Activity}
      action={<span className="panel__tag">Live</span>}
    >
      <div className="rover-telemetry-grid">
        {showBattery && (
          <div className="rover-telemetry-card">
            <div className="chart-card__header">
              <span>Battery Consumption</span>
              <span className="mono small">87% • −1.2% today</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                  datasets: [batteryDataset],
                }}
                options={roverChartOptions}
              />
            </div>
          </div>
        )}

        {showRoverTemp && (
          <div className="rover-telemetry-card">
            <div className="chart-card__header">
              <span>Rover Temperature</span>
              <span className="mono small">−35°C • Stable</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                  datasets: [roverTempDataset],
                }}
                options={roverChartOptions}
              />
            </div>
          </div>
        )}

        {showCommLatency && (
          <div className="rover-telemetry-card">
            <div className="chart-card__header">
              <span>Communication Latency</span>
              <span className="mono small">8.2 min • −0.5 recent</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                  datasets: [commLatencyDataset],
                }}
                options={roverChartOptions}
              />
            </div>
          </div>
        )}
      </div>
    </Panel>
  )
}