#Requires -Version 5.0
<#
.SYNOPSIS
  Start the integrated Disaster-Affected Family Reunification + FloodSafe Chennai platform
  
.DESCRIPTION
  Launches all required services in the correct order:
  1. Reunification Backend (port 8000)
  2. FloodSafe Backend (port 8090)
  3. Reunification Frontend (port 5173)
  4. FloodSafe Frontend (port 8001)
  5. Express Reverse Proxy (port 3001)
  
.EXAMPLE
  .\start-integrated.ps1
  
.NOTES
  Requires: Node.js 18+, Python 3.10+
  Stop with: Ctrl+C in terminal or use Stop-IntegratedPlatform
#>

param(
  [switch]$SkipProxy = $false,   # Skip proxy startup
  [switch]$Help = $false         # Show help
)

if ($Help) {
  Get-Help $MyInvocation.MyCommand.Path
  exit 0
}

$ErrorActionPreference = "Stop"
$WarningPreference = "SilentlyContinue"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $ROOT "backend"
$FRONTEND_DIR = Join-Path $ROOT "frontend"
$FLOODSAFE_DIR = Join-Path $ROOT "floodsafe-chennai"
$FLOODSAFE_BACKEND_DIR = Join-Path $FLOODSAFE_DIR "backend"
$FLOODSAFE_FRONTEND_DIR = Join-Path $FLOODSAFE_DIR "frontend"

$logDir = Join-Path $ROOT "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$startedProcesses = @()

# ============================================================================
# Helper functions
# ============================================================================

function Write-Header([string]$text) {
  Write-Host ""
  Write-Host "================================================================" -ForegroundColor Cyan
  Write-Host "  $text" -ForegroundColor Cyan
  Write-Host "================================================================" -ForegroundColor Cyan
}

function Write-Success([string]$service, [string]$status) {
  Write-Host "  [OK] $service : $status" -ForegroundColor Green
}

function Write-Error-Msg([string]$service, [string]$status) {
  Write-Host "  [ERROR] $service : $status" -ForegroundColor Red
}

function Write-Warning-Msg([string]$service, [string]$status) {
  Write-Host "  [WARN] $service : $status" -ForegroundColor Yellow
}

function Test-PortAvailable([int]$port) {
  try {
    $socket = New-Object System.Net.Sockets.TcpClient
    $socket.Connect('127.0.0.1', $port)
    $socket.Close()
    return $false  # Port in use
  } catch {
    return $true   # Port available
  }
}

function Test-PortListening([int]$port, [int]$maxWait = 30) {
  $elapsed = 0
  while ($elapsed -lt $maxWait) {
    if (-not (Test-PortAvailable $port)) {
      return $true
    }
    Start-Sleep -Seconds 1
    $elapsed += 1
  }
  return $false
}

function Ensure-Tool([string]$tool, [string]$name) {
  try {
    $version = & $tool --version 2>&1 | Select-Object -First 1
    Write-Success "Tool: $name" "Found"
    return $true
  } catch {
    Write-Error-Msg "Tool: $name" "NOT FOUND - Install $name and try again"
    return $false
  }
}

function Start-ServiceProcess([string]$name, [string]$workDir, [string]$command, [string[]]$args, [string]$logFile) {
  Write-Host "    Starting $name from $workDir..."
  
  try {
    $process = Start-Process -FilePath $command `
      -ArgumentList $args `
      -WorkingDirectory $workDir `
      -RedirectStandardOutput $logFile `
      -RedirectStandardError "$logFile.err" `
      -NoNewWindow `
      -PassThru
    
    $script:startedProcesses += $process
    Write-Success "$name" "PID $($process.Id)"
    return $process
  } catch {
    Write-Error-Msg "$name" "Failed to start: $_"
    return $null
  }
}

function Stop-IntegratedPlatform {
  Write-Header "Stopping all services"
  foreach ($process in $script:startedProcesses) {
    try {
      if (-not $process.HasExited) {
        Write-Host "  Stopping PID $($process.Id)..."
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
      }
    } catch {
      Write-Warning-Msg "Process $($process.Id)" "Could not stop: $_"
    }
  }
  Write-Success "Cleanup" "All services stopped"
}

# Trap Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
  Stop-IntegratedPlatform
}

# ============================================================================
# Main startup
# ============================================================================

Write-Host ""
Write-Header "INTEGRATED PLATFORM STARTUP"

