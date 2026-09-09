'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Zap, Brain, Search, Database, Play, ChevronRight,
  Github, MessageSquare, FileText, Mail, TrendingUp,
  AlertCircle, CheckCircle2, Trash2, LogOut, LogIn, UserPlus,
  CreditCard, Sparkles, ArrowRight
} from 'lucide-react'
import { signIn, signUp, signOut, onAuthStateChange, getAuthHeaders } from '../lib/auth'
import type { User } from '@supabase/supabase-js'
import { Logo } from '../components/Logo'

// ── Types ──────────────────────────────────────────────────────────────────
type StepType = 'search' | 'reason' | 'remember' | 'act' | 'start' | 'complete' | 'error'

interface Step {
  type: StepType
  message: string
  tool?: string
  ts: number
}

interface Memory {
  id: string
  content: string
  category: string
}

interface Signal {
  title: string
  snippet: string
  source: string
  importance: 'high' | 'medium' | 'low'
}

// ── Constants ──────────────────────────────────────────────────────────────
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const STEP_META: Record<StepType, { icon: React.ReactNode; color: string; label: string }> = {
  start:    { icon: <Zap size={13} />,           color: 'text-fleet-accent',  label: 'INIT'    },
  search:   { icon: <Search size={13} />,        color: 'text-blue-400',      label: 'SEARCH'  },
  reason:   { icon: <Brain size={13} />,         color: 'text-purple-400',    label: 'REASON'  },
  remember: { icon: <Database size={13} />,      color: 'text-fleet-signal',  label: 'MEMORY'  },
  act:      { icon: <Zap size={13} />,           color: 'text-fleet-warn',    label: 'ACT'     },
  complete: { icon: <CheckCircle2 size={13} />,  color: 'text-fleet-signal',  label: 'DONE'    },
  error:    { icon: <AlertCircle size={13} />,   color: 'text-fleet-danger',  label: 'ERROR'   },
}

const ACTION_ICONS: Record<string, React.ReactNode> = {
  github:  <Github size={14} />,
  slack:   <MessageSquare size={14} />,
  notion:  <FileText size={14} />,
  gmail:   <Mail size={14} />,
  linear:  <TrendingUp size={14} />,
}

const EXAMPLE_TASKS = [
  "Monitor my competitors Linear and Notion for new launches this week",
  "Search for AI agent framework trends and create a GitHub issue with findings",
  "Find any Product Hunt launches in the project management space today",
  "Check if there are any negative mentions of my brand on social media",
  "Research the latest funding rounds in B2B SaaS and draft a Notion page",
]

