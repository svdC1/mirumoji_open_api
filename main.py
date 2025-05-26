# main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.gpt_router import gpt_router
from routers.audio_router import audio_router
from routers.health_router import health_router
from routers.dict_router import dict_router

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

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gpt_router)
app.include_router(audio_router)
app.include_router(health_router)
app.include_router(dict_router)
