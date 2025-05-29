import os
from databases import Database
from sqlalchemy import create_engine
from db.Tables import METADATA
from db.Tables import (gpt_templates)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mirumoji.db")
database = Database(DATABASE_URL)
METADATA = METADATA
engine = create_engine(DATABASE_URL)
METADATA.create_all(engine)


async def get_db() -> Database:
    return database


async def connect_db() -> None:
    await database.connect()


async def disconnect_db() -> None:
    await database.disconnect()


async def get_gpt_template_db(profile_id: str):
    q = gpt_templates.select().where(gpt_templates.c.profile_id == profile_id)
    return await database.fetch_one(q)
