import { useRef, useState } from 'react'

const MODES = [
  { key: 'texto',  label: 'Texto' },
  { key: 'url',    label: 'URL' },
  { key: 'imagen', label: 'Imagen' },
]

const ANALYZE_LABEL = {
  texto:  'Analizar mensaje',
  url:    'Analizar URL',
  imagen: 'Analizar imagen',
}

export default function MessageInput({
  message, onChange, onAnalyze, loading,
  imageFile, onImageSelect,
  urlInput, onUrlChange,
  inputMode, onModeChange,
}) {
  const fileInputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  const isEmpty =
    inputMode === 'texto'  ? !message.trim() :
    inputMode === 'url'    ? !urlInput.trim() :
    /* imagen */             !imageFile

  function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (file) onImageSelect(file)
  }

  function handleRemoveImage() {
    onImageSelect(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleDragOver(e) {
    e.preventDefault()
    if (!isDragging) setIsDragging(true)
  }

  function handleDragLeave(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) setIsDragging(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      onModeChange('imagen')
      onImageSelect(file)
    }
  }

  return (
    <div
      className={`flex flex-col gap-3 relative rounded-xl transition-colors
        ${isDragging ? 'outline outline-2 outline-blue-500 outline-offset-2' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="absolute inset-0 z-10 rounded-xl bg-blue-500/10 border-2 border-dashed border-blue-500
                        flex items-center justify-center pointer-events-none">
          <span className="text-blue-400 text-sm font-medium">Suelta la imagen aquí</span>
        </div>
      )}
      {/* Tabs */}
      <div className="flex rounded-xl overflow-hidden border border-slate-700 text-xs font-medium">
        {MODES.map(m => (
          <button
            key={m.key}
            type="button"
            onClick={() => onModeChange(m.key)}
            className={`flex-1 py-2 transition-colors
              ${inputMode === m.key
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:bg-slate-700/50'}`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Input area by mode */}
      {inputMode === 'texto' && (
        <textarea
          value={message}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Email, SMS, WhatsApp... Copia y pega el contenido completo del mensaje que quieres analizar."
          rows={6}
          className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100
                     placeholder-slate-500 p-4 text-sm resize-none
                     focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                     transition-colors"
        />
      )}

      {inputMode === 'url' && (
        <input
          type="url"
          value={urlInput}
          onChange={(e) => onUrlChange(e.target.value)}
          placeholder="https://ejemplo.com/link-sospechoso"
          className="w-full rounded-xl bg-slate-800 border border-slate-700 text-slate-100
                     placeholder-slate-500 px-4 py-3 text-sm
                     focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                     transition-colors"
        />
      )}

      {inputMode === 'imagen' && (
        imageFile ? (
          <div className="relative rounded-xl border border-slate-600 overflow-hidden bg-slate-800">
            <img
              src={URL.createObjectURL(imageFile)}
              alt="Vista previa"
              className="w-full max-h-64 object-contain"
            />
            <button
              onClick={handleRemoveImage}
              className="absolute top-2 right-2 bg-slate-900/80 text-slate-300 hover:text-white
                         text-xs px-2 py-1 rounded-lg border border-slate-600"
            >
              Quitar
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 w-full py-8 rounded-xl text-xs
                       text-slate-400 hover:text-slate-200 border border-dashed border-slate-600
                       hover:border-slate-400 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            Sube o arrastra una captura de pantalla
          </button>
        )
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      <button
        onClick={onAnalyze}
        disabled={isEmpty || loading}
        className="w-full py-3 rounded-xl font-semibold text-white text-sm uppercase tracking-wider
                   bg-blue-600 hover:bg-blue-500 active:bg-blue-700
                   disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed
                   transition-colors"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Analizando...
          </span>
        ) : ANALYZE_LABEL[inputMode]}
      </button>
    </div>
  )
}
