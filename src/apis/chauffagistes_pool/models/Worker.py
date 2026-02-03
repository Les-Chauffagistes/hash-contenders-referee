from typing import TypedDict

class Worker(TypedDict):
    workername: str
    hashrate1m: str
    hashrate5m: str
    hashrate1hr: str
    hashrate1d: str
    hashrate7d: str
    lastshare: int
    shares: int
    bestshare: float
    bestever: int