import { Doughnut } from 'react-chartjs-2'
import { missionProgress } from '../../services/missionData.js'
import { CHART_COLORS } from './chartSetup.js'

const data = {
  labels: ['Simulated progress', 'Remaining'],
  datasets: [
    {
      data: [missionProgress.value, 100 - missionProgress.value],
      backgroundColor: [CHART_COLORS.accent, CHART_COLORS.track],
      borderWidth: 0,
      hoverOffset: 3,
    },
  ],
}

const options = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '76%',
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
        label: (context) => `${context.parsed}% (simulated)`,
      },
    },
  },
}

export default function MissionProgressChart() {
  return (
    <div className="progress-chart">
      <Doughnut data={data} options={options} />
      <div className="progress-chart__center" aria-hidden="true">
        <strong>{missionProgress.value}%</strong>
        <span>SIMULATED</span>
      </div>
    </div>
  )
}
