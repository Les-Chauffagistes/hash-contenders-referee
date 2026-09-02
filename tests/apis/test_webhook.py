import asyncio
from unittest.mock import MagicMock

import pytest

from src.apis.contenders import webhook


class _FakeResponseCtx:
    """Fake context manager renvoyé par `session.post(...)`, simule une réponse HTTP
    (ou une erreur réseau/timeout si `exc` est fourni)."""

    def __init__(self, exc: Exception | None = None):
        self._exc = exc

    async def __aenter__(self):
        if self._exc:
            raise self._exc
        return MagicMock()

    async def __aexit__(self, *args):
        return False


def _track_created_tasks(monkeypatch) -> list[asyncio.Task]:
    """Intercepte les tasks créées par `asyncio.create_task` dans le module webhook,
    pour pouvoir les attendre explicitement dans les tests (la fonction testée est
    fire-and-forget et ne renvoie pas la task elle-même)."""
    created_tasks: list[asyncio.Task] = []
    real_create_task = asyncio.create_task

    def _tracking_create_task(coro):
        task = real_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(webhook.asyncio, "create_task", _tracking_create_task)
    return created_tasks


def test_send_termination_event_is_non_blocking():
    """La fonction doit être appelable sans await (fire-and-forget strict) :
    elle ne bloque jamais le flux principal du Referee."""
    assert not asyncio.iscoroutinefunction(webhook.send_termination_event_to_frontend)


@pytest.mark.asyncio
async def test_send_termination_event_posts_to_settle_endpoint(monkeypatch):
    session = MagicMock()
    session.post = MagicMock(return_value=_FakeResponseCtx())
    monkeypatch.setattr(webhook.Connector, "get_session", classmethod(lambda cls: session))
    created_tasks = _track_created_tasks(monkeypatch)

    webhook.send_termination_event_to_frontend(42)
    await asyncio.gather(*created_tasks)

    session.post.assert_called_once_with("/api/internal/battles/42/settle")


@pytest.mark.asyncio
async def test_send_termination_event_never_raises_on_http_failure(monkeypatch):
    """Timeout / erreur réseau : ne doit jamais remonter d'exception, ce chemin est
    volontairement non fiable (Phase 6 sweep côté Next rattrape les cas manqués)."""
    session = MagicMock()
    session.post = MagicMock(return_value=_FakeResponseCtx(exc=TimeoutError("boom")))
    monkeypatch.setattr(webhook.Connector, "get_session", classmethod(lambda cls: session))
    created_tasks = _track_created_tasks(monkeypatch)

    webhook.send_termination_event_to_frontend(7)

    results = await asyncio.gather(*created_tasks, return_exceptions=True)
    assert results == [None]


def test_send_cancellation_event_is_non_blocking():
    """Même garantie fire-and-forget que la notification de fin de bataille."""
    assert not asyncio.iscoroutinefunction(webhook.send_cancellation_event_to_frontend)


@pytest.mark.asyncio
async def test_send_cancellation_event_posts_to_cancel_endpoint(monkeypatch):
    session = MagicMock()
    session.post = MagicMock(return_value=_FakeResponseCtx())
    monkeypatch.setattr(webhook.Connector, "get_session", classmethod(lambda cls: session))
    created_tasks = _track_created_tasks(monkeypatch)

    webhook.send_cancellation_event_to_frontend(42)
    await asyncio.gather(*created_tasks)

    session.post.assert_called_once_with("/api/internal/battles/42/cancel")


@pytest.mark.asyncio
async def test_send_cancellation_event_never_raises_on_http_failure(monkeypatch):
    """Même garantie fire-and-forget que la notification de fin de bataille :
    une notification perdue est rattrapée par le sweep périodique côté Next."""
    session = MagicMock()
    session.post = MagicMock(return_value=_FakeResponseCtx(exc=TimeoutError("boom")))
    monkeypatch.setattr(webhook.Connector, "get_session", classmethod(lambda cls: session))
    created_tasks = _track_created_tasks(monkeypatch)

    webhook.send_cancellation_event_to_frontend(7)

    results = await asyncio.gather(*created_tasks, return_exceptions=True)
    assert results == [None]