// ── Auth Gate Component ────────────────────────────────────────────────────
function AuthGate({ onAuthenticated }: { onAuthenticated: (user: User) => void }) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) return
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      if (mode === 'signin') {
        const { user, error: authError } = await signIn(email, password)
        if (authError) {
          setError(authError.message)
        } else if (user) {
          onAuthenticated(user)
        }
      } else {
        const { user, error: authError } = await signUp(email, password)
        if (authError) {
          setError(authError.message)
        } else if (user) {
          // Supabase may require email confirmation
          if (user.email_confirmed_at) {
            onAuthenticated(user)
          } else {
            setMessage('Account created! Check your email to confirm your address, then sign in.')
            setMode('signin')
          }
        }
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-fleet-bg text-fleet-text flex flex-col items-center justify-center p-4">
      {/* Logo */}
      <div className="flex flex-col items-center gap-2 mb-8 text-center">
        <Logo size={44} showText={true} textClassName="text-xl" />
        <p className="text-xs text-fleet-muted font-mono mt-1">Autonomous AI Chief of Staff for Solo Founders</p>
      </div>

      {/* Auth Card */}
      <div className="w-full max-w-sm rounded-xl border border-fleet-border bg-fleet-surface p-6">
        {/* Tab toggle */}
        <div className="flex rounded-lg border border-fleet-border overflow-hidden mb-6">
          <button
            onClick={() => { setMode('signin'); setError(null); setMessage(null) }}
            className={`flex-1 py-2 text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1.5 ${
              mode === 'signin'
                ? 'bg-fleet-accent text-white'
                : 'text-fleet-muted hover:text-fleet-text'
            }`}
          >
            <LogIn size={12} />
            Sign In
          </button>
          <button
            onClick={() => { setMode('signup'); setError(null); setMessage(null) }}
            className={`flex-1 py-2 text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1.5 ${
              mode === 'signup'
                ? 'bg-fleet-accent text-white'
                : 'text-fleet-muted hover:text-fleet-text'
            }`}
          >
            <UserPlus size={12} />
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-fleet-muted font-mono block mb-1">Email</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              className="w-full bg-fleet-bg border border-fleet-border rounded-lg px-3 py-2.5 text-sm font-mono text-fleet-text placeholder:text-fleet-muted/50 focus:outline-none focus:border-fleet-accent transition-colors"
            />
          </div>
          <div>
            <label className="text-xs text-fleet-muted font-mono block mb-1">Password</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              className="w-full bg-fleet-bg border border-fleet-border rounded-lg px-3 py-2.5 text-sm font-mono text-fleet-text placeholder:text-fleet-muted/50 focus:outline-none focus:border-fleet-accent transition-colors"
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-fleet-danger/10 border border-fleet-danger/20 p-3">
              <AlertCircle size={13} className="text-fleet-danger shrink-0 mt-0.5" />
              <p className="text-xs text-fleet-danger leading-relaxed">{error}</p>
            </div>
          )}

          {message && (
            <div className="flex items-start gap-2 rounded-lg bg-fleet-signal/10 border border-fleet-signal/20 p-3">
              <CheckCircle2 size={13} className="text-fleet-signal shrink-0 mt-0.5" />
              <p className="text-xs text-fleet-signal leading-relaxed">{message}</p>
            </div>
          )}

          <button
            id="auth-submit"
            type="submit"
            disabled={loading || !email.trim() || !password.trim()}
            className="w-full py-2.5 rounded-lg bg-fleet-accent hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 glow-accent"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : mode === 'signin' ? (
              <><LogIn size={14} /> Sign In</>
            ) : (
              <><UserPlus size={14} /> Create Account</>
            )}
          </button>
        </form>
      </div>

      <p className="mt-4 text-xs text-fleet-muted/50 font-mono">
        Powered by Supabase Auth · FleetMind Phase 1
      </p>
    </div>
  )
}

