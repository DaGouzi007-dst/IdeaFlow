# 一次性把后端环境装好
# 用法：在仓库根目录执行  .\scripts\setup.ps1

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$venv = Join-Path $root '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host '== 创建虚拟环境 .venv ==' -ForegroundColor Cyan
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $installed = & py.exe -0p 2>$null
        if ($installed -match '3\.1[2-9]|3\.2[0-9]') {
            & py.exe -3.12 -m venv $venv
        } else {
            & py.exe -3 -m venv $venv
        }
    } else {
        & python -m venv $venv
    }
}

Write-Host '== 安装后端依赖 ==' -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $backend 'requirements.txt')

Write-Host ''
Write-Host '后端依赖装好了。下一步：' -ForegroundColor Green
Write-Host '  1) 另开一个终端跑后端： .\scripts\dev-backend.ps1'
Write-Host '  2) 装前端依赖：        cd frontend; npm install'
Write-Host '  3) 跑前端：            cd frontend; npm run dev'
Write-Host ''
Write-Host '第一次启动后端时会自动建表并灌 5 条模拟想法。' -ForegroundColor DarkGray
