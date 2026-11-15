import { useState, useRef } from 'react'
import {
  Microscope,
  Search,
  Image,
} from 'lucide-react'
import { cvLabImages } from '../../data/marsVisualData.js'

export default function ComputerVisionLab() {
  const images = cvLabImages
  const [activeImg, setActiveImg] = useState(null)
  const [showProcessing, setShowProcessing] = useState(false)
  const [processingImg] = useState(null)
  const fileInputRef = useRef(null)


  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        setActiveImg({
          id: 'uploaded',
          title: file.name,
          originalImage: e.target.result,
          processedImage: '',
          processingDescription: 'Imagen cargada del usuario - procesamiento demo',
          parameters: {
            operation: 'Carga de archivo local',
            model: 'N/A - demostración client-side',
          },
        })
        setShowProcessing(true)
      }
      reader.readAsDataURL(file)
    }
  }

  return (
    <div className="computer-vision-lab">
      <div className="cv-lab-header">
        <Microscope className="cv-lab-header-icon" />
        <span>Computer Vision Lab</span>
      </div>

      <div className="cv-lab-toolbar">
        <Search size={18} aria-hidden="true" />
        <span className="toolbar-label">Análisis visual de imágenes de Marte</span>

        <div className="file-upload-btn">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept="image/*"
            style={{ display: 'none' }}
            aria-label="Cargar imagen para análisis visual"
          />
          <button className="upload-btn" aria-label="Cargar imagen">
            <Image size={16} aria-hidden="true" /> Cargar imagen
          </button>
        </div>
      </div>

      <div className="cv-lab-images">
        {images.map((img) => (
          <div
            key={img.id}
            className="cv-lab-image-card"
            onClick={() => setActiveImg(img)}
          >
            <h4>{img.title}</h4>
            <p>{img.description}</p>
            <button
              onClick={(e) => e.stopPropagation()}
              className="cv-analyze-btn"
              aria-label="Analizar imagen"
            >
              Analizar
            </button>
          </div>
        ))}
      </div>

      {/* Selected image details */}
      {activeImg && (
        <div className="cv-image-details">
          <h4>{activeImg.title}</h4>
          <p>{activeImg.description}</p>
          <div className="cv-parameters">
            <strong>Parámetros del análisis:</strong>
            <ul>
              {activeImg.parameters && Object.entries(activeImg.parameters).map(
                ([key, value]) => <li key={key}>{key}: {value}</li>
              )}
            </ul>
          </div>
          <a
            className="cv-original-link"
            href={activeImg.originalImage}
            target="_blank"
            rel="noreferrer"
          >
            Ver imagen original en NASA
          </a>
          <button
            onClick={() => setActiveImg(null)}
            className="cv-close-details"
            aria-label="Cerrar detalles"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Processing preview */}
      {showProcessing && processingImg && (
        <div className="processing-preview">
          <h4>{processingImg.title} - Procesamiento client-side</h4>
          <p>{processingImg.processingDescription || 'Procesamiento visual demo'}</p>
          <p><strong>Parámetros:</strong> {JSON.stringify(processingImg.parameters)}</p>
          <div className="processing-images">
            <div className="processing-panel">
              <Original originalImg={processingImg.originalImage} />
              <Processed processedImg={processingImg.processedImage} />
            </div>
            <div className="processing-params">
              <p>Operación: {processingImg.parameters.operation}</p>
              <p>Modelo: {processingImg.parameters.model}</p>
            </div>
          </div>
          <button
            onClick={() => setShowProcessing(false)}
            className="close-processing"
            aria-label="Cerrar preview"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Uploaded image processing preview */}
      {activeImg && activeImg.id === 'uploaded' && showProcessing && (
        <div className="upload-processing-preview">
          <h4>Imagen Cargada - Procesamiento Demo</h4>
          <p>Procesamiento client-side en el navegador</p>
          <Original originalImg={activeImg.originalImage} />
          <Processed processedImg={activeImg.processedImage} />
          <div className="processing-params">
            <p>Operación: {activeImg.parameters.operation}</p>
            <p>Modelo: {activeImg.parameters.model}</p>
          </div>
          <button
            onClick={() => setShowProcessing(false)}
            className="close-processing"
            aria-label="Cerrar preview"
          >
            Cerrar
          </button>
        </div>
      )}
    </div>
  )
}

function Original({ originalImg }) {
  return <img src={originalImg} alt="Original" className="processing-original" loading="lazy" />
}

function Processed({ processedImg }) {
  if (!processedImg) {
    return <p className="no-processed">No hay imagen procesada aún - el procesamiento ocurre client-side</p>
  }
  return <img src={processedImg} alt="Procesado" className="processing-processed" loading="lazy" />
}