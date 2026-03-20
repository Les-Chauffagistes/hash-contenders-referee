from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


BattleMode = Literal["DUEL", "FFA", "TEAM_VS_TEAM"]


class BattleCreateSchema(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    mode: BattleMode = "DUEL"
    start_height: Optional[int] = Field(default=None, ge=0)
    planned_start_at: Optional[datetime] = None
    rounds: int = Field(default=1, ge=1, le=1000)
    max_pv: int = Field(default=100, ge=1, le=1_000_000)
    are_addresses_privates: bool = False


class BattleUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    mode: Optional[BattleMode] = None
    start_height: Optional[int] = Field(default=None, ge=0)
    planned_start_at: Optional[datetime] = None
    rounds: Optional[int] = Field(default=None, ge=1, le=1000)
    max_pv: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    are_addresses_privates: Optional[bool] = None