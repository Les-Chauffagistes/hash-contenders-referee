import os
from pathlib import Path
from shutil import which
import subprocess
import sys

import asyncpg
from prisma import Prisma
import pytest_asyncio
import pytest
from src.modules.logger.logger import Logger
from src.rules.Referee import Referee
from dotenv import load_dotenv

load_dotenv(".env.test")
def _resolve_prisma_cli() -> str:
    prisma = which("prisma")
    if prisma:
        return prisma

    candidates = [
        Path(sys.executable).resolve().parent / "prisma",
        Path(__file__).resolve().parents[1] / "venv" / "bin" / "prisma",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "Unable to locate the Prisma CLI. Expected it in PATH or venv/bin/prisma."
    )


def _ensure_test_db():
    """Crée la BDD de test et applique le schéma Prisma si nécessaire."""
    db_url = os.environ["DATABASE_URL"]
    db_name = db_url.rsplit("/", 1)[-1].split("?")[0]
    server_url = db_url.rsplit("/", 1)[0] + "/template1"

    import asyncio

    async def _create_db():
        conn = await asyncpg.connect(server_url)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not exists:
                print("creating", db_name)
                await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()

    asyncio.run(_create_db())

    subprocess.run(
        [_resolve_prisma_cli(), "db", "push", "--skip-generate"],
        env={**os.environ, "DATABASE_URL": db_url},
        check=True,
        capture_output=True,
    )


_ensure_test_db()


# NE PAS RÉUTILISER. UTILISER prisma_tx SI BESOIN DE PRISMA
@pytest_asyncio.fixture
async def prisma_client():
    prisma = Prisma()
    await prisma.connect()
    yield prisma
    await prisma.disconnect()

@pytest_asyncio.fixture
async def prisma_tx(prisma_client: Prisma):
    tx =  prisma_client.tx()
    transaction = await tx.start()
    try:
        yield transaction

    finally:
        await tx.rollback()

@pytest.fixture
def log():
    log = Logger()
    yield log

@pytest.fixture
def referee(prisma_tx: Prisma, log: Logger):
    referee = Referee()
    referee.prisma = prisma_tx
    referee.log = log

    yield referee