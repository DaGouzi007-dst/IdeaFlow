# 启动后端（带热重载）
# 用法：在仓库根目录执行  .\scripts\dev-backend.ps1            默认 8000
#                           .\scripts\dev-backend.ps1 -Port 8003  联调用这个端口

param([int]$Port = 8000)

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host '还没装依赖，先执行 .\scripts\setup.ps1' -ForegroundColor Yellow
    exit 1
}

Write-Host ("后端启动中： http://127.0.0.1:{0}" -f $Port) -ForegroundColor Cyan
Write-Host ("接口文档：   http://127.0.0.1:{0}/docs" -f $Port) -ForegroundColor Cyan
Push-Location $backend
try {
    & $venvPython -m uvicorn main:app --reload --port $Port
} finally {
    Pop-Location
}
