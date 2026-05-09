#Requires -Version 5.1
<#
KAP Okuryazar — tek tıkla kurulum + başlatma scripti.

Yaptıkları:
  1. Python, Git, Node kontrol eder. Eksikse winget ile kurmayı dener.
  2. backend/.env ve frontend/.env.local yoksa otomatik oluşturur.
  3. pip install + npm install çalıştırır (yalnızca gerekirse).
  4. Backend (uvicorn :8000) ve frontend (next dev :3000) için 2 ayrı pencere açar.
  5. Tarayıcıda http://localhost:3000 açar.

Kullanım:
  - start.bat dosyasına çift tıkla, ya da PowerShell'de:
      .\start.ps1
#>

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Write-Info($msg)    { Write-Host ">> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)      { Write-Host "OK $msg" -ForegroundColor Green }
function Write-Warn2($msg)   { Write-Host "!! $msg" -ForegroundColor Yellow }
function Write-Err2($msg)    { Write-Host "XX $msg" -ForegroundColor Red }

function Test-Cmd($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Ensure-Tool {
    param(
        [string]$Cmd,
        [string]$WingetId,
        [string]$DownloadUrl,
        [string]$DisplayName
    )
    if (Test-Cmd $Cmd) {
        Write-Ok "$DisplayName kurulu ($Cmd)."
        return
    }
    Write-Warn2 "$DisplayName bulunamadi."
    if (Test-Cmd "winget") {
        Write-Info "winget ile $DisplayName kuruluyor (1-2 dk surebilir)..."
        try {
            winget install --id $WingetId -e --accept-source-agreements --accept-package-agreements --silent | Out-Null
            Refresh-Path
            if (Test-Cmd $Cmd) {
                Write-Ok "$DisplayName kuruldu."
                return
            }
        } catch {
            Write-Warn2 "winget kurulumu hata verdi: $_"
        }
    }
    Write-Err2 "$DisplayName otomatik kurulamadi."
    Write-Host "    Lutfen sunu indir ve kur, sonra bu scripti tekrar calistir:" -ForegroundColor Yellow
    Write-Host "    $DownloadUrl" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=== KAP Okuryazar baslaticisi ===" -ForegroundColor Magenta
Write-Host ""

# 1) Gerekli toollari dogrula / kur
Ensure-Tool -Cmd "git"    -WingetId "Git.Git"            -DownloadUrl "https://git-scm.com/download/win"   -DisplayName "Git"
Ensure-Tool -Cmd "python" -WingetId "Python.Python.3.12" -DownloadUrl "https://www.python.org/downloads/"  -DisplayName "Python"
Ensure-Tool -Cmd "node"   -WingetId "OpenJS.NodeJS.LTS"  -DownloadUrl "https://nodejs.org/"                -DisplayName "Node.js"

# 2) .env dosyalarini olustur
$backendEnv = Join-Path $repoRoot "backend\.env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $repoRoot "backend\.env.example") $backendEnv
    Write-Ok "backend\.env olusturuldu (GEMINI_API_KEY bos -> Gemini fallback modunda calisir)."
} else {
    Write-Ok "backend\.env mevcut."
}

$frontendEnv = Join-Path $repoRoot "frontend\.env.local"
if (-not (Test-Path $frontendEnv)) {
    Copy-Item (Join-Path $repoRoot "frontend\.env.example") $frontendEnv
    Write-Ok "frontend\.env.local olusturuldu."
} else {
    Write-Ok "frontend\.env.local mevcut."
}

# 3) Python paketleri (yalniz gerekli ise)
$backendDir = Join-Path $repoRoot "backend"
Push-Location $backendDir
try {
    Write-Info "Backend Python paketleri kontrol ediliyor..."
    $needPip = $false
    try {
        python -c "import fastapi, uvicorn, dotenv, requests, bs4, rapidfuzz, pypdf" 2>$null
        if ($LASTEXITCODE -ne 0) { $needPip = $true }
    } catch {
        $needPip = $true
    }
    if ($needPip) {
        Write-Info "pip install calisiyor (1-2 dk)..."
        python -m pip install --upgrade pip | Out-Null
        python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Err2 "pip install basarisiz."
            exit 1
        }
        Write-Ok "Python paketleri kuruldu."
    } else {
        Write-Ok "Python paketleri zaten kurulu."
    }
} finally {
    Pop-Location
}

# 4) npm paketleri (yalniz node_modules yoksa)
$frontendDir = Join-Path $repoRoot "frontend"
Push-Location $frontendDir
try {
    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        Write-Info "npm install calisiyor (2-3 dk)..."
        npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) {
            Write-Err2 "npm install basarisiz."
            exit 1
        }
        Write-Ok "Frontend paketleri kuruldu."
    } else {
        Write-Ok "Frontend node_modules mevcut."
    }
} finally {
    Pop-Location
}

# 5) Backend ve frontend'i ayri pencerelerde baslat
Write-Info "Backend (uvicorn :8000) yeni pencerede baslatiliyor..."
$backendCmd = "cd `"$backendDir`"; Write-Host '=== KAP Okuryazar BACKEND (port 8000) ===' -ForegroundColor Cyan; Write-Host 'Kapatmak icin Ctrl+C'; Write-Host ''; uvicorn app.main:app --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null

Start-Sleep -Seconds 2

Write-Info "Frontend (next dev :3000) yeni pencerede baslatiliyor..."
$frontendCmd = "cd `"$frontendDir`"; Write-Host '=== KAP Okuryazar FRONTEND (port 3000) ===' -ForegroundColor Magenta; Write-Host 'Kapatmak icin Ctrl+C'; Write-Host ''; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null

# 6) Tarayiciyi ac
Write-Info "Tarayici 6 saniye sonra acilacak..."
Start-Sleep -Seconds 6
Start-Process "http://localhost:3000"

Write-Host ""
Write-Ok "Hepsi calisiyor."
Write-Host "  Backend  : http://localhost:8000/health"
Write-Host "  Frontend : http://localhost:3000"
Write-Host ""
Write-Host "Iki ayri PowerShell penceresi acildi. Kapatmak icin onlarda Ctrl+C bas." -ForegroundColor Yellow
Write-Host ""
