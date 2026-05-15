import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { parentApi } from '../api.js'
import { setToken } from '../auth.js'

export default function Login() {
  const [email, setEmail] = useState('parent@quest-academy.app')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      const r = await parentApi.login(email, password)
      if (r.role !== 'parent') throw new Error('Parent account required')
      setToken(r.access_token)
      nav('/admin')
    } catch (e) {
      setErr('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-100 to-amber-100 p-4">
      <form onSubmit={submit} className="card w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-1">Parent Dashboard</h1>
        <p className="text-sm text-slate-500 mb-5">Quest Academy</p>
        <label className="block text-sm font-medium mb-1">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 mb-4"
          required
        />
        <label className="block text-sm font-medium mb-1">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 mb-4"
          required
        />
        {err && <p className="text-sm text-red-600 mb-3">{err}</p>}
        <button type="submit" disabled={loading} className="btn btn-primary w-full">
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
        <a href="/" className="block text-sm text-slate-500 mt-4 text-center underline">← Back to Quest</a>
      </form>
    </div>
  )
}
