# main.py
import logging
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from routers.gpt_router import gpt_router
from routers.audio_router import audio_router
from routers.health_router import health_router
from routers.dict_router import dict_router
from routers.video_router import video_router
from routers.profile_router import profile_router
from contextlib import asynccontextmanager
from database import connect_db, disconnect_db, DATABASE_URL

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)8s %(name)s | %(message)s",
                    )
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────
# App setup
# ───────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    os.makedirs("media_files/profiles", exist_ok=True)
    os.makedirs("media_files/temp", exist_ok=True)
    logger.info("media_files directories ensured.")
    yield
    await disconnect_db()


app = FastAPI(
    title="Mirumoji",
    description="Japanese sentence breakdown, audio processing and GPT.",
    lifespan=lifespan
)

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
app.include_router(profile_router)


logger.info(f"Database URL: {DATABASE_URL}")
logger.info("Application setup complete. Static files served from\
    './media_files' at '/media'.")
