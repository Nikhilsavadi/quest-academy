import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { childApi } from '../api.js'
import { sounds } from '../sounds.js'
import QuestionCard from '../components/QuestionCard.jsx'
import LevelUpModal from '../components/LevelUpModal.jsx'
import BeltExamModal from '../components/BeltExamModal.jsx'
import SVGQuestion from '../components/SVGQuestion.jsx'

export default function Quest() {
  const { id } = useParams()
  const nav = useNavigate()
  const [session, setSession] = useState(null)
  const [idx, setIdx] = useState(0)
  const [sessionXp, setSessionXp] = useState(0)
  const [combo, setCombo] = useState(0)
  const [feedback, setFeedback] = useState(null)
  const [hint, setHint] = useState(null)
  const [hintUsed, setHintUsed] = useState({})
  const [done, setDone] = useState(null)
  const [timeLeft, setTimeLeft] = useState(null)
  const [loadingNext, setLoadingNext] = useState(false)
  const startedAt = useRef(Date.now())
  const questStart = useRef(Date.now())

  useEffect(() => {
    childApi.quest(id).then(s => {
      setSession(s)
      if (s.session_type === 'belt_exam' && s.time_limit_seconds) {
        setTimeLeft(s.time_limit_seconds)
      }
    })
  }, [id])

  // Belt exam countdown
  useEffect(() => {
    if (timeLeft == null) return
    if (timeLeft <= 0) { complete(); return }
    const t = setTimeout(() => setTimeLeft(timeLeft - 1), 1000)
    return () => clearTimeout(t)
  }, [timeLeft])

  if (!session) return <div className="p-6 text-center">Loading...</div>

  const questions = session.questions
  const q = questions[idx]
  const isExam = session.session_type === 'belt_exam'

  // Auto-advance past worked example
  const advance = () => {
    setFeedback(null)
    setHint(null)
    if (idx + 1 >= questions.length) {
      complete()
    } else {
      setIdx(idx + 1)
      startedAt.current = Date.now()
    }
  }

  const submit = async (selectedIndex) => {
    if (q.is_worked_example) { advance(); return }
    if (feedback) return
    const timeTaken = Date.now() - startedAt.current
    const r = await childApi.answer({
      question_id: q.id, selected_index: selectedIndex,
      time_taken_ms: timeTaken, used_hint: !!hintUsed[q.id],
    })
    setFeedback({ ...r, selected: selectedIndex })
    setSessionXp(x => x + r.xp_awarded)
    setCombo(r.combo)
    if (r.is_correct) {
      sounds.correctByDifficulty(session.difficulty)
      if (r.combo >= 5) sounds.combo5()
      else if (r.combo >= 3) sounds.combo3()
    } else {
      sounds.wrong()
    }
  }

  const requestHint = async () => {
    if (isExam || q.is_worked_example) return
    const r = await childApi.hint(q.id)
    setHint(r.hint)
    setHintUsed({ ...hintUsed, [q.id]: true })
  }

  const complete = async () => {
    const r = await childApi.complete(id)
    sounds.questComplete()
    if (r.new_badges?.length) sounds.badgeEarned()
    if (r.level_up) sounds.levelUp()
    setDone(r)
  }

  const playAnother = async () => {
    setLoadingNext(true)
    try {
      const r = await childApi.extraQuest()
      // Reset for the fresh session; effect on [id] refetches after nav.
      setDone(null); setSession(null)
      setIdx(0); setSessionXp(0); setCombo(0)
      setFeedback(null); setHint(null); setHintUsed({})
      questStart.current = Date.now(); startedAt.current = Date.now()
      nav(`/quest/${r.session_id}`)
    } catch (e) {
      alert(e?.response?.data?.detail || 'Could not start another quest.')
      nav('/')
    } finally {
      setLoadingNext(false)
    }
  }

  if (done) {
    return (
      <SessionComplete
        session={session}
        done={done}
        onHome={() => nav('/')}
        onPlayAnother={playAnother}
        loadingNext={loadingNext}
      />
    )
  }

  const fmtTime = (s) => `${Math.floor(s/60)}:${(s%60).toString().padStart(2,'0')}`

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-md mx-auto p-4">
        <header className="flex items-center justify-between mb-3 text-sm">
          <button onClick={() => nav('/')} className="text-slate-500">← Home</button>
          <div>Q {idx + 1} / {questions.length}</div>
          <div className="font-bold">+{sessionXp} XP</div>
        </header>

        {isExam && (
          <div className="card mb-3 bg-red-50 border border-red-300 text-center">
            <p className="text-xs font-bold uppercase text-red-700">⚔️ Belt Exam Mode</p>
            <p className="text-2xl font-mono font-bold">{timeLeft != null ? fmtTime(timeLeft) : '--:--'}</p>
          </div>
        )}

        {!isExam && combo >= 3 && (
          <div className="fixed top-4 right-4 bg-amber-400 text-white font-bold rounded-full px-4 py-2 animate-badge-pop shadow-lg">
            🔥 Combo ×{combo >= 5 ? 3 : 2}!
          </div>
        )}

        <QuestionCard
          question={q}
          feedback={feedback}
          hint={hint}
          onSelect={submit}
          onContinue={advance}
        />

        {!isExam && !q.is_worked_example && !feedback && (
          <button
            onClick={requestHint}
            disabled={hintUsed[q.id]}
            className={`btn ${hintUsed[q.id] ? 'btn-disabled' : 'btn-secondary'} w-full mt-3`}
          >
            💡 {hintUsed[q.id] ? 'Hint used' : 'Get a hint (costs 50% XP)'}
          </button>
        )}
      </div>
    </div>
  )
}

