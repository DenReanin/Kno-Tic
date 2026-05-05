import { useState, useRef } from 'react'

const SCORE_COLOR = (score) => {
  if (score < 30) return 'text-blue-400'
  if (score < 60) return 'text-amber-400'
  if (score < 80) return 'text-orange-400'
  return 'text-red-400'
}

const CATEGORY_COLOR = {
  seguro:     'bg-blue-500/20 text-blue-300',
  sospechoso: 'bg-amber-500/20 text-amber-300',
  phishing:   'bg-orange-500/20 text-orange-300',
  smishing:   'bg-red-500/20 text-red-300',
  fraude:     'bg-red-500/20 text-red-300',
}

function getAnalysisType(content) {
  if (content.startsWith('[Imagen:')) return 'IMG'
  if (/^https?:\/\//.test(content))   return 'URL'
  return 'TXT'
}

function formatPreview(content) {
  if (content.startsWith('[Imagen:')) return 'Captura de pantalla'
  return content.length > 60 ? content.slice(0, 60) + '...' : content
}

function formatDate(isoString) {
  const d = new Date(isoString)
  return d.toLocaleDateString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

const TYPE_STYLE = {
  TXT: 'bg-slate-600/40 text-slate-400',
  URL: 'bg-blue-500/20 text-blue-400',
  IMG: 'bg-purple-500/20 text-purple-400',
}

function EyeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  )
}

export default function HistoryPanel({ items, onClose, onView, onRefetch }) {
  const [search, setSearch]                   = useState('')
  const [categoryFilter, setCategoryFilter]   = useState('')
  const debounceRef                           = useRef(null)

  function handleSearchChange(e) {
    const val = e.target.value
    setSearch(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => onRefetch(val, categoryFilter), 300)
  }

  function handleCategoryChange(e) {
    const val = e.target.value
    setCategoryFilter(val)
    onRefetch(search, val)
  }

  if (!items || items.length === 0) {
    return (
      <div className="bg-slate-800/60 border border-slate-700 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
            Historial de análisis
          </h2>
          <button onClick={onClose} className="text-xs text-slate-500 hover:text-slate-200 transition-colors">
            Cerrar
          </button>
        </div>
        <div className="flex gap-2 px-6 py-3 border-b border-slate-700/50">
          <input
            type="text" value={search} onChange={handleSearchChange}
            placeholder="Buscar en historial..."
            className="flex-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-100
                       placeholder-slate-500 px-3 py-2 text-xs
                       focus:outline-none focus:border-blue-500 transition-colors"
          />
          <select value={categoryFilter} onChange={handleCategoryChange}
            className="rounded-lg bg-slate-800 border border-slate-700 text-slate-400
                       px-3 py-2 text-xs focus:outline-none focus:border-blue-500 transition-colors">
            <option value="">Todas</option>
            <option value="seguro">Seguro</option>
            <option value="sospechoso">Sospechoso</option>
            <option value="phishing">Phishing</option>
            <option value="smishing">Smishing</option>
            <option value="fraude">Fraude</option>
          </select>
        </div>
        <div className="p-6 text-center">
          <p className="text-slate-500 text-sm">No se encontraron análisis.</p>
          <button onClick={onClose} className="mt-4 text-xs text-slate-400 hover:text-slate-200 underline">
            Cerrar historial
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-2xl overflow-hidden">
      {/* Cabecera del panel */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
          Historial de análisis
        </h2>
        <button
          onClick={onClose}
          className="text-xs text-slate-500 hover:text-slate-200 transition-colors"
        >
          Cerrar
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-2 px-6 py-3 border-b border-slate-700/50">
        <input
          type="text" value={search} onChange={handleSearchChange}
          placeholder="Buscar en historial..."
          className="flex-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-100
                     placeholder-slate-500 px-3 py-2 text-xs
                     focus:outline-none focus:border-blue-500 transition-colors"
        />
        <select value={categoryFilter} onChange={handleCategoryChange}
          className="rounded-lg bg-slate-800 border border-slate-700 text-slate-400
                     px-3 py-2 text-xs focus:outline-none focus:border-blue-500 transition-colors">
          <option value="">Todas</option>
          <option value="seguro">Seguro</option>
          <option value="sospechoso">Sospechoso</option>
          <option value="phishing">Phishing</option>
          <option value="smishing">Smishing</option>
          <option value="fraude">Fraude</option>
        </select>
      </div>

      {/* Lista */}
      <ul className="divide-y divide-slate-700/50">
        {items.map((item) => (
          <li key={item.id} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-700/30 transition-colors">

            {/* Puntuación */}
            <span className={`text-2xl font-bold tabular-nums w-12 shrink-0 ${SCORE_COLOR(item.risk_score)}`}>
              {item.risk_score}
            </span>

            {/* Categoría + tipo + preview */}
            <div className="flex flex-col gap-1 min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded-full self-start ${CATEGORY_COLOR[item.category] || CATEGORY_COLOR.sospechoso}`}>
                  {item.category}
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${TYPE_STYLE[getAnalysisType(item.full_content)]}`}>
                  {getAnalysisType(item.full_content)}
                </span>
                {item.feedback && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold
                    ${item.feedback === 'correcto'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'}`}>
                    {item.feedback === 'correcto' ? '✓' : '✗'}
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-400 truncate">{formatPreview(item.full_content)}</p>
            </div>

            {/* Fecha + botón ver */}
            <div className="flex flex-col items-end gap-2 shrink-0">
              <span className="text-xs text-slate-600">
                {formatDate(item.date)}
              </span>
              <button
                onClick={() => onView(item)}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-blue-400
                           border border-slate-700 hover:border-blue-500/50
                           px-2 py-1 rounded-lg transition-colors"
              >
                <EyeIcon />
                Ver
              </button>
            </div>

          </li>
        ))}
      </ul>
    </div>
  )
}
