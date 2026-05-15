import Confetti from './Confetti.jsx'

export default function LevelUpModal({ levelUp, done, onHome }) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
      <Confetti />
      <div className="card max-w-md w-full text-center bg-gradient-to-br from-violet-100 to-amber-100 animate-level-burst">
        <p className="text-sm uppercase font-bold text-violet-700">Level Up!</p>
        <h2 className="text-3xl font-black my-2">{levelUp.to}</h2>
        <p className="text-sm text-slate-600 mb-2">From {levelUp.from} → {levelUp.to}</p>
        <p className="text-lg font-bold mb-3">{levelUp.xp} XP</p>
        <p className="text-sm mb-3">Score this session: {done.score}/{done.total} · +{done.xp_total_session} XP</p>
        <button onClick={onHome} className="btn btn-primary w-full">Keep going! ⚔️</button>
      </div>
    </div>
  )
}
