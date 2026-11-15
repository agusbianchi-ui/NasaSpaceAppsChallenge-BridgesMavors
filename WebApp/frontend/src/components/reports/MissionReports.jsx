import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'

export default function MissionReports() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setTimeout(() => {
      setReports([])
      setLoading(false)
    }, 2000)
  }, [])

  return (
    <div className="mission-reports">
      <div className="mission-reports-header">
        <FileText className="mission-reports-icon" />
        <span>Informes Científicos</span>
      </div>

      <div className="mission-reports-content">
        {loading ? (
          <p>Cargando informes...</p>
        ) : reports.length === 0 ? (
          <p>No hay informes guardados</p>
        ) : (
          <ul>
            {reports.map((report) => (
              <li key={report.id} className="report-item">
                <div>
                  <strong>{report.title}</strong>
                  <span className="report-meta">
                    {report.date ? new Date(report.date).toLocaleDateString() : 'Sin fecha'}
                  </span>
                </div>
                <p className="report-dataset">
                  Dataset: {report.dataset || 'Ninguno'}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}