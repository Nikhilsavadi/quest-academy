const TOPICS = {
  Maths: ['Number Patterns','Mental Arithmetic','Factors & Multiples','Fractions','Place Value','Word Problems','Shape Area','Perimeter','Angles','Sequences & Series','Time & Calendars','Logic Puzzles','Probability'],
  NVR: ['NVR Sequences','NVR Matrices','NVR Odd One Out','NVR Rotations','NVR Analogies'],
  VR: ['Word Analogies','Letter Sequences','Number Codes','Missing Words','Logical Deduction','Hidden Words','Word Connections'],
}
const DIFFS = ['starter','challenge','olympiad']

function color(row) {
  if (!row || row.attempts === 0) return 'bg-slate-100 text-slate-400'
  const a = row.accuracy
  if (a >= 0.8) return 'bg-green-300'
  if (a >= 0.6) return 'bg-yellow-300'
  return 'bg-red-300'
}

export default function MasteryHeatmap({ rows, onCellClick }) {
  const byTopic = {}
  rows.forEach(r => { byTopic[r.topic] = r })
  return (
    <div className="space-y-4">
      {Object.entries(TOPICS).map(([subj, topics]) => (
        <div key={subj}>
          <h3 className="font-bold text-sm mb-1">{subj}</h3>
          <div className="overflow-x-auto">
            <table className="text-xs w-full">
              <thead><tr><th className="text-left pl-1">Topic</th>{DIFFS.map(d => <th key={d} className="px-2 capitalize">{d}</th>)}<th>Acc</th><th>n</th></tr></thead>
              <tbody>
                {topics.map(t => {
                  const r = byTopic[t]
                  return (
                    <tr key={t} className="border-b">
                      <td className="py-1 pl-1 cursor-pointer hover:underline" onClick={() => onCellClick(t)}>{t}</td>
                      {DIFFS.map(d => (
                        <td key={d} className={`px-2 text-center ${r && r.current_difficulty === d ? color(r) : 'bg-slate-50'}`}>
                          {r && r.current_difficulty === d ? '●' : ''}
                        </td>
                      ))}
                      <td className="px-2 text-center">{r ? Math.round((r.accuracy || 0) * 100) + '%' : '—'}</td>
                      <td className="px-2 text-center">{r?.attempts ?? 0}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
