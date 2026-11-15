import { useState } from 'react'
import { API_BASE_URL } from '../../services/marsApi.js'
import { Bot as AiAssistant } from 'lucide-react'

export default function AIAssistant() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const baseUrl = API_BASE_URL

  const sendMessage = async () => {
    if (!input.trim()) return
    setLoading(true)
    setMessages(prev => [...prev, { role: 'user', content: input }])
    setInput('')

    try {
      const response = await fetch(`${baseUrl}/api/v1/ai/assistant`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${errorData.detail || 'Error en la consulta'}` }])
        return
      }

      const data = await response.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: `No se pudo conectar con el asistente en ${baseUrl}. Verifique que el backend esté corriendo.` }])
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <div className="ai-assistant">
      <div className="ai-assistant-header">
        <AiAssistant className="ai-assistant-icon" />
        <span>Asistente Científico Mars Ops</span>
        <button
          className="ai-assistant-close"
          onClick={clearChat}
          title="Limpiar conversación"
        />
      </div>

      <div className="ai-assistant-messages" role="region" aria-label="Conversación con asistente científico">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`ai-message ai-message-${msg.role}`}
            style={{ animation: `fadeIn 0.3s ease ${idx * 0.05}s` }}
          >
            <div className="ai-message-avatar">
              {msg.role === 'user' ? 'U' : 'A'}
            </div>
            <div className="ai-message-content">
              <p className="ai-message-text">{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="ai-message ai-message-assistant">
            <div className="ai-message-avatar">A</div>
            <div className="ai-message-content">
              <p className="ai-message-text">Analizando...</p>
            </div>
          </div>
        )}
        {messages.length === 0 && (
          <div className="ai-message ai-system">
            <p className="ai-system-text">
              Bienvenido al Asistente Científico Mars Ops. Haga una pregunta sobre el estado de la misión, análisis de dunas, datasets disponibles o hallazgos científicos.
            </p>
          </div>
        )}
      </div>

      <div className="ai-assistant-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escriba su consulta..."
          disabled={loading}
          aria-label="Mensaje para el asistente científico"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          aria-label="Enviar mensaje al asistente"
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
            <line x1="12" y1="1" x2="12" y2="23" />
            <polyline points="19 10 5 21 12 15 23 10" />
          </svg>
        </button>
      </div>
    </div>
  )
}