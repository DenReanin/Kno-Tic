function getColor(score) {
  if (score < 30) return '#3b82f6'  // azul
  if (score < 60) return '#f59e0b'  // amarillo
  if (score < 80) return '#f97316'  // naranja
  return '#ef4444'                   // rojo
}

function getLabel(score) {
  if (score < 30) return 'SEGURO'
  if (score < 60) return 'SOSPECHOSO'
  if (score < 80) return 'PELIGRO'
  return 'PHISHING'
}

export default function RiskGauge({ score }) {
  const color = getColor(score)
  const label = getLabel(score)
  const radius = 54
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference * (1 - score / 100)

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="160" height="160" viewBox="0 0 160 160">
        {/* Pista de fondo */}
        <circle
          cx="80" cy="80" r={radius}
          fill="none" stroke="#334155" strokeWidth="14"
        />
        {/* Arco de progreso */}
        <circle
          cx="80" cy="80" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 80 80)"
          style={{ transition: 'stroke-dashoffset 0.7s ease, stroke 0.7s ease' }}
        />
        {/* Porcentaje */}
        <text
          x="80" y="74"
          textAnchor="middle"
          fontSize="28"
          fontWeight="bold"
          fill={color}
          style={{ transition: 'fill 0.7s ease' }}
        >
          {score}%
        </text>
        {/* Etiqueta */}
        <text
          x="80" y="96"
          textAnchor="middle"
          fontSize="11"
          fontWeight="600"
          fill="#94a3b8"
          letterSpacing="1"
        >
          {label}
        </text>
      </svg>
    </div>
  )
}
