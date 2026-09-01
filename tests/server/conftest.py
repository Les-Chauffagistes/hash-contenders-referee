"""`src/server/**` transitively imports `init.py` (needs API_URL/API_TOKEN) and, for
handlers behind auth, `src.settings.Settings` (needs the full set below). Neither
`sonar.yml` nor `test.yml` currently sets these, so any test that imports these
modules crashes at collection time — which is also why coverage.py silently drops
them from the report entirely. Setting harmless test defaults here (only if unset)
makes this whole subtree importable and testable.
"""

import os

os.environ.setdefault("API_URL", "wss://shares-ws.test.invalid/ws")
os.environ.setdefault("API_TOKEN", "test-api-token")
os.environ.setdefault("AUTH_API_URL", "http://auth.test.invalid")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SERVER_PORT", "8095")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3003")

import pytest
from init import app as global_app, referee as global_referee


@pytest.fixture
def wired_app(prisma_tx, log):
    """Branche la transaction de test sur les singletons globaux `app`/`referee` de
    `init.py`, que `src/server/**` utilise directement (pas d'injection par requête)."""
    global_app["prisma"] = prisma_tx
    global_referee.prisma = prisma_tx
    global_referee.log = log
    yield global_app
