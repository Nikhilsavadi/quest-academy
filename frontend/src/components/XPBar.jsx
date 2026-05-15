export default function XPBar({ xp, next }) {
  let pct = 100, label = `${xp} XP`
  if (next) {
    pct = Math.min(100, Math.round((xp / next.at) * 100))
    label = `${xp} / ${next.at} XP → ${next.name}`
  }
  return (
    <div>
      <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-questPurple to-questAmber transition-all duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
      {next && next.remaining <= 50 && (
        <p className="text-xs text-amber-600 font-semibold animate-pulse">SO CLOSE! {next.remaining} XP to {next.name}</p>
      )}
    </div>
  )
}
