# Nova Agent — Start backend, frontend, and optional LangGraph Studio

param(
    [switch]$Studio  # Pass -Studio to also start the LangGraph dev server
)

Write-Host "=== Nova Agent ===" -ForegroundColor Cyan

# Backend
Write-Host "`n[1/3] Starting backend on :8010..." -ForegroundColor Yellow
$backendJob = Start-Process -PassThru -NoNewWindow -FilePath "$PSScriptRoot\venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--reload" -WorkingDirectory "$PSScriptRoot\backend"

# Frontend
Write-Host "[2/3] Starting frontend on :5174..." -ForegroundColor Yellow
$frontendJob = Start-Process -PassThru -NoNewWindow -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory "$PSScriptRoot\frontend"

# LangGraph Studio (opcional)
if ($Studio) {
    Write-Host "[3/3] Starting LangGraph Studio on :2024..." -ForegroundColor Yellow
    $studioJob = Start-Process -PassThru -NoNewWindow -FilePath "$PSScriptRoot\venv\Scripts\langgraph.exe" -ArgumentList "dev", "--port", "2024" -WorkingDirectory "$PSScriptRoot\backend"
    Write-Host "  LangGraph Studio: http://localhost:2024" -ForegroundColor Magenta
    Write-Host "  (o abre https://smith.langchain.com/studio y conecta a localhost:2024)" -ForegroundColor DarkGray
} else {
    Write-Host "[3/3] LangGraph Studio omitido. Usa: .\start.ps1 -Studio para activarlo." -ForegroundColor DarkGray
}

Write-Host "`nNova Agent running:" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8010" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5174" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop." -ForegroundColor Gray

try { Wait-Process -Id $backendJob.Id } catch {}
