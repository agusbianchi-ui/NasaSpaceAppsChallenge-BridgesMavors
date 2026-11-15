import { Clock3, MapPin, Menu, Radio } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useClock } from '../../hooks/useClock.js'
import { missionProfile } from '../../services/missionData.js'
import { getSectionByPath } from '../../services/navigation.js'

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

const TIME_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: 'UTC',
})

export default function Header({ onMenuClick }) {
  const { pathname } = useLocation()
  const now = useClock()
  const section = getSectionByPath(pathname)

  return (
    <header className="app-header">
      <div className="header__left">
        <button
          type="button"
          className="header__menu"
          aria-label="Open navigation"
          onClick={onMenuClick}
        >
          <Menu size={20} aria-hidden="true" />
        </button>
        <div className="header__title-group">
          <p className="header__eyebrow">
            <span className="status-dot" aria-hidden="true" />
            MARS OPS · {missionProfile.missionId}
          </p>
          <h2 className="header__title">{section.label}</h2>
        </div>
      </div>

      <div className="header__meta">
        <span className="header__chip header__chip--mission">
          <Radio size={13} aria-hidden="true" />
          MISSION <strong>{missionProfile.phase}</strong>
        </span>
        <span className="header__chip">
          <MapPin size={13} aria-hidden="true" />
          {missionProfile.location}
        </span>
        <span className="header__chip mono">
          <Clock3 size={13} aria-hidden="true" />
          {DATE_FORMATTER.format(now).toUpperCase()} ·{' '}
          {TIME_FORMATTER.format(now)} UTC
        </span>
        <span className="header__chip header__chip--link">
          <span className="status-dot" aria-hidden="true" />
          LINK STABLE <em>SIM</em>
        </span>
      </div>
    </header>
  )
}
