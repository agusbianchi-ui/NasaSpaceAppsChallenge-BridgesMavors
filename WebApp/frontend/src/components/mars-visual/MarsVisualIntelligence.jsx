import { Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { marsCategories, marsImageGallery } from '../../data/marsVisualData.js'

export default function MarsVisualIntelligence() {
  const gallery = marsImageGallery

  const categoryMap = {
    barchan: 'Barchan Dunes',
    linear: 'Linear Dunes',
    transverse: 'Transverse Dunes',
    polar: 'Polar Dunes',
    craters: 'Craters',
    erosion: 'Surface Erosion',
    terrain: 'Martian Terrain',
  }

  const cards = gallery.map((item) => (
    <div
      key={item.id}
      className="mars-carousel-card"
      style={{
        flex: '0 0 calc(calc(33.333% - 16px))',
        minWidth: 180,
        marginRight: 8,
      }}
    >
      <img
        src={item.imageUrl}
        alt={item.title}
        loading="lazy"
        style={{
          width: '100%',
          height: 170,
          objectFit: 'cover',
          borderRadius: '10px 10px 0 0',
          background: 'linear-gradient(135deg, #1a2230 0%, #0d141f 100%)',
        }}
        onError={({ target }) => {
          target.onError = null
          target.src = 'https://images-assets.nasa.gov/image/PIA12345/PIA12345~orig.jpg'
        }}
      />
      <div className="mars-carousel-card-overlay">
        <span className="mars-carousel-category" style={{ color: item.category?.color || '#FF8C32' }}>
          {item.category ? categoryMap[item.category] : ''}
        </span>
        <h5 className="mars-carousel-title" style={{
          fontSize: '12px',
          margin: '4px 0 0',
          color: '#e8edf4',
          lineHeight: '1.3',
          display: '-webkit-box',
          '-webkit-box-orient': 'vertical',
          '-webkit-line-clamp': 2,
          overflow: 'hidden',
        }}>
          {item.title}
        </h5>
        <p className="mars-carousel-desc" style={{
          fontSize: '10px',
          margin: '4px 0 0',
          color: '#6b7c93',
          lineHeight: '1.3',
          display: '-webkit-box',
          '-webkit-box-orient': 'vertical',
          '-webkit-line-clamp': 2,
          overflow: 'hidden',
        }}>
          {item.description}
        </p>
        <div style={{ fontSize: '9px', color: '#94a3b8', margin: '2px 0 0' }}>
          NASA/JPL-Caltech/University of Arizona
        </div>
      </div>
    </div>
  ))

  return (
    <div className="mars-visual-intelligence">
      <div className="mars-visual-intelligence-header">
        <span>Mars Visual Intelligence</span>
      </div>

      <div className="mars-visual-intelligence-toolbar">
        <div className="toolbar-search">
          <Search size={16} aria-hidden="true" />
          <input
            type="text"
            placeholder="Buscar"
          />
        </div>

        <div className="toolbar-category">
          <select>
            <option value="all">Todas</option>
            {marsCategories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mars-visual-intelligence-content">
        <h2 className="section-subtitle">Imágenes de Marte</h2>
        
        <div className="mars-carousel-container">
          <button
            className="mars-carousel-arrow left"
            aria-label="Imágenes anteriores"
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </button>

          <div className="mars-carousel-inner" style={{ overflow: 'auto', scrollbarWidth: 'none', '-ms-overflow-style': 'none' }}>
            {cards}
          </div>

          <button
            className="mars-carousel-arrow right"
            aria-label="Siguientes imágenes"
          >
            <ChevronRight size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="mars-carousel-count">
          {gallery.length} imágenes
        </div>
      </div>
    </div>
  )
}