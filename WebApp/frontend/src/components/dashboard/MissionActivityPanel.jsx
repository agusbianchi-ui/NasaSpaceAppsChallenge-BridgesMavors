import { ListChecks } from 'lucide-react'
import { missionActivity } from '../../services/missionData.js'
import Panel from '../Panel.jsx'
import StatusPill from '../StatusPill.jsx'

export default function MissionActivityPanel({ enhancedActivity }) {
  const activities = enhancedActivity || missionActivity.map((event) => ({
    ...event,
    relatedTargets: [],
  }))

  return (
    <Panel
      title="Mission Activity"
      eyebrow="Scientific operations log"
      icon={ListChecks}
      action={<span className="panel__tag">Live</span>}
    >
      <ul className="activity-list">
        {activities.map((event) => (
          <li key={event.id} className="activity-item">
            <span className="activity-item__dot" aria-hidden="true" />
            <div className="activity-item__content">
              <div className="activity-item__top">
                <span className="mono">{event.time}</span>
                <span className="activity-item__related">
                  {event.relatedTargets.length > 0
                    ? `Related to ${event.relatedTargets.map((t) => t.name).join(', ')}`
                    : 'Standalone event'}
                </span>
                <StatusPill>{event.status}</StatusPill>
              </div>
              <p className="activity-item__title">{event.title}</p>
              <p className="activity-item__detail">{event.detail}</p>
              {event.relatedTargets.length > 0 && (
                <p className="activity-item__target-link">
                  <strong>Scientific Target:</strong> {event.relatedTargets[0].name}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

MissionActivityPanel.defaultProps = {
  enhancedActivity: undefined,
  targetMap: undefined,
}