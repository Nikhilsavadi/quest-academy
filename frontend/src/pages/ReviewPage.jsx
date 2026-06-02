// Standalone review page — linked from the "Recent Quests" history strip on
// home so the child can revisit any past session's wrong answers without
// replaying the quest. Backed by /api/child/session/:id/review.

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { childApi } from '../api.js'
import SVGQuestion from '../components/SVGQuestion.jsx'

export default function ReviewPage() {
  const { id } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState(null)

  useEffect(() => {
    childApi.review(id).then(setData).catch(() => setData({ error: true }))
  }, [id])

  if (!data) return <div className="p-6 text-center">Loading…</div>
  if (data.error) {
    return (
      <div className="p-6 text-center">
        Could not load review.{' '}
        <button onClick={() => nav('/home')} className="underline">Home</button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4">
      <div className="max-w-md mx-auto">
        <header className="flex items-center justify-between mb-4">
          <button onClick={() => nav('/home')} className="text-violet-700 font-semibold">← Home</button>
          <h2 className="font-bold">
            Review · {data.session_topic}
          </h2>
          <span className="text-sm text-slate-500">
            {data.wrong.length} miss{data.wrong.length === 1 ? '' : 'es'}
          </span>
        </header>
        {data.wrong.length === 0 && (
          <div className="card text-center">
            <p className="text-3xl mb-2">🎯</p>
            <p className="font-bold">No misses on this quest — you nailed it!</p>
          </div>
        )}
        {data.wrong.map((q, i) => (
          <div key={q.question_id} className="card mb-3">
            <p className="text-xs text-slate-500 mb-1">Q{i + 1} · {q.topic}</p>
            <p className="font-semibold mb-3">{q.question_text}</p>
            {q.svg_content && <SVGQuestion svg={q.svg_content} />}
            <div className="space-y-2 mb-3">
              {q.options.map((opt, idx) => {
                const isCorrect = idx === q.correct_index
                const isPicked = idx === q.picked_index
                let cls = 'border-slate-200 bg-white'
                if (isCorrect) cls = 'border-emerald-400 bg-emerald-50'
                else if (isPicked) cls = 'border-rose-400 bg-rose-50'
                return (
                  <div key={idx} className={`border-2 rounded-lg p-2 text-sm flex justify-between ${cls}`}>
                    <span>{opt}</span>
                    {isCorrect && <span className="text-emerald-700 font-bold">✓ correct</span>}
                    {isPicked && !isCorrect && <span className="text-rose-700 font-bold">your pick</span>}
                  </div>
                )
              })}
            </div>
            {q.explanation && (
              <div className="text-xs bg-amber-50 border border-amber-200 rounded p-2 text-amber-900">
                💡 {q.explanation}
              </div>
            )}
          </div>
        ))}
        <button onClick={() => nav('/home')} className="btn btn-primary w-full">Done reviewing</button>
      </div>
    </div>
  )
}
