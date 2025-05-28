import logging
import os
import shutil
import uuid
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    status
)
from processing.Processor import Processor
from profile_manager import ensure_profile_exists
from mirumojidb.db import get_db
from mirumojidb.Tables import (profile_transcripts,
                               profile_files
                               )

logger = logging.getLogger(__name__)
audio_router = APIRouter(prefix='/audio')

processor = Processor()

BASE_MEDIA_PATH = "media_files"
PROFILES_MEDIA_PATH = os.path.join(BASE_MEDIA_PATH, "profiles")


@audio_router.post("/transcribe_from_audio")
async def transcribe_from_audio(
    file: UploadFile = File(...),
    clean_audio: str = Form("false"),
    gpt_explain: str = Form("false"),
    profile_id: str = Depends(ensure_profile_exists)
):
    if not profile_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="X-Profile-ID header is required.")

    do_clean_audio = clean_audio.lower() == "true"
    do_gpt_explain = gpt_explain.lower() == "true"

    profile_audio_path = os.path.join(PROFILES_MEDIA_PATH, profile_id, "audios"
                                      )
    os.makedirs(profile_audio_path, exist_ok=True)

    original_filename = file.filename
    saved_audio_disk_filename = f"{uuid.uuid4()}_{original_filename}"
    audio_file_location = os.path.join(profile_audio_path,
                                       saved_audio_disk_filename)
    # relative_audio_path will be used for DB storage and constructing URLs
    relative_audio_path = os.path.join("profiles", profile_id, "audios",
                                       saved_audio_disk_filename)

    try:
        with open(audio_file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        logger.info(f"Audio file saved to \
            {audio_file_location} for profile {profile_id}")

        logger.info(f"Starting transcription for {audio_file_location} \
            (clean: {do_clean_audio})")
        srt_transcript = """1
00:00:00,500 --> 00:00:02,000
This is a dummy transcript.

2
00:00:02,500 --> 00:00:04,000
Replace with actual transcription output.
"""
        logger.info(f"Transcription complete for {audio_file_location}")

        gpt_explanation_text = None
        if do_gpt_explain:
            logger.info(f"Generating GPT explanation for\
                transcript of {audio_file_location}")
            gpt_explanation_text = f"This is a GPT explanation for the dummy\
                transcript of {original_filename}. \
                    Clean audio was {do_clean_audio}."
            logger.info(f"GPT explanation generated for {audio_file_location}")

        db = await get_db()

        # 1. Save transcript metadata
        transcript_id = str(uuid.uuid4())
        insert_transcript_query = profile_transcripts.insert().values(
            id=transcript_id,
            profile_id=profile_id,
            original_file_name=original_filename,
            transcript=srt_transcript,
            gpt_explanation=gpt_explanation_text,
            audio_file_path=relative_audio_path
        )
        await db.execute(insert_transcript_query)
        logger.info(f"Transcript {transcript_id} for {original_filename} \
            saved to profile {profile_id}")

        # 2. Save a reference to the audio file in profile_files table
        audio_profile_file_id = str(uuid.uuid4())
        insert_profile_file_query = profile_files.insert().values(
            id=audio_profile_file_id,
            profile_id=profile_id,
            file_name=original_filename,
            file_path=relative_audio_path,
            file_type="audio_source",
            related_transcript_id=transcript_id
        )
        await db.execute(insert_profile_file_query)
        logger.info(
            f"Audio file {original_filename} \
                (path: {relative_audio_path}) also registered in profile_files\
                    with ID {audio_profile_file_id} for\
                        transcript {transcript_id}")

        return {
            "transcript": srt_transcript,
            "gpt_explanation": gpt_explanation_text
        }

    except Exception as e:
        logger.exception(f"Error during transcription for profile \
            {profile_id},file {original_filename}")
        # Consider cleanup of saved audio file if DB operations fail later
        if os.path.exists(audio_file_location):
            try:
                os.remove(audio_file_location)
            except OSError as ose:
                logger.error(f"Could not remove audio file\
                {audio_file_location} after error: {ose}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to transcribe audio: {str(e)}")
