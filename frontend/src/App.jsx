import { useState } from 'react'
import axios from 'axios'
import { jsPDF } from 'jspdf'
import MessageInput from './components/MessageInput'
import RiskGauge from './components/RiskGauge'
import IndicatorList from './components/IndicatorList'
import HistoryPanel from './components/HistoryPanel'
import StatsPanel from './components/StatsPanel'

const API = ''

const CATEGORY_BADGE = {
  seguro:      'bg-blue-500/20 text-blue-300 border-blue-500/30',
  sospechoso:  'bg-amber-500/20 text-amber-300 border-amber-500/30',
  phishing:    'bg-orange-500/20 text-orange-300 border-orange-500/30',
  smishing:    'bg-red-500/20 text-red-300 border-red-500/30',
  fraude:      'bg-red-500/20 text-red-300 border-red-500/30',
}

export default function App() {
  const [message, setMessage]                   = useState('')
  const [imageFile, setImageFile]               = useState(null)
  const [urlInput, setUrlInput]                 = useState('')
  const [inputMode, setInputMode]               = useState('texto')
  const [result, setResult]                     = useState(null)
  const [loading, setLoading]                   = useState(false)
  const [error, setError]                       = useState(null)
  const [showHistory, setShowHistory]           = useState(false)
  const [history, setHistory]                   = useState([])
  const [showStats, setShowStats]               = useState(false)
  const [stats, setStats]                       = useState(null)
  const [copied, setCopied]                     = useState(false)
  const [historyModal, setHistoryModal]         = useState(null)
  const [currentAnalysisId, setCurrentAnalysisId] = useState(null)
  const [feedback, setFeedback]                 = useState(null)
  const [feedbackSent, setFeedbackSent]         = useState(false)

  async function handleAnalyze() {
    setLoading(true)
    setError(null)
    setResult(null)
    setCurrentAnalysisId(null)
    setFeedback(null)
    setFeedbackSent(false)
    try {
      let response
      if (inputMode === 'imagen' && imageFile) {
        const formData = new FormData()
        formData.append('file', imageFile)
        response = await axios.post(`${API}/analyze-image`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      } else if (inputMode === 'url') {
        response = await axios.post(`${API}/analyze-url`, { url: urlInput })
      } else {
        response = await axios.post(`${API}/analyze`, { content: message })
      }
      setResult(response.data)
      setCurrentAnalysisId(response.data.analysis_id)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al conectar con el servidor.')
    } finally {
      setLoading(false)
    }
  }

  async function handleFetchHistory(search = '', category = '') {
    const params = new URLSearchParams()
    if (search)   params.set('search', search)
    if (category) params.set('category', category)
    try {
      const response = await axios.get(`${API}/history?${params.toString()}`)
      setHistory(response.data)
    } catch {
      setError('No se pudo cargar el historial.')
    }
  }

  async function handleShowHistory() {
    if (showHistory) { setShowHistory(false); return }
    setShowStats(false)
    await handleFetchHistory()
    setShowHistory(true)
  }

  async function handleShowStats() {
    if (showStats) { setShowStats(false); return }
    setShowHistory(false)
    try {
      const response = await axios.get(`${API}/stats`)
      setStats(response.data)
      setShowStats(true)
    } catch {
      setError('No se pudieron cargar las estadísticas.')
    }
  }

  function handleReset() {
    setMessage('')
    setImageFile(null)
    setUrlInput('')
    setInputMode('texto')
    setResult(null)
    setError(null)
    setShowHistory(false)
    setShowStats(false)
    setCurrentAnalysisId(null)
    setFeedback(null)
    setFeedbackSent(false)
  }

  function handleShare() {
    if (!result) return
    const tactics = result.indicators?.map(i => `• ${i.type}: ${i.description}`).join('\n') || ''
    const text = [
      `Kno-Tic — Análisis de mensaje`,
      `Riesgo: ${result.risk_score}% · ${result.category.toUpperCase()}`,
      tactics ? `\nIndicadores:\n${tactics}` : '',
      `\n${result.summary}`,
      `\n— Analizado con Kno-Tic (Talento Sabadell 2026)`
    ].filter(Boolean).join('\n')

    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function handleExportPDF() {
    if (!result) return
    const doc = new jsPDF()
    const W = doc.internal.pageSize.getWidth()

    function riskColor(score) {
      if (score < 30) return [59, 130, 246]
      if (score < 60) return [245, 158, 11]
      if (score < 80) return [249, 115, 22]
      return [239, 68, 68]
    }

    const color = riskColor(result.risk_score)

    // Cabecera
    doc.setFillColor(30, 30, 40)
    doc.rect(0, 0, W, 28, 'F')
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(16)
    doc.setFont('helvetica', 'bold')
    doc.text('KNO-TIC', 14, 13)
    doc.setFontSize(9)
    doc.setFont('helvetica', 'normal')
    doc.text('Informe de análisis de seguridad', 14, 21)
    doc.setTextColor(180, 180, 180)
    doc.text(new Date().toLocaleString('es-ES'), W - 14, 21, { align: 'right' })

    let y = 42

    // Bloque de riesgo
    doc.setFillColor(...color)
    doc.rect(14, y - 5, 4, 22, 'F')
    doc.setTextColor(30, 30, 40)
    doc.setFontSize(28)
    doc.setFont('helvetica', 'bold')
    doc.text(`${result.risk_score}%`, 24, y + 10)
    doc.setFontSize(11)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(80, 80, 80)
    doc.text(result.category.toUpperCase(), 24, y + 18)

    y += 32

    // Separador
    doc.setDrawColor(220, 220, 220)
    doc.line(14, y, W - 14, y)
    y += 10

    // Indicadores
    if (result.indicators?.length) {
      doc.setFontSize(9)
      doc.setFont('helvetica', 'bold')
      doc.setTextColor(100, 100, 100)
      doc.text('INDICADORES DETECTADOS', 14, y)
      y += 8

      doc.setFont('helvetica', 'normal')
      doc.setTextColor(40, 40, 40)
      result.indicators.forEach(ind => {
        doc.setFont('helvetica', 'bold')
        doc.setFontSize(10)
        doc.text(ind.type.replace('_', ' ').toUpperCase(), 18, y)
        y += 5
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9.5)
        doc.setTextColor(70, 70, 70)
        const lines = doc.splitTextToSize(ind.description, W - 32)
        doc.text(lines, 18, y)
        y += lines.length * 5.5 + 4
      })
      y += 4
    }

    // Separador
    doc.setDrawColor(220, 220, 220)
    doc.line(14, y, W - 14, y)
    y += 10

    // Resumen
    doc.setFontSize(9)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(100, 100, 100)
    doc.text('RESUMEN', 14, y)
    y += 7
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    doc.setTextColor(40, 40, 40)
    const summaryLines = doc.splitTextToSize(result.summary, W - 28)
    doc.text(summaryLines, 14, y)
    y += summaryLines.length * 5.5 + 16

    // Footer
    doc.setDrawColor(220, 220, 220)
    doc.line(14, y, W - 14, y)
    y += 6
    doc.setFontSize(8)
    doc.setTextColor(160, 160, 160)
    doc.text('Analizado por Kno-Tic', 14, y)

    doc.save('kno-tic-informe.pdf')
  }

  async function handleFeedback(value) {
    if (!currentAnalysisId || feedbackSent) return
    try {
      await axios.patch(`${API}/feedback/${currentAnalysisId}`, { value })
      setFeedback(value)
      setFeedbackSent(true)
    } catch {
      setError('No se pudo enviar el feedback.')
    }
  }

  async function handleLearn(indicator_type, description) {
    const resp = await axios.post(`${API}/learn`, {
      indicator_type,
      description,
      summary: result?.summary || '',
    })
    return resp.data.explanation
  }

  const panelOpen = showHistory || showStats

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col items-center px-4 py-10">

      {/* Cabecera */}
      <header className="w-full max-w-xl mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Kno<span className="text-blue-400"> - </span>Tic
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">Detector de phishing e ingeniería social</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleShowStats}
            className="text-xs text-slate-400 hover:text-slate-200 border border-slate-700
                       hover:border-slate-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            {showStats ? 'Cerrar' : 'Stats'}
          </button>
          <button
            onClick={handleShowHistory}
            className="text-xs text-slate-400 hover:text-slate-200 border border-slate-700
                       hover:border-slate-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            {showHistory ? 'Cerrar' : 'Historial'}
          </button>
          {result && (
            <button
              onClick={handleReset}
              className="text-xs text-slate-400 hover:text-slate-200 border border-slate-700
                         hover:border-slate-500 px-3 py-1.5 rounded-lg transition-colors"
            >
              Nuevo
            </button>
          )}
        </div>
      </header>

      {/* Tarjeta principal */}
      <main className="w-full max-w-xl flex flex-col gap-6">

        {/* Paneles */}
        {showStats && stats && (
          <StatsPanel stats={stats} onClose={() => setShowStats(false)} />
        )}
        {showHistory && (
          <HistoryPanel
            items={history}
            onClose={() => setShowHistory(false)}
            onView={item => setHistoryModal(item)}
            onRefetch={handleFetchHistory}
          />
        )}

        {/* Input */}
        {!result && !panelOpen && (
          <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6">
            <MessageInput
              message={message}
              onChange={setMessage}
              onAnalyze={handleAnalyze}
              loading={loading}
              imageFile={imageFile}
              onImageSelect={setImageFile}
              urlInput={urlInput}
              onUrlChange={setUrlInput}
              inputMode={inputMode}
              onModeChange={setInputMode}
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Resultado */}
        {result && !panelOpen && (
          <div className="flex flex-col gap-4">

            {/* Gauge + categoría + acciones */}
            <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6 flex flex-col items-center gap-4">
              <RiskGauge score={result.risk_score} />
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${CATEGORY_BADGE[result.category] || CATEGORY_BADGE.sospechoso}`}>
                {result.category}
              </span>

              {/* Acciones: compartir + PDF */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleShare}
                  className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200
                             border border-slate-700 hover:border-slate-500 px-4 py-1.5 rounded-lg transition-colors"
                >
                  {copied ? 'Copiado' : 'Compartir resultado'}
                </button>
                <button
                  onClick={handleExportPDF}
                  className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200
                             border border-slate-700 hover:border-slate-500 px-4 py-1.5 rounded-lg transition-colors"
                >
                  Descargar informe
                </button>
              </div>

              {/* Feedback */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">¿El análisis es correcto?</span>
                <button
                  onClick={() => handleFeedback('correcto')}
                  disabled={feedbackSent}
                  className={`text-xs px-3 py-1 rounded-lg border transition-colors disabled:cursor-not-allowed
                    ${feedback === 'correcto'
                      ? 'bg-green-500/20 text-green-300 border-green-500/30'
                      : 'text-slate-400 border-slate-700 hover:text-slate-200 hover:border-slate-500'}`}
                >
                  Correcto
                </button>
                <button
                  onClick={() => handleFeedback('incorrecto')}
                  disabled={feedbackSent}
                  className={`text-xs px-3 py-1 rounded-lg border transition-colors disabled:cursor-not-allowed
                    ${feedback === 'incorrecto'
                      ? 'bg-red-500/20 text-red-300 border-red-500/30'
                      : 'text-slate-400 border-slate-700 hover:text-slate-200 hover:border-slate-500'}`}
                >
                  Incorrecto
                </button>
                {feedbackSent && (
                  <span className="text-xs text-slate-500">Gracias por tu valoración</span>
                )}
              </div>
            </div>

            {/* Indicadores */}
            <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6">
              <IndicatorList
                indicators={result.indicators}
                summary={result.summary}
                onLearn={handleLearn}
              />
            </div>

            {/* Mensaje / URL analizado */}
            {inputMode === 'texto' && message && (
              <details className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4 text-xs text-slate-500 cursor-pointer">
                <summary className="font-medium text-slate-400 hover:text-slate-200 transition-colors">
                  Ver mensaje analizado
                </summary>
                <p className="mt-3 whitespace-pre-wrap break-words leading-relaxed">
                  {message}
                </p>
              </details>
            )}
            {inputMode === 'url' && urlInput && (
              <details className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4 text-xs text-slate-500 cursor-pointer">
                <summary className="font-medium text-slate-400 hover:text-slate-200 transition-colors">
                  Ver URL analizada
                </summary>
                <p className="mt-3 break-all leading-relaxed">{urlInput}</p>
                {result.final_url && result.final_url !== urlInput && (
                  <p className="mt-1 text-slate-600">URL final: {result.final_url}</p>
                )}
                {result.redirect_chain?.length > 1 && (
                  <p className="mt-1 text-slate-600">{result.redirect_chain.length - 1} redirección(es)</p>
                )}
                {result.suspicious_patterns?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {result.suspicious_patterns.map((p, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20">
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </details>
            )}

          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-12 text-xs text-slate-600">
        Talento Sabadell · 2026 · Den Reanin Gerasimov
      </footer>

      {/* Modal — resultado del historial */}
      {historyModal && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
          onClick={() => setHistoryModal(null)}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-xl max-h-[85vh] overflow-y-auto flex flex-col gap-5 p-6"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Resultado guardado</p>
              <button
                onClick={() => setHistoryModal(null)}
                className="text-slate-400 hover:text-slate-200 text-xl leading-none transition-colors"
              >
                x
              </button>
            </div>

            <div className="flex flex-col items-center gap-3">
              <RiskGauge score={historyModal.result.risk_score} />
              <span className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${CATEGORY_BADGE[historyModal.result.category] || CATEGORY_BADGE.sospechoso}`}>
                {historyModal.result.category}
              </span>
            </div>

            <IndicatorList
              indicators={historyModal.result.indicators}
              summary={historyModal.result.summary}
            />
          </div>
        </div>
      )}

    </div>
  )
}
