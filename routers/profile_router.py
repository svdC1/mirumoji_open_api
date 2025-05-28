import logging
import uuid
import os
import shutil
import json
import datetime # Required for ProfileTranscriptResponse & Anki export
import random # For Anki model ID
import time # For Anki deck ID
from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    File, UploadFile, Form, Path
)
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import genanki # For Anki deck generation

from database import get_db, gpt_templates, clips, profile_files, profile_transcripts
from profile_manager import ensure_profile_exists

logger = logging.getLogger(__name__)
profile_router = APIRouter(prefix='/profiles', dependencies=[Depends(ensure_profile_exists)])

BASE_MEDIA_PATH = "media_files"
TEMP_MEDIA_PATH = os.path.join(BASE_MEDIA_PATH, "temp") # For Anki decks
os.makedirs(TEMP_MEDIA_PATH, exist_ok=True) # Ensure temp dir exists

# --- Pydantic Models --- 
class GptTemplateBase(BaseModel):
    sys_msg: str = Field(..., alias="sysMsg")
    prompt: str
class GptTemplateResponse(GptTemplateBase):
    id: str
class ClipResponse(BaseModel):
    id: str; get_url: str; breakdown_response: Any
class ProfileFileResponse(BaseModel):
    id: str; file_name: str; get_url: str
    file_type: Optional[str] = None
    created_at: Optional[str] = None 
class ProfileTranscriptResponse(BaseModel):
    id: str; transcript: str
    original_file_name: Optional[str] = None
    gpt_explanation: Optional[str] = None
    get_url: Optional[str] = None
    created_at: Optional[str] = None
class AnkiExportResponse(BaseModel):
    anki_deck_url: str

# --- GPT Template Management --- (collapsed)
@profile_router.get("/gpt_template", response_model=GptTemplateResponse)
async def get_gpt_template(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); q = gpt_templates.select().where(gpt_templates.c.profile_id == profile_id)
    rec = await db.fetch_one(q); 
    if not rec: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GPT template not found.")
    return GptTemplateResponse(id=rec.id, sysMsg=rec.sys_msg, prompt=rec.prompt)
@profile_router.post("/gpt_template", response_model=GptTemplateResponse)
async def upsert_gpt_template(template_data: GptTemplateBase, profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); values = {"profile_id": profile_id, "sys_msg": template_data.sys_msg, "prompt": template_data.prompt}
    q = gpt_templates.select().where(gpt_templates.c.profile_id == profile_id); ex = await db.fetch_one(q)
    if ex: await db.execute(gpt_templates.update().where(gpt_templates.c.id == ex.id).values(**values)); tid = ex.id
    else: tid = str(uuid.uuid4()); values["id"] = tid; await db.execute(gpt_templates.insert().values(**values))
    return GptTemplateResponse(id=tid, sysMsg=values["sys_msg"], prompt=values["prompt"])
@profile_router.delete("/gpt_template", status_code=status.HTTP_200_OK)
async def delete_gpt_template(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); res = await db.execute(gpt_templates.delete().where(gpt_templates.c.profile_id == profile_id))
    if res == 0: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GPT template not found.")
    return {"success": True, "message": "Template deleted successfully."}

