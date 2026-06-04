# setup.ps1
# Run ONCE after cloning the repo.
# Sets up Python venvs, installs all dependencies, creates .env

Write-Host "🔧 NeuroLens Setup" -ForegroundColor Cyan
Write-Host "This will take 5-10 minutes (downloading models and packages)." -ForegroundColor Yellow
Write-Host ""

# Copy .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env from .env.example" -ForegroundColor Green
}

# Backend venv
Write-Host "📦 Setting up backend..." -ForegroundColor Yellow
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
Set-Location ..
Write-Host "✅ Backend ready" -ForegroundColor Green

# NPU engine venv (shares backend venv for simplicity)
Write-Host "⚡ Setting up NPU engine..." -ForegroundColor Yellow
Set-Location npu_engine
# Use backend venv — no separate venv needed
..\backend\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Write-Host "Exporting embedding model to ONNX (one time, ~30-60s)..."
python -c "from inference.embedding_runner import export_to_onnx; export_to_onnx()"
deactivate
Set-Location ..
Write-Host "✅ NPU engine ready" -ForegroundColor Green

# Speech service venv
Write-Host "🎙 Setting up speech service..." -ForegroundColor Yellow
Set-Location speech_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
Set-Location ..
Write-Host "✅ Speech service ready" -ForegroundColor Green

# Frontend
Write-Host "⚛️  Setting up frontend..." -ForegroundColor Yellow
Set-Location frontend
npm install
Set-Location ..
Write-Host "✅ Frontend ready" -ForegroundColor Green

# Ollama model
Write-Host ""
Write-Host "📥 Pulling Llama 3 model (3.8 GB — will take a while)..." -ForegroundColor Yellow
Write-Host "   Make sure Ollama is installed: https://ollama.ai/download" -ForegroundColor Gray
ollama pull llama3

Write-Host ""
Write-Host "🎉 Setup complete! Run: .\start-dev.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run .\start-dev.ps1" -ForegroundColor White
Write-Host "  2. Open http://localhost:5173 and register an account" -ForegroundColor White
Write-Host "  3. Upload a PDF and try asking a question" -ForegroundColor White
Write-Host "  4. Run: cd npu_engine && python benchmark.py" -ForegroundColor White
Write-Host "     → Record the CPU vs NPU numbers for your README!" -ForegroundColor Yellow
