from typing import TypedDict
from .PoolHashrates import PoolHashrates
from .PoolRuntime import PoolRuntime
from .PoolShares import PoolShares


class Pool(TypedDict):
    runtime: PoolRuntime
    hashrates: PoolHashrates
    shares: PoolShares