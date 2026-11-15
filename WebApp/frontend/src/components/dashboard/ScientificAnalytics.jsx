import { Line, Bar } from 'react-chartjs-2'
import { Activity } from 'lucide-react'
import { scientificAnalytics } from '../../services/missionData.js'
import { Panel } from '../Panel.jsx'

const elevationColor = '#67e8f9'
const terrainColor = '#a855f7'
const trendColor = '#10b981'
const measurementColors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#10b981', '#8b5cf6']

const chartOptions = {
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

const elevationDataset = {
  label: 'Elevation Profile',
  data: scientificAnalytics.elevationProfile.elevation,
  borderColor: elevationColor,
  backgroundColor: 'rgba(103, 232, 233, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const terrainDataset = {
  label: 'Terrain Analysis',
  data: scientificAnalytics.terrainAnalysis.values,
  backgroundColor: 'rgba(168, 85, 247, 0.1)',
  borderColor: terrainColor,
  borderWidth: 2,
}

const trendDataset = {
  label: 'Environmental Trends',
  data: [
    { label: 'Temperature', value: '-0.3°C' },
    { label: 'Pressure', value: '+12 Pa' },
    { label: 'Wind', value: '12.5 m/s avg' },
  ],
  backgroundColor: 'rgba(16, 185, 129, 0.1)',
  borderColor: trendColor,
  borderWidth: 2,
}

export default function ScientificAnalytics() {
  return (
    <Panel
      title="Scientific Analytics"
      eyebrow="Research data overview"
      icon={Activity}
      action={<span className="panel__tag">Live</span>}
    >
      <div className="scientific-analytics-grid">
        <div className="scientific-card">
          <div className="chart-card__header">
            <span>Elevation Profile</span>
            <span className="mono small">−2,610 m to −2,590 m</span>
          </div>
          <div className="chart-frame">
            <Line
              data={{
                labels: scientificAnalytics.elevationProfile.labels,
                datasets: [elevationDataset],
              }}
              options={chartOptions}
            />
          </div>
        </div>

        <div className="scientific-card">
          <div className="chart-card__header">
            <span>Terrain Analysis</span>
            <span className="mono small">Hazard score breakdown</span>
          </div>
          <div className="chart-frame">
            <Bar
              data={{
                labels: scientificAnalytics.terrainAnalysis.labels,
                datasets: [terrainDataset],
              }}
              options={chartOptions}
            />
          </div>
        </div>

        <div className="scientific-card">
          <div className="chart-card__header">
            <span>Environmental Trends</span>
          </div>
          <div className="chart-frame" style={{ height: '120px' }}>
            <Bar
              data={{
                labels: ['Temperature', 'Pressure', 'Wind'],
                datasets: [trendDataset],
              }}
              options={chartOptions}
            />
          </div>
        </div>

        <div className="scientific-card">
          <div className="chart-card__header">
            <span>Recent Measurements</span>
          </div>
          <div className="measurements-list">
            {scientificAnalytics.scientificMeasurements.map((m) => (
              <div
                key={m.id}
                className="measurement-item"
                style={{
                  borderLeft: `3px solid ${measurementColors[0]}`,

                  }}
                >
                <span className="mono measurement-variable"
                  style={{ color: measurementColors[0] }}
                >
                  {m.variable}: {m.value}
                </span>
                <span className="mono measurement-sol">
                  Sol {m.sol}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  )
}