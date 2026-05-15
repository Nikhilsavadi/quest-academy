const ICONS = {
  bronze_badge: '🥉',
  silver_cape: '🦸',
  trophy: '🏆',
  diamond: '💎',
  gold_crown: '👑',
}

export default function AvatarDisplay({ items = [] }) {
  return (
    <div className="relative w-14 h-14 rounded-full bg-gradient-to-br from-violet-200 to-amber-100 border-2 border-white shadow flex items-center justify-center">
      <span className="text-2xl">🧑‍🎓</span>
      {items.length > 0 && (
        <div className="absolute -bottom-1 -right-1 text-lg">
          {items.map(i => ICONS[i]).filter(Boolean).slice(0, 1).join('')}
        </div>
      )}
    </div>
  )
}
