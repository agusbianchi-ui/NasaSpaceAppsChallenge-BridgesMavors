import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Database,
  FileText,
  MapPin,
  Ruler,
  Satellite,
  XCircle,
} from 'lucide-react'
import Panel from '../Panel.jsx'
import StatusPill from '../StatusPill.jsx'

const SIZE_FORMATTER = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
})

function humanize(value) {
  if (!value) {
    return 'Not reported'
  }
  return String(value).replaceAll('_', ' ')
}

function formatBytes(value) {
  if (!Number.isFinite(value)) {
    return 'Unknown size'
  }
  if (value < 1024) {
    return `${value} B`
  }
  if (value < 1024 ** 2) {
    return `${SIZE_FORMATTER.format(value / 1024)} KiB`
  }
  if (value < 1024 ** 3) {
    return `${SIZE_FORMATTER.format(value / 1024 ** 2)} MiB`
  }
  return `${SIZE_FORMATTER.format(value / 1024 ** 3)} GiB`
}

function DatasetCard({ dataset, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`dataset-card${selected ? ' is-selected' : ''}`}
      aria-pressed={selected}
      onClick={() => onSelect(dataset.dataset_id)}
    >
      <span className="dataset-card__top">
        <span className="dataset-card__name">{dataset.name}</span>
        <StatusPill
          tone={dataset.has_temporal_series ? 'accent' : 'muted'}
        >
          {dataset.has_temporal_series ? 'Temporal series' : 'No series'}
        </StatusPill>
      </span>
      <span className="dataset-card__location">
        <MapPin size={13} aria-hidden="true" />
        {dataset.location}
      </span>
      <span className="dataset-card__meta">
        <span>{dataset.instrument}</span>
        <span>{dataset.has_pixels ? 'Pixels declared' : 'Metadata only'}</span>
      </span>
    </button>
  )
}

