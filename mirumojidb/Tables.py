import uuid
from sqlalchemy import (MetaData,
                        Table,
                        Column,
                        String,
                        Text,
                        ForeignKey,
                        UniqueConstraint,
                        JSON,
                        Float,
                        DateTime)
import datetime

METADATA = MetaData()
# ---------------------
# ---Profiles Table---
profiles = Table(
    "profiles",
    METADATA,
    Column("id",
           String,
           primary_key=True,
           index=True),
    Column("name",
           String,
           unique=True,
           index=True),
)
# ----------------------------
# --- GPT Templates Table ---
gpt_templates = Table(
    "gpt_templates",
    METADATA,
    Column("id",
           String,
           primary_key=True,
           index=True,
           default=lambda: str(uuid.uuid4())),
    Column("profile_id",
           String,
           ForeignKey("profiles.id", ondelete="CASCADE"),
           nullable=False,
           unique=True),
    Column("sys_msg",
           Text,
           nullable=False),
    Column("prompt",
           Text,
           nullable=False),
    UniqueConstraint("profile_id",
                     name="uq_profile_template")
)
# ---------------------------------
# --- Profile Transcripts Table ---
profile_transcripts = Table(
    "profile_transcripts",
    METADATA,
    Column("id",
           String,
           primary_key=True,
           index=True,
           default=lambda: str(uuid.uuid4())),
    Column("profile_id",
           String,
           ForeignKey("profiles.id", ondelete="CASCADE"),
           nullable=False),
    Column("original_file_name",
           String,
           nullable=True),
    Column("transcript",
           Text,
           nullable=False),
    Column("gpt_explanation",
           Text,
           nullable=True),
    # Relative path: profiles/<profile_id>/audios/filename
    Column("audio_file_path",
           String,
           nullable=True),
    Column("created_at", DateTime, default=datetime.datetime.now())
)
# ---------------------------
# --- Profile Files Table ---
profile_files = Table(
    "profile_files",
    METADATA,
    Column("id",
           String,
           primary_key=True,
           index=True,
           default=lambda: str(uuid.uuid4())),
    Column("profile_id",
           String,
           ForeignKey("profiles.id", ondelete="CASCADE"),
           nullable=False),
    # User-facing file name
    Column("file_name",
           String,
           nullable=False),
    # Relative path from media_files dir,
    # e.g., profiles/profile_id/videos/my_video.mp4
    Column("file_path",
           String,
           nullable=False,
           unique=True),
    # e.g., 'original_video', 'converted_video', 'audio_source', 'video_clip'
    Column("file_type",
           String,
           nullable=True),
    Column("created_at",
           DateTime,
           default=datetime.datetime.now()),
    # Link to a transcript if this is its source audio/video
    Column("related_transcript_id",
           String,
           ForeignKey("profile_transcripts.id"),
           nullable=True),
)
# -------------------
# --- Clips Table ---
clips = Table(
    "clips",
    METADATA,
    Column("id",
           String,
           primary_key=True,
           index=True,
           default=lambda: str(uuid.uuid4())),
    Column("profile_id",
           String,
           ForeignKey("profiles.id", ondelete="CASCADE"),
           nullable=False),
    Column("clip_start_time",
           Float,
           nullable=False),
    Column("clip_end_time",
           Float,
           nullable=False),
    # Store the full JSON string or dict
    Column("gpt_breakdown_response",
           JSON,
           nullable=False),
    # Relative path: profiles/<profile_id>/clips/filename.webm
    Column("video_clip_path",
           String,
           nullable=False,
           unique=True),
    Column("original_video_file_name",
           String,
           nullable=True),
    # If sourced from a URL
    Column("original_video_url",
           String,
           nullable=True),
    Column("created_at",
           DateTime,
           default=datetime.datetime.now()),
)
# ------------------------------
