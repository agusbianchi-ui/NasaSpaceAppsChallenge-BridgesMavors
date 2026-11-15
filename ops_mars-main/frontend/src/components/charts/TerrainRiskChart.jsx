import { Bar } from 'react-chartjs-2'
import { terrainRiskSeries } from '../../services/missionData.js'
import { CHART_COLORS } from './chartSetup.js'

const data = {
  labels: terrainRiskSeries.labels,
  datasets: [
    {
      label: terrainRiskSeries.label,
      data: terrainRiskSeries.values,
      backgroundColor: CHART_COLORS.accentSoft,
      borderColor: CHART_COLORS.accent,
      borderWidth: 1,
      borderRadius: 4,
      barPercentage: 0.62,
    },
  ],
}

const options = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
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
      displayColors: false,
      callbacks: {
        label: (context) => `Hazard score: ${context.parsed.x} / 100`,
      },
    },
  },
  scales: {
    x: {
      min: 0,
      max: 100,
      grid: {
        color: CHART_COLORS.grid,
      },
      border: {
        display: false,
      },
      ticks: {
        color: CHART_COLORS.text,
      },
    },
    y: {
      grid: {
        display: false,
      },
      border: {
        display: false,
      },
      ticks: {
        color: CHART_COLORS.text,
      },
    },
  },
}

export default function TerrainRiskChart() {
  return (
    <div className="chart-frame chart-frame--terrain">
      <Bar data={data} options={options} />
    </div>
  )
}
