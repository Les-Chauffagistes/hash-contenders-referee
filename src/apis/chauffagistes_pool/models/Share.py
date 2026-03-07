from typing import Optional
from dataclasses import dataclass
from typing import Any

@dataclass
class Share:
    workinfoid: int
    clientid: int
    diff: int
    sdiff: float
    hash: str
    result: bool
    errn: int
    createdate: str
    ts: float
    workername: str
    username: str
    address: str
    worker: str
    workernameAddr: str
    ip: str
    agent: str
    round: str
    file: str
    rejectReason: Optional[str] = None

    @classmethod
    def from_any(cls, data: Any) -> "Share":
        if isinstance(data, dict):
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        elif isinstance(data, Share):
            return data
        else:
            raise ValueError(f"Cannot create Share from {data!r}")