# --- Clip Management --- (collapsed)
@profile_router.post("/clips/save", status_code=status.HTTP_201_CREATED)
async def save_video_clip(profile_id: str = Depends(ensure_profile_exists), clip_start_time: str = Form(...), clip_end_time: str = Form(...), gpt_breakdown_response: str = Form(...), video_clip: UploadFile = File(...), original_video_file_name: Optional[str] = Form(None), original_video_url: Optional[str] = Form(None)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    p_path = os.path.join(BASE_MEDIA_PATH, "profiles", profile_id, "clips"); os.makedirs(p_path, exist_ok=True)
    fname = f"{uuid.uuid4()}_{video_clip.filename}"; loc = os.path.join(p_path, fname); rel_path = os.path.join("profiles",profile_id,"clips",fname)
    try:
        with open(loc, "wb+") as f: shutil.copyfileobj(video_clip.file, f)
        gpt_j = json.loads(gpt_breakdown_response); s_time = float(clip_start_time); e_time = float(clip_end_time)
        db = await get_db(); c_id = str(uuid.uuid4())
        await db.execute(clips.insert().values(id=c_id,profile_id=profile_id,clip_start_time=s_time,clip_end_time=e_time,gpt_breakdown_response=gpt_j,video_clip_path=rel_path,original_video_file_name=original_video_file_name,original_video_url=original_video_url))
        await db.execute(profile_files.insert().values(id=str(uuid.uuid4()),profile_id=profile_id,file_name=video_clip.filename,file_path=rel_path,file_type="video_clip"))
        return {"success": True, "message": "Clip saved successfully.", "clip_id": c_id}
    except json.JSONDecodeError: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON.")
    except ValueError: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time format.")
    except HTTPException: raise
    except Exception as e:
        logger.exception("Err saving clip")
        if os.path.exists(loc):
            os.remove(loc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save clip: {e}")
@profile_router.get("/clips", response_model=List[ClipResponse])
async def get_saved_clips(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); query = clips.select().where(clips.c.profile_id == profile_id).order_by(clips.c.created_at.desc())
    return [ClipResponse(id=c.id,get_url=f"/media/{c.video_clip_path}",breakdown_response=c.gpt_breakdown_response) for c in await db.fetch_all(query)]
@profile_router.delete("/clips/{clipId}", status_code=status.HTTP_200_OK)
async def delete_saved_clip(clipId: str = Path(..., title="ID of clip to delete"), profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); clip_r = await db.fetch_one(clips.select().where(clips.c.id==clipId).where(clips.c.profile_id==profile_id))
    if not clip_r: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")
    await db.execute(clips.delete().where(clips.c.id == clipId).where(clips.c.profile_id == profile_id))
    await db.execute(profile_files.delete().where(profile_files.c.file_path == clip_r.video_clip_path).where(profile_files.c.profile_id == profile_id))
    fp = os.path.join(BASE_MEDIA_PATH, clip_r.video_clip_path)
    if os.path.exists(fp):
        try:
            os.remove(fp); logger.info(f"Deleted: {fp}")
        except OSError as e:
            logger.error(f"Err deleting {fp}: {e}")
    else:
        logger.warning(f"Not found for del: {fp}")
    return {"success": True, "message": "Clip deleted successfully."}

# --- Profile File Management --- (collapsed)
@profile_router.get("/files", response_model=List[ProfileFileResponse])
async def get_profile_files(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); query = profile_files.select().where(profile_files.c.profile_id == profile_id).order_by(profile_files.c.created_at.desc())
    return [ProfileFileResponse(id=f.id,file_name=f.file_name,get_url=f"/media/{f.file_path}",file_type=f.file_type,created_at=f.created_at.isoformat() if f.created_at else None) for f in await db.fetch_all(query)]
@profile_router.delete("/files/{fileId}", status_code=status.HTTP_200_OK)
async def delete_profile_file(fileId: str = Path(..., title="ID of file to delete"), profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); file_r = await db.fetch_one(profile_files.select().where(profile_files.c.id == fileId).where(profile_files.c.profile_id == profile_id))
    if not file_r: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File record not found.")
    await db.execute(profile_files.delete().where(profile_files.c.id == fileId))
    fp = os.path.join(BASE_MEDIA_PATH, file_r.file_path)
    if os.path.exists(fp):
        try:
            os.remove(fp); logger.info(f"Deleted file: {fp}")
        except OSError as e:
            logger.error(f"Err deleting {fp}: {e}")
    else: logger.warning(f"File not found for del: {fp}")
    if file_r.file_type == "video_clip": 
        if await db.execute(clips.delete().where(clips.c.video_clip_path == file_r.file_path)) > 0: logger.info(f"Del assoc. clip for {file_r.file_path}")
    elif file_r.file_type == "audio_source":
        if await db.execute(profile_transcripts.update().where(profile_transcripts.c.audio_file_path == file_r.file_path).values(audio_file_path=None)) > 0: logger.info(f"Cleared path in transcripts for {file_r.file_path}")
    return {"success": True, "message": "File deleted successfully."}

# --- Profile Transcript Management --- (collapsed)
@profile_router.get("/transcripts", response_model=List[ProfileTranscriptResponse])
async def get_profile_transcripts(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); query = profile_transcripts.select().where(profile_transcripts.c.profile_id == profile_id).order_by(profile_transcripts.c.created_at.desc())
    res_trans = []
    for t in await db.fetch_all(query):
        url = f"/media/{t.audio_file_path}" if t.audio_file_path else None
        res_trans.append(ProfileTranscriptResponse(id=t.id,original_file_name=t.original_file_name,transcript=t.transcript,gpt_explanation=t.gpt_explanation,get_url=url,created_at=t.created_at.isoformat() if t.created_at else None))
    return res_trans
@profile_router.delete("/transcripts/{transcriptId}", status_code=status.HTTP_200_OK)
async def delete_profile_transcript(transcriptId: str = Path(..., title="ID of transcript to delete"), profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    db = await get_db(); trans_r = await db.fetch_one(profile_transcripts.select().where(profile_transcripts.c.id == transcriptId).where(profile_transcripts.c.profile_id == profile_id))
    if not trans_r: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found.")
    await db.execute(profile_transcripts.delete().where(profile_transcripts.c.id == transcriptId))
    logger.info(f"Del transcript {transcriptId}")
    if trans_r.audio_file_path:
        aud_path = trans_r.audio_file_path
        if await db.execute(profile_files.delete().where(profile_files.c.file_path == aud_path).where(profile_files.c.profile_id == profile_id)) > 0:
            logger.info(f"Del assoc. profile_files for: {aud_path}")
            fp_aud = os.path.join(BASE_MEDIA_PATH, aud_path)
            if os.path.exists(fp_aud):
                try:
                    os.remove(fp_aud)
                    logger.info(f"Del audio file: {fp_aud}")
                except OSError as e:
                    logger.error(f"Err del audio {fp_aud}: {e}")
            else:
                logger.warning(f"Audio file not found for del: {fp_aud}")
        else:
            logger.warning(f"No profile_files entry for {aud_path} with transcript {transcriptId}")
    return {"success": True, "message": "Transcript deleted successfully."}

# --- Anki Export --- 
@profile_router.get("/anki_export", response_model=AnkiExportResponse)
async def export_anki_deck(profile_id: str = Depends(ensure_profile_exists)):
    if not profile_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Profile-ID header is required.")
    
    db = await get_db()
    query = clips.select().where(clips.c.profile_id == profile_id).order_by(clips.c.created_at.asc())
    profile_clips = await db.fetch_all(query)

    if not profile_clips:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No clips found for this profile to export.")

    # Create a unique deck ID and name
    # Deck ID needs to be an integer. Using epoch time + random for uniqueness.
    deck_id = int(time.time() * 1000) + random.randint(0, 10000)
    deck_name = f"{profile_id}_Mirumoji_Clips"
    anki_deck = genanki.Deck(deck_id, deck_name)

    # Define Anki note model (customize fields as needed)
    # Using random model ID, as recommended by genanki if not managing specific model versions
    model_id = random.randint(1_000_000_000, 2_000_000_000)
    anki_model = genanki.Model(
        model_id,
        'Mirumoji Clip Model',
        fields=[
            {'name': 'Sentence'}, # From gpt_breakdown_response.focus.word or similar
            {'name': 'FocusWord'}, # From gpt_breakdown_response.focus.word
            {'name': 'Reading'},   # From gpt_breakdown_response.focus.reading
            {'name': 'Meanings'},  # From gpt_breakdown_response.focus.meanings
            {'name': 'Explanation'},# From gpt_breakdown_response.gpt_explanation
            {'name': 'Video'},     # For the video clip media
            {'name': 'Source'},    # Optional: original_video_file_name or original_video_url
        ],
        templates=[
            {
                'name': 'Clip Card',
                'qfmt': '{{Sentence}}<br><br>{{Video}}',
                'afmt': '{{FrontSide}}<hr id="answer"><b>{{FocusWord}}</b> [{{Reading}}]<br>{{Meanings}}<br><br><i>Explanation:</i><br>{{Explanation}}<br><br><i>Source: {{Source}}</i>',
            },
        ]
    )
    anki_deck.add_model(anki_model)
    
    media_files_to_package = []

    for clip_data in profile_clips:
        breakdown = clip_data.gpt_breakdown_response # This is a dict/JSON
        sentence_text = breakdown.get("sentence", "")
        focus_info = breakdown.get("focus", {})
        focus_word = focus_info.get("word", "N/A")
        reading = focus_info.get("reading", "")
        meanings = ", ".join(focus_info.get("meanings", []))
        gpt_explanation = breakdown.get("gpt_explanation", "")
        
        video_clip_on_disk = os.path.basename(clip_data.video_clip_path)
        source_info = clip_data.original_video_file_name or clip_data.original_video_url or "N/A"

        note_fields = [
            sentence_text,
            focus_word,
            reading,
            meanings,
            gpt_explanation,
            f'[sound:{video_clip_on_disk}]', # Anki media reference
            source_info
        ]
        anki_note = genanki.Note(model=anki_model, fields=note_fields)
        anki_deck.add_note(anki_note)
        
        # Add full path of the media file to be packaged
        full_media_path = os.path.join(BASE_MEDIA_PATH, clip_data.video_clip_path)
        if os.path.exists(full_media_path):
            media_files_to_package.append(full_media_path)
        else:
            logger.warning(f"Media file {full_media_path} for clip {clip_data.id} not found. It will be missing in Anki deck.")

    # Package the deck with media files
    anki_package = genanki.Package(anki_deck)
    anki_package.media_files = media_files_to_package
    
    # Save the .apkg file to a temporary servable location
    # Ensure TEMP_MEDIA_PATH (e.g., media_files/temp) is created and servable
    apkg_filename = f"{profile_id}_anki_deck_{int(time.time())}.apkg"
    apkg_filepath = os.path.join(TEMP_MEDIA_PATH, apkg_filename)
    
    try:
        anki_package.write_to_file(apkg_filepath)
        logger.info(f"Anki deck for profile {profile_id} saved to {apkg_filepath}")
    except Exception as e:
        logger.exception(f"Failed to write Anki package for profile {profile_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate Anki deck: {str(e)}")

    # Return the URL to the generated .apkg file
    # /media is the mount point for StaticFiles(directory="media_files")
    anki_deck_url = f"/media/temp/{apkg_filename}" 
    return AnkiExportResponse(anki_deck_url=anki_deck_url)

