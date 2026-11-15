import { Activity } from 'lucide-react'
import { missionStatus } from '../../services/missionData.js'
import Panel from '../Panel.jsx'

export default function MissionStatus() {
  const {
    sol,
    missionDuration,
    roverStatus,
    batteryLevel,
    communicationSignal,
    missionProgress,
    progressLabel,
  } = missionStatus

  const statusColors = {
    Online: '#10b981',
    Offline: '#ef4444',
    SafeMode: '#f59e0b',
  }

  const signalColors = {
    Strong: '#10b981',
    Moderate: '#f59e0b',
    Weak: '#ef4444',
  }

  return (
    <Panel
      title="Mission Status"
      eyebrow="Key indicators"
      icon={Activity}
      action={<span className="panel__tag">Live</span>}
    >
      <div className="mission-status-grid">
        <div className="mission-status-item">
          <span className="mission-status-label">Sol</span>
          <strong className="mission-status-value">{sol}</strong>
        </div>

        <div className="mission-status-item">
          <span className="mission-status-label">Duration</span>
          <strong className="mission-status-value">{missionDuration}</strong>
        </div>

        <div className="mission-status-item">
          <span className="mission-status-label">Rover</span>
          <strong className="mission-status-value" style={{ color: statusColors[roverStatus] }}>
            {roverStatus}
          </strong>
        </div>

        <div className="mission-status-item">
          <span className="mission-status-label">Battery</span>
          <strong className="mission-status-value"
            style={{ color: batteryLevel > 80 ? '#10b981' : batteryLevel > 50 ? '#f59e0b' : '#ef4444' }}>
            {batteryLevel}%
          </strong>
        </div>

        <div className="mission-status-item">
          <span className="mission-status-label">Signal</span>
          <strong className="mission-status-value"
            style={{ color: signalColors[communicationSignal] }}>
            {communicationSignal}
          </strong>
        </div>

        <div className="mission-status-item">
          <span className="mission-status-label">Progress</span>
          <strong className="mission-status-value"
            style={{ width: `${missionProgress}%`, background: 'var(--accent-soft)', padding: '2px 4px' }}>
            {missionProgress}% {progressLabel}
          </strong>
        </div>
      </div>
    </Panel>
  )
}