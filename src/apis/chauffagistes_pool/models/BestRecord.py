from typing import TypedDict


class BestRecord(TypedDict):
    month: str
    sdiff: float
    username: str
    workername: str
    epoch: float