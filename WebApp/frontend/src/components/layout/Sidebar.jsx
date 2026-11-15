import { Orbit, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '../../services/navigation.js'

export default function Sidebar({ open, onClose }) {
  return (
    <aside
      className={`sidebar${open ? ' is-open' : ''}`}
      aria-label="Primary navigation"
    >
      <div className="sidebar__brand">
        <span className="sidebar__mark">
          <Orbit size={24} aria-hidden="true" />
        </span>
        <div className="sidebar__brand-copy">
          <p className="sidebar__brand-name">MARS OPS</p>
          <p className="sidebar__brand-sub">Mission Control</p>
        </div>
        <button
          type="button"
          className="sidebar__close"
          aria-label="Close navigation"
          onClick={onClose}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>

      <nav className="sidebar__nav" aria-label="Sections">
        <p className="sidebar__section-label">Operations</p>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon

          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              title={item.description}
              onClick={onClose}
              className={({ isActive }) =>
                `nav-link${isActive ? ' is-active' : ''}`
              }
            >
              <Icon size={17} aria-hidden="true" />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__status">
          <span className="status-dot" aria-hidden="true" />
          Simulation environment
        </div>
        <p className="sidebar__footer-note">
          All telemetry and operational events shown here are synthetic.
        </p>
      </div>
    </aside>
  )
}
