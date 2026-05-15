import { parentApi } from '../api.js'

export default function ProgressionBanner({ suggestions, onAction }) {
  if (!suggestions || !suggestions.length) {
    return (
      <div className="card">
        <h2 className="font-bold mb-2">Progression Suggestions</h2>
        <p className="text-sm text-slate-500">No pending suggestions.</p>
      </div>
    )
  }
  return (
    <div className="card">
      <h2 className="font-bold mb-2">Progression Suggestions</h2>
      <div className="space-y-2">
        {suggestions.map(s => (
          <div key={s.id} className="flex items-center justify-between bg-amber-50 rounded-lg p-2 text-sm">
            <span>⬆️ Move <b>{s.subject}: {s.topic}</b> from <i>{s.from}</i> to <b>{s.to}</b></span>
            <div className="flex gap-1">
              <button onClick={() => parentApi.approve(s.id).then(onAction)} className="btn btn-success text-xs py-1 px-2">Approve</button>
              <button onClick={() => parentApi.dismiss(s.id).then(onAction)} className="btn btn-secondary text-xs py-1 px-2">Dismiss</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
