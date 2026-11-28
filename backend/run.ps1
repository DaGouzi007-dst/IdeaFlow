# 启动第二部分服务（组内约定端口 8002）
Set-Location $PSScriptRoot
uvicorn app:app --reload --port 8002