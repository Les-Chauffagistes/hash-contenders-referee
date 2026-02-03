from typing import Dict, List
from dataclasses import dataclass

@dataclass
class PoolShares:
    diff: float
    accepted: int
    rejected: int
    bestshare: int
    SPS1m: float
    SPS5m: float
    SPS15m: float
    SPS1h: float