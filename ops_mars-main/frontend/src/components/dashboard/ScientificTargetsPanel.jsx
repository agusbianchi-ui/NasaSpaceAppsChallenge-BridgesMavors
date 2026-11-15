import { FlaskConical } from 'lucide-react'
import { scientificTargets } from '../../services/missionData.js'
import Panel from '../Panel.jsx'
import StatusPill from '../StatusPill.jsx'

export default function ScientificTargetsPanel({ limit, action }) {
  const visibleTargets = limit
    ? scientificTargets.slice(0, limit)
    : scientificTargets

  return (
    <Panel
      title="Scientific Targets"
      eyebrow="Analysis queue"
      icon={FlaskConical}
      action={action ?? <span className="panel__tag">Simulated</span>}
    >
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Target</th>
              <th scope="col">Type</th>
              <th scope="col">Analysis</th>
            </tr>
          </thead>
          <tbody>
            {visibleTargets.map((target) => (
              <tr key={target.id}>
                <td className="mono">{target.id}</td>
                <td>
                  <span className="data-table__primary">{target.name}</span>
                  <span className="data-table__secondary">
                    Confidence: {target.confidence}
                  </span>
                </td>
                <td>{target.type}</td>
                <td>
                  <StatusPill>{target.status}</StatusPill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
