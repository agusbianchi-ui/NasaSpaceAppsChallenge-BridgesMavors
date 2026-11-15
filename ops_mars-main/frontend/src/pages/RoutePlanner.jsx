import { Route as RouteIcon, ShieldAlert } from 'lucide-react'
import Panel from '../components/Panel.jsx'
import SimulationNotice from '../components/SimulationNotice.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { routeNote, routeSummary, routeWaypoints } from '../services/missionData.js'

export default function RoutePlanner() {
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">Traverse planning</p>
          <h1>Route Planner</h1>
          <p className="page-heading__description">
            Demonstration traverse corridor for the Jezero Crater planning
            scenario. Interactive route editing is not enabled in this build.
          </p>
        </div>
        <span className="page-heading__phase">ROUTE · SIM-01</span>
      </div>

      <SimulationNotice compact />

      <div className="metric-grid">
        {routeSummary.map((item) => (
          <div className="metric-card" key={item.id}>
            <span className="metric-card__label">{item.label}</span>
            <strong className="metric-card__value">{item.value}</strong>
            <span className="metric-card__detail">Simulated value</span>
          </div>
        ))}
      </div>

      <Panel
        title="Planned Waypoints"
        eyebrow="Candidate corridor"
        icon={RouteIcon}
        action={<span className="panel__tag">Simulated</span>}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Waypoint</th>
                <th scope="col">Location</th>
                <th scope="col">Coordinates</th>
                <th scope="col">Distance</th>
                <th scope="col">Risk</th>
              </tr>
            </thead>
            <tbody>
              {routeWaypoints.map((waypoint) => (
                <tr key={waypoint.id}>
                  <td className="mono">{waypoint.id}</td>
                  <td>
                    <span className="data-table__primary">{waypoint.name}</span>
                  </td>
                  <td className="mono">{waypoint.coordinates}</td>
                  <td className="mono">{waypoint.distance}</td>
                  <td>
                    <StatusPill>{waypoint.risk}</StatusPill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="panel__note">{routeNote}</p>
      </Panel>

      <div className="coming-soon">
        <span className="coming-soon__icon">
          <ShieldAlert size={22} aria-hidden="true" />
        </span>
        <h3>Interactive route optimization pending</h3>
        <p>
          Future stages will connect the planner to terrain analysis and allow
          operators to edit waypoints, compare corridors, and simulate traverse
          constraints.
        </p>
      </div>
    </div>
  )
}
