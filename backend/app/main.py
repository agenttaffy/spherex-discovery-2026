from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.api.health import router as health_router
from app.api.observations import router as obs_router
from app.api.frames import router as frames_router
from app.api.demo import router as demo_router

app = FastAPI(
    title="SPHEREx Discovery API",
    description="Scientific backend service for exploring time-domain SPHEREx observations (NASA Space Apps 2026).",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router, prefix="/api", tags=["System"])
app.include_router(obs_router, prefix="/api", tags=["Observations"])
app.include_router(frames_router, prefix="/api", tags=["Frames"])
app.include_router(demo_router, prefix="/api", tags=["Demo"])

@app.get("/")
def root():
    return {
        "project": "SPHEREx Discovery",
        "competition": "NASA Space Apps Challenge 2026",
        "documentation": "/docs",
        "status": "operational"
    }
