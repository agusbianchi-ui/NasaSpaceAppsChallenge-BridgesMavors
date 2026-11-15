import { useState } from 'react'
import AeolianIntelligence from '../components/aeolian/AeolianIntelligence.jsx'
import AIAssistant from '../components/ai/AIAssistant.jsx'
import SimulationNotice from '../components/SimulationNotice.jsx'
import MarsVisualIntelligence from '../components/mars-visual/MarsVisualIntelligence.jsx'
import DuneExplorer from '../components/mars-visual/DuneExplorer.jsx'
import ComputerVisionLab from '../components/mars-visual/ComputerVisionLab.jsx'
import { scientificInsights } from '../data/marsVisualData.js'
import ScientificInsightCard from '../components/mars-visual/ScientificInsightCard.jsx'

export default function AISystems() {
  const [activeTab, setActiveTab] = useState('visual')

  const tabNames = [
    { key: 'visual', icon: 'image', label: 'Visual Gallery' },
    { key: 'dune', icon: 'mountain', label: 'Dune Explorer' },
    { key: 'cv', icon: 'scan-eye', label: 'CV Lab' },
  ]

  return (
    <div className="page">
      {/* Header profesional AI Systems - compacto y alineado */}
      <header className="ai-systems-header">
        <div className="ai-systems-header-inner">
          <h1 className="ai-systems-title">Mars Visual Intelligence</h1>
          <p className="ai-systems-subtitle">Explore Martian landscapes and aeolian formations.</p>
          <span className="ai-systems-badge">NASA DATA</span>
        </div>
      </header>

      <SimulationNotice compact />
      <AeolianIntelligence />
      <AIAssistant />

      {/* Sistema de pestañas horizontal rediseñado - segmented tabs */}
      <div className="ai-systems-tabs">
        {tabNames.map(({ key, icon, label }) => (
          <button
            key={key}
            className={`tab-${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
            aria-label={label}
            style={{
              flex: '1',
              minWidth: 0,
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
            >
              {icon === 'image'
                ? '<line x1="3" y1="3" x2="21" y2="21" /><line x1="3" y1="21" x2="21" y2="3" />'
                : icon === 'mountain'
                ? '<path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" />'
                : '<path d="M18 13v12a5 5 0 0 1-10 0V13"/><circle cx="10" cy="13" r="3" />'}
            </svg>
            <span>{label}</span>
          </button>
        ))}
      </div>

      <div className="ai-systems-toolbar">
        {/* Buscador y selector en una sola fila */}
        <div className="toolbar-row">
          <div className="toolbar-search">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="Search formations..."
              aria-label="Buscar formaciones marcianas"
            />
          </div>

          <div className="toolbar-selector">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
            >
              <line x1="6" y1="9" x2="6" y2="15" />
              <line x1="10" y1="9" x2="10" y2="15" />
              <line x1="14" y1="9" x2="14" y2="15" />
            </svg>
            <select aria-label="Filtrar por categoría">
              <option value="all">All categories</option>
            </select>
            <svg
              width="8"
              height="8"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
            >
              <polyline points="6 9 9 14 14 9" />
            </svg>
          </div>
        </div>
      </div>

      {/* Indicadores de contenido debajo de los filtros */}
      <div className="ai-systems-indicators">
        <span className="ai-systems-indicator">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
          </svg>
          Available Imagery
        </span>
        <span className="ai-systems-indicator">
          {scientificInsights.length}
        </span>
        <span className="ai-systems-indicator">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
          </svg>
          NASA DATA
        </span>
      </div>

      <div className="ai-systems-content">
        {activeTab === 'visual' && <MarsVisualIntelligence />}
        {activeTab === 'dune' && <DuneExplorer />}
        {activeTab === 'cv' && <ComputerVisionLab />}
      </div>

      <div className="scientific-insights-section">
        <h2>Información Científica</h2>
        <div className="insights-grid">
          {scientificInsights.map((insight) => (
            <ScientificInsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      </div>
    </div>
  )
}