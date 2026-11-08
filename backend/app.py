from fastapi import FastAPI
from routers import router

app = FastAPI(title="Search & Trace API")
app.include_router(router)