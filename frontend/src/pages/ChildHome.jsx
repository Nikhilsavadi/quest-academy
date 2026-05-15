import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { childApi } from '../api.js'
import { clearToken } from '../auth.js'
import { setSoundEnabled } from '../sounds.js'
import XPBar from '../components/XPBar.jsx'
import StreakCounter from '../components/StreakCounter.jsx'
import BeltProgress from '../components/BeltProgress.jsx'
import RivalWidget from '../components/RivalWidget.jsx'
import DailyQuestCard from '../components/DailyQuestCard.jsx'
import BonusQuestCard from '../components/BonusQuestCard.jsx'
import BadgeShelf from '../components/BadgeShelf.jsx'
import AvatarDisplay from '../components/AvatarDisplay.jsx'
import TablesTrainer from '../components/TablesTrainer.jsx'

export default function ChildHome() {
  const [home, setHome] = useState(null)
  const [tablesOpen, setTablesOpen] = useState(false)
  const nav = useNavigate()

  const load = () => childApi.home().then(setHome).catch(() => setHome({ error: true }))
  useEffect(() => { load() }, [])

  if (!home) return <div className="p-6 text-center">Loading your quest...</div>
  if (home.error) return <div className="p-6 text-center">Could not reach Quest Academy. Try again.</div>

  const theme = home.avatar?.theme || 'default'

  const toggleSound = async () => {
    const r = await childApi.soundToggle()
    setSoundEnabled(r.sound_enabled)
    setHome({ ...home, sound_enabled: r.sound_enabled })
  }

  const beltExamReady = home.belt?.exam_unlocked
  const startBeltExam = async () => {
    // Belt exam session was created server-side when parent toggled — find it
    // We trigger by going to /parent for schedule, but child needs to actually start it
    // Convention: exam session is the latest pending belt_exam session for the child
    // We expose belt_exam session id via /api/child/home? For simplicity, we go to dashboard hint
    alert('Ask a parent to start the belt exam from the dashboard.')
  }

  return (
    <div className={`min-h-screen theme-${theme} pb-20`}>
      <div className="max-w-md mx-auto p-4">
        <header className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <AvatarDisplay items={home.avatar?.active_items || []} />
            <div>
              <p className="text-xs text-slate-500">Welcome back</p>
              <h1 className="text-xl font-bold">{home.name}</h1>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={toggleSound} className="tap-target text-2xl" title="Toggle sound">
              {home.sound_enabled ? '🔊' : '🔇'}
            </button>
            <button
              onClick={() => {
                if (confirm('Sign out and return to the entry screen?')) {
                  clearToken()
                  nav('/', { replace: true })
                }
              }}
              className="tap-target text-2xl" title="Exit">🚪</button>
          </div>
        </header>

        <div className="card mb-3">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-xs uppercase text-slate-500">Level</p>
              <p className="font-bold text-lg">{home.level}</p>
            </div>
            <StreakCounter streak={home.streak} />
          </div>
          <XPBar xp={home.xp} next={home.next_level} />
        </div>

        <BeltProgress belt={home.belt} />

        {beltExamReady && (
          <div className="card mb-3 bg-yellow-50 border-2 border-yellow-400">
            <p className="font-bold text-lg">⚔️ BELT EXAM READY!</p>
            <p className="text-sm text-slate-600 mb-2">A parent will start it from their dashboard.</p>
            <button onClick={startBeltExam} className="btn btn-primary w-full">Ready when parent says go</button>
          </div>
        )}

        <RivalWidget rival={home.rival} />

        <DailyQuestCard quest={home.daily_quest} onStart={(id) => nav(`/quest/${id}`)} />

        {home.bonus_quests?.map(b => (
          <BonusQuestCard key={b.id} bonus={b} onStart={() => nav(`/quest/${b.id}`)} />
        ))}

        <div className="card mb-3 cursor-pointer hover:bg-slate-50" onClick={() => setTablesOpen(true)}>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-bold">⚡ Tables Trainer</p>
              <p className="text-xs text-slate-500">Times tables blitz</p>
            </div>
            <span className="text-2xl">→</span>
          </div>
        </div>

        <div className="text-xs text-slate-500 mb-2">
          📈 This week: {home.weekly_xp} XP · Best: {home.weekly_best_xp} XP
        </div>

        <BadgeShelf badges={home.badges || []} />
      </div>

      {tablesOpen && (
        <TablesTrainer onClose={() => { setTablesOpen(false); load() }} />
      )}
    </div>
  )
}
