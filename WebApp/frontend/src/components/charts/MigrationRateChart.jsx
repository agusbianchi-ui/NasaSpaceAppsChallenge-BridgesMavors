import { Bar } from 'react-chartjs-2'
import { CHART_COLORS } from './chartSetup.js'

function chartData(pairs) {
  return {
    labels: pairs.map(
      (pair) => `${pair.reference_id} -> ${pair.moving_id}`,
    ),
    datasets: [
      {
        label: 'Observed migration rate',
        data: pairs.map(
          (pair) => pair.observed_migration.rate_m_per_earth_year,
        ),
        backgroundColor: CHART_COLORS.accentSoft,
        borderColor: CHART_COLORS.accent,
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.58,
      },
    ],
  }
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
        label: (context) =>
          `Observed rate: ${context.parsed.x.toFixed(3)} m / Earth year`,
      },
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: {
        color: CHART_COLORS.grid,
      },
      border: {
        display: false,
      },
      ticks: {
        color: CHART_COLORS.text,
        callback: (value) => `${value} m`,
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

export default function MigrationRateChart({ pairs }) {
  const validPairs = pairs.filter(
    (pair) =>
      pair.observed_migration?.valid &&
      Number.isFinite(pair.observed_migration.rate_m_per_earth_year),
  )

  if (validPairs.length === 0) {
    return null
  }

  return (
    <section className="chart-block" aria-label="Observed migration rates">
      <div className="chart-block__heading">
        <span>Observed annualized migration rate</span>
        <span>m / Earth year</span>
      </div>
      <div className="chart-frame chart-frame--aeolian">
        <Bar data={chartData(validPairs)} options={options} />
      </div>
      <p className="panel__note">
        Linear annualization over each observation interval, not a forecast or
        a sediment flux measurement.
      </p>
    </section>
  )
}
