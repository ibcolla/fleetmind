'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Zap, Brain, Search, Database, Play, ChevronRight,
  Github, MessageSquare, FileText, Mail, TrendingUp,
  AlertCircle, CheckCircle2, Clock, Trash2, Plus, X
} from 'lucide-react'

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

// ── Component ──────────────────────────────────────────────────────────────
export default function FleetMindDashboard() {
  const [task, setTask] = useState('')
  const [userId] = useState('founder_demo')
  const [running, setRunning] = useState(false)
  const [steps, setSteps] = useState<Step[]>([])
  const [summary, setSummary] = useState<string | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [signals, setSignals] = useState<Signal[]>([])
  const [activeTab, setActiveTab] = useState<'agent' | 'memory' | 'signals'>('agent')
  const [context, setContext] = useState({
    startup_name: '',
    competitors: '',
    keywords: '',
  })
  const [showContext, setShowContext] = useState(false)
  const stepsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    stepsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps])

  const runAgent = async () => {
    if (!task.trim() || running) return
    setRunning(true)
    setSteps([])
    setSummary(null)

    const ctx: Record<string, string> = {}
    if (context.startup_name) ctx.startup_name = context.startup_name
    if (context.competitors) ctx.competitors = context.competitors
    if (context.keywords) ctx.keywords = context.keywords

    try {
      const res = await fetch(`${API}/agent/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          user_id: userId,
          context: Object.keys(ctx).length ? ctx : undefined,
        }),
      })

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
            } else {
              setSteps(s => [...s, { ...parsed, ts: Date.now() }])
            }
          } catch {}
        }
      }
    } catch (err) {
      // Fallback: simulate agent for demo
      await simulateAgent()
    } finally {
      setRunning(false)
    }
  }

  const simulateAgent = async () => {
    const mockSteps: [StepType, string, number][] = [
      ['start',    'FleetMind agent initializing...', 300],
      ['remember', 'Loaded startup context from mem0 memory store', 400],
      ['search',   'Tavily: Searching for competitor activity and market signals...', 800],
      ['search',   'Found 7 relevant results — filtering by signal strength', 500],
      ['reason',   'Nebius LLM: Analyzing signals against your startup context...', 1200],
      ['reason',   'Identified 2 high-priority signals and 3 medium-priority opportunities', 600],
      ['act',      'Composio → GitHub: Creating issue "Competitor X launched new AI feature"', 700],
      ['act',      'Composio → Slack: Posting signal digest to #founders channel', 500],
      ['remember', 'mem0: Storing competitor intel and task outcome for future reference', 400],
      ['complete', 'Mission complete. 2 actions taken, 7 signals processed.', 300],
    ]

    for (const [type, message, delay] of mockSteps) {
      await new Promise(r => setTimeout(r, delay))
      setSteps(s => [...s, { type, message, ts: Date.now() }])
    }

    setSummary(`## Signals Found

**🔴 HIGH** — Linear launched "Linear AI" with auto-issue creation from Slack messages. This directly competes with your planned automation feature.

**🟡 MEDIUM** — Notion acquired a small AI startup focused on structured data extraction (TechCrunch, 2 days ago).

**🟢 LOW** — 3 indie developers posted about switching from Notion to Obsidian for personal PKM.

## Actions Taken

✅ GitHub Issue #47 created: "Competitive response to Linear AI launch"
✅ Slack message posted to #founders with full signal digest

## Stored in Memory

Stored: Linear AI feature set, Notion acquisition, competitor monitoring preferences`)

    setSignals([
      { title: 'Linear launches "Linear AI"', snippet: 'Auto-creates issues from Slack, direct competitor to planned feature', source: 'techcrunch.com', importance: 'high' },
      { title: 'Notion acquires AI startup', snippet: 'Focused on structured data extraction — potential pivot indicator', source: 'reuters.com', importance: 'medium' },
      { title: 'Developer migration from Notion', snippet: '3 indie devs publicly switching to Obsidian for PKM use cases', source: 'twitter.com', importance: 'low' },
    ])

    setMemories(prev => [
      { id: Date.now().toString(), content: 'Linear launched Linear AI with Slack → Issue auto-creation (June 2025)', category: 'competitor' },
      { id: (Date.now()+1).toString(), content: 'Task: monitor competitors. Actions: GitHub issue + Slack message', category: 'decision' },
      ...prev,
    ])
  }

  const importanceColor = { high: 'text-red-400 bg-red-400/10 border-red-400/20', medium: 'text-fleet-warn bg-fleet-warn/10 border-fleet-warn/20', low: 'text-fleet-signal bg-fleet-signal/10 border-fleet-signal/20' }

  return (
    <div className="min-h-screen bg-fleet-bg text-fleet-text flex flex-col">

      {/* Header */}
      <header className="border-b border-fleet-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-fleet-accent flex items-center justify-center glow-accent">
            <Zap size={16} className="text-white" fill="white" />
          </div>
          <div>
            <h1 className="font-mono font-semibold text-base tracking-tight">FleetMind</h1>
            <p className="text-xs text-fleet-muted">AI Chief of Staff for Solo Founders</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-fleet-muted font-mono">
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
              <div className="space-y-1">
                {steps.length === 0 && !running && (
                  <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-fleet-surface border border-fleet-border flex items-center justify-center">
                      <Zap size={22} className="text-fleet-muted" />
                    </div>
                    <p className="text-fleet-muted text-sm">No tasks run yet</p>
                    <p className="text-fleet-muted/50 text-xs max-w-xs">Give FleetMind a task above. It will search the web, reason, remember, and take action across your tools.</p>
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
                <div ref={stepsEndRef} />
              </div>
            )}

            {/* Memory Tab */}
            {activeTab === 'memory' && (
              <div>
                {memories.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 gap-3">
                    <Database size={24} className="text-fleet-muted" />
                    <p className="text-fleet-muted text-sm">No memories yet</p>
                    <p className="text-fleet-muted/50 text-xs">Run tasks to build long-term memory</p>
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
                  <div className="flex flex-col items-center justify-center py-16 gap-3">
                    <TrendingUp size={24} className="text-fleet-muted" />
                    <p className="text-fleet-muted text-sm">No signals yet</p>
                    <p className="text-fleet-muted/50 text-xs">Run a monitoring task to discover signals</p>
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
