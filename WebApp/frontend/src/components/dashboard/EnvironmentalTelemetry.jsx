import { Line } from 'react-chartjs-2'
import { Panel } from '../Panel.jsx'
import { Loader2 } from 'lucide-react'
import { telemetrySeries } from '../../services/missionData.js'

const COLOR_TEMPERATURE = '#ff6b6b'
const COLOR_PRESSURE = '#4ecdc4'
const COLOR_WIND = '#ffe66d'
const COLOR_HUMIDITY = '#8b5cf6'

const environmentalChartOptions = {
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
      padding: 8,
      displayColors: false,
      callbacks: {
        label: (context) => {
          const label = context.dataset.label || ''
          const value = context.parsed.y
          return `${label}: ${value} ${telemetrySeries.unit}`
        },
      },
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

const temperatureDataset = {
  label: 'Temperature',
  data: [],
  borderColor: COLOR_TEMPERATURE,
  backgroundColor: 'rgba(255, 107, 107, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const pressureDataset = {
  label: 'Atmospheric Pressure',
  data: [],
  borderColor: COLOR_PRESSURE,
  backgroundColor: 'rgba(78, 205, 196, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const windDataset = {
  label: 'Wind Speed',
  data: [],
  borderColor: COLOR_WIND,
  backgroundColor: 'rgba(255, 230, 109, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const humidityDataset = {
  label: 'Humidity',
  data: [],
  borderColor: COLOR_HUMIDITY,
  backgroundColor: 'rgba(139, 92, 246, 0.1)',
  borderWidth: 2,
  pointRadius: 4,
  pointHoverRadius: 6,
  tension: 0.4,
  fill: true,
}

const defaultVisible = ['temperature']

export default function EnvironmentalTelemetry({ visibleMetrics = defaultVisible }) {
  const showTemperature = visibleMetrics.includes('temperature')
  const showPressure = visibleMetrics.includes('pressure')
  const showWind = visibleMetrics.includes('wind')
  const showHumidity = visibleMetrics.includes('humidity')

  return (
    <Panel
      title="Environmental Telemetry"
      eyebrow="Primary monitoring"
      icon={Loader2}
      action={<span className="panel__tag">Live</span>}
    >
      <div className="environmental-charts-wrapper">
        {showTemperature && (
          <div className="environmental-chart-card">
            <div className="chart-card__header">
              <span>Temperature Evolution</span>
              <span className="mono small">Min: −68°C Max: −60°C</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
                  datasets: [temperatureDataset],
                }}
                options={environmentalChartOptions}
              />
            </div>
            <div className="chart-card__legend">
              <span
                style={{
                  color: COLOR_TEMPERATURE,
                  background: 'rgba(255, 107, 107, 0.1)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.64rem',
                }}
              />
              <span>Temp</span>
            </div>
          </div>
        )}

        {showPressure && (
          <div className="environmental-chart-card">
            <div className="chart-card__header">
              <span>Atmospheric Pressure</span>
              <span className="mono small">Min: 680 Pa Max: 710 Pa</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
                  datasets: [pressureDataset],
                }}
                options={environmentalChartOptions}
              />
            </div>
            <div className="chart-card__legend">
              <span
                style={{
                  color: COLOR_PRESSURE,
                  background: 'rgba(78, 205, 196, 0.1)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.64rem',
                }}
              />
              <span>Pressure</span>
            </div>
          </div>
        )}

        {showWind && (
          <div className="environmental-chart-card">
            <div className="chart-card__header">
              <span>Wind Speed</span>
              <span className="mono small">Min: 9 m/s Max: 16 m/s</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
                  datasets: [windDataset],
                }}
                options={environmentalChartOptions}
              />
            </div>
            <div className="chart-card__legend">
              <span
                style={{
                  color: COLOR_WIND,
                  background: 'rgba(255, 230, 109, 0.1)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.64rem',
                }}
              />
              <span>Wind</span>
            </div>
          </div>
        )}

        {showHumidity && (
          <div className="environmental-chart-card">
            <div className="chart-card__header">
              <span>Humidity</span>
              <span className="mono small">Min: 72% Max: 85%</span>
            </div>
            <div className="chart-frame">
              <Line
                data={{
                  labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
                  datasets: [humidityDataset],
                }}
                options={environmentalChartOptions}
              />
            </div>
            <div className="chart-card__legend">
              <span
                style={{
                  color: COLOR_HUMIDITY,
                  background: 'rgba(139, 92, 246, 0.1)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.64rem',
                }}
              />
              <span>Humidity</span>
            </div>
          </div>
        )}
      </div>
    </Panel>
  )
}