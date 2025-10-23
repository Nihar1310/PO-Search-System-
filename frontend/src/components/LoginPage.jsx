import { useState } from 'react'
import GlassButton from './GlassButton'
import { API_BASE_URL } from '../services/api'

export default function LoginPage({ onSuccess, errorMessage }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(errorMessage || null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const formBody = new URLSearchParams()
      formBody.append('username', username)
      formBody.append('password', password)

      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        body: formBody.toString(),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        credentials: 'include'
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.detail || 'Authentication failed')
      }

      const data = await res.json()
      onSuccess(data)
    } catch (err) {
      setError(err.message || 'Unable to login')
      setPassword('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 to-blue-100 px-4">
      <div className="glass max-w-md w-full rounded-[28px] p-10 shadow-2xl border border-white/40">
        <div className="mb-8 text-center space-y-2">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-500 text-white text-xl font-semibold shadow-lg">
            PO
          </div>
          <h1 className="text-2xl font-semibold text-slate-900">Welcome back</h1>
          <p className="text-sm text-slate-500">Sign in to continue to your Purchase Order workspace.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-inner focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="Enter your username"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-inner focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="Enter your password"
              required
            />
          </div>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <GlassButton
            type="submit"
            variant="primary"
            className="w-full justify-center py-3 text-sm font-semibold"
            loading={loading}
            disabled={loading}
          >
            {loading ? 'Signing in…' : 'Sign in securely'}
          </GlassButton>
        </form>

        <p className="mt-8 text-xs text-center text-slate-400">
          Protected with encrypted sessions · Contact admin if you need access
        </p>
      </div>
    </div>
  )
}
