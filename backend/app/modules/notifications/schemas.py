from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List

class AlertSchema(BaseModel):
    id: str
    title: str
    body: str
    category: str = "INFO"
    created_at: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)

class AlertList(BaseModel):
    data: List[AlertSchema]
    total: int
