import { useEffect, useState } from 'react'
import SVGQuestion from './SVGQuestion.jsx'
import SVGOption from './SVGOption.jsx'
import MatrixImage from './MatrixImage.jsx'

export default function QuestionCard({ question, feedback, hint, onSelect, onContinue }) {
  const [floats, setFloats] = useState([])

  // Reset floats on new question
  useEffect(() => { setFloats([]) }, [question.id])

  if (question.is_worked_example) {
    return (
      <div className="card">
        <p className="text-xs text-violet-600 uppercase font-bold mb-2">Worked Example</p>
        <p className="font-semibold mb-3">{question.question_text}</p>
        <div className="text-sm whitespace-pre-line bg-violet-50 rounded-lg p-3 mb-3">
          {question.walkthrough}
        </div>
        <button onClick={onContinue} className="btn btn-primary w-full">
          I've got it — let's go! ⚔️
        </button>
      </div>
    )
  }

  const handle = (i) => {
    if (feedback) return
    setFloats([...floats, { i, key: Date.now() }])
    onSelect(i)
  }

  // Detect if options are SVG strings
  const optionsAreSVG = question.options.length > 0 && /^\s*<svg/i.test(question.options[0] || '')

  return (
    <div className="card">
      <p className="text-sm font-semibold mb-1 text-slate-500">{question.topic}</p>
      <p className="font-bold text-lg leading-snug whitespace-pre-wrap mb-3">{question.question_text}</p>
      {question.svg_content && <SVGQuestion svg={question.svg_content} />}
      {question.image_bank_id && <MatrixImage id={question.image_bank_id} />}

      {hint && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3 text-sm">
          💡 {hint}
        </div>
      )}

      <div className={`grid ${optionsAreSVG ? 'grid-cols-2' : 'grid-cols-1'} gap-2`}>
        {question.options.map((opt, i) => {
          let cls = 'btn relative tap-target text-left '
          if (feedback) {
            if (i === feedback.correct_index) cls += 'bg-green-500 text-white animate-flash-green'
            else if (feedback.selected === i) cls += 'bg-red-400 text-white animate-shake'
            else cls += 'bg-slate-100 text-slate-500'
          } else {
            cls += 'btn-secondary hover:bg-slate-200'
          }
          return (
            <button key={i} onClick={() => handle(i)} disabled={!!feedback} className={cls}>
              {optionsAreSVG ? <SVGOption svg={opt} /> : opt}
              {floats.filter(f => f.i === i).map(f => (
                <span key={f.key} className="absolute right-3 top-2 text-questAmber font-bold animate-float-up pointer-events-none">
                  +{feedback?.xp_awarded || ''}
                </span>
              ))}
            </button>
          )
        })}
      </div>

      {feedback && (
        <div className={`mt-3 rounded-lg p-3 text-sm ${feedback.is_correct ? 'bg-green-50' : 'bg-red-50'}`}>
          <p className="font-semibold mb-1">
            {feedback.is_correct ? randomCorrect() : 'Nearly! Here\'s the trick…'}
          </p>
          <p className="text-slate-700">{feedback.explanation}</p>
          {!!feedback.xp_awarded && (
            <p className="text-xs mt-1 text-questPurple">+{feedback.xp_awarded} XP</p>
          )}
          <button onClick={onContinue} className="btn btn-primary w-full mt-2">Next →</button>
        </div>
      )}
    </div>
  )
}

const CORRECT_MSGS = [
  "Brilliant! ⚡", "You're on fire! 🔥", "Too easy for you! 😎",
  "RGS would be proud! 🏆", "Genius! 🧠", "Unstoppable! 💪",
]
function randomCorrect() {
  return CORRECT_MSGS[Math.floor(Math.random() * CORRECT_MSGS.length)]
}
