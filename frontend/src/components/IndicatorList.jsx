import { useState } from 'react'

const ICONS = {
  urgencia:        { color: 'text-amber-400 bg-amber-400/10 border-amber-400/20' },
  autoridad:       { color: 'text-purple-400 bg-purple-400/10 border-purple-400/20' },
  miedo:           { color: 'text-orange-400 bg-orange-400/10 border-orange-400/20' },
  suplantacion:    { color: 'text-red-400 bg-red-400/10 border-red-400/20' },
  datos_personales:{ color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20' },
  enlace:          { color: 'text-blue-400 bg-blue-400/10 border-blue-400/20' },
  otro:            { color: 'text-slate-400 bg-slate-400/10 border-slate-400/20' },
}

export default function IndicatorList({ indicators, summary, onLearn }) {
  const [learnState, setLearnState] = useState({ index: null, loading: false, explanation: null })

  async function handleLearn(index, ind) {
    if (!onLearn) return
    setLearnState({ index, loading: true, explanation: null })
    try {
      const explanation = await onLearn(ind.type, ind.description)
      setLearnState({ index, loading: false, explanation })
    } catch {
      setLearnState({ index, loading: false, explanation: 'No se pudo cargar la explicación.' })
    }
  }

  if (!indicators || indicators.length === 0) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
        <p className="text-green-400 text-sm">{summary || 'No se detectaron señales de alerta.'}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
        Señales detectadas
      </h3>
      <div className="flex flex-col gap-2">
        {indicators.map((ind, i) => {
          const style = ICONS[ind.type] || ICONS.otro
          return (
            <div
              key={i}
              className={`flex items-start gap-3 p-4 rounded-xl border ${style.color}`}
            >
              <div className="flex flex-col gap-1 flex-1">
                <span className="text-sm font-bold uppercase tracking-wide opacity-80">
                  {ind.type.replace('_', ' ')}
                </span>
                <span className="text-sm opacity-90">{ind.description}</span>
                {onLearn && (
                  <button
                    onClick={() => handleLearn(i, ind)}
                    disabled={learnState.loading}
                    className="mt-1 text-xs text-blue-400 hover:text-blue-300 self-start
                               disabled:text-slate-600 disabled:cursor-not-allowed transition-colors"
                  >
                    {learnState.loading && learnState.index === i ? 'Cargando...' : 'Aprender más'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Panel de formación */}
      {learnState.explanation && (
        <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-blue-400 uppercase tracking-wide">
              Aprender más
              {learnState.index !== null && indicators[learnState.index]
                ? ` · ${indicators[learnState.index].type.replace('_', ' ')}`
                : ''}
            </span>
            <button
              onClick={() => setLearnState({ index: null, loading: false, explanation: null })}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              Cerrar
            </button>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
            {learnState.explanation}
          </p>
        </div>
      )}

      {summary && (
        <p className="text-sm text-slate-400 italic border-t border-slate-700 pt-3 mt-1">
          {summary}
        </p>
      )}
    </div>
  )
}
