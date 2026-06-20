#!/usr/bin/env bash
set -euo pipefail

echo "==> Setting up backend (Python / FastAPI)"
cd "$(dirname "$0")/.."
cd backend
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
deactivate
cd ..

echo "==> Setting up frontend (Vue 3 / Vite / TS)"
cd frontend
npm install
cd ..

echo "==> Installing Claude Code CLI"
npm install -g @anthropic-ai/claude-code

echo "==> Done. Next steps:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0"
echo "  Frontend: cd frontend && npm run dev -- --host"
echo "  GitHub:   gh auth login   # then  gh repo create"
echo "  Claude:   claude          # first run prompts for authentication"
