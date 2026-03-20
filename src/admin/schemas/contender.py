from typing import Optional

from pydantic import BaseModel, Field


class ContenderCreateSchema(BaseModel):
    slot: int = Field(..., ge=1, le=100)
    name: str = Field(..., min_length=1, max_length=120)
    address: str = Field(..., min_length=8, max_length=255)
    team_name: Optional[str] = Field(default=None, max_length=120)


class ContenderUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    address: Optional[str] = Field(default=None, min_length=8, max_length=255)
    team_name: Optional[str] = Field(default=None, max_length=120)