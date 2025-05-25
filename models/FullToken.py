from pydantic import BaseModel, ConfigDict
from typing import List


class FullToken(BaseModel):
    surface: str
    lemma: str
    reading: str
    pos: str
    meanings: List
    jlpt: str
    examples: List
    # Pydantic v2 style config
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"
    )
