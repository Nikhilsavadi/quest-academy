export default function DailyQuestCard({ quest, onStart }) {
  if (!quest) {
    return (
      <div className="card mb-3">
        <p className="font-bold">⏳ No quest today</p>
        <p className="text-sm text-slate-500">Come back tomorrow.</p>
      </div>
    )
  }
  if (quest.status === 'rest_day') {
    return (
      <div className="card mb-3 bg-blue-50">
        <p className="font-bold">🌴 Rest Day</p>
        <p className="text-sm text-slate-600">Streak preserved. Come back tomorrow!</p>
      </div>
    )
  }
  if (quest.status === 'completed') {
    return (
      <div className="card mb-3 bg-green-50">
        <p className="font-bold">✅ Daily Quest done</p>
        <p className="text-sm text-slate-600">Score {quest.score}/{quest.total} · +{quest.xp_awarded} XP</p>
      </div>
    )
  }
  return (
    <div className="card mb-3 bg-gradient-to-br from-amber-100 to-yellow-50 border-2 border-amber-300">
      <p className="font-bold text-lg">🟡 Today's Quest — {quest.subject}</p>
      <p className="text-sm text-slate-600 mb-3">{quest.total || 20} questions · keep your streak going!</p>
      <button onClick={() => onStart(quest.id)} className="btn btn-primary w-full text-lg animate-pulse">
        ⚔️ START
      </button>
    </div>
  )
}
