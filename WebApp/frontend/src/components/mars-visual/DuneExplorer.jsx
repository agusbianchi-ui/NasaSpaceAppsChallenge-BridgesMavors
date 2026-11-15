import { useState } from 'react'
import { Search, Eye, Mountain } from 'lucide-react'
import { marsCategories, marsImageGallery } from '../../data/marsVisualData.js'

export default function DuneExplorer() {
  const gallery = marsImageGallery
  const [searchTerm, setSearchTerm] = useState('')
  const [activeCategory, setActiveCategory] = useState('all')
  const [selectedImage, setSelectedImage] = useState(null)


  const categoryNames = {
    barchan: 'Barchan Dunes',
    linear: 'Linear Dunes',
    transverse: 'Transverse Dunes',
    polar: 'Polar Dunes',
  }

  const handleSearch = (e) => setSearchTerm(e.target.value)

  const filteredGallery = gallery.filter((item) => {
    const matchesSearch =
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesCategory =
      activeCategory === 'all' || item.category === activeCategory

    return matchesSearch && matchesCategory
  })

  const filtered = filteredGallery

  return (
    <div className="dune-explorer">
      <div className="dune-explorer-header">
        <Mountain className="dune-explorer-icon" />
        <span>Dune Explorer</span>
      </div>

      <div className="dune-explorer-toolbar">
        <div className="toolbar-search">
          <Search size={18} aria-hidden="true" />
          <input
            type="text"
            placeholder="Buscar dunas..."
            value={searchTerm}
            onChange={handleSearch}
            aria-label="Buscar en explorador de dunas"
          />
        </div>

        <div className="toolbar-category">
          <select
            onChange={(e) => setActiveCategory(e.target.value)}
            aria-label="Filtrar por tipo de duna"
          >
            <option value="all">Todos los tipos</option>
            {marsCategories.filter((c) => c.id.startsWith('barchan') || c.id.startsWith('linear') || c.id.startsWith('transverse') || c.id.startsWith('polar')).map((cat) => (
              <option key={cat.id} value={cat.id}>
                {categoryNames[cat.id]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="dune-explorer-grid">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <Search size={48} aria-hidden="true" />
            <p>No se encontraron dunas con los filtros aplicados</p>
          </div>
        ) : (
          filtered.map((item) => (
            <div
              key={item.id}
              className="dune-card"
              onClick={() => setSelectedImage(item.id)}
            >
              <img
                src={item.imageUrl}
                alt={item.title}
                loading="lazy"
                onError={({ target }) => {
                  target.onError = null
                  target.src =
                    'https://images-assets.nasa.gov/image/PIA28472/PIA28472~orig.jpg'
                }}
              />
              <div className="dune-card-overlay">
                <span className="dune-category" style={{ color: marsCategories.find(category => category.id === item.category)?.color || 'var(--accent)' }}>
                  {categoryNames[item.category] || 'Unclassified'}
                </span>
                <h4 className="dune-card-title">{item.title}</h4>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Expanded view */}
      {selectedImage && (
        <div className="image-expander">
          <div className="expander-header">
            <Eye size={24} aria-hidden="true" />
            <span>Duna: {filtered.find((i) => i.id === selectedImage)?.title}</span>
            <button
              onClick={() => setSelectedImage(null)}
              className="expander-close"
              aria-label="Cerrar vista"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div className="expander-image">
            <img
              src={filtered.find((i) => i.id === selectedImage)?.imageUrl}
              alt={selectedImage}
              loading="lazy"
            />
          </div>

          <div className="expander-details">
            <div className="detail-row">
              <span className="detail-label">Tipo</span>
              <span className="detail-value">
                {categoryNames[
                  gallery.find((i) => i.id === selectedImage)?.category
                ]}
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Ubicación</span>
              <span className="detail-value">
                {filtered.find((i) => i.id === selectedImage)?.location}
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Crédito</span>
              <span className="detail-value">
                {filtered.find((i) => i.id === selectedImage)?.credit}
              </span>
            </div>
            <a
              className="expander-original"
              href={filtered.find((i) => i.id === selectedImage)?.originalUrl}
              target="_blank"
              rel="noreferrer"
            >
              Ver imagen original en NASA
            </a>
          </div>
        </div>
      )}
    </div>
  )
}