const COLORS = ['#7c3aed','#f59e0b','#10b981','#ef4444','#3b82f6','#ec4899']
export default function Confetti() {
  const pieces = Array.from({length: 20}, (_, i) => i)
  return (
    <div className="pointer-events-none fixed inset-0 z-40">
      {pieces.map(i => {
        const left = Math.random() * 100
        const delay = Math.random() * 0.5
        const color = COLORS[i % COLORS.length]
        return (
          <span
            key={i}
            className="confetti-piece animate-confetti"
            style={{
              left: `${left}%`,
              backgroundColor: color,
              animationDelay: `${delay}s`,
              animationDuration: `${1.2 + Math.random()}s`,
            }}
          />
        )
      })}
    </div>
  )
}
