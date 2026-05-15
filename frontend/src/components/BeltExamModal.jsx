import Confetti from './Confetti.jsx'

const BELT_NAMES = ['Unranked', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Elite Scholar']

export default function BeltExamModal({ done, onHome }) {
  const belt = done.belt_progress?.current_belt || 0
  const passed = belt > 0 && done.score / done.total >= 0.8
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
      {passed && <Confetti />}
      <div className="card max-w-md w-full text-center bg-gradient-to-br from-amber-100 to-yellow-50">
        {passed ? (
          <>
            <h2 className="text-3xl font-black mb-2 animate-level-burst">
              🏆 {BELT_NAMES[belt]} BELT ACHIEVED!
            </h2>
            <p className="text-lg mb-3">You scored {done.score}/{done.total}</p>
            <p className="text-base font-bold text-questPurple mb-3">+{done.xp_total_session} XP</p>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-bold mb-2">So close!</h2>
            <p className="text-lg mb-3">You scored {done.score}/{done.total}</p>
            <p className="text-sm text-slate-600 mb-3">You need 80% to pass — try again in 48 hours.</p>
            <p className="text-sm text-slate-700">Keep practising weaker topics and you'll get it.</p>
          </>
        )}
        <button onClick={onHome} className="btn btn-primary w-full mt-3">Back home</button>
      </div>
    </div>
  )
}
