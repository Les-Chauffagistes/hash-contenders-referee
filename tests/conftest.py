from collections.abc import Generator
import os
from pathlib import Path
from shutil import which
import subprocess
import sys

from prisma import Prisma
import pytest
import pytest_asyncio
from src.modules.logger.logger import Logger
from src.rules.Referee import Referee
from testcontainers.postgres import PostgresContainer


POSTGRES_IMAGE = "postgres:18.1-alpine3.23"


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


@pytest.fixture(scope="session")
def database_url() -> Generator[str, None, None]:
    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        with PostgresContainer(POSTGRES_IMAGE, driver=None) as postgres:
            db_url = postgres.get_connection_url()
            os.environ["DATABASE_URL"] = db_url
            subprocess.run(
                [_resolve_prisma_cli(), "migrate", "deploy"],
                env={**os.environ, "DATABASE_URL": db_url},
                check=True,
            )
            yield db_url
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


# NE PAS RÉUTILISER. UTILISER prisma_tx SI BESOIN DE PRISMA
@pytest_asyncio.fixture
async def prisma_client(database_url: str):
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