// Web Audio API tones — no audio files. All sounds <1s.
let ctx = null
let enabled = localStorage.getItem('quest_sound') === '1'

function getCtx() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === 'suspended') ctx.resume()
  return ctx
}

export function setSoundEnabled(on) {
  enabled = !!on
  localStorage.setItem('quest_sound', on ? '1' : '0')
}
export function soundEnabled() { return enabled }

function tone(freq, durationMs, type = 'sine', gain = 0.25, startOffset = 0) {
  const c = getCtx(); if (!c) return
  const osc = c.createOscillator(); const g = c.createGain()
  osc.type = type; osc.frequency.value = freq
  g.gain.setValueAtTime(0, c.currentTime + startOffset)
  g.gain.linearRampToValueAtTime(gain, c.currentTime + startOffset + 0.005)
  g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + startOffset + durationMs / 1000)
  osc.connect(g); g.connect(c.destination)
  osc.start(c.currentTime + startOffset); osc.stop(c.currentTime + startOffset + durationMs / 1000 + 0.02)
}

function chord(freqs, durationMs, gain = 0.18) {
  freqs.forEach(f => tone(f, durationMs, 'sine', gain))
}

export const sounds = {
  correctStarter() {
    if (!enabled) return
    tone(523.25, 80)
  },
  correctChallenge() {
    if (!enabled) return
    chord([523.25, 659.25], 100)
  },
  correctOlympiad() {
    if (!enabled) return
    chord([523.25, 659.25, 783.99, 1046.5], 150, 0.12)
  },
  wrong() {
    if (!enabled) return
    tone(220, 150, 'triangle', 0.2)
  },
  combo3() {
    if (!enabled) return
    tone(523, 80, 'sine', 0.22)
    tone(659, 80, 'sine', 0.22, 0.08)
  },
  combo5() {
    if (!enabled) return
    tone(523, 60, 'sine', 0.22)
    tone(659, 60, 'sine', 0.22, 0.06)
    tone(784, 80, 'sine', 0.22, 0.12)
  },
  levelUp() {
    if (!enabled) return
    const notes = [261.63, 329.63, 392, 523.25]
    notes.forEach((n, i) => tone(n, 120, 'sine', 0.22, i * 0.1))
  },
  badgeEarned() {
    if (!enabled) return
    chord([392, 493.88, 587.33], 500, 0.18)
  },
  streakMilestone() {
    if (!enabled) return
    chord([329.63, 415.3, 493.88], 300, 0.18)
  },
  questComplete() {
    if (!enabled) return
    chord([523.25, 659.25, 783.99], 600, 0.16)
  },
  correctByDifficulty(d) {
    if (d === 'olympiad') return this.correctOlympiad()
    if (d === 'challenge') return this.correctChallenge()
    return this.correctStarter()
  },
}
