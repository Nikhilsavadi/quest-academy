import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { childApi } from '../api.js'
import { sounds } from '../sounds.js'
import QuestionCard from '../components/QuestionCard.jsx'
import LevelUpModal from '../components/LevelUpModal.jsx'
import BeltExamModal from '../components/BeltExamModal.jsx'

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

  if (done) {
    return <SessionComplete session={session} done={done} onHome={() => nav('/')} />
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

function SessionComplete({ session, done, onHome }) {
  const isExam = session.session_type === 'belt_exam'
  const pct = done.total ? Math.round((done.score / done.total) * 100) : 0
  const stars = pct >= 100 ? 3 : pct >= 80 ? 2 : pct >= 60 ? 1 : 0

  if (isExam) {
    return <BeltExamModal done={done} onHome={onHome} />
  }
  if (done.level_up) {
    return <LevelUpModal levelUp={done.level_up} done={done} onHome={onHome} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-amber-50 flex items-center justify-center p-4">
      <div className="card w-full max-w-md">
        <h2 className="text-2xl font-bold mb-2">Quest Complete!</h2>
        <p className="text-lg mb-2">Score: {done.score} / {done.total} {'⭐'.repeat(stars)}</p>
        <div className="text-sm text-slate-600 mb-3">
          <div>Base XP: {done.xp_breakdown.base}</div>
          <div>Streak multiplier: ×{done.xp_breakdown.streak_multiplier}</div>
          <div>Max combo: {done.xp_breakdown.max_combo}</div>
          <div className="font-bold text-base text-slate-800 mt-1">Total: +{done.xp_total_session} XP</div>
        </div>
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
        {done.rival && (
          <div className="text-sm bg-violet-50 rounded-lg p-2 mb-3">
            {done.rival.child_ahead
              ? <>🎉 You're ahead of Max! Lead: +{done.rival.lead_or_deficit} XP</>
              : <>Max is ahead — Gap: {done.rival.lead_or_deficit} XP</>}
          </div>
        )}
        <div className="flex gap-2">
          <button onClick={onHome} className="btn btn-primary flex-1">🏠 Home</button>
        </div>
      </div>
    </div>
  )
}
