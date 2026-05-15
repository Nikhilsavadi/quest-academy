export default function StreakCounter({ streak }) {
  const pulse = streak >= 7
  return (
    <div className={`text-right ${pulse ? 'animate-pulse-streak' : ''}`}>
      <p className="text-2xl">🔥 {streak}</p>
      <p className="text-xs text-slate-500">day streak</p>
    </div>
  )
}
