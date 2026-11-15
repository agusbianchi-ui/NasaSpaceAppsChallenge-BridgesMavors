export default function ScientificInsightCard({ insight }) {
  return (
    <div className="scientific-insight-card" style={{ borderLeftColor: insight.color }}>
      <div className="card-header">
        <inset className="card-icon" style={{ color: insight.color }}>
          {insight.icon}
        </inset>
        <span className="card-title">{insight.title}</span>
      </div>
      <p className="card-content">{insight.content}</p>
    </div>
  )
}