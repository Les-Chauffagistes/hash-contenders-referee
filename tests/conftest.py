from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rules.Referee import Referee


@pytest.fixture
def prisma():
    return SimpleNamespace(
        rounds=SimpleNamespace(
            find_many=AsyncMock(),
            find_unique=AsyncMock(),
        ),
        battles=SimpleNamespace(
            update=AsyncMock(),
            find_unique=AsyncMock(),
        ),
        battle_entries=SimpleNamespace(
            create=AsyncMock(),
        ),
        query_raw=AsyncMock(),
        execute_raw=AsyncMock(),
    )


@pytest.fixture
def broadcaster():
    return SimpleNamespace(
        new_round=AsyncMock(),
        new_best_share=AsyncMock(),
        hit_result=AsyncMock(),
        battle_end=AsyncMock(),
    )


@pytest.fixture
def logger():
    return SimpleNamespace(
        debug=AsyncMock(),
        info=AsyncMock(),
        warn=AsyncMock(),
        warning=AsyncMock(),
        exception=AsyncMock(),
    )


@pytest.fixture
def referee(prisma, broadcaster, logger):
    r = Referee()
    r.prisma = prisma
    r.event_dispatcher = broadcaster
    r.log = logger
    return r


@pytest.fixture
def battle():
    return SimpleNamespace(
        id=1,
        status="LIVE",
        start_height=100,
        entries=[
            SimpleNamespace(
                id=101,
                slot=1,
                address="bc1aaa",
                worker_name="rig1",
                current_pv=3,
                rounds_won=0,
                rounds_lost=0,
                status="ACTIVE",
            ),
            SimpleNamespace(
                id=102,
                slot=2,
                address="bc1bbb",
                worker_name="rig2",
                current_pv=3,
                rounds_won=0,
                rounds_lost=0,
                status="ACTIVE",
            ),
        ],
    )


@pytest.fixture
def share_slot1():
    return SimpleNamespace(
        address="bc1aaa",
        worker="rig1",
        sdiff=12345,
        round=hex(100),
    )


@pytest.fixture
def share_slot2():
    return SimpleNamespace(
        address="bc1bbb",
        worker="rig2",
        sdiff=23456,
        round=hex(100),
    )