# Check prerequisites
Write-Header "Checking Prerequisites"
$allOk = $true
$allOk = (Ensure-Tool "node" "Node.js") -and $allOk
$allOk = (Ensure-Tool "python" "Python") -and $allOk

if (-not $allOk) {
  Write-Error-Msg "Setup" "Missing required tools"
  exit 1
}

# Check ports
Write-Header "Checking Port Availability"
$ports = @(5173, 8000, 8001, 8090, 3001)
foreach ($port in $ports) {
  if (Test-PortAvailable -port $port) {
    Write-Success "Port $port" "Available"
  } else {
    Write-Error-Msg "Port $port" "Already in use"
    Write-Host "Use 'netstat -ano | findstr $port' to find the process"
    exit 1
  }
}

# Install dependencies
Write-Header "Preparing Dependencies"

# Reunification Backend
$backendVenv = Join-Path $BACKEND_DIR "venv"
if (-not (Test-Path $backendVenv)) {
  Write-Host "  Creating Python venv for Reunification Backend..."
  Push-Location $BACKEND_DIR
  python -m venv venv 2>&1 | Out-Null
  & ".\venv\Scripts\pip.exe" install -q -r requirements.txt 2>&1 | Out-Null
  Pop-Location
  Write-Success "Reunification Backend" "Virtual environment created"
} else {
  Write-Success "Reunification Backend" "Virtual environment ready"
}

# Proxy node_modules
$proxyModules = Join-Path $ROOT "node_modules"
if (-not (Test-Path $proxyModules)) {
  Write-Host "  Installing npm dependencies for proxy..."
  Push-Location $ROOT
  npm install --silent 2>&1 | Out-Null
  Pop-Location
  Write-Success "Proxy" "npm dependencies installed"
} else {
  Write-Success "Proxy" "npm dependencies ready"
}

# FloodSafe Frontend dependencies
$floodsafeFrontendModules = Join-Path $FLOODSAFE_FRONTEND_DIR "node_modules"
if (-not (Test-Path $floodsafeFrontendModules)) {
  Write-Host "  Installing npm dependencies for FloodSafe Frontend..."
  Push-Location $FLOODSAFE_FRONTEND_DIR
  npm install --silent 2>&1 | Out-Null
  Pop-Location
  Write-Success "FloodSafe Frontend" "npm dependencies installed"
} else {
  Write-Success "FloodSafe Frontend" "npm dependencies ready"
}

# FloodSafe Backend
$floodsafeBackendVenv = Join-Path $FLOODSAFE_BACKEND_DIR "venv"
if (-not (Test-Path $floodsafeBackendVenv)) {
  Write-Host "  Creating Python venv for FloodSafe Backend..."
  Push-Location $FLOODSAFE_BACKEND_DIR
  python -m venv venv 2>&1 | Out-Null
  & ".\venv\Scripts\pip.exe" install -q -r requirements.txt 2>&1 | Out-Null
  Pop-Location
  Write-Success "FloodSafe Backend" "Virtual environment created"
} else {
  Write-Success "FloodSafe Backend" "Virtual environment ready"
}

# Reunification Frontend dependencies
$reunificationFrontendModules = Join-Path $FRONTEND_DIR "node_modules"
if (-not (Test-Path $reunificationFrontendModules)) {
  Write-Host "  Installing npm dependencies for Reunification Frontend..."
  Push-Location $FRONTEND_DIR
  npm install --silent 2>&1 | Out-Null
  Pop-Location
  Write-Success "Reunification Frontend" "npm dependencies installed"
} else {
  Write-Success "Reunification Frontend" "npm dependencies ready"
}

# Start services
Write-Header "Starting Services"

# Backend services first
$backendLog = Join-Path $logDir "reunification-backend.log"
$backendProc = Start-ServiceProcess `
  "Reunification Backend" `
  $BACKEND_DIR `
  "python" `
  @("-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000") `
  $backendLog

$floodsafeBackendLog = Join-Path $logDir "floodsafe-backend.log"
$floodsafeBackendProc = Start-ServiceProcess `
  "FloodSafe Backend" `
  $FLOODSAFE_BACKEND_DIR `
  "python" `
  @("-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8090") `
  $floodsafeBackendLog

Start-Sleep -Seconds 3

