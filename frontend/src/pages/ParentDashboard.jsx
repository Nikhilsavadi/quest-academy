import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { parentApi } from '../api.js'
import { clearToken } from '../auth.js'
import MasteryHeatmap from '../components/MasteryHeatmap.jsx'
import ProgressionBanner from '../components/ProgressionBanner.jsx'

const TABS = ['Overview', 'Mastery', 'Belt', 'Tables', 'Scanner', 'Max', 'History']

export default function ParentDashboard() {
  const [tab, setTab] = useState('Overview')
  const [dash, setDash] = useState(null)
  const [notifs, setNotifs] = useState([])
  const nav = useNavigate()

  const load = () => {
    parentApi.dashboard().then(setDash).catch(() => clearToken())
    parentApi.notifications().then(r => setNotifs(r.items)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  if (!dash) return <div className="p-6">Loading parent dashboard…</div>

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="font-bold text-lg">Quest Academy — Parent</h1>
            <p className="text-xs text-slate-500">
              {dash.child.name} · {dash.level} · {dash.xp} XP · 🔥 {dash.streak}d ·
              {' '}<span className="font-semibold">{dash.belt.current_name} Belt</span>
              {' '}· {dash.today_questions}/{dash.cap} today
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm">🔔 {dash.notifications_unread}</span>
            <button onClick={() => nav('/')} className="btn btn-secondary text-sm py-1 px-3">Child View</button>
            <button onClick={() => { clearToken(); nav('/admin/login') }} className="text-sm text-slate-500 underline">Logout</button>
          </div>
        </div>
        <nav className="max-w-5xl mx-auto px-2 pb-2 flex gap-1 overflow-x-auto">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap ${tab === t ? 'bg-questPurple text-white' : 'bg-slate-100 text-slate-600'}`}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      <main className="max-w-5xl mx-auto p-4">
        <Notifications notifs={notifs} onRead={(id) => parentApi.notifRead(id).then(load)} />

        {tab === 'Overview' && <Overview dash={dash} onReload={load} />}
        {tab === 'Mastery' && <MasteryTab />}
        {tab === 'Belt' && <BeltTab onReload={load} />}
        {tab === 'Tables' && <TablesTab />}
        {tab === 'Scanner' && <ScannerTab beltOk={dash.belt.current >= 1} />}
        {tab === 'Max' && <MaxTab />}
        {tab === 'History' && <HistoryTab />}
      </main>
    </div>
  )
}

function Notifications({ notifs, onRead }) {
  if (!notifs.length) return null
  return (
    <div className="mb-4 space-y-2">
      {notifs.filter(n => !n.read).slice(0, 5).map(n => (
        <div key={n.id} className="card flex items-center justify-between bg-amber-50 border border-amber-200">
          <span className="text-sm">{n.message}</span>
          <button onClick={() => onRead(n.id)} className="text-xs underline text-slate-500">Mark read</button>
        </div>
      ))}
    </div>
  )
}

function Overview({ dash, onReload }) {
  const [suggestions, setSuggestions] = useState([])
  const [form, setForm] = useState({ subject: 'Maths', topic: '', difficulty: '', source: 'ai_generated' })
  const [restDate, setRestDate] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => { parentApi.suggestions().then(r => setSuggestions(r.suggestions)) }, [])

  const assign = async () => {
    setMsg('')
    try {
      await parentApi.assignBonus({
        subject: form.subject,
        topic: form.topic || null,
        difficulty: form.difficulty || null,
        source: form.source,
      })
      setMsg('Bonus quest assigned ✅')
      onReload()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Failed')
    }
  }

  const setRest = async () => {
    if (!restDate) return
    await parentApi.restDay(restDate)
    setMsg(`Rest day set: ${restDate}`)
    setRestDate('')
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <ProgressionBanner suggestions={suggestions} onAction={() => parentApi.suggestions().then(r => setSuggestions(r.suggestions))} />

      <div className="card">
        <h2 className="font-bold mb-2">Assign Bonus Quest</h2>
        <select value={form.subject} onChange={e => setForm({...form, subject: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 mb-2">
          {/* v1: Maths-only — NVR/VR generation has visual bugs, suspended */}
          {['Maths'].map(s => <option key={s}>{s}</option>)}
        </select>
        <input placeholder="Topic (leave blank = auto pick weakest)" value={form.topic} onChange={e => setForm({...form, topic: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 mb-2" />
        <select value={form.difficulty} onChange={e => setForm({...form, difficulty: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 mb-2">
          <option value="">Auto (current level)</option>
          <option value="starter">Starter</option>
          <option value="challenge">Challenge</option>
          <option value="olympiad">Olympiad</option>
        </select>
        <button onClick={assign} className="btn btn-primary w-full">Assign</button>
        {msg && <p className="text-sm mt-2 text-slate-600">{msg}</p>}
      </div>

      <div className="card">
        <h2 className="font-bold mb-2">Rest Day</h2>
        <div className="flex gap-2">
          <input type="date" value={restDate} onChange={e => setRestDate(e.target.value)} className="border rounded-lg px-2 py-1.5 flex-1" />
          <button onClick={setRest} className="btn btn-secondary">Set</button>
        </div>
        <p className="text-xs text-slate-500 mt-2">Streak is preserved on rest days.</p>
      </div>

      <div className="card">
        <h2 className="font-bold mb-2">Today</h2>
        <p className="text-sm">Questions completed: {dash.today_questions} / {dash.cap}</p>
        <p className="text-sm">Belt: {dash.belt.current_name} ({dash.belt.current})</p>
        {dash.belt.exam_unlocked_belt && (
          <p className="text-sm text-amber-700 font-semibold">⚔️ Belt {dash.belt.exam_unlocked_belt} exam unlocked</p>
        )}
      </div>
    </div>
  )
}

function MasteryTab() {
  const [rows, setRows] = useState([])
  const [detail, setDetail] = useState(null)
  useEffect(() => { parentApi.mastery().then(r => setRows(r.rows)) }, [])
  const openTopic = (topic) => parentApi.topicRecent(topic).then(setDetail)
  return (
    <div className="card">
      <h2 className="font-bold mb-3">Mastery Heatmap</h2>
      <MasteryHeatmap rows={rows} onCellClick={openTopic} />
      {detail && (
        <div className="mt-4 border-t pt-3">
          <h3 className="font-bold mb-2">{detail.topic} — last 5</h3>
          {detail.recent.map((r, i) => (
            <div key={i} className="text-sm flex justify-between">
              <span className="truncate flex-1">{r.is_correct ? '✅' : '❌'} {r.question}</span>
              <span className="text-slate-400 text-xs">{new Date(r.answered_at).toLocaleDateString()}</span>
            </div>
          ))}
          <button onClick={() => setDetail(null)} className="text-xs underline text-slate-500 mt-2">Close</button>
        </div>
      )}
    </div>
  )
}

function BeltTab({ onReload }) {
  const [status, setStatus] = useState(null)
  const [history, setHistory] = useState([])
  const [msg, setMsg] = useState('')
  const load = () => {
    parentApi.beltStatus().then(setStatus)
    parentApi.beltHistory().then(r => setHistory(r.exams))
  }
  useEffect(load, [])

  const schedule = async () => {
    try {
      const r = await parentApi.beltSchedule()
      setMsg(`Belt exam ready — session ${r.session_id}. Open child view to start.`)
      load(); onReload()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Failed')
    }
  }

  const override = async () => {
    const belt = parseInt(prompt('Unlock which belt? (1-5)'), 10)
    if (!belt) return
    await parentApi.beltOverride(belt)
    load(); onReload()
  }

  if (!status) return <div>Loading…</div>
  return (
    <div className="card">
      <h2 className="font-bold mb-1">Belt Progress</h2>
      <p className="text-sm text-slate-500 mb-3">Current: {status.current_belt_name} → Next: {status.next_belt_name || 'Max'}</p>

      <div className="space-y-1 mb-3">
        {status.checklist.map((c, i) => (
          <div key={i} className="text-sm flex justify-between border-b py-1">
            <span>
              {c.met ? '✅' : '⏳'} {c.label || `${c.subject} ${c.needed ? `: ${c.have}/${c.needed}` : ''}`}
              {c.qualifying && c.qualifying.length > 0 && (
                <span className="text-xs text-slate-500"> — {c.qualifying.join(', ')}</span>
              )}
            </span>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button onClick={schedule} disabled={!status.exam_unlocked} className={`btn flex-1 ${status.exam_unlocked ? 'btn-primary' : 'btn-disabled'}`}>
          {status.exam_unlocked ? `Start ${status.next_belt_name} Exam` : 'Gate not met yet'}
        </button>
        <button onClick={override} className="btn btn-secondary">Override</button>
      </div>
      {msg && <p className="text-sm mt-2 text-slate-600">{msg}</p>}

      <h3 className="font-bold mt-4 mb-1">Exam history</h3>
      {history.length === 0 ? (
        <p className="text-sm text-slate-500">No exams yet.</p>
      ) : history.map((e, i) => (
        <div key={i} className="text-sm border-b py-1 flex justify-between">
          <span>{e.passed ? '✅' : '❌'} Belt {e.belt} — {e.score}/{e.total}</span>
          <span className="text-slate-400 text-xs">{new Date(e.attempted_at).toLocaleDateString()}</span>
        </div>
      ))}
    </div>
  )
}

function TablesTab() {
  const [hm, setHm] = useState(null)
  const [target, setTarget] = useState({ correct_target: 20, time_limit_seconds: 60, include_division: false })
  const load = () => parentApi.tablesHeatmap().then(d => { setHm(d); setTarget(d.target) })
  useEffect(load, [])

  const save = async () => {
    await parentApi.setTablesTarget(target)
    load()
  }

  if (!hm) return <div>Loading…</div>
  const grid = {}
  hm.cells.forEach(c => { grid[`${c.m}_${c.n}`] = c })

  const color = (cell) => {
    if (!cell || cell.attempts === 0) return 'bg-slate-100'
    const ms = cell.avg_response_ms
    const acc = cell.correct / cell.attempts
    if (acc < 0.7) return 'bg-red-300'
    if (ms < 1500) return 'bg-green-300'
    if (ms < 3000) return 'bg-yellow-300'
    if (ms < 5000) return 'bg-orange-300'
    return 'bg-red-300'
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div className="card overflow-x-auto">
        <h2 className="font-bold mb-2">12×12 Heatmap</h2>
        <table className="text-xs">
          <thead><tr><th></th>{Array.from({length:12}, (_,i) => <th key={i} className="w-8 text-center">{i+1}</th>)}</tr></thead>
          <tbody>
            {Array.from({length:12}, (_,r) => (
              <tr key={r}>
                <th className="text-right pr-1">{r+1}</th>
                {Array.from({length:12}, (_,c) => {
                  const cell = grid[`${r+1}_${c+1}`]
                  return (
                    <td key={c} className={`w-8 h-8 text-center align-middle ${color(cell)} border`}>
                      {cell?.attempts ? Math.round(cell.avg_response_ms/100)/10 : ''}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-slate-500 mt-2">Cell shows avg response (s). PB Blitz: {hm.target.best_blitz_seconds ?? '—'}s</p>
      </div>
      <div className="card">
        <h2 className="font-bold mb-2">Blitz Target</h2>
        <label className="text-sm">Correct target</label>
        <input type="number" value={target.correct_target} onChange={e => setTarget({...target, correct_target: parseInt(e.target.value)})} className="border rounded-lg px-2 py-1 w-full mb-2" />
        <label className="text-sm">Time limit (seconds)</label>
        <input type="number" value={target.time_limit_seconds} onChange={e => setTarget({...target, time_limit_seconds: parseInt(e.target.value)})} className="border rounded-lg px-2 py-1 w-full mb-2" />
        <label className="text-sm flex items-center gap-2">
          <input type="checkbox" checked={target.include_division} onChange={e => setTarget({...target, include_division: e.target.checked})} />
          Include division facts
        </label>
        <button onClick={save} className="btn btn-primary w-full mt-3">Save Target</button>
      </div>
    </div>
  )
}

function ScannerTab({ beltOk }) {
  const [templates, setTemplates] = useState([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const load = () => parentApi.templates().then(r => setTemplates(r.templates))
  useEffect(load, [])

  const upload = async (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setBusy(true); setMsg('Reading question styles…')
    try {
      const r = await parentApi.scanTemplate(f)
      const name = prompt('Name this template:', r.template.source_name) || r.template.source_name
      await parentApi.confirmTemplate(r.template.id, name)
      setMsg('Template saved ✅')
      load()
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Scan failed')
    } finally {
      setBusy(false)
    }
  }

  const assign = async (id) => {
    const c = parseInt(prompt('How many questions? (1-10)', '10'), 10)
    if (!c || c < 1 || c > 10) return
    try { await parentApi.assignFromTemplate(id, c); setMsg('Assigned ✅') }
    catch (e) { setMsg(e.response?.data?.detail || 'Failed') }
  }

  if (!beltOk) {
    return <div className="card text-center">Bond Scanner unlocks at Bronze Belt 🥉</div>
  }

  return (
    <div className="card">
      <h2 className="font-bold mb-2">📷 Bond Scanner</h2>
      <p className="text-sm text-slate-500 mb-3">Upload a workbook page (JPEG/PNG, max 10MB). We extract the style and generate questions matching it.</p>
      <label className="btn btn-primary inline-block">
        Upload workbook page
        <input type="file" accept="image/jpeg,image/png" onChange={upload} className="hidden" />
      </label>
      {busy && <p className="text-sm mt-2">Reading question styles…</p>}
      {msg && <p className="text-sm mt-2">{msg}</p>}

      <h3 className="font-bold mt-4 mb-2">Saved templates ({templates.length})</h3>
      <div className="grid md:grid-cols-2 gap-3">
        {templates.map(t => (
          <div key={t.id} className="border rounded-lg p-3">
            {t.thumbnail_path && <img src={t.thumbnail_path} alt="" className="w-full h-32 object-cover rounded mb-2" />}
            <p className="font-semibold text-sm">{t.source_name}</p>
            <p className="text-xs text-slate-500">{t.subject} · {t.difficulty} · {t.year_group}</p>
            <p className="text-xs text-slate-500">Used: {t.times_used}×</p>
            <div className="flex gap-1 mt-2">
              <button onClick={() => assign(t.id)} className="btn btn-primary text-xs flex-1 py-1">Assign</button>
              <button onClick={() => parentApi.deleteTemplate(t.id).then(load)} className="btn btn-secondary text-xs py-1">🗑</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MaxTab() {
  const [c, setC] = useState(null)
  const load = () => parentApi.maxControls().then(setC)
  useEffect(load, [])
  if (!c) return <div>Loading…</div>

  return (
    <div className="card">
      <h2 className="font-bold mb-2">Max — Rival Controls</h2>
      <p className="text-sm">Max XP: {c.current_xp} · Day {c.cycle_day}/28 · Today's rate: {c.daily_rate}</p>
      {c.surge_active && <p className="text-sm text-red-600">⚠️ Surge active</p>}

      <div className="mt-3">
        <label className="text-sm font-medium">Difficulty</label>
        <div className="flex gap-2 mt-1">
          {['friendly','standard','competitive'].map(d => (
            <button key={d} onClick={() => parentApi.maxUpdate({base_difficulty: d}).then(load)}
              className={`btn flex-1 ${c.base_difficulty === d ? 'btn-primary' : 'btn-secondary'}`}>
              {d}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <button onClick={() => {
          const x = parseInt(prompt('Override Max XP:', c.current_xp), 10)
          if (!isNaN(x)) parentApi.maxUpdate({manual_xp: x}).then(load)
        }} className="btn btn-secondary mr-2">Manual XP override</button>
        <button onClick={() => { if (confirm('Reset XP + belts for both? (badges kept)')) parentApi.maxReset().then(load) }} className="btn btn-secondary">New Semester</button>
      </div>

      <h3 className="font-bold mt-4 mb-2">Last 30 days</h3>
      {c.history.length === 0 ? <p className="text-sm text-slate-500">No data yet.</p> :
        <div className="overflow-x-auto">
          <table className="text-xs w-full">
            <thead><tr><th>Date</th><th>Child</th><th>Max</th></tr></thead>
            <tbody>{c.history.slice(-15).map(h => (
              <tr key={h.date}><td>{h.date}</td><td>{h.child}</td><td>{h.max}</td></tr>
            ))}</tbody>
          </table>
        </div>
      }
    </div>
  )
}

function HistoryTab() {
  const [rows, setRows] = useState([])
  const [subj, setSubj] = useState('')
  useEffect(() => { parentApi.history(subj || null).then(r => setRows(r.sessions)) }, [subj])
  return (
    <div className="card">
      <h2 className="font-bold mb-2">Session History</h2>
      <select value={subj} onChange={e => setSubj(e.target.value)} className="border rounded-lg px-2 py-1 mb-3">
        <option value="">All subjects</option>
        {['Maths','NVR','VR'].map(s => <option key={s}>{s}</option>)}
      </select>
      <div className="overflow-x-auto">
        <table className="text-sm w-full">
          <thead><tr className="text-left text-slate-500"><th>Date</th><th>Type</th><th>Subject</th><th>Topic</th><th>Diff</th><th>Score</th><th>Source</th></tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.id} className="border-b">
              <td>{new Date(r.date).toLocaleDateString()}</td>
              <td>{r.type}</td>
              <td>{r.subject}</td>
              <td>{r.topic}</td>
              <td>{r.difficulty}</td>
              <td>{r.score}/{r.total}</td>
              <td>{r.source}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  )
}
