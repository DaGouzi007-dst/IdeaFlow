# 启动后端（带热重载），默认 8000 端口
# 用法：在仓库根目录执行  .\scripts\dev-backend.ps1

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host '还没装依赖，先执行 .\scripts\setup.ps1' -ForegroundColor Yellow
    exit 1
}

Write-Host '后端启动中： http://127.0.0.1:8000' -ForegroundColor Cyan
Write-Host '接口文档：   http://127.0.0.1:8000/docs' -ForegroundColor Cyan
Push-Location $backend
try {
    & $venvPython -m uvicorn main:app --reload --port 8000
} finally {
    Pop-Location
}
