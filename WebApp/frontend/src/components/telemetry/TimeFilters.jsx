function TimeFilters({ onSelect, selectedPeriod }) {
  const periods = [
    { label: 'Last 6h', value: '6h' },
    { label: 'Last 12h', value: '12h' },
    { label: 'Last 24h', value: '24h' },
    { label: 'Last 7d', value: '7d' },
    { label: 'Last 30d', value: '30d' },
  ]

  return (
    <div className="time-filters">
      {periods.map((period) => (
        <button
          key={period.value}
          className={`time-filter-btn ${period.value === selectedPeriod ? 'active' : ''}`}
          onClick={() => onSelect(period.value)}
        >
          {period.label}
        </button>
      ))}
    </div>
  )
}

export default TimeFilters