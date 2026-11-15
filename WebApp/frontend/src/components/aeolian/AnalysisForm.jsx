import { AlertTriangle, LoaderCircle, Play, SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import Panel from '../Panel.jsx'

const INITIAL_OBSERVATIONS = [
  {
    role: 'reference',
    title: 'Reference observation',
    observation_id: 'reference',
    product_id: '',
    acquisition_datetime_utc: '',
    image_path: '',
    mask_path: '',
  },
  {
    role: 'moving',
    title: 'Moving observation',
    observation_id: 'moving',
    product_id: '',
    acquisition_datetime_utc: '',
    image_path: '',
    mask_path: '',
  },
]

function toUtcIso(value) {
  const text = value.trim()
  if (!text) {
    return ''
  }
  if (text.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(text)) {
    return text
  }
  return `${text}${text.length === 16 ? ':00' : ''}Z`
}

function isRelativeServerPath(value) {
  const text = value.trim()
  if (!text) {
    return false
  }
  if (
    text.startsWith('/') ||
    text.startsWith('~') ||
    /^[A-Za-z]:[\\/]/.test(text) ||
    /^[A-Za-z][A-Za-z0-9+.-]*:\/\//.test(text)
  ) {
    return false
  }
  return !text.split(/[\\/]/).some((segment) => segment === '..')
}

function validateForm({
  observations,
  useMetricScale,
  scaleX,
  scaleY,
  scaleSource,
  minIntervalDays,
}) {
  const errors = {}
  const identifiers = new Set()

  observations.forEach((observation, index) => {
    const value = (field) => observation[field].trim()

    if (!value('observation_id')) {
      errors[`obs-${index}-observation_id`] = 'Observation ID is required.'
    } else if (identifiers.has(value('observation_id'))) {
      errors[`obs-${index}-observation_id`] =
        'Observation IDs must be unique.'
    } else {
      identifiers.add(value('observation_id'))
    }

    if (!value('product_id')) {
      errors[`obs-${index}-product_id`] = 'Product ID is required.'
    }
    if (!observation.acquisition_datetime_utc) {
      errors[`obs-${index}-acquisition_datetime_utc`] =
        'An aware UTC acquisition time is required.'
    }
    if (!isRelativeServerPath(value('image_path'))) {
      errors[`obs-${index}-image_path`] =
        'Use a relative path without absolute prefixes or "..".'
    }
    if (!isRelativeServerPath(value('mask_path'))) {
      errors[`obs-${index}-mask_path`] =
        'Use a relative path without absolute prefixes or "..".'
    }
  })

  if (useMetricScale) {
    const x = Number(scaleX)
    const y = scaleY.trim() === '' ? null : Number(scaleY)
    if (!Number.isFinite(x) || x <= 0) {
      errors.scaleX = 'X metres per pixel must be a positive number.'
    }
    if (y !== null && (!Number.isFinite(y) || y <= 0)) {
      errors.scaleY = 'Y metres per pixel must be a positive number.'
    }
    if (!scaleSource.trim()) {
      errors.scaleSource = 'A scale source is required for provenance.'
    }
  }

  if (minIntervalDays.trim() !== '') {
    const interval = Number(minIntervalDays)
    if (!Number.isFinite(interval) || interval < 0) {
      errors.minIntervalDays = 'Minimum interval must be zero or greater.'
    }
  }

  return errors
}

function FieldError({ message }) {
  if (!message) {
    return null
  }
  return <span className="field__error">{message}</span>
}

export default function AnalysisForm({
  dataset,
  onSubmit,
  loading,
  error,
}) {
  const [observations, setObservations] = useState(INITIAL_OBSERVATIONS)
  const [method, setMethod] = useState('centroid')
  const [crs, setCrs] = useState('')
  const [minIntervalDays, setMinIntervalDays] = useState('1')
  const [includeGeometry, setIncludeGeometry] = useState(true)
  const [useMetricScale, setUseMetricScale] = useState(false)
  const [scaleX, setScaleX] = useState('')
  const [scaleY, setScaleY] = useState('')
  const [scaleSource, setScaleSource] = useState('')
  const [errors, setErrors] = useState({})

  function updateObservation(index, field, value) {
    setObservations((current) =>
      current.map((observation, itemIndex) =>
        itemIndex === index ? { ...observation, [field]: value } : observation,
      ),
    )
  }

  function handleSubmit(event) {
    event.preventDefault()

    const nextErrors = validateForm({
      observations,
      useMetricScale,
      scaleX,
      scaleY,
      scaleSource,
      minIntervalDays,
    })
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    const interval =
      minIntervalDays.trim() === '' ? 1 : Number(minIntervalDays)

    onSubmit({
      dataset_id: dataset.dataset_id,
      observations: observations.map((observation) => ({
        observation_id: observation.observation_id.trim(),
        product_id: observation.product_id.trim(),
        acquisition_datetime_utc: toUtcIso(
          observation.acquisition_datetime_utc,
        ),
        image_path: observation.image_path.trim(),
        mask_path: observation.mask_path.trim(),
        crs: crs.trim() || null,
      })),
      method,
      meters_per_pixel: useMetricScale
        ? {
            x_m_per_pixel: Number(scaleX),
            ...(scaleY.trim() === '' ? {} : { y_m_per_pixel: Number(scaleY) }),
            source: scaleSource.trim(),
          }
        : null,
      min_interval_days: interval,
      include_geometry: includeGeometry,
    })
  }

  return (
    <Panel
      title="Observed Migration Analysis"
      eyebrow="Run mars_ml on local observations"
      icon={SlidersHorizontal}
      action={<span className="panel__tag">Observed only</span>}
      className="aeolian-form-panel"
    >
      <div className="aeolian-notice aeolian-notice--compact" role="note">
        <AlertTriangle size={16} aria-hidden="true" />
        <p>
          <span>Local files required.</span> Image and mask paths must already
          exist under the backend&apos;s <code>AEOLIAN_DATA_ROOT</code>. This
          interface does not upload files, and masks must be single-band,
          binary, and match their image dimensions.
        </p>
      </div>

      {dataset.analysis_capability.blockers.length > 0 && (
        <p className="panel__note">
          The manifest is not analysis-ready by itself. Supplying dated local
          observations and masks is required before the backend can run.
        </p>
      )}

      <form className="aeolian-form" onSubmit={handleSubmit} noValidate>
        <div className="observation-list">
          {observations.map((observation, index) => (
            <fieldset className="observation-card" key={observation.role}>
              <legend>{observation.title}</legend>
              <div className="form-grid">
                <label className="field">
                  <span>Observation ID</span>
                  <input
                    type="text"
                    value={observation.observation_id}
                    onChange={(event) =>
                      updateObservation(
                        index,
                        'observation_id',
                        event.target.value,
                      )
                    }
                    aria-invalid={Boolean(
                      errors[`obs-${index}-observation_id`],
                    )}
                    autoComplete="off"
                  />
                  <FieldError
                    message={errors[`obs-${index}-observation_id`]}
                  />
                </label>

                <label className="field">
                  <span>Product ID</span>
                  <input
                    type="text"
                    value={observation.product_id}
                    onChange={(event) =>
                      updateObservation(index, 'product_id', event.target.value)
                    }
                    placeholder="PDS product identifier"
                    aria-invalid={Boolean(errors[`obs-${index}-product_id`])}
                    autoComplete="off"
                  />
                  <FieldError message={errors[`obs-${index}-product_id`]} />
                </label>

                <label className="field">
                  <span>Acquisition (UTC)</span>
                  <input
                    type="datetime-local"
                    step="1"
                    value={observation.acquisition_datetime_utc}
                    onChange={(event) =>
                      updateObservation(
                        index,
                        'acquisition_datetime_utc',
                        event.target.value,
                      )
                    }
                    aria-invalid={Boolean(
                      errors[`obs-${index}-acquisition_datetime_utc`],
                    )}
                  />
                  <FieldError
                    message={
                      errors[`obs-${index}-acquisition_datetime_utc`]
                    }
                  />
                </label>

                <label className="field">
                  <span>Image path</span>
                  <input
                    type="text"
                    value={observation.image_path}
                    onChange={(event) =>
                      updateObservation(index, 'image_path', event.target.value)
                    }
                    placeholder="inputs/reference.tif"
                    aria-invalid={Boolean(errors[`obs-${index}-image_path`])}
                    autoComplete="off"
                    spellCheck="false"
                  />
                  <FieldError message={errors[`obs-${index}-image_path`]} />
                </label>

                <label className="field field--wide">
                  <span>Mask path</span>
                  <input
                    type="text"
                    value={observation.mask_path}
                    onChange={(event) =>
                      updateObservation(index, 'mask_path', event.target.value)
                    }
                    placeholder="inputs/reference_mask.png"
                    aria-invalid={Boolean(errors[`obs-${index}-mask_path`])}
                    autoComplete="off"
                    spellCheck="false"
                  />
                  <FieldError message={errors[`obs-${index}-mask_path`]} />
                </label>
              </div>
            </fieldset>
          ))}
        </div>

        <fieldset className="form-section">
          <legend>Processing</legend>
          <div className="form-grid">
            <label className="field">
              <span>Method</span>
              <select
                value={method}
                onChange={(event) => setMethod(event.target.value)}
              >
                <option value="centroid">Centroid displacement</option>
                <option value="crest">Crest displacement</option>
              </select>
              <span className="field__hint">
                Geometry change alone is never treated as migration.
              </span>
            </label>

            <label className="field">
              <span>CRS</span>
              <input
                type="text"
                value={crs}
                onChange={(event) => setCrs(event.target.value)}
                placeholder="IAU2000:49900"
                autoComplete="off"
                spellCheck="false"
              />
              <span className="field__hint">
                Leave blank to use raster metadata. All observations must share
                the same CRS.
              </span>
            </label>

            <label className="field">
              <span>Minimum interval (days)</span>
              <input
                type="number"
                min="0"
                step="0.1"
                value={minIntervalDays}
                onChange={(event) => setMinIntervalDays(event.target.value)}
                aria-invalid={Boolean(errors.minIntervalDays)}
              />
              <FieldError message={errors.minIntervalDays} />
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={includeGeometry}
                onChange={(event) =>
                  setIncludeGeometry(event.target.checked)
                }
              />
              Include mask geometry diagnostics
            </label>
          </div>
        </fieldset>

        <fieldset className="form-section">
          <legend>Metric scale</legend>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={useMetricScale}
              onChange={(event) => setUseMetricScale(event.target.checked)}
            />
            Provide an explicit verified metres-per-pixel scale
          </label>
          <p className="panel__note">
            The API never infers metres from a degree grid. Without an explicit
            scale, pixel displacement is returned but metric distance and
            migration rate remain withheld.
          </p>

          {useMetricScale && (
            <div className="form-grid">
              <label className="field">
                <span>X metres per pixel</span>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={scaleX}
                  onChange={(event) => setScaleX(event.target.value)}
                  aria-invalid={Boolean(errors.scaleX)}
                />
                <FieldError message={errors.scaleX} />
              </label>

              <label className="field">
                <span>Y metres per pixel (optional)</span>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={scaleY}
                  onChange={(event) => setScaleY(event.target.value)}
                  aria-invalid={Boolean(errors.scaleY)}
                />
                <span className="field__hint">
                  Leave blank to use the X value for both axes.
                </span>
                <FieldError message={errors.scaleY} />
              </label>

              <label className="field field--wide">
                <span>Scale source</span>
                <input
                  type="text"
                  value={scaleSource}
                  onChange={(event) => setScaleSource(event.target.value)}
                  placeholder="Product metadata or verified calibration source"
                  aria-invalid={Boolean(errors.scaleSource)}
                  autoComplete="off"
                />
                <FieldError message={errors.scaleSource} />
              </label>
            </div>
          )}
        </fieldset>

        {error && (
          <div className="form-error" role="alert">
            <AlertTriangle size={16} aria-hidden="true" />
            <p>{error}</p>
          </div>
        )}

        <div className="aeolian-actions">
          <button
            type="submit"
            className="button-primary"
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? (
              <LoaderCircle size={16} className="spin" aria-hidden="true" />
            ) : (
              <Play size={16} aria-hidden="true" />
            )}
            {loading ? 'Running analysis...' : 'Run observed analysis'}
          </button>
          <span className="panel__note">
            Results are computed by the local API and stored in memory.
          </span>
        </div>
      </form>
    </Panel>
  )
}
