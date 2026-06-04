# start-dev.ps1
# NeuroLens development startup script for Windows
# Run from the neurolens/ root: .\start-dev.ps1
#
# What this does:
#   1. Starts Docker infrastructure (Postgres, MinIO, ChromaDB)
#   2. Activates Python venv and starts backend
#   3. Starts speech service
#   4. Starts frontend dev server
#   5. Opens browser to http://localhost:5173
#
# Prerequisites (run once):
#   - Docker Desktop installed and running
#   - Python 3.11+ installed
#   - Node.js 20+ installed
#   - Ollama installed: https://ollama.ai/download
#   - Run setup.ps1 first for initial install

Write-Host "🧠 Starting NeuroLens..." -ForegroundColor Cyan

# Check Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# 1. Start infrastructure
Write-Host "📦 Starting infrastructure..." -ForegroundColor Yellow
Set-Location infra
docker compose up -d
Set-Location ..

# Wait for Postgres to be ready
Write-Host "⏳ Waiting for Postgres..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 2. Start backend in new terminal
Write-Host "🔧 Starting backend API..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD\backend'; .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload --port 8000"
)

# 3. Start speech service in new terminal
Write-Host "🎙 Starting speech service..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD\speech_service'; .\.venv\Scripts\Activate.ps1; uvicorn server:app --port 8002 --reload"
)

# 4. Start frontend in new terminal
Write-Host "⚛️  Starting frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD\frontend'; npm run dev"
)

Start-Sleep -Seconds 4

Write-Host ""
Write-Host "✅ NeuroLens is starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "  🌐 Frontend:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "  📡 Backend API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  🗄  MinIO UI:   http://localhost:9001  (minioadmin / minioadmin123)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ⚡ Don't forget to run: ollama serve" -ForegroundColor Yellow
Write-Host ""

# Open browser
Start-Process "http://localhost:5173"
