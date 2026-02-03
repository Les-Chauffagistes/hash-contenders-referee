from typing import Optional
from dataclasses import dataclass
from typing import Any

@dataclass
class Share:
    workinfoid: int
    clientid: int
    enonce1: str
    enonce2: str
    nonce: str
    ntime: str
    diff: float
    sdiff: Optional[float]
    hash: str
    result: bool
    errn: int
    createdate: float
    createby: str
    createcode: str
    createinet: str
    workername: str
    username: str
    address: str
    agent: str
    reject_reason: Optional[str]
    round: str

    @classmethod
    def from_any(cls, data: Any) -> "Share":
        if isinstance(data, dict):
            return cls(**data)
        elif isinstance(data, Share):
            return data
        else:
            raise ValueError(f"Cannot create Share from {data!r}")
