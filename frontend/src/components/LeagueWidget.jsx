export default function LeagueWidget({ rival }) {
  if (!rival || !rival.leaderboard) return null
  const board = rival.leaderboard
  const hint = rival.action_hint

  return (
    <div className="card mb-3 bg-slate-900 text-white">
      <p className="text-xs uppercase tracking-wide text-slate-400 mb-2">⚔️ The League</p>
      <div className="space-y-1.5 mb-3">
        {board.map(row => (
          <LeagueRow key={row.name} row={row} />
        ))}
      </div>
      {hint && (
        <div className="bg-slate-800 rounded-lg p-2 border border-slate-700">
          <p className="font-bold text-amber-300 text-sm">{hint.headline}</p>
          <p className="text-sm text-slate-100 mt-0.5">{hint.action}</p>
          {hint.why && <p className="text-xs text-slate-400 mt-1">{hint.why}</p>}
        </div>
      )}
    </div>
  )
}

function LeagueRow({ row }) {
  const isYou = row.is_child
  const medal = row.rank === 1 ? '🥇' : row.rank === 2 ? '🥈' : row.rank === 3 ? '🥉' : ` #${row.rank}`
  const rowCls = isYou
    ? 'bg-violet-700/40 border border-violet-400'
    : 'bg-slate-800/60'
  return (
    <div className={`flex items-center justify-between rounded-lg px-2 py-1.5 ${rowCls}`}>
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-base w-7 text-center">{medal}</span>
        <span className="text-xl">{row.avatar}</span>
        <span className={`truncate ${isYou ? 'font-bold' : ''}`}>
          {isYou ? 'YOU' : row.name}
        </span>
        {row.surge_active && <span className="text-xs text-amber-300">🔥 surge</span>}
      </div>
      <span className="font-mono text-sm font-bold">{row.xp.toLocaleString()} XP</span>
    </div>
  )
}
