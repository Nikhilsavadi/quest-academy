import { useEffect, useRef, useState } from 'react'
import { tablesApi } from '../api.js'
import { sounds } from '../sounds.js'

const ALT_KEY = 'quest_tables_alt'  // flips MCQ vs typed each session

export default function TablesTrainer({ onClose }) {
  const [mode, setMode] = useState(null)  // null | blitz | target | fix_it
  const [config, setConfig] = useState(null)
  useEffect(() => { tablesApi.heatmap().then(setConfig) }, [])

  if (!mode) return (
    <div className="fixed inset-0 bg-white z-40 overflow-y-auto p-4">
      <div className="max-w-md mx-auto">
        <header className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">⚡ Tables Trainer</h2>
          <button onClick={onClose} className="text-2xl">✕</button>
        </header>
        <p className="text-sm text-slate-500 mb-4">
          PB Blitz: {config?.target?.best_blitz_seconds ? `${config.target.best_blitz_seconds}s` : '— no record yet'}
        </p>
        <button onClick={() => setMode('blitz')} className="btn btn-primary w-full mb-2">⚡ Blitz Mode (20 facts)</button>
        <button onClick={() => setMode('target')} className="btn btn-secondary w-full mb-2">
          🎯 Target Mode ({config?.target?.correct_target ?? 20} in {config?.target?.time_limit_seconds ?? 60}s)
        </button>
        <button onClick={() => setMode('fix_it')} className="btn btn-secondary w-full">🔧 Fix It Round</button>
      </div>
    </div>
  )

  return <TablesSession mode={mode} config={config} onDone={onClose} onBack={() => setMode(null)} />
}

function genFact(weakFacts = null) {
  if (weakFacts && weakFacts.length) {
    const f = weakFacts[Math.floor(Math.random() * weakFacts.length)]
    return { m: f.m, n: f.n }
  }
  return { m: 1 + Math.floor(Math.random() * 12), n: 1 + Math.floor(Math.random() * 12) }
}

function neighbourDistractors(answer, m, n) {
  const set = new Set()
  // Neighbouring multiples of m and n
  const candidates = [
    m * (n - 1), m * (n + 1), (m - 1) * n, (m + 1) * n,
    answer + m, answer - m, answer + n, answer - n,
  ].filter(v => v > 0 && v !== answer)
  for (const c of candidates) {
    if (set.size >= 3) break
    set.add(c)
  }
  while (set.size < 3) set.add(answer + (set.size + 1))
  return [...set].slice(0, 3)
}

