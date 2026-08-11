import asyncio

from aiohttp import ClientSession, ClientTimeout

from src.settings import settings
from src.modules.logger.logger import Logger

log = Logger()

# Court volontairement : ce chemin est fire-and-forget, on ne veut pas retarder
# le Referee en attendant une réponse de Next.js.
REQUEST_TIMEOUT = ClientTimeout(total=3)

# Garde une référence forte sur les tasks en cours pour éviter qu'elles ne soient
# ramassées par le garbage collector avant d'avoir terminé (piège classique
# d'asyncio.create_task sans référence conservée).
_pending_tasks: set[asyncio.Task] = set()


class Connector:
    """Session aiohttp partagée, réutilisée pour tous les appels vers le frontend
    plutôt que d'en recréer une à chaque notification."""

    _session: ClientSession | None = None

    @classmethod
    def get_session(cls) -> ClientSession:
        if cls._session is None:
            cls._session = ClientSession(
                base_url=settings.frontend_url, timeout=REQUEST_TIMEOUT
            )
        return cls._session


async def _post_termination_event(battle_id: int | str) -> None:
    """Effectue réellement l'appel HTTP. Toute erreur (réseau, timeout, statut HTTP
    en erreur) est avalée ici : ce chemin est volontairement non fiable, une Phase 6
    de sweep périodique côté Next rattrape les notifications manquées."""
    session = Connector.get_session()
    try:
        async with session.post(f"/api/internal/battles/{battle_id}/settle"):
            pass
    except Exception as exc:  # noqa: BLE001 - fire-and-forget, ne doit jamais remonter
        log.debug(
            f"[BATTLE {battle_id}] Notification de fin de bataille au frontend ignorée",
            exc,
        )


def send_termination_event_to_frontend(battle_id: int | str) -> None:
    """Notifie Next.js (hash-contenders) qu'une bataille vient de se terminer, pour
    déclencher le settlement des paris associés (escrow + outbox côté Next).

    Fire-and-forget strict :
    - à appeler uniquement APRÈS que `battles.is_finished` a été committé en base,
      jamais avant (sinon Next pourrait lire `is_finished=false` en requêtant
      `/status/{battle_id}` juste après avoir reçu la notification) ;
    - ne bloque jamais l'appelant : la requête HTTP est schedulée en tâche de fond,
      cette fonction retourne immédiatement ;
    - pas de retry, timeout court, la réponse (y compris erreurs) est ignorée.
    """
    task = asyncio.create_task(_post_termination_event(battle_id))
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)
