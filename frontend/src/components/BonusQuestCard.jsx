export default function BonusQuestCard({ bonus, onStart }) {
  return (
    <div className="card mb-3 bg-violet-50 border border-violet-200">
      <p className="font-bold">⚡ Bonus Quest — {bonus.subject}</p>
      <p className="text-sm text-slate-600 mb-2">
        {bonus.topic} · {bonus.difficulty} · {bonus.questions_count} questions
      </p>
      <button onClick={onStart} className="btn btn-primary w-full">Start Bonus</button>
    </div>
  )
}
