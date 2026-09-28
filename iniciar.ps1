$project = $PSScriptRoot
$runtime = 'C:\Users\Usuario\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) { $runtime = 'python' }
$connection = New-Object System.Net.Sockets.TcpClient
try { $connection.Connect('127.0.0.1',8000); $occupied = $true } catch { $occupied = $false } finally { $connection.Dispose() }
if ($occupied) {
  try {
    $state = Invoke-RestMethod 'http://localhost:8000/api/session' -TimeoutSec 5
    if ($null -eq $state.needsSetup) { throw 'Servidor incorrecto' }
    $setup = Join-Path $project '.private\setup-url.txt'
    if ($state.needsSetup -and (Test-Path -LiteralPath $setup)) { Start-Process (Get-Content -LiteralPath $setup -Raw) } else { Start-Process 'http://localhost:8000/admin/' }
  } catch { Write-Host 'El puerto 8000 está ocupado por otro servidor. Cerralo antes de iniciar.' }
  exit
}
Start-Process -FilePath $runtime -ArgumentList 'server.py' -WorkingDirectory $project -WindowStyle Hidden
$ready = $false
for ($attempt=0; $attempt -lt 10; $attempt++) {
  try { $state = Invoke-RestMethod 'http://localhost:8000/api/session' -TimeoutSec 2; if ($null -ne $state.needsSetup) { $ready = $true; break } } catch {}
  Start-Sleep -Milliseconds 500
}
if (-not $ready) { Write-Host 'El servidor no pudo iniciar. Verificá Python y los permisos de la carpeta.'; exit 1 }
$setup = Join-Path $project '.private\setup-url.txt'
if (Test-Path -LiteralPath $setup) { Start-Process (Get-Content -LiteralPath $setup -Raw) } else { Start-Process 'http://localhost:8000/admin/' }