function TablesSession({ mode, config, onDone, onBack }) {
  const [fact, setFact] = useState(genFact())
  const [opts, setOpts] = useState([])
  const [typed, setTyped] = useState('')
  const [useMCQ, setUseMCQ] = useState(() => {
    const last = localStorage.getItem(ALT_KEY)
    const next = last === 'mcq' ? 'typed' : 'mcq'
    localStorage.setItem(ALT_KEY, next)
    return next === 'mcq'
  })
  const [correct, setCorrect] = useState(0)
  const [total, setTotal] = useState(0)
  const [facts, setFacts] = useState([])
  const [streak, setStreak] = useState(0)
  const [feedback, setFeedback] = useState(null)
  const [weakFacts, setWeakFacts] = useState(null)
  const [done, setDone] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const startedAt = useRef(Date.now())
  const factStartedAt = useRef(Date.now())

  const target = config?.target?.correct_target ?? 20
  const timeLimit = config?.target?.time_limit_seconds ?? 60

  useEffect(() => {
    if (mode === 'fix_it') {
      tablesApi.weakFacts().then(r => {
        const wf = r.facts.length ? r.facts : null
        setWeakFacts(wf)
        const f = genFact(wf)
        setFact(f); buildOpts(f)
      })
    } else {
      buildOpts(fact)
    }
  }, [])

  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt.current) / 1000)), 200)
    return () => clearInterval(id)
  }, [])

  // Auto-end conditions
  useEffect(() => {
    if (done) return
    if (mode === 'blitz' && total >= 20) finish()
    if (mode === 'target') {
      if (correct >= target) finish(true)
      if (elapsed >= timeLimit) finish()
    }
    if (mode === 'fix_it' && elapsed >= 120) finish()
  }, [total, correct, elapsed])

  const buildOpts = (f) => {
    const ans = f.m * f.n
    const distractors = neighbourDistractors(ans, f.m, f.n)
    const all = [ans, ...distractors].sort(() => Math.random() - 0.5)
    setOpts(all)
    setTyped('')
    factStartedAt.current = Date.now()
  }

  const submit = (value) => {
    const ans = fact.m * fact.n
    const isCorrect = value === ans
    const responseMs = Date.now() - factStartedAt.current
    setTotal(t => t + 1)
    if (isCorrect) {
      setCorrect(c => c + 1)
      setStreak(s => s + 1)
      sounds.correctStarter()
    } else {
      setStreak(0)
      sounds.wrong()
    }
    setFacts(arr => [...arr, { multiplicand: fact.m, multiplier: fact.n, correct: isCorrect, response_ms: responseMs }])
    setFeedback({ correct: isCorrect, ans })
    setTimeout(() => {
      setFeedback(null)
      const f = genFact(weakFacts)
      setFact(f); buildOpts(f)
    }, isCorrect ? 250 : 700)
  }

  const finish = async (hitTarget = false) => {
    if (done) return
    const duration = Math.floor((Date.now() - startedAt.current) / 1000)
    const r = await tablesApi.log({
      mode, total_questions: total, correct, duration_seconds: duration, facts,
    })
    setDone({ correct, total, duration, pb_broken: r.pb_broken, xp: r.xp, badges: r.new_badges, hitTarget })
  }

  if (done) {
    return (
      <div className="fixed inset-0 bg-white z-40 p-4">
        <div className="max-w-md mx-auto">
          <h2 className="text-2xl font-bold mb-2">Tables done!</h2>
          <p>Correct: {done.correct} / {done.total}</p>
          <p>Time: {done.duration}s</p>
          <p className="text-questPurple font-bold">+{done.xp} XP</p>
          {done.pb_broken && <p className="text-amber-600 font-bold animate-badge-pop">🎉 New best!</p>}
          {done.hitTarget && <p className="text-green-600 font-bold">🎯 Target hit!</p>}
          <button onClick={onDone} className="btn btn-primary w-full mt-3">Done</button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-white z-40 p-4">
      <div className="max-w-md mx-auto">
        <header className="flex justify-between items-center mb-4">
          <button onClick={onBack} className="text-slate-500">← Back</button>
          <span className="text-sm">⏱ {elapsed}s · ✅ {correct}/{total} · 🔥 {streak}</span>
        </header>

        <div className="card text-center">
          <p className="text-4xl font-bold mb-4">{fact.m} × {fact.n} = ?</p>
          {feedback && (
            <p className={`text-lg font-bold ${feedback.correct ? 'text-green-600' : 'text-red-500'}`}>
              {feedback.correct ? '✅' : `❌ ${fact.m} × ${fact.n} = ${feedback.ans}`}
            </p>
          )}
          {!feedback && useMCQ && (
            <div className="grid grid-cols-2 gap-2 mt-2">
              {opts.map((o, i) => (
                <button key={i} onClick={() => submit(o)} className="btn btn-secondary text-lg tap-target">{o}</button>
              ))}
            </div>
          )}
          {!feedback && !useMCQ && (
            <form onSubmit={(e) => { e.preventDefault(); const n = parseInt(typed, 10); if (!isNaN(n)) submit(n) }}>
              <input
                autoFocus inputMode="numeric" pattern="[0-9]*"
                value={typed}
                onChange={e => setTyped(e.target.value.replace(/[^0-9]/g, ''))}
                className="text-3xl text-center border-2 border-slate-300 rounded-xl px-4 py-3 w-32"
              />
              <button type="submit" className="btn btn-primary block w-full mt-3">Submit</button>
            </form>
          )}
        </div>

        <button onClick={() => finish()} className="text-xs text-slate-500 underline w-full text-center mt-3">End early</button>
      </div>
    </div>
  )
}
