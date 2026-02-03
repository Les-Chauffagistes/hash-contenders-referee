from typing import TypedDict

class PoolRuntime(TypedDict):
    runtime: int
    lastupdate: int
    users: int
    workers: int
    idle: int
    disconnected: int