# Frontend services
$frontendLog = Join-Path $logDir "reunification-frontend.log"
$frontendProc = Start-ServiceProcess `
  "Reunification Frontend" `
  $FRONTEND_DIR `
  "npm" `
  @("run", "dev") `
  $frontendLog

Start-Sleep -Seconds 3

$floodsafeFrontendLog = Join-Path $logDir "floodsafe-frontend.log"
$floodsafeFrontendProc = Start-ServiceProcess `
  "FloodSafe Frontend" `
  $FLOODSAFE_FRONTEND_DIR `
  "npm" `
  @("run", "dev") `
  $floodsafeFrontendLog

Start-Sleep -Seconds 3

# Proxy (optional)
if (-not $SkipProxy) {
  $proxyLog = Join-Path $logDir "proxy.log"
  $proxyProc = Start-ServiceProcess `
    "Proxy Server" `
    $ROOT `
    "node" `
    @("proxy-server.js") `
    $proxyLog
  
  Start-Sleep -Seconds 2
}

# Health checks
Write-Header "Health Checks"

if (Test-PortListening 8000 15) {
  Write-Success "Reunification Backend" "Listening on port 8000"
} else {
  Write-Warning-Msg "Reunification Backend" "Not responding - check $backendLog"
}

if (Test-PortListening 8090 15) {
  Write-Success "FloodSafe Backend" "Listening on port 8090"
} else {
  Write-Warning-Msg "FloodSafe Backend" "Not responding - check $floodsafeBackendLog"
}

if (Test-PortListening 5173 15) {
  Write-Success "Reunification Frontend" "Listening on port 5173"
} else {
  Write-Warning-Msg "Reunification Frontend" "Not responding - check $frontendLog"
}

if (Test-PortListening 8001 15) {
  Write-Success "FloodSafe Frontend" "Listening on port 8001"
} else {
  Write-Warning-Msg "FloodSafe Frontend" "Not responding - check $floodsafeFrontendLog"
}

if (-not $SkipProxy) {
  if (Test-PortListening 3001 15) {
    Write-Success "Proxy Server" "Listening on port 3001"
  } else {
    Write-Warning-Msg "Proxy Server" "Not responding - check $proxyLog"
  }
}

# Final status
Write-Header "PLATFORM READY"

Write-Host ""
Write-Host "ACCESS POINTS:"
Write-Host "  - Local:   http://localhost:3001/"
Write-Host "  - Network: http://192.168.22.127:3001/"
Write-Host ""
Write-Host "RUNNING SERVICES:"
Write-Host "  - Reunification Backend:   http://localhost:8000"
Write-Host "  - Reunification Frontend:  http://localhost:5173"
Write-Host "  - FloodSafe Backend:       http://localhost:8090"
Write-Host "  - FloodSafe Frontend:      http://localhost:8001"
if (-not $SkipProxy) {
  Write-Host "  - Proxy Server:            http://localhost:3001"
}
Write-Host ""
Write-Host "LOGS:"
Write-Host "  - Reunification Backend: $backendLog"
Write-Host "  - FloodSafe Backend:     $floodsafeBackendLog"
Write-Host "  - Reunification Frontend: $frontendLog"
Write-Host "  - FloodSafe Frontend:    $floodsafeFrontendLog"
if (-not $SkipProxy) {
  Write-Host "  - Proxy Server:          $proxyLog"
}
Write-Host ""
Write-Host "STOP: Press Ctrl+C"
Write-Host ""

# Keep running
while ($true) {
  Start-Sleep -Seconds 10
  
  # Check if any process died
  if ($backendProc -and $backendProc.HasExited) {
    Write-Warning-Msg "Reunification Backend" "Process exited (see $backendLog)"
  }
  if ($floodsafeBackendProc -and $floodsafeBackendProc.HasExited) {
    Write-Warning-Msg "FloodSafe Backend" "Process exited (see $floodsafeBackendLog)"
  }
  if ($frontendProc -and $frontendProc.HasExited) {
    Write-Warning-Msg "Reunification Frontend" "Process exited (see $frontendLog)"
  }
  if ($floodsafeFrontendProc -and $floodsafeFrontendProc.HasExited) {
    Write-Warning-Msg "FloodSafe Frontend" "Process exited (see $floodsafeFrontendLog)"
  }
  if ($proxyProc -and $proxyProc.HasExited) {
    Write-Warning-Msg "Proxy Server" "Process exited (see $proxyLog)"
  }
}
