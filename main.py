# main.py
import logging
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from routers.gpt_router import gpt_router
from routers.audio_router import audio_router
from routers.health_router import health_router
from routers.dict_router import dict_router
from routers.video_router import video_router
from routers.profile_router import profile_router # Added

from database import connect_db, disconnect_db, DATABASE_URL # Removed get_db, profiles, engine, metadata as they aren't directly used here
from profile_manager import ensure_profile_exists

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)8s %(name)s | %(message)s",
                    )
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────
# App setup
# ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Mirumoji",
    description="Japanese sentence breakdown, audio processing and GPT.",
)

# Database event handlers
@app.on_event("startup")
async def startup_db_client():
    await connect_db()
    os.makedirs("media_files/profiles", exist_ok=True)
    os.makedirs("media_files/temp", exist_ok=True)
    logger.info("media_files directories ensured.")

@app.on_event("shutdown")
async def shutdown_db_client():
    await disconnect_db()

app.mount("/media", StaticFiles(directory="media_files"), name="media")

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
    )

app.include_router(gpt_router)
app.include_router(audio_router)
app.include_router(health_router)
app.include_router(dict_router)
app.include_router(video_router)
app.include_router(profile_router) # Added

@app.get("/test_profile_creation")
async def test_profile_creation(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id:
        raise HTTPException(status_code=400, detail="X-Profile-ID header is required for this test endpoint.")
    return {"message": f"Successfully ensured profile exists: {profile_id}"}

logger.info(f"Database URL: {DATABASE_URL}")
logger.info("Application setup complete. Static files served from './media_files' at '/media'.")
