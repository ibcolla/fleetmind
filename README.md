# ⚡ FleetMind — AI Chief of Staff for Solo Founders

> **Monitor signals. Reason. Remember. Act.** Your autonomous AI ops agent that never sleeps.

![FleetMind Banner](docs/banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Built for BuilderShip](https://img.shields.io/badge/Built%20for-BuilderShip%20Hackathon-orange.svg)](https://ship.builders)

---

## 🎯 The Problem

Solo founders are drowning in noise. Every day you miss:
- A competitor launching a feature that threatens your roadmap
- A market signal that could redefine your positioning  
- An inbound opportunity buried in your inbox
- A trend that should inform your next sprint

You can't hire a Chief of Staff. **FleetMind is that hire.**

---

## 🤖 What FleetMind Does

FleetMind runs a continuous **4-step intelligence loop**:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   SEARCH    │───▶│   REASON    │───▶│  REMEMBER   │───▶│     ACT     │
│   Tavily    │    │   Nebius    │    │    mem0     │    │  Composio   │
│  real-time  │    │  LLM 70B    │    │  long-term  │    │ 250+ tools  │
│   signals   │    │  synthesis  │    │   memory    │    │  execution  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**Example task**: *"Monitor my competitors Linear and Notion for new launches"*

1. 🔍 **Tavily** searches the web for competitor activity in real-time
2. 🧠 **Nebius LLM** (Llama 3.1 70B) synthesizes findings into prioritized insights
3. 💾 **mem0** stores competitor intel and recalls past context across sessions  
4. ⚡ **Composio** creates a GitHub issue, posts a Slack alert, drafts a Notion report

---

## 🏗 Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         FleetMind Frontend                         │
│                    Next.js 14 + Tailwind CSS                       │
│          Agent Log │ Memory Browser │ Signal Dashboard             │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ REST + SSE Stream
┌──────────────────────────────▼─────────────────────────────────────┐
│                         FastAPI Backend                             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    FleetMind Agent                           │   │
│  │           LangChain AgentExecutor (OpenAI Functions)         │   │
│  └──────┬──────────────┬──────────────┬──────────────┬─────────┘   │
│         │              │              │              │              │
│  ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐      │
│  │   Tavily    │ │   Nebius   │ │   mem0   │ │  Composio  │      │
│  │  3 search   │ │ Llama3.1   │ │ Memory   │ │ 5 action   │      │
│  │   tools     │ │   70B      │ │  Client  │ │  tools     │      │
│  └─────────────┘ └────────────┘ └──────────┘ └────────────┘      │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys for: Nebius, Tavily, mem0, Composio

### 1. Clone & configure

```bash
git clone https://github.com/yourusername/fleetmind.git
cd fleetmind

# Backend
cp backend/.env.example backend/.env
# Fill in your API keys in backend/.env
```

### 2. Start the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### 4. Or use Docker Compose

```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

---

## 🔑 Getting Free Sponsor Credits

| Service | Free Credits | Promo Code |
|---------|-------------|------------|
| **Composio** | 3 months Starter | `SHIP_BUILDERS` at composio.dev |
| **Nebius** | $50–100 inference credits | `BUILDER-SHIP-HACK` |
| **Tavily** | Free tier + extras | `TVLY-7CCN692Z` at tavily.com |
| **mem0** | 3 months Starter | `SHIPBUILDERS` at mem0.ai |

---

## 📡 API Reference

### Run Agent
```http
POST /agent/run
{
  "task": "Monitor my competitors for new launches",
  "user_id": "founder_123",
  "context": {
    "startup_name": "MyStartup",
    "competitors": "linear.app, notion.so",
    "keywords": "project management, AI ops"
  }
}
```

### Stream Agent (SSE)
```http
POST /agent/stream
# Returns Server-Sent Events with real-time step updates
```

### Memory
```http
GET  /memory/{user_id}           # Get all memories
DELETE /memory/{user_id}/{id}    # Delete a memory
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, Tailwind CSS, TypeScript |
| Backend | FastAPI, Python 3.11 |
| Agent Framework | LangChain (AgentExecutor, OpenAI Functions) |
| LLM Inference | **Nebius AI** (Llama 3.1 70B Instruct) |
| Web Intelligence | **Tavily** (search + extraction) |
| Persistent Memory | **mem0** (long-term agent memory) |
| Action Execution | **Composio** (GitHub, Slack, Notion, Gmail, Linear) |
| Streaming | FastAPI SSE + React EventSource |
| Deployment | Docker Compose / Vercel + Railway |

---

## 🎬 Demo

> 📹 [Watch 60-second demo](https://youtu.be/your-demo-link)

**Live demo**: [fleetmind.vercel.app](https://fleetmind.vercel.app)

---

## 🏆 Built for BuilderShip Hackathon

Built in 1 day for the [BuilderShip Yacht Hackathon](https://lu.ma/buildership) by Composio, Nebius, and Tavily.

---

## 📄 License

MIT © 2025 — Built by [Your Name](https://github.com/yourusername)
