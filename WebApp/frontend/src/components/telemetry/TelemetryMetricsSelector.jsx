function TelemetryMetricsSelector({ visibleMetrics, onToggleMetric }) {
  const allMetrics = [
    { label: 'Temperature', value: 'temperature', default: true },
    { label: 'Atmospheric Pressure', value: 'pressure' },
    { label: 'Wind Speed', value: 'wind' },
    { label: 'Battery Level', value: 'battery', default: true },
    { label: 'Rover Temperature', value: 'roverTemp' },
    { label: 'Communication Latency', value: 'commLatency' },
  ]

  return (
    <div className="telemetry-metrics-selector">
      <span className="selector-label">Telemetry Metrics</span>
      <div className="selector-options">
        {allMetrics.map((metric) => (
          <label
            key={metric.value}
            className={`selector-item ${visibleMetrics.includes(metric.value) ? 'active' : ''}`}
          >
            <input
              type="checkbox"
              checked={visibleMetrics.includes(metric.value)}
              onChange={() => onToggleMetric(metric.value)}
              className="selector-checkbox"
            />
            <span>{metric.label}</span>
          </label>
        ))}
      </div>
    </div>
  )
}

TelemetryMetricsSelector.defaultProps = {
  visibleMetrics: ['temperature', 'battery'],
}

export default TelemetryMetricsSelector