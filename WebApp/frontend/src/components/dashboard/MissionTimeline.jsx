import { Activity } from 'lucide-react'
import { missionActivity } from '../../services/missionData.js'
import Panel from '../Panel.jsx'

export default function MissionTimeline() {
  return (
    <Panel
      title="Mission Activity Timeline"
      eyebrow="Event log"
      icon={Activity}
      action={<span className="panel__tag">Live</span>}
    >
      <ul className="timeline-list">
        {missionActivity.map((event) => (
          <li
            key={event.id}
            className="timeline-item"
            style={{
              borderLeft: `3px solid`,
            }}
          >
            <div className="timeline-dot" />
            <div className="timeline-content">
              <div className="timeline-header">
                <span className="timeline-time">{event.time}</span>
                <span className="timeline-type">{event.status}</span>
              </div>
              <h3 className="timeline-title">{event.title}</h3>
              <p className="timeline-detail">{event.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  )
}