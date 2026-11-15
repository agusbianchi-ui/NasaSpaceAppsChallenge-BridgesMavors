import { BrainCircuit, LockKeyhole } from 'lucide-react'
import Panel from '../Panel.jsx'

const REQUIRED_ARTIFACTS = [
  'A trained checkpoint with a run report and held-out grouped metrics.',
  'Verified Mars observations with explicit dates and a metric scale.',
  'An independent validation set that was not used for training.',
  'Calibrated uncertainty for the requested prediction target.',
]

export default function PredictionPanel() {
  return (
    <Panel
      title="Predictive Model"
      eyebrow="Model availability"
      icon={BrainCircuit}
      action={<span className="panel__tag">Unavailable</span>}
      className="prediction-panel"
    >
      <div className="prediction-status">
        <span className="prediction-status__icon">
          <LockKeyhole size={22} aria-hidden="true" />
        </span>
        <div>
          <h3>Predictive model under development</h3>
          <p>
            No validated checkpoint, training report, or independent Mars
            validation set is registered. The prediction endpoint explicitly
            returns <code>501 not_implemented</code>; no simulated forecast is
            produced.
          </p>
        </div>
      </div>

      <div>
        <p className="panel__note">Required before predictions can be enabled:</p>
        <ul className="check-list">
          {REQUIRED_ARTIFACTS.map((artifact) => (
            <li key={artifact}>
              <LockKeyhole size={13} aria-hidden="true" />
              {artifact}
            </li>
          ))}
        </ul>
      </div>

      <p className="panel__note">
        Observed displacement and migration rates are separate from model
        predictions and must never be presented as forecasts.
      </p>
    </Panel>
  )
}
