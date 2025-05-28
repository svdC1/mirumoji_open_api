import logging
import os
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
import shutil

from profile_manager import ensure_profile_exists

logger = logging.getLogger(__name__)
video_router = APIRouter(prefix='/video')


BASE_MEDIA_PATH = "media_files"
PROFILES_MEDIA_PATH = os.path.join(BASE_MEDIA_PATH, "profiles")


@video_router.post("/generate_srt")
async def generate_srt(
    video_file: UploadFile = File(...),
    profile_id: str = Depends(ensure_profile_exists)
):
    if not profile_id:
        raise HTTPException(status_code=400,
                            detail="X-Profile-ID header is required.")

    # Create profile-specific directory if it doesn't exist
    profile_video_path = os.path.join(PROFILES_MEDIA_PATH,
                                      profile_id, "videos")
    profile_srt_path = os.path.join(PROFILES_MEDIA_PATH, profile_id, "srts")
    os.makedirs(profile_video_path, exist_ok=True)
    os.makedirs(profile_srt_path, exist_ok=True)

    video_file_location = os.path.join(profile_video_path, video_file.filename)
    srt_file_name = f"{os.path.splitext(video_file.filename)[0]}.srt"
    srt_file_location = os.path.join(profile_srt_path, srt_file_name)

    try:
        # Save the uploaded video file
        with open(video_file_location, "wb+") as file_object:
            shutil.copyfileobj(video_file.file, file_object)

        logger.info(f"Video file saved to {video_file_location}\
            for profile {profile_id}")

        srt_content = """1
00:00:01,000 --> 00:00:02,000
Hello

2
00:00:03,000 --> 00:00:04,000
World
"""

        # Save the generated SRT file (optional, but good practice)
        with open(srt_file_location, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_content)
        logger.info(f"SRT file saved to {srt_file_location}\
            for profile {profile_id}")

        # Here you might want to save metadata to the database:
        # e.g., original video name, path to video, path to SRT, profile_id

        return {"srt_content": srt_content}
    except Exception as e:
        logger.error(f"Error generating SRT for {video_file.filename}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to generate SRT: {str(e)}")


@video_router.post("/convert_to_mp4")
async def convert_to_mp4(
    video_file: UploadFile = File(...),
    # use_nvenc: bool = Form(False), # Example of an optional parameter
    profile_id: str = Depends(ensure_profile_exists)
):
    if not profile_id:
        raise HTTPException(status_code=400,
                            detail="X-Profile-ID header is required.")

    profile_originals_path = os.path.join(PROFILES_MEDIA_PATH,
                                          profile_id, "originals")
    profile_converted_path = os.path.join(PROFILES_MEDIA_PATH,
                                          profile_id, "converted")
    os.makedirs(profile_originals_path, exist_ok=True)
    os.makedirs(profile_converted_path, exist_ok=True)

    original_file_location = os.path.join(profile_originals_path,
                                          video_file.filename)

    base_filename, _ = os.path.splitext(video_file.filename)
    converted_filename = f"{base_filename}_converted.mp4"
    converted_file_location = os.path.join(profile_converted_path,
                                           converted_filename)

    try:
        # Save the original uploaded video file
        with open(original_file_location, "wb+") as file_object:
            shutil.copyfileobj(video_file.file, file_object)
        logger.info(f"Original video file saved to {original_file_location}\
            for profile {profile_id}")

        if video_file.filename.lower().endswith(".mp4"):
            shutil.copyfile(original_file_location, converted_file_location)
        else:
            # Create a dummy mp4 file for non-mp4 inputs for now
            with open(converted_file_location, "w") as f:
                f.write("dummy mp4 content")
            logger.warning(f"Non-MP4 file {video_file.filename} received; \
                dummy MP4 created at {converted_file_location}.")

        if not os.path.exists(converted_file_location):
            raise HTTPException(status_code=500,
                                detail="Video conversion failed.")

        logger.info(f"Video file converted and saved to \
            {converted_file_location} for profile {profile_id}")

        converted_video_url_path = f"/media/profiles/{profile_id}/converted/\
            {converted_filename}"

        return {"converted_video_url": converted_video_url_path}
    except Exception as e:
        logger.error(f"Error converting video {video_file.filename}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to convert video: {str(e)}")
