# 启动前端（Vite），默认 5173 端口
# 用法：在仓库根目录执行  .\scripts\dev-frontend.ps1

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'

if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host '还没装前端依赖，先执行：cd frontend; npm install' -ForegroundColor Yellow
    exit 1
}

Write-Host '前端启动中： http://127.0.0.1:5173' -ForegroundColor Cyan
Write-Host '打开这个地址就能看到页面' -ForegroundColor Cyan
Push-Location $frontend
try {
    npm run dev
} finally {
    Pop-Location
}
