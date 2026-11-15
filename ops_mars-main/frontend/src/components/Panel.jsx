export default function Panel({
  title,
  eyebrow,
  icon: Icon,
  action,
  className = '',
  children,
}) {
  return (
    <section className={`panel ${className}`.trim()}>
      <header className="panel__header">
        <div className="panel__heading">
          {Icon && (
            <span className="panel__icon">
              <Icon size={16} aria-hidden="true" />
            </span>
          )}
          <div>
            {eyebrow && <p className="panel__eyebrow">{eyebrow}</p>}
            {title && <h2 className="panel__title">{title}</h2>}
          </div>
        </div>
        {action && <div className="panel__action">{action}</div>}
      </header>
      <div className="panel__body">{children}</div>
    </section>
  )
}
