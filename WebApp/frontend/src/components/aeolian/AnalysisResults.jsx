import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Gauge,
  Ruler,
} from 'lucide-react'
import MigrationRateChart from '../charts/MigrationRateChart.jsx'
import Panel from '../Panel.jsx'
import StatusPill from '../StatusPill.jsx'

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: 'UTC',
})

const STATUS_TONES = {
  analyzed: 'ok',
  completed: 'ok',
  displacement_only: 'accent',
  registration_unreliable: 'warning',
  registration_not_attempted: 'warning',
  mask_not_overlapping: 'warning',
  completed_without_valid_migration: 'warning',
}

function humanize(value) {
  if (!value) {
    return 'Unknown'
  }
  return String(value).replaceAll('_', ' ')
}

function formatDate(value) {
  if (!value) {
    return 'Not reported'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return `${DATE_FORMATTER.format(date)} UTC`
}

function formatNumber(value, digits = 2) {
  if (!Number.isFinite(value)) {
    return 'Withheld'
  }
  return value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function Metric({ label, value, unit }) {
  return (
    <div className="pair-metric">
      <dt>{label}</dt>
      <dd>
        {value}
        {unit && value !== 'Withheld' && <span>{unit}</span>}
      </dd>
    </div>
  )
}

function PairCard({ pair, index }) {
  const migration = pair.observed_migration
  const registration = pair.registration
  const geometry = pair.geometry
  const reasons = [
    ...new Set([...(pair.reasons ?? []), ...(migration?.reasons ?? [])]),
  ]

  return (
    <article className="pair-card">
      <header className="pair-card__header">
        <div>
          <p className="pair-card__eyebrow">Pair {index + 1}</p>
          <h3>
            {pair.reference_id} <span aria-hidden="true">→</span>{' '}
            {pair.moving_id}
          </h3>
          <p className="pair-card__dates">
            {formatDate(pair.reference_datetime_utc)} to{' '}
            {formatDate(pair.moving_datetime_utc)}
          </p>
        </div>
        <StatusPill tone={STATUS_TONES[pair.status] ?? 'muted'}>
          {humanize(pair.status)}
        </StatusPill>
      </header>

      {migration && (
        <section className="pair-section">
          <div className="pair-section__heading">
            <h4>
              <Activity size={14} aria-hidden="true" />
              Observed migration
            </h4>
            <StatusPill tone={migration.valid ? 'ok' : 'warning'}>
              {migration.valid ? 'Valid' : 'Withheld'}
            </StatusPill>
          </div>
          <dl className="pair-metrics">
            <Metric
              label="Interval"
              value={formatNumber(migration.interval_days, 2)}
              unit="days"
            />
            <Metric
              label="dx east"
              value={formatNumber(migration.dx_m, 2)}
              unit="m"
            />
            <Metric
              label="dy north"
              value={formatNumber(migration.dy_m, 2)}
              unit="m"
            />
            <Metric
              label="Distance"
              value={formatNumber(migration.distance_m, 2)}
              unit="m"
            />
            <Metric
              label="Direction"
              value={formatNumber(migration.direction_azimuth_deg, 1)}
              unit="deg from north"
            />
            <Metric
              label="Rate"
              value={formatNumber(migration.rate_m_per_earth_year, 3)}
              unit="m / Earth year"
            />
            <Metric
              label="Rate standard error"
              value={formatNumber(
                migration.rate_standard_error_m_per_earth_year,
                3,
              )}
              unit="m / Earth year"
            />
            <Metric label="Method" value={migration.method} />
          </dl>

          {migration.assumptions.length > 0 && (
            <details className="pair-details">
              <summary>Assumptions</summary>
              <ul className="reason-list">
                {migration.assumptions.map((assumption) => (
                  <li key={assumption}>{assumption}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      {registration && (
        <section className="pair-section">
          <div className="pair-section__heading">
            <h4>
              <Gauge size={14} aria-hidden="true" />
              Registration quality
            </h4>
            <StatusPill tone={registration.reliable ? 'ok' : 'warning'}>
              {registration.reliable ? 'Reliable' : 'Unreliable'}
            </StatusPill>
          </div>
          <dl className="pair-metrics">
            <Metric label="Method" value={humanize(registration.method)} />
            <Metric label="Matches" value={registration.matches} />
            <Metric label="Inliers" value={registration.inliers} />
            <Metric
              label="Inlier ratio"
              value={`${formatNumber(registration.inlier_ratio * 100, 1)}%`}
            />
            <Metric
              label="RMS error"
              value={formatNumber(registration.rms_error_px, 2)}
              unit="px"
            />
            <Metric
              label="Median error"
              value={formatNumber(registration.median_error_px, 2)}
              unit="px"
            />
            <Metric
              label="Phase response"
              value={formatNumber(registration.phase_response, 3)}
            />
          </dl>
          {registration.message && (
            <p className="panel__note">{registration.message}</p>
          )}
        </section>
      )}

      {geometry && (
        <section className="pair-section">
          <div className="pair-section__heading">
            <h4>
              <Ruler size={14} aria-hidden="true" />
              Geometry diagnostics
            </h4>
            <StatusPill tone={geometry.reliable ? 'ok' : 'warning'}>
              {geometry.reliable ? 'Reliable' : 'Unreliable'}
            </StatusPill>
          </div>
          <dl className="pair-metrics">
            <Metric label="IoU" value={formatNumber(geometry.iou, 3)} />
            <Metric label="Dice" value={formatNumber(geometry.dice, 3)} />
            <Metric
              label="Area delta"
              value={geometry.area_delta_px}
              unit="px"
            />
            <Metric
              label="Centroid dx"
              value={formatNumber(geometry.centroid_dx_m, 2)}
              unit="m"
            />
            <Metric
              label="Centroid dy"
              value={formatNumber(geometry.centroid_dy_m, 2)}
              unit="m"
            />
            <Metric
              label="Orientation difference"
              value={formatNumber(geometry.orientation_difference_deg, 1)}
              unit="deg"
            />
            <Metric
              label="Chamfer distance"
              value={formatNumber(geometry.chamfer_distance_m, 2)}
              unit="m"
            />
          </dl>
          <p className="panel__note">
            Geometry diagnostics are not an independent measurement of dune
            migration.
          </p>
        </section>
      )}

      {reasons.length > 0 && (
        <section className="pair-section">
          <div className="pair-section__heading">
            <h4>
              <AlertTriangle size={14} aria-hidden="true" />
              Withheld or rejected
            </h4>
          </div>
          <ul className="reason-list">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}

function ResultMeta({ label, children }) {
  return (
    <div className="result-meta__item">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

export default function AnalysisResults({ result }) {
  const scale = result.provenance.meters_per_pixel
  const scaleLabel = scale
    ? `${scale[0]} x ${scale[1]} m/px`
    : 'Not supplied'

  return (
    <Panel
      title="Analysis Result"
      eyebrow="API response · observed data"
      icon={Activity}
      action={
        <StatusPill tone={STATUS_TONES[result.status] ?? 'muted'}>
          {humanize(result.status)}
        </StatusPill>
      }
      className="aeolian-results"
    >
      <div className="metric-grid">
        <div className="metric-card">
          <span className="metric-card__label">Observations</span>
          <strong className="metric-card__value">
            {result.summary.observation_count}
          </strong>
          <span className="metric-card__detail">Input rasters</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Pairs</span>
          <strong className="metric-card__value">
            {result.summary.pair_count}
          </strong>
          <span className="metric-card__detail">Consecutive dated pairs</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Valid migration</span>
          <strong className="metric-card__value">
            {result.summary.valid_migration_count}
          </strong>
          <span className="metric-card__detail">Observed pairs with rates</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Metric scale</span>
          <strong className="metric-card__value metric-card__value--small">
            {scaleLabel}
          </strong>
          <span className="metric-card__detail">
            {result.provenance.scale_source ?? 'Metric values withheld'}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Predictions</span>
          <strong className="metric-card__value metric-card__value--small">
            {result.prediction_status === 'available' ? 'Available' : 'Unavailable'}
          </strong>
          <span className="metric-card__detail">
            {result.predictions.length} model result
            {result.predictions.length === 1 ? '' : 's'}
          </span>
        </div>
      </div>

      <dl className="result-meta">
        <ResultMeta label="Analysis ID">
          <span className="mono">{result.analysis_id}</span>
        </ResultMeta>
        <ResultMeta label="Created">{formatDate(result.created_at_utc)}</ResultMeta>
        <ResultMeta label="Dataset">
          {result.dataset.name}
          <span className="mono result-meta__sub">{result.dataset_id}</span>
        </ResultMeta>
        <ResultMeta label="CRS">
          <span className="mono">{result.provenance.crs}</span>
        </ResultMeta>
        <ResultMeta label="Scientific status">
          {humanize(result.provenance.scientific_status)}
        </ResultMeta>
        <ResultMeta label="Software">
          <span className="mono">{result.provenance.software}</span>
        </ResultMeta>
      </dl>

      <MigrationRateChart pairs={result.pairs} />

      <div className="pair-list">
        {result.pairs.map((pair, index) => (
          <PairCard
            key={`${pair.reference_id}-${pair.moving_id}`}
            pair={pair}
            index={index}
          />
        ))}
      </div>

      <div className="result-columns">
        <section className="result-section">
          <h3>
            <AlertTriangle size={15} aria-hidden="true" />
            Limitations
          </h3>
          <ul className="reason-list">
            {result.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>

        <section className="result-section">
          <h3>
            <CheckCircle2 size={15} aria-hidden="true" />
            Pipeline notes
          </h3>
          {result.notes.length > 0 ? (
            <ul className="reason-list">
              {result.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : (
            <p className="panel__note">No additional pipeline notes.</p>
          )}
        </section>
      </div>

      <details className="result-details">
        <summary>
          <FileText size={15} aria-hidden="true" />
          Provenance and input files
        </summary>
        <dl className="result-meta result-meta--compact">
          <ResultMeta label="Dataset source">
            {result.provenance.dataset_source}
          </ResultMeta>
          <ResultMeta label="Dataset provider">
            {result.provenance.dataset_provider}
          </ResultMeta>
          <ResultMeta label="Dataset retrieved">
            {result.provenance.dataset_retrieved_at_utc ?? 'Not reported'}
          </ResultMeta>
          <ResultMeta label="Local observations required">
            {result.provenance.local_observations_required ? 'Yes' : 'No'}
          </ResultMeta>
        </dl>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Observation</th>
                <th scope="col">Role</th>
                <th scope="col">Path</th>
                <th scope="col">SHA-256</th>
              </tr>
            </thead>
            <tbody>
              {result.provenance.files.map((file) => (
                <tr key={`${file.observation_id}-${file.role}`}>
                  <td className="mono">{file.observation_id}</td>
                  <td>{humanize(file.role)}</td>
                  <td className="mono">{file.path}</td>
                  <td className="mono">{file.sha256}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Panel>
  )
}
