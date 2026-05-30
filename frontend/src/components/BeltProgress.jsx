const BELT_ICONS = ['🎓', '🥉', '🥈', '🥇', '💎', '🏆', '💠', '🌟', '🐉']

export default function BeltProgress({ belt }) {
  if (!belt) return null
  const checklist = belt.checklist || []
  const met = checklist.filter(c => c.met).length
  const total = checklist.length
  const glow = belt.exam_unlocked
  return (
    <div className={`card mb-3 ${glow ? 'border-2 border-yellow-400 animate-pulse' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-xs uppercase text-slate-500">Belt</p>
          <p className="font-bold text-base">
            {BELT_ICONS[belt.current]} {belt.current_name}
            {belt.next_name && <span className="text-slate-400"> → {belt.next_name}</span>}
          </p>
        </div>
        {total > 0 && (
          <div className="text-right">
            <p className="text-xs text-slate-500">Gate</p>
            <p className="font-bold">{met}/{total}</p>
          </div>
        )}
      </div>
      {total > 0 && (
        <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber-400 to-yellow-500 transition-all duration-700"
            style={{ width: `${(met/total)*100}%` }}
          />
        </div>
      )}
      {total > 0 && (
        <ul className="mt-3 space-y-1.5">
          {checklist.map((item, i) => (
            <ChecklistRow key={i} item={item} />
          ))}
        </ul>
      )}
      {glow && <p className="text-xs text-amber-700 font-bold mt-2">⚔️ Belt Exam Ready!</p>}
    </div>
  )
}

function ChecklistRow({ item }) {
  const label = item.label || item.subject || 'Goal'
  const progress = formatProgress(item)
  return (
    <li className="flex items-start justify-between gap-2 text-sm">
      <span className="flex items-start gap-1.5 min-w-0">
        <span className="shrink-0">{item.met ? '✅' : '⬜'}</span>
        <span className={item.met ? 'text-slate-500 line-through' : 'text-slate-800'}>
          {label}
        </span>
      </span>
      {progress && (
        <span className={`shrink-0 font-mono text-xs ${item.met ? 'text-emerald-600' : 'text-slate-500'}`}>
          {progress}
        </span>
      )}
    </li>
  )
}

function formatProgress(item) {
  if (item.have != null && item.needed != null) return `${item.have} / ${item.needed}`
  if (item.value != null) return String(item.value)
  return null
}
