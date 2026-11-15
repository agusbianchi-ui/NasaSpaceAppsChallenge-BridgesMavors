import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js'

Chart.register(
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
)

Chart.defaults.color = '#8290A3'
Chart.defaults.font.family =
  "'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif"
Chart.defaults.font.size = 10

export const CHART_COLORS = {
  accent: '#E87532',
  accentSoft: 'rgba(232, 117, 50, 0.16)',
  secondary: '#D94B35',
  secondarySoft: 'rgba(217, 75, 53, 0.16)',
  text: '#8290A3',
  textStrong: '#E8EDF4',
  grid: 'rgba(130, 144, 163, 0.12)',
  track: 'rgba(130, 144, 163, 0.14)',
  tooltipBackground: '#111824',
  tooltipBorder: 'rgba(130, 144, 163, 0.24)',
}
