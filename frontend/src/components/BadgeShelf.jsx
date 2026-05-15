export default function BadgeShelf({ badges }) {
  const recent = (badges || []).slice(-3)
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-bold text-sm">Badges</h3>
        <span className="text-xs text-slate-500">{badges.length} total</span>
      </div>
      {recent.length === 0 ? (
        <p className="text-sm text-slate-400">Earn your first badge by completing a quest.</p>
      ) : (
        <div className="flex gap-2">
          {recent.map(b => (
            <div key={b.id} className="bg-amber-50 rounded-lg p-2 text-center flex-1">
              <div className="text-2xl">{b.icon}</div>
              <div className="text-xs">{b.name}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
