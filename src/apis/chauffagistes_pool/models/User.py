from typing import List, TypedDict
from .Worker import Worker


class User(TypedDict):
    hashrate1m: str
    hashrate5m: str
    hashrate1hr: str
    hashrate1d: str
    hashrate7d: str
    lastshare: int
    workers: int
    shares: int
    bestshare: float
    bestever: int
    authorised: int
    worker: List[Worker]