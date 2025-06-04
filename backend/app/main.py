# app/main.py
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import redis
from .routers import scraping, analytics, reports
from .services.scheduler import start_background_tasks

app = FastAPI(
    title="Market Intelligence Platform",
    description="Automated business intelligence and competitor monitoring",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.include_router(scraping.router, prefix="/api/v1/scraping")
app.include_router(analytics.router, prefix="/api/v1/analytics")
app.include_router(reports.router, prefix="/api/v1/reports")

@app.on_event("startup")
async def startup_event():
    start_background_tasks()
