import { ListChecks } from 'lucide-react'
import { missionActivity, operationsStatus } from '../../services/missionData.js'
import Panel from '../Panel.jsx'
import StatusPill from '../StatusPill.jsx'

export default function MissionActivityPanel() {
  return (
    <Panel
      title="Mission Activity"
      eyebrow="Operations log"
      icon={ListChecks}
      action={<span className="panel__tag">Simulated</span>}
    >
      <ul className="activity-list">
        {missionActivity.map((event) => (
          <li className="activity-item" key={event.id}>
            <span className="activity-item__dot" aria-hidden="true" />
            <div className="activity-item__content">
              <div className="activity-item__top">
                <span className="mono">{event.time}</span>
                <StatusPill>{event.status}</StatusPill>
              </div>
              <p className="activity-item__title">{event.title}</p>
              <p className="activity-item__detail">{event.detail}</p>
            </div>
          </li>
        ))}
      </ul>

      <dl className="operations-status">
        {operationsStatus.map((status) => (
          <div key={status.id}>
            <dt>{status.label}</dt>
            <dd className={`is-${status.tone}`}>{status.value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  )
}
