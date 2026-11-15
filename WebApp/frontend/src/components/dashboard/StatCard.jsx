export default function StatCard({
  icon: Icon,
  label,
  value,
  meta,
  tone = 'default',
}) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__top">
        <span className="stat-card__label">{label}</span>
        {Icon && (
          <Icon className="stat-card__icon" size={18} aria-hidden="true" />
        )}
      </div>
      <strong className="stat-card__value">{value}</strong>
      <span className="stat-card__meta">{meta}</span>
    </article>
  )
}
