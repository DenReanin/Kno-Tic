const TACTIC_LABELS = {
  urgencia:         'Urgencia',
  autoridad:        'Autoridad',
  miedo:            'Miedo',
  suplantacion:     'Suplantación',
  datos_personales: 'Datos personales',
  enlace:           'Enlace',
  otro:             'Otro',
}

const CATEGORY_STYLE = {
  seguro:      { bar: 'bg-blue-500',   text: 'text-blue-400',   label: 'Seguro' },
  sospechoso:  { bar: 'bg-amber-500',  text: 'text-amber-400',  label: 'Sospechoso' },
  phishing:    { bar: 'bg-orange-500', text: 'text-orange-400', label: 'Phishing' },
  smishing:    { bar: 'bg-red-400',    text: 'text-red-400',    label: 'Smishing' },
  fraude:      { bar: 'bg-red-600',    text: 'text-red-500',    label: 'Fraude' },
}

export default function StatsPanel({ stats, onClose }) {
  const byCategory = stats.by_category || {}
  const total = stats.total || 1

  const categoryOrder = ['seguro', 'sospechoso', 'phishing', 'smishing', 'fraude']
  const categories = categoryOrder.filter(k => byCategory[k])

  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
          Estadísticas
        </h2>
        <button
          onClick={onClose}
          className="text-xs text-slate-500 hover:text-slate-200 transition-colors"
        >
          Cerrar
        </button>
      </div>

      {/* Tres métricas principales */}
      <div className="grid grid-cols-3 gap-3 p-5 pb-3">
        <div className="bg-slate-700/40 rounded-xl p-4 text-center flex flex-col items-center gap-1">
          <p className="text-3xl font-bold text-slate-100">{stats.total}</p>
          <p className="text-xs text-slate-400">Analizados</p>
        </div>
        <div className="bg-slate-700/40 rounded-xl p-4 text-center flex flex-col items-center gap-1">
          <p className="text-3xl font-bold text-red-400">{stats.phishing_percent}%</p>
          <p className="text-xs text-slate-400">Amenazas</p>
        </div>
        <div className="bg-slate-700/40 rounded-xl p-4 text-center flex flex-col items-center gap-1">
          <p className="text-base font-bold text-amber-400 leading-tight text-center break-words">
            {TACTIC_LABELS[stats.top_tactic] || stats.top_tactic || '—'}
          </p>
          <p className="text-xs text-slate-400">Táctica más usada</p>
        </div>
      </div>

      {/* Desglose por categoría */}
      {categories.length > 0 && (
        <div className="px-5 pb-5 flex flex-col gap-2">
          <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold mb-1">
            Desglose
          </p>
          {categories.map(key => {
            const style = CATEGORY_STYLE[key] || { bar: 'bg-slate-500', text: 'text-slate-400', label: key }
            const count = byCategory[key]
            const pct = Math.round((count / total) * 100)
            return (
              <div key={key} className="flex items-center gap-3">
                <span className={`text-xs w-24 shrink-0 ${style.text}`}>{style.label}</span>
                <div className="flex-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${style.bar}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-slate-500 w-8 text-right tabular-nums">{count}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
