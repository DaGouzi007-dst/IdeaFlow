from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import router

app = FastAPI(title="Search & Trace API")
app.include_router(router)          # /api/* 和 /viewer/* 先注册

_static = Path(__file__).parent / "static"
_static.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=_static, html=True), name="static")