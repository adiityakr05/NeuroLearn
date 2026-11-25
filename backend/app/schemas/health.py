from typing import Optional
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    version: str
    project: str
    database: str

    model_config = ConfigDict(from_attributes=True)