function SessionComplete({ session, done, onHome, onPlayAnother, loadingNext }) {
  const isExam = session.session_type === 'belt_exam'
  const pct = done.total ? Math.round((done.score / done.total) * 100) : 0
  const stars = pct >= 100 ? 3 : pct >= 80 ? 2 : pct >= 60 ? 1 : 0
  const [showReview, setShowReview] = useState(false)

  if (isExam) {
    return <BeltExamModal done={done} onHome={onHome} />
  }
  if (done.level_up) {
    return <LevelUpModal levelUp={done.level_up} done={done} onHome={onHome} />
  }
  if (showReview) {
    return <ReviewWrong sessionId={session.id} onBack={() => setShowReview(false)} />
  }

  const hype = pct >= 100 ? '🔥 PERFECT! You smashed it!'
    : pct >= 80 ? '⭐ Brilliant work!'
    : pct >= 60 ? '👍 Solid round!'
    : '💪 Keep going — every wrong answer makes you stronger!'

  const nextPct = done.level_next
    ? Math.max(4, Math.min(100, 100 - (done.level_next.remaining / done.level_next.at) * 100))
    : null

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-amber-50 flex items-center justify-center p-4">
      <div className="card w-full max-w-md">
        <h2 className="text-2xl font-bold mb-1">Quest Complete!</h2>
        <p className="text-base font-bold text-violet-700 mb-3">{hype}</p>

        {done.personal_best?.is_new_best && (
          <div className="bg-amber-100 border-2 border-amber-400 rounded-lg p-3 mb-3 animate-badge-pop">
            <p className="font-bold text-amber-800">🏆 NEW PERSONAL BEST!</p>
            <p className="text-xs text-amber-700">
              Previous best: {done.personal_best.previous_best_score}/{done.personal_best.previous_best_total}
            </p>
          </div>
        )}

        <p className="text-lg mb-2">Score: {done.score} / {done.total} {'⭐'.repeat(stars)}</p>
        <div className="text-sm text-slate-600 mb-3">
          <div>Base XP: {done.xp_breakdown.base}</div>
          <div>Streak multiplier: ×{done.xp_breakdown.streak_multiplier}</div>
          <div>Max combo: {done.xp_breakdown.max_combo}</div>
          {done.xp_breakdown.perfect_bonus > 0 && (
            <div className="font-bold text-amber-700 animate-badge-pop">🏆 Perfect quest! +{done.xp_breakdown.perfect_bonus} XP</div>
          )}
          {done.xp_breakdown.strong_bonus > 0 && (
            <div className="font-bold text-violet-700 animate-badge-pop">⭐ Strong finish (≥90%)! +{done.xp_breakdown.strong_bonus} XP</div>
          )}
          {done.xp_breakdown.graduation_bonus > 0 && (
            <div className="font-bold text-emerald-700 animate-badge-pop">
              📈 Topic graduated! +{done.xp_breakdown.graduation_bonus} XP
              {done.xp_breakdown.promotions?.map((p, i) => (
                <div key={i} className="text-xs font-normal text-emerald-600">
                  {p.topic}: {p.from} → {p.to}
                </div>
              ))}
            </div>
          )}
          <div className="font-bold text-base text-slate-800 mt-1">Total: +{done.xp_total_session} XP</div>
        </div>

        {done.level && (
          <div className="bg-violet-50 border border-violet-200 rounded-lg p-3 mb-3">
            <div className="flex items-center justify-between mb-1">
              <p className="font-bold text-violet-900">🎖 {done.level}</p>
              {done.belt_name && (
                <p className="text-sm text-violet-700">{done.belt_name} Belt</p>
              )}
            </div>
            <p className="text-xs text-violet-700 mb-2">Total: {done.level_total_xp?.toLocaleString()} XP</p>
            {done.level_next && nextPct != null && (
              <>
                <div className="h-2 bg-violet-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-violet-500 to-amber-400"
                    style={{ width: `${nextPct}%` }}
                  />
                </div>
                <p className="text-xs text-violet-700 mt-1">
                  {done.level_next.remaining} XP to {done.level_next.name}
                </p>
              </>
            )}
          </div>
        )}

        {done.new_badges?.length > 0 && (
          <div className="mb-3">
            <p className="font-bold mb-1">🎉 Badges earned:</p>
            <div className="flex gap-2">
              {done.new_badges.map(b => (
                <div key={b.id} className="bg-amber-100 rounded-lg px-3 py-2 animate-badge-pop">
                  <span className="text-2xl">{b.icon}</span> {b.name}
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="text-sm bg-slate-50 rounded-lg p-2 mb-3">
          🔥 Streak: {done.streak} day{done.streak === 1 ? '' : 's'}
          {done.daily_done && ' — Daily Quest done! Streak safe.'}
        </div>
        {done.rival?.leaderboard && (
          <div className="text-sm bg-violet-50 rounded-lg p-2 mb-3">
            <p className="font-bold text-violet-900">
              ⚔️ League rank: #{done.rival.child_position} of {done.rival.leaderboard.length}
            </p>
            {done.rival.action_hint && (
              <>
                <p className="text-xs text-violet-800 mt-1">{done.rival.action_hint.headline}</p>
                <p className="text-xs text-violet-700">{done.rival.action_hint.action}</p>
              </>
            )}
          </div>
        )}
        {done.has_wrong_answers && (
          <button
            onClick={() => setShowReview(true)}
            className="btn btn-secondary w-full mb-2"
          >
            🔍 Review what I got wrong
          </button>
        )}
        <div className="flex gap-2">
          {onPlayAnother && (
            <button
              onClick={onPlayAnother}
              disabled={loadingNext}
              className={`btn ${loadingNext ? 'btn-disabled' : 'btn-primary'} flex-1`}
            >
              {loadingNext ? 'Loading…' : '⚡ Play another'}
            </button>
          )}
          <button onClick={onHome} className="btn btn-secondary flex-1">🏠 Home</button>
        </div>
      </div>
    </div>
  )
}

function ReviewWrong({ sessionId, onBack }) {
  const [data, setData] = useState(null)
  useEffect(() => {
    childApi.review(sessionId).then(setData).catch(() => setData({ error: true }))
  }, [sessionId])

  if (!data) return <div className="p-6 text-center">Loading…</div>
  if (data.error) {
    return (
      <div className="p-6 text-center">
        Could not load review.{' '}
        <button onClick={onBack} className="underline">Back</button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4">
      <div className="max-w-md mx-auto">
        <header className="flex items-center justify-between mb-4">
          <button onClick={onBack} className="text-violet-700 font-semibold">← Back</button>
          <h2 className="font-bold">Review</h2>
          <span className="text-sm text-slate-500">
            {data.wrong.length} miss{data.wrong.length === 1 ? '' : 'es'}
          </span>
        </header>
        {data.wrong.length === 0 && (
          <div className="card text-center">
            <p className="text-3xl mb-2">🎯</p>
            <p className="font-bold">No misses — you got them all right!</p>
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
        <button onClick={onBack} className="btn btn-primary w-full">Done reviewing</button>
      </div>
    </div>
  )
}
