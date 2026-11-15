import { useEffect, useState } from 'react'
import { fetchAeolianDatasets, analyzeAeolian } from '../../services/marsApi.js'
import { DatasetCatalog, DatasetDetails } from './DatasetExplorer.jsx'
import AnalysisForm from './AnalysisForm.jsx'
import AnalysisResults from './AnalysisResults.jsx'
import PredictionPanel from './PredictionPanel.jsx'
export default function AeolianIntelligence() {
  const [datasets, setDatasets] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  useEffect(() => {
    const controller = new AbortController()
    fetchAeolianDatasets({ signal: controller.signal }).then(data => { setDatasets(data); setSelectedId(data[0]?.dataset_id || null) }).catch(error => { if (error.name !== 'AbortError') setError(error.message) })
    return () => controller.abort()
  }, [])
  const dataset = datasets.find(item => item.dataset_id === selectedId)
  async function analyze(payload) {
    setLoading(true); setError(''); setResult(null)
    try { setResult(await analyzeAeolian(payload)) } catch (error) { setError(error.message) } finally { setLoading(false) }
  }
  return <section aria-label="Aeolian analysis">
    {error && <p role="alert">{error}</p>}
    <DatasetCatalog datasets={datasets} selectedId={selectedId} onSelect={id => { setSelectedId(id); setResult(null); setError('') }} />
    {dataset && <><DatasetDetails dataset={dataset} /><AnalysisForm key={selectedId} dataset={dataset} onSubmit={analyze} loading={loading} error={error} /></>}
    {result && <AnalysisResults result={result} />}
    <PredictionPanel />
  </section>
}
