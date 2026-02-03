from prisma import Prisma
import pytest_asyncio
import pytest
from src.modules.logger.logger import Logger
from src.rules.Referee import Referee
from state import client_webosckets



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