function MetadataItem({ label, children }) {
  return (
    <div className="metadata-item">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function Flag({ ok, children }) {
  const Icon = ok ? CheckCircle2 : XCircle

  return (
    <span className={`dataset-flag${ok ? ' dataset-flag--ok' : ''}`}>
      <Icon size={13} aria-hidden="true" />
      {children}
    </span>
  )
}

export function DatasetCatalog({ datasets, selectedId, onSelect }) {
  return (
    <Panel
      title="Dataset Catalog"
      eyebrow="Source-referenced Mars manifests"
      icon={Database}
      action={<span className="panel__tag">{datasets.length} datasets</span>}
      className="aeolian-catalog"
    >
      <p className="panel__note">
        Metadata comes from the local <code>mars_ml</code> manifests. No Mars
        pixels or per-dune labels are bundled with this repository.
      </p>
      <div className="dataset-list">
        {datasets.map((dataset) => (
          <DatasetCard
            key={dataset.dataset_id}
            dataset={dataset}
            selected={dataset.dataset_id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </Panel>
  )
}

export function DatasetDetails({ dataset }) {
  const capability = dataset.analysis_capability
  const dates = dataset.acquisition_dates ?? []

  return (
    <Panel
      title={dataset.name}
      eyebrow="Dataset metadata"
      icon={Satellite}
      action={
        <StatusPill tone={capability.temporal_analysis ? 'accent' : 'muted'}>
          {capability.temporal_analysis ? 'Temporal analysis' : 'No analysis'}
        </StatusPill>
      }
      className="aeolian-details"
    >
      <div className="dataset-detail__lead">
        <p>
          <MapPin size={14} aria-hidden="true" />
          {dataset.location}
        </p>
        <p>
          <Satellite size={14} aria-hidden="true" />
          {dataset.mission} · {dataset.instrument}
        </p>
      </div>

      <dl className="metadata-grid">
        <MetadataItem label="Dataset ID">
          <span className="mono">{dataset.dataset_id}</span>
        </MetadataItem>
        <MetadataItem label="Provider">{dataset.provider}</MetadataItem>
        <MetadataItem label="Source">{dataset.source}</MetadataItem>
        <MetadataItem label="Data type">{humanize(dataset.data_type)}</MetadataItem>
        <MetadataItem label="Version">{dataset.version ?? 'Not reported'}</MetadataItem>
        <MetadataItem label="Retrieved">
          {dataset.retrieved_at_utc ?? 'Not reported'}
        </MetadataItem>
        <MetadataItem label="License">{dataset.license}</MetadataItem>
        <MetadataItem label="DOI">
          {dataset.doi ? (
            <a
              className="text-link"
              href={`https://doi.org/${dataset.doi}`}
              target="_blank"
              rel="noreferrer"
            >
              {dataset.doi}
            </a>
          ) : (
            'Not reported'
          )}
        </MetadataItem>
      </dl>

      <div className="dataset-detail__section">
        <h3>
          <CalendarDays size={15} aria-hidden="true" />
          Acquisition dates
        </h3>
        {dates.length > 0 ? (
          <ul className="inline-list mono">
            {dates.map((date) => (
              <li key={date}>{date}</li>
            ))}
          </ul>
        ) : (
          <p className="panel__note">
            No acquisition dates are stored in the manifest (
            {humanize(dataset.acquisition_dates_status)}). Dates must be
            resolved from product metadata and supplied per observation.
          </p>
        )}
      </div>

      <div className="dataset-detail__section">
        <h3>
          <Ruler size={15} aria-hidden="true" />
          Resolution and coordinate reference
        </h3>
        <ul className="resolution-list">
          {dataset.resolution.map((item) => (
            <li key={`${item.product}-${item.value}`}>
              <strong className="mono">
                {item.value} {item.unit}
              </strong>
              <span>{item.product}</span>
            </li>
          ))}
        </ul>
        <dl className="metadata-grid metadata-grid--compact">
          <MetadataItem label="CRS">{dataset.coordinate_reference_system.name}</MetadataItem>
          <MetadataItem label="Units">
            {dataset.coordinate_reference_system.units}
          </MetadataItem>
          <MetadataItem label="Code">
            {dataset.coordinate_reference_system.code ?? 'Not reported'}
          </MetadataItem>
          <MetadataItem label="Spheroid">
            {dataset.coordinate_reference_system.spheroid ?? 'Not reported'}
          </MetadataItem>
        </dl>
      </div>

      <div className="dataset-flags">
        <Flag ok={dataset.has_temporal_series}>Temporal series</Flag>
        <Flag ok={dataset.has_pixels}>Pixels in manifest</Flag>
        <Flag ok={dataset.has_labels}>Labels in manifest</Flag>
        <Flag ok={capability.analysis_ready}>Analysis-ready manifest</Flag>
      </div>

      {capability.blockers.length > 0 && (
        <div className="dataset-blockers">
          <h3>
            <AlertTriangle size={15} aria-hidden="true" />
            Analysis blockers
          </h3>
          <ul className="reason-list">
            {capability.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </div>
      )}

      {dataset.limitations.length > 0 && (
        <div className="dataset-detail__section">
          <h3>
            <AlertTriangle size={15} aria-hidden="true" />
            Limitations
          </h3>
          <ul className="reason-list">
            {dataset.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </div>
      )}

      {dataset.files.length > 0 && (
        <div className="dataset-detail__section">
          <h3>
            <FileText size={15} aria-hidden="true" />
            Referenced files
          </h3>
          <div className="table-scroll dataset-files">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">File</th>
                  <th scope="col">Role</th>
                  <th scope="col">Size</th>
                  <th scope="col">SHA-256</th>
                </tr>
              </thead>
              <tbody>
                {dataset.files.map((file) => (
                  <tr key={`${file.name}-${file.role}`}>
                    <td className="mono">{file.name}</td>
                    <td>{humanize(file.role)}</td>
                    <td className="mono">{formatBytes(file.size_bytes)}</td>
                    <td className="mono">
                      {file.sha256 ? file.sha256.slice(0, 16) : 'Not recorded'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {dataset.notes && <p className="panel__note">{dataset.notes}</p>}
    </Panel>
  )
}
