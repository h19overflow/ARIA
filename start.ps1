$root = $PSScriptRoot

Write-Host "Starting Redis (port 6379)..."
$redis = Start-Process -FilePath "docker" -ArgumentList "run --rm -p 6379:6379 redis:alpine" -PassThru -NoNewWindow

Write-Host "Starting ChromaDB (port 8001)..."
$chroma = Start-Process -FilePath "$root\.venv\Scripts\chroma.exe" -ArgumentList "run --host 0.0.0.0 --port 8001" -WorkingDirectory $root -PassThru -NoNewWindow

Write-Host "Waiting for Redis + ChromaDB to be ready..."
Start-Sleep -Seconds 4

Write-Host "Starting backend (port 8002)..."
$backend = Start-Process -FilePath "$root\.venv\Scripts\uvicorn.exe" -ArgumentList "src.api.main:app --reload --host 0.0.0.0 --port 8002" -WorkingDirectory $root -PassThru -NoNewWindow

Write-Host "Starting frontend..."
$frontend = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "$root\frontend" -PassThru -NoNewWindow

Write-Host "Redis PID: $($redis.Id) | ChromaDB PID: $($chroma.Id) | Backend PID: $($backend.Id) | Frontend PID: $($frontend.Id)"
Write-Host "Press Ctrl+C to stop all."

try {
    while (!$redis.HasExited -and !$chroma.HasExited -and !$backend.HasExited -and !$frontend.HasExited) {
        Start-Sleep -Milliseconds 500
    }
} finally {
    Stop-Process -Id $redis.Id, $chroma.Id, $backend.Id, $frontend.Id -ErrorAction SilentlyContinue
    Write-Host "Shutting down..."
}
