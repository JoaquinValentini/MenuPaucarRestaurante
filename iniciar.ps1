$ErrorActionPreference = 'Stop'

function Get-ValidPython {
  $candidates = @(
    'python',
    'py',
    'python3'
  )

  foreach ($candidate in $candidates) {
    try {
      $cmd = Get-Command $candidate -ErrorAction Stop
      $path = $cmd.Source
      if (-not $path) { continue }
      if (-not (Test-Path -LiteralPath $path)) { continue }

      $probe = & $path -c "import sys; print(sys.executable)" 2>$null
      if ($LASTEXITCODE -eq 0 -and $probe) {
        return $path
      }
    } catch {}
  }

  foreach ($glob in @(
    "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
    "$env:ProgramFiles\Python\Python*\python.exe",
    "$env:ProgramFiles(x86)\Python\Python*\python.exe"
  )) {
    foreach ($item in (Get-ChildItem -Path $glob -ErrorAction SilentlyContinue | Sort-Object -Descending)) {
      if ((Test-Path -LiteralPath $item.FullName)) {
        $probe = & $item.FullName -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe) {
          return $item.FullName
        }
      }
    }
  }

  return $null
}

$project = $PSScriptRoot
$runtime = Get-ValidPython

if (-not $runtime) {
  Write-Host 'No se encontró un intérprete de Python válido en esta PC.' -ForegroundColor Yellow
  Write-Host 'Instalá Python 3.11+ desde: https://www.python.org/downloads/windows/' -ForegroundColor Yellow
  try { Start-Process 'https://www.python.org/downloads/windows/' } catch {}
  Read-Host 'Presioná Enter para cerrar'
  exit 1
}

# Instalar dependencias si hace falta.
$requirements = Join-Path $project 'requirements.txt'
if (Test-Path -LiteralPath $requirements) {
  & $runtime -m pip install -r $requirements
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'No se pudieron instalar las dependencias de Python.' -ForegroundColor Red
    Read-Host 'Presioná Enter para cerrar'
    exit 1
  }
}

$connection = New-Object System.Net.Sockets.TcpClient
try { $connection.Connect('127.0.0.1', 8000); $occupied = $true } catch { $occupied = $false } finally { $connection.Dispose() }

if ($occupied) {
  try {
    $state = Invoke-RestMethod 'http://localhost:8000/api/session' -TimeoutSec 5
    if ($null -eq $state.needsSetup) { throw 'Servidor incorrecto' }
    if ($state.autoPublishVersion -ne 2) {
      Write-Host 'Sigue abierto un servidor anterior. Cerralo antes de iniciar esta versión con publicación automática.' -ForegroundColor Yellow
      Read-Host 'Enter para cerrar'
      exit 1
    }

    $setup = Join-Path $project '.private\setup-url.txt'
    if ($state.needsSetup -and (Test-Path -LiteralPath $setup)) {
      Start-Process (Get-Content -LiteralPath $setup -Raw)
    } else {
      Start-Process 'http://localhost:8000/admin/'
    }
  } catch {
    Write-Host 'El puerto 8000 está ocupado por otro servidor. Cerralo antes de iniciar.' -ForegroundColor Yellow
  }
  exit
}

$server = Start-Process -FilePath $runtime -ArgumentList 'server.py' -WorkingDirectory $project -WindowStyle Hidden -PassThru
$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
  try {
    $state = Invoke-RestMethod 'http://localhost:8000/api/session' -TimeoutSec 2
    if ($null -ne $state.needsSetup) {
      $ready = $true
      break
    }
  } catch {}
  Start-Sleep -Milliseconds 500
}

if (-not $ready) {
  Write-Host 'El servidor no pudo iniciar. Revisá Python, permisos de la carpeta y que no exista otro servicio en el puerto 8000.' -ForegroundColor Red
  if ($server) { Stop-Process -Id $server.Id -ErrorAction SilentlyContinue }
  Read-Host 'Presioná Enter para cerrar'
  exit 1
}

$setup = Join-Path $project '.private\setup-url.txt'
if (Test-Path -LiteralPath $setup) {
  Start-Process (Get-Content -LiteralPath $setup -Raw)
} else {
  Start-Process 'http://localhost:8000/admin/'
}
