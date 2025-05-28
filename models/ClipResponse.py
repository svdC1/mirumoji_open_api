from typing import Any
from pydantic import BaseModel


class ClipResponse(BaseModel):
    id: str
    get_url: str
    breakdown_response: Any
