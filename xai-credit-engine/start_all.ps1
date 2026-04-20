$ErrorActionPreference = "Stop"

Write-Host "XAI Credit Engine Başlatılıyor..." -ForegroundColor Cyan

# Backend'i arka planda başlat
Write-Host "Backend başlatılıyor (Port 8000)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "python3" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory ".\backend"

Start-Sleep -Seconds 3

# Frontend'i başlat
Write-Host "Frontend başlatılıyor (Port 5173)..." -ForegroundColor Yellow
Set-Location ".\frontend"
npm run dev
