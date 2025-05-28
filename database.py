import os
import uuid # For generating unique IDs
from databases import Database
from sqlalchemy import (create_engine, MetaData, Table, Column, String, 
                        Text, ForeignKey, UniqueConstraint, JSON, Float, DateTime)
import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mirumoji.db")

database = Database(DATABASE_URL)
metadata = MetaData()

profiles = Table(
    "profiles",
    metadata,
    Column("id", String, primary_key=True, index=True),
    Column("name", String, unique=True, index=True), # Profile ID from X-Profile-ID header
)

gpt_templates = Table(
    "gpt_templates",
    metadata,
    Column("id", String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())),
    Column("profile_id", String, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("sys_msg", Text, nullable=False),
    Column("prompt", Text, nullable=False),
    UniqueConstraint("profile_id", name="uq_profile_template")
)

profile_transcripts = Table(
    "profile_transcripts",
    metadata,
    Column("id", String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())),
    Column("profile_id", String, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
    Column("original_file_name", String, nullable=True),
    Column("transcript", Text, nullable=False),
    Column("gpt_explanation", Text, nullable=True),
    Column("audio_file_path", String, nullable=True), # Relative path: profiles/<profile_id>/audios/filename
    Column("created_at", DateTime, default=datetime.datetime.utcnow)
)

# Generic table for any file associated with a profile (original uploads, conversions etc.)
# This can be used to list files under "Fetch Profile's Files"
profile_files = Table(
    "profile_files",
    metadata,
    Column("id", String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())),
    Column("profile_id", String, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
    Column("file_name", String, nullable=False), # User-facing file name
    Column("file_path", String, nullable=False, unique=True), # Relative path from media_files dir, e.g., profiles/profile_id/videos/my_video.mp4
    Column("file_type", String, nullable=True), # e.g., 'original_video', 'converted_video', 'audio_source', 'video_clip'
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
    Column("related_transcript_id", String, ForeignKey("profile_transcripts.id"), nullable=True), # Link to a transcript if this is its source audio/video
    # Add other metadata like size, mimetype if needed
)

clips = Table(
    "clips",
    metadata,
    Column("id", String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())),
    Column("profile_id", String, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
    Column("clip_start_time", Float, nullable=False),
    Column("clip_end_time", Float, nullable=False),
    Column("gpt_breakdown_response", JSON, nullable=False), # Store the full JSON string or dict
    Column("video_clip_path", String, nullable=False, unique=True), # Relative path: profiles/<profile_id>/clips/filename.webm
    Column("original_video_file_name", String, nullable=True),
    Column("original_video_url", String, nullable=True), # If sourced from a URL
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
    # We can link a clip to a profile_file entry if the video_clip_path is also stored there with type 'video_clip'
    # Column("profile_file_id", String, ForeignKey("profile_files.id"), nullable=True)
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

async def get_db() -> Database:
    return database

async def connect_db():
    await database.connect()

async def disconnect_db():
    await database.disconnect()
