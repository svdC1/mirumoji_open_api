import logging
from fastapi import (APIRouter,
                     UploadFile,
                     File,
                     Form)
from processing.Processor import Processor
logger = logging.getLogger(__name__)

audio_router = APIRouter(prefix='/audio')

processor = Processor()
audio_tools = processor.audio_tools
gpt_explain_service = processor.sentence_breakdown_service.gpt_explainer


@audio_router.post("/srt_from_s3")
async def srt_from_audio():

    return None


@audio_router.post("/convert_from_s3")
async def convert_to_mp4():
    return None


@audio_router.post("/transcribe_recording")
async def transcribe_audio(
    file: UploadFile = File(...),
    clean_audio: bool = Form(False),
    gpt_explain: bool = Form(False)
):
    return None
