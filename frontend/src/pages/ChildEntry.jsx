import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { childApi } from '../api.js'
import { setToken, getToken } from '../auth.js'

export default function ChildEntry() {
  const [name, setName] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()

  // If already logged in (token in localStorage), skip the entry screen
  useEffect(() => {
    if (getToken()) {
      nav('/home', { replace: true })
    }
  }, [nav])

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    const cleaned = name.trim()
    if (!cleaned) { setErr('Type your name'); return }
    setLoading(true)
    try {
      const r = await childApi.enter(cleaned)
      setToken(r.access_token)
      nav('/home', { replace: true })
    } catch (e) {
      const msg = e.response?.data?.detail || 'Could not let you in'
      setErr(typeof msg === 'string' ? msg : 'Could not let you in')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-100 via-pink-50 to-amber-100 p-4">
      <form onSubmit={submit} className="card w-full max-w-md text-center">
        <div className="text-5xl mb-2">🏰</div>
        <h1 className="text-3xl font-extrabold mb-1 text-violet-700">Quest Academy</h1>
        <p className="text-sm text-slate-500 mb-6">Type your name to start</p>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          autoFocus
          autoComplete="off"
          autoCapitalize="words"
          className="w-full rounded-xl border-2 border-violet-200 focus:border-violet-500 focus:outline-none px-4 py-3 text-lg text-center mb-3"
          required
          maxLength={40}
        />
        {err && <p className="text-sm text-red-600 mb-3">{err}</p>}
        <button type="submit" disabled={loading}
                className="btn btn-primary w-full text-lg py-3">
          {loading ? 'Loading...' : 'Enter →'}
        </button>
        <a href="/admin/login" className="block text-xs text-slate-400 mt-6 hover:text-slate-600">
          parent / admin
        </a>
      </form>
    </div>
  )
}
