export default function RivalWidget({ rival }) {
  if (!rival) return null
  const ahead = rival.child_ahead
  const gap = rival.lead_or_deficit
  const trend = rival.trend
  return (
    <div className="card mb-3 bg-slate-900 text-white">
      <p className="text-xs uppercase tracking-wide text-slate-400">⚔️ You vs Max</p>
      <div className="flex justify-between items-baseline mt-1">
        <span>You: <span className="font-bold">{rival.child_xp} XP</span></span>
        <span className={`text-xs font-bold ${ahead ? 'text-green-400' : 'text-red-400'}`}>
          {ahead ? '🟢 AHEAD' : '🔴 BEHIND'}
        </span>
      </div>
      <div className="text-sm text-slate-300">Max: {rival.max_xp} XP</div>
      <div className={`text-sm mt-1 ${ahead ? 'text-green-300' : 'text-red-300'}`}>
        {ahead ? `Lead: +${gap} XP` : `Gap: ${gap} XP`}
      </div>
      <div className="text-xs text-slate-400 mt-1">
        {trend === 'closing' && '📉 closing'}
        {trend === 'widening' && '📈 widening'}
        {trend === 'neutral' && '— steady'}
      </div>
      {rival.surge_active && <p className="text-xs text-yellow-300 mt-1">⚠️ Max is training hard this week…</p>}
    </div>
  )
}
