#!/bin/bash
# FleetMind Quick Setup Script
# Run: chmod +x setup.sh && ./setup.sh

set -e

echo "⚡ FleetMind Setup"
echo "=================="

# Backend
echo ""
echo "📦 Setting up backend..."
cd backend
cp .env.example .env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "✅ Backend ready"

echo ""
echo "🔑 IMPORTANT: Fill in your API keys in backend/.env"
echo "   - NEBIUS_API_KEY (nebius.ai — code: BUILDER-SHIP-HACK)"
echo "   - TAVILY_API_KEY (tavily.com — code: TVLY-7CCN692Z)"
echo "   - MEM0_API_KEY   (mem0.ai — code: SHIPBUILDERS)"
echo "   - COMPOSIO_API_KEY (composio.dev — code: SHIP_BUILDERS)"

# Frontend
echo ""
echo "🎨 Setting up frontend..."
cd ../frontend
npm install
echo "✅ Frontend ready"

echo ""
echo "🚀 To start FleetMind:"
echo "   Terminal 1: cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "   Terminal 2: cd frontend && npm run dev"
echo ""
echo "   Or: docker-compose up --build"
echo ""
echo "   Open: http://localhost:3000"
echo ""
echo "⚡ Good luck at BuilderShip! 🛥️"