// ── Main Dashboard Component ───────────────────────────────────────────────
export default function FleetMindDashboard() {
  // Auth state
  const [authUser, setAuthUser] = useState<User | null | undefined>(undefined) // undefined = loading
  const [task, setTask] = useState('')
  const [running, setRunning] = useState(false)
  const [steps, setSteps] = useState<Step[]>([])
  const [summary, setSummary] = useState<string | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [signals, setSignals] = useState<Signal[]>([])
  const [isOverLimit, setIsOverLimit] = useState(false)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [telemetry, setTelemetry] = useState<{
    total_tokens: number
    input_tokens: number
    output_tokens: number
    estimated_cost: number
    duration_ms: number
  } | null>(null)
  const [activeTab, setActiveTab] = useState<'agent' | 'memory' | 'signals'>('agent')
  const [context, setContext] = useState({
    startup_name: '',
    competitors: '',
    keywords: '',
  })
  const [showContext, setShowContext] = useState(false)
  const stepsEndRef = useRef<HTMLDivElement>(null)

  // Subscribe to auth state on mount
  useEffect(() => {
    const unsubscribe = onAuthStateChange((user) => {
      setAuthUser(user)
    })
    return unsubscribe
  }, [])

  useEffect(() => {
    stepsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps])

  const handleSignOut = async () => {
    await signOut()
    setSteps([])
    setSummary(null)
    setMemories([])
    setSignals([])
    setIsOverLimit(false)
    setTelemetry(null)
  }

  const handleUpgradeToPro = async () => {
    setCheckoutLoading(true)
    try {
      const headers = await getAuthHeaders()
      const res = await fetch(`${API}/billing/checkout-session`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ return_url: window.location.origin }),
      })
      if (!res.ok) throw new Error('Failed to create checkout session')
      const data = await res.json()
      if (data.checkout_url) {
        window.location.href = data.checkout_url
      }
    } catch (err) {
      console.error('Checkout error:', err)
    } finally {
      setCheckoutLoading(false)
    }
  }

  const runAgent = useCallback(async () => {
    if (!task.trim() || running || !authUser) return
    setRunning(true)
    setSteps([])
    setSummary(null)
    setTelemetry(null)

    const ctx: Record<string, string> = {}
    if (context.startup_name) ctx.startup_name = context.startup_name
    if (context.competitors) ctx.competitors = context.competitors
    if (context.keywords) ctx.keywords = context.keywords

    try {
      // Get auth headers — JWT in Authorization header, NOT in URL
      const headers = await getAuthHeaders()

      const res = await fetch(`${API}/agent/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          task,
          // user_id intentionally omitted — backend derives from JWT
          context: Object.keys(ctx).length ? ctx : undefined,
        }),
      })

      if (!res.ok) {
        if (res.status === 402) {
          setIsOverLimit(true)
          setSteps(s => [...s, {
            type: 'error',
            message: 'Free tier usage limit reached (10 runs max). Please upgrade to FleetMind Pro to continue.',
            ts: Date.now()
          }])
          setRunning(false)
          return
        }
        if (res.status === 401) {
          setSteps(s => [...s, {
            type: 'error',
            message: 'Session expired. Please sign in again.',
            ts: Date.now()
          }])
          setRunning(false)
          return
        }
        throw new Error(`HTTP ${res.status}`)
      }

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No stream')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const raw = decoder.decode(value)
        for (const line of raw.split('\n')) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') { setRunning(false); break }
          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'complete') {
              setSummary(parsed.message)
              setSteps(s => [...s, { type: 'complete', message: 'Task completed', ts: Date.now() }])
            } else if (parsed.type === 'telemetry') {
              setTelemetry({
                total_tokens: parsed.total_tokens,
                input_tokens: parsed.input_tokens,
                output_tokens: parsed.output_tokens,
                estimated_cost: parsed.estimated_cost,
                duration_ms: parsed.duration_ms,
              })
            } else {
              setSteps(s => [...s, { ...parsed, ts: Date.now() }])
            }
          } catch {}
        }
      }
    } catch (err) {
      // Production error handling: render explicit error banner without fake simulation
      const errorMessage = err instanceof Error ? err.message : 'Agent execution failed.'
      setSteps(s => [...s, {
        type: 'error',
        message: `Execution error: ${errorMessage}. Please check your backend connection and configuration.`,
        ts: Date.now()
      }])
    } finally {
      setRunning(false)
    }
  }, [task, running, authUser, context])

  const importanceColor = {
    high: 'text-red-400 bg-red-400/10 border-red-400/20',
    medium: 'text-fleet-warn bg-fleet-warn/10 border-fleet-warn/20',
    low: 'text-fleet-signal bg-fleet-signal/10 border-fleet-signal/20'
  }

  // ── Loading state (checking auth) ────────────────────────────────────────
  if (authUser === undefined) {
    return (
      <div className="min-h-screen bg-fleet-bg text-fleet-text flex items-center justify-center">
        <div className="flex items-center gap-3 text-fleet-muted font-mono text-sm">
          <span className="w-4 h-4 border-2 border-fleet-muted/30 border-t-fleet-muted rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    )
  }

  // ── Unauthenticated: show login gate ─────────────────────────────────────
  if (authUser === null) {
    return <AuthGate onAuthenticated={setAuthUser} />
  }

  // ── Authenticated: show FleetMind dashboard ──────────────────────────────
  return (
    <div className="min-h-screen bg-fleet-bg text-fleet-text flex flex-col">

      {/* Header */}
      <header className="border-b border-fleet-border px-6 py-4 flex items-center justify-between">
        <Logo size={34} showText={true} />
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-fleet-muted font-mono">
            <span className="w-2 h-2 rounded-full bg-fleet-signal animate-pulse-slow inline-block" />
            <span>LIVE</span>
            <span className="mx-2 opacity-30">|</span>
            <span className="opacity-60">Powered by</span>
            <span className="text-fleet-accent ml-1">Nebius</span>
            <span className="opacity-30 mx-1">·</span>
            <span className="text-blue-400">Composio</span>
            <span className="opacity-30 mx-1">·</span>
            <span className="text-purple-400">Tavily</span>
            <span className="opacity-30 mx-1">·</span>
            <span className="text-fleet-signal">mem0</span>
          </div>
          {/* User info + upgrade button + sign out */}
          <div className="flex items-center gap-2">
            <button
              id="header-upgrade-btn"
              onClick={handleUpgradeToPro}
              disabled={checkoutLoading}
              className="hidden sm:flex items-center gap-1.5 text-xs text-fleet-accent hover:text-white bg-fleet-accent/10 hover:bg-fleet-accent transition-all px-3 py-1 rounded-lg border border-fleet-accent/30 font-mono font-medium disabled:opacity-50"
            >
              {checkoutLoading ? (
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Sparkles size={12} />
                  <span>Upgrade to Pro</span>
                </>
              )}
            </button>
            <span className="text-xs text-fleet-muted font-mono hidden sm:block truncate max-w-[140px]">
              {authUser.email}
            </span>
            <button
              id="sign-out-btn"
              onClick={handleSignOut}
              title="Sign out"
              className="flex items-center gap-1.5 text-xs text-fleet-muted hover:text-fleet-danger transition-colors px-2 py-1 rounded border border-fleet-border hover:border-fleet-danger/40 font-mono"
            >
              <LogOut size={12} />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar */}
        <aside className="w-64 border-r border-fleet-border p-4 flex flex-col gap-4 hidden lg:flex">
          <div>
            <p className="text-xs text-fleet-muted font-mono uppercase tracking-wider mb-2">Startup Context</p>
            <button
              onClick={() => setShowContext(!showContext)}
              className="w-full text-left text-xs text-fleet-muted hover:text-fleet-text transition-colors flex items-center gap-1"
            >
              <ChevronRight size={12} className={`transition-transform ${showContext ? 'rotate-90' : ''}`} />
              Configure context
            </button>
            {showContext && (
              <div className="mt-2 space-y-2 animate-slide-in">
                {['startup_name', 'competitors', 'keywords'].map(k => (
                  <div key={k}>
                    <label className="text-xs text-fleet-muted mb-1 block capitalize">{k.replace('_', ' ')}</label>
                    <input
                      value={context[k as keyof typeof context]}
                      onChange={e => setContext(c => ({ ...c, [k]: e.target.value }))}
                      placeholder={k === 'competitors' ? 'linear.app, notion.so' : k === 'keywords' ? 'AI ops, SaaS' : 'Your startup'}
                      className="w-full bg-fleet-bg border border-fleet-border rounded px-2 py-1.5 text-xs font-mono text-fleet-text placeholder:text-fleet-muted/50 focus:outline-none focus:border-fleet-accent"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-xs text-fleet-muted font-mono uppercase tracking-wider mb-2">Example Tasks</p>
            <div className="space-y-1">
              {EXAMPLE_TASKS.map((t, i) => (
                <button
                  key={i}
                  onClick={() => setTask(t)}
                  className="w-full text-left text-xs text-fleet-muted hover:text-fleet-text hover:bg-fleet-surface rounded px-2 py-1.5 transition-colors leading-relaxed"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-auto">
            <div className="rounded-lg border border-fleet-border bg-fleet-surface p-3 space-y-2">
              {[
                { label: 'Signals Today', value: signals.length.toString(), color: 'text-blue-400' },
                { label: 'Actions Taken', value: steps.filter(s => s.type === 'act').length.toString(), color: 'text-fleet-warn' },
                { label: 'Memories', value: memories.length.toString(), color: 'text-fleet-signal' },
              ].map(stat => (
                <div key={stat.label} className="flex justify-between items-center">
                  <span className="text-xs text-fleet-muted">{stat.label}</span>
                  <span className={`text-sm font-mono font-semibold ${stat.color}`}>{stat.value}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Task input */}
          <div className="border-b border-fleet-border p-4">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <textarea
                  value={task}
                  onChange={e => setTask(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) runAgent() }}
                  placeholder="What should your AI Chief of Staff do? e.g. 'Monitor my competitors and alert me to any new launches this week'"
                  rows={2}
                  className="w-full bg-fleet-surface border border-fleet-border rounded-lg px-4 py-3 text-sm font-mono text-fleet-text placeholder:text-fleet-muted/50 focus:outline-none focus:border-fleet-accent resize-none leading-relaxed pr-20"
                />
                <span className="absolute bottom-2 right-3 text-xs text-fleet-muted/40 font-mono">⌘↵</span>
              </div>
              <button
                id="run-agent-btn"
                onClick={runAgent}
                disabled={!task.trim() || running}
                className="px-5 rounded-lg bg-fleet-accent hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center gap-2 glow-accent"
              >
                {running ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Play size={15} fill="white" />
                )}
                {running ? 'Running' : 'Run'}
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-fleet-border px-4 flex gap-0">
            {(['agent', 'memory', 'signals'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-3 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-fleet-accent text-fleet-accent'
                    : 'border-transparent text-fleet-muted hover:text-fleet-text'
                }`}
              >
                {tab}
                {tab === 'memory' && memories.length > 0 && (
                  <span className="ml-1.5 bg-fleet-signal/20 text-fleet-signal text-xs rounded-full px-1.5 py-0.5">{memories.length}</span>
                )}
                {tab === 'signals' && signals.length > 0 && (
                  <span className="ml-1.5 bg-blue-400/20 text-blue-400 text-xs rounded-full px-1.5 py-0.5">{signals.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-4">

            {/* Agent Log */}
            {activeTab === 'agent' && (
              <div className="space-y-3">
                {/* Upgrade to Pro Card */}
                {isOverLimit && (
                  <div className="mb-4 rounded-xl border border-fleet-accent/40 bg-gradient-to-r from-fleet-accent/10 via-purple-500/10 to-fleet-surface p-5 shadow-lg animate-slide-in">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <div className="space-y-1.5 max-w-xl">
                        <div className="flex items-center gap-2">
                          <span className="flex items-center justify-center w-6 h-6 rounded-lg bg-fleet-accent text-white font-semibold">
                            <Sparkles size={14} />
                          </span>
                          <h2 className="text-sm font-mono font-bold text-fleet-text">
                            Free Tier Limit Reached (10 Runs Max)
                          </h2>
                        </div>
                        <p className="text-xs text-fleet-muted leading-relaxed">
                          You've reached your free 10-run limit. Upgrade to FleetMind Pro to unlock unlimited agent executions, team workspace access, and cloud strategy brief exports.
                        </p>
                        <div className="flex flex-wrap gap-3 text-xs font-mono text-fleet-text/80 pt-1">
                          <div className="flex items-center gap-1">
                            <CheckCircle2 size={12} className="text-fleet-signal" />
                            <span>Unlimited Runs</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <CheckCircle2 size={12} className="text-fleet-signal" />
                            <span>Team Workspace</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <CheckCircle2 size={12} className="text-fleet-signal" />
                            <span>Cloud Artifact Exports</span>
                          </div>
                        </div>
                      </div>
                      <button
                        id="upgrade-pro-card-btn"
                        onClick={handleUpgradeToPro}
                        disabled={checkoutLoading}
                        className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-fleet-accent hover:bg-blue-500 text-white font-mono font-semibold text-xs transition-all duration-200 shadow-md glow-accent flex items-center justify-center gap-2 shrink-0 disabled:opacity-50"
                      >
                        {checkoutLoading ? (
                          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                          <>
                            <CreditCard size={14} />
                            <span>Upgrade to Pro — $49/mo</span>
                            <ArrowRight size={13} />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {steps.length === 0 && !running && !isOverLimit && (
                  <div className="rounded-2xl border border-dashed border-fleet-border bg-fleet-surface/40 p-10 flex flex-col items-center justify-center text-center gap-4 animate-slide-in my-6">
                    <div className="w-14 h-14 rounded-2xl bg-fleet-accent/10 border border-fleet-accent/20 flex items-center justify-center glow-accent">
                      <Sparkles size={24} className="text-fleet-accent" />
                    </div>
                    <div className="space-y-1 max-w-sm">
                      <h3 className="text-sm font-mono font-semibold text-fleet-text">
                        No missions executed yet
                      </h3>
                      <p className="text-xs text-fleet-muted leading-relaxed">
                        Assign your first task to FleetMind above. Your AI Chief of Staff will monitor live signals, reason, remember context, and execute actions across your integrations.
                      </p>
                    </div>
                    <div className="flex flex-wrap justify-center gap-2 pt-2 max-w-md">
                      <button
                        onClick={() => setTask("Monitor my competitors Linear and Notion for new launches this week")}
                        className="text-xs font-mono px-3 py-1.5 rounded-lg border border-fleet-border bg-fleet-surface hover:border-fleet-accent/50 hover:text-fleet-accent transition-all text-fleet-muted"
                      >
                        ⚡ Competitor Monitor
                      </button>
                      <button
                        onClick={() => setTask("Search for AI agent framework trends and create a GitHub issue with findings")}
                        className="text-xs font-mono px-3 py-1.5 rounded-lg border border-fleet-border bg-fleet-surface hover:border-fleet-accent/50 hover:text-fleet-accent transition-all text-fleet-muted"
                      >
                        🚀 Tech Trends → GitHub
                      </button>
                    </div>
                  </div>
                )}

                {steps.map((step, i) => {
                  const meta = STEP_META[step.type]
                  return (
                    <div key={i} className="flex gap-3 animate-slide-in py-2 border-b border-fleet-border/30">
                      <div className={`flex items-center gap-1.5 font-mono text-xs w-20 shrink-0 ${meta.color}`}>
                        {meta.icon}
                        <span>{meta.label}</span>
                      </div>
                      <p className="text-xs text-fleet-muted leading-relaxed flex-1">{step.message}</p>
                      <span className="text-xs text-fleet-muted/30 font-mono shrink-0">
                        {new Date(step.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  )
                })}

                {running && (
                  <div className="flex gap-3 py-2">
                    <div className="flex items-center gap-1.5 font-mono text-xs w-20 shrink-0 text-fleet-accent">
                      <Brain size={13} />
                      <span>THINK</span>
                    </div>
                    <p className="text-xs text-fleet-muted cursor-blink">Processing</p>
                  </div>
                )}

                {summary && (
                  <div className="mt-4 rounded-xl border border-fleet-accent/30 bg-fleet-accent/5 p-4 animate-slide-in">
                    <p className="text-xs font-mono text-fleet-accent mb-3 uppercase tracking-wider">Agent Summary</p>
                    <div className="text-sm text-fleet-text leading-relaxed whitespace-pre-line">{summary}</div>
                  </div>
                )}

                {telemetry && (
                  <div className="mt-4 rounded-xl border border-fleet-signal/30 bg-fleet-signal/5 p-3 flex flex-wrap items-center justify-between gap-3 animate-slide-in font-mono text-xs">
                    <div className="flex items-center gap-2 text-fleet-signal font-semibold">
                      <Sparkles size={14} />
                      <span>Execution Telemetry (Nebius Token Factory)</span>
                    </div>
                    <div className="flex items-center gap-4 text-fleet-text">
                      <div>
                        <span className="text-fleet-muted">Latency: </span>
                        <span className="text-purple-400 font-bold">{(telemetry.duration_ms / 1000).toFixed(1)}s</span>
                      </div>
                      <div>
                        <span className="text-fleet-muted">Tokens: </span>
                        <span className="text-fleet-accent font-bold">{telemetry.total_tokens.toLocaleString()} ({telemetry.input_tokens} in / {telemetry.output_tokens} out)</span>
                      </div>
                      <div>
                        <span className="text-fleet-muted">Estimated Cost: </span>
                        <span className="text-fleet-signal font-bold">${telemetry.estimated_cost.toFixed(6)}</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={stepsEndRef} />
              </div>
            )}

            {/* Memory Tab */}
            {activeTab === 'memory' && (
              <div>
                {memories.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-fleet-border bg-fleet-surface/40 p-10 flex flex-col items-center justify-center text-center gap-4 animate-slide-in my-6">
                    <div className="w-14 h-14 rounded-2xl bg-fleet-signal/10 border border-fleet-signal/20 flex items-center justify-center">
                      <Database size={24} className="text-fleet-signal" />
                    </div>
                    <div className="space-y-1 max-w-sm">
                      <h3 className="text-sm font-mono font-semibold text-fleet-text">
                        Workspace memory is clear
                      </h3>
                      <p className="text-xs text-fleet-muted leading-relaxed">
                        FleetMind automatically extracts key decisions, competitor insights, and founder preferences into your tenant-isolated mem0 memory store as tasks complete.
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setActiveTab('agent')
                        setTask("Monitor my competitors Linear and Notion for new launches this week")
                      }}
                      className="text-xs font-mono px-4 py-2 rounded-lg bg-fleet-signal/10 hover:bg-fleet-signal/20 text-fleet-signal border border-fleet-signal/30 transition-all flex items-center gap-2 mt-1"
                    >
                      <span>Run a task to build memory</span>
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-xs text-fleet-muted font-mono">{memories.length} memories stored in mem0</p>
                    </div>
                    {memories.map(m => (
                      <div key={m.id} className="rounded-lg border border-fleet-border bg-fleet-surface p-3 flex gap-3 group animate-slide-in">
                        <span className={`text-xs font-mono px-2 py-0.5 rounded shrink-0 h-fit ${
                          m.category === 'competitor' ? 'bg-red-400/10 text-red-400' :
                          m.category === 'decision' ? 'bg-fleet-accent/10 text-fleet-accent' :
                          m.category === 'preference' ? 'bg-purple-400/10 text-purple-400' :
                          'bg-fleet-muted/10 text-fleet-muted'
                        }`}>{m.category}</span>
                        <p className="text-xs text-fleet-text leading-relaxed flex-1">{m.content}</p>
                        <button
                          onClick={() => setMemories(prev => prev.filter(x => x.id !== m.id))}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-fleet-muted hover:text-fleet-danger"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Signals Tab */}
            {activeTab === 'signals' && (
              <div>
                {signals.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-fleet-border bg-fleet-surface/40 p-10 flex flex-col items-center justify-center text-center gap-4 animate-slide-in my-6">
                    <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                      <TrendingUp size={24} className="text-blue-400" />
                    </div>
                    <div className="space-y-1 max-w-sm">
                      <h3 className="text-sm font-mono font-semibold text-fleet-text">
                        No market signals detected yet
                      </h3>
                      <p className="text-xs text-fleet-muted leading-relaxed">
                        Tavily & Deep Reader automatically discover real-time market shifts, competitor moves, and product launches when you trigger market monitoring runs.
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setActiveTab('agent')
                        setTask("Find any Product Hunt launches in the project management space today")
                      }}
                      className="text-xs font-mono px-4 py-2 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 transition-all flex items-center gap-2 mt-1"
                    >
                      <span>Scan Product Hunt for signals</span>
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-fleet-muted font-mono mb-3">{signals.length} signals detected via Tavily</p>
                    {signals.map((s, i) => (
                      <div key={i} className="rounded-xl border border-fleet-border bg-fleet-surface p-4 animate-slide-in">
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <h3 className="text-sm font-medium text-fleet-text leading-tight">{s.title}</h3>
                          <span className={`text-xs font-mono px-2 py-0.5 rounded border shrink-0 ${importanceColor[s.importance]}`}>
                            {s.importance.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-fleet-muted leading-relaxed">{s.snippet}</p>
                        <p className="text-xs text-fleet-muted/50 font-mono mt-2">{s.source}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
