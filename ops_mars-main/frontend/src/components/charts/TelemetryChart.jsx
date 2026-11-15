import { Line } from 'react-chartjs-2'
import { telemetrySeries } from '../../services/missionData.js'
import { CHART_COLORS } from './chartSetup.js'

const data = {
  labels: telemetrySeries.labels,
  datasets: [
    {
      label: telemetrySeries.label,
      data: telemetrySeries.values,
      borderColor: CHART_COLORS.accent,
      backgroundColor: CHART_COLORS.accentSoft,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHoverBackgroundColor: CHART_COLORS.accent,
      pointHoverBorderColor: CHART_COLORS.textStrong,
      tension: 0.4,
      fill: true,
    },
  ],
}

const options = {
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
      backgroundColor: CHART_COLORS.tooltipBackground,
      borderColor: CHART_COLORS.tooltipBorder,
      borderWidth: 1,
      titleColor: CHART_COLORS.textStrong,
      bodyColor: CHART_COLORS.text,
      padding: 10,
      displayColors: false,
      callbacks: {
        label: (context) => `${context.parsed.y} ${telemetrySeries.unit}`,
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
        color: CHART_COLORS.text,
        maxRotation: 0,
      },
    },
    y: {
      grid: {
        color: CHART_COLORS.grid,
      },
      border: {
        display: false,
      },
      ticks: {
        color: CHART_COLORS.text,
        callback: (value) => `${value}°`,
      },
    },
  },
}

export default function TelemetryChart() {
  return (
    <div className="chart-frame">
      <Line data={data} options={options} />
    </div>
  )
}
