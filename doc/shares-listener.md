# Shares Listener — Connexion au pool de minage

→ [README](./README.md) | [Architecture](./architecture.md) | [Referee](./referee.md)

Fichiers : `src/rules/shares_listener.py`, `src/apis/chauffagistes_pool/ws.py`

## `shares_listener()` — boucle de surveillance

Coroutine principale lancée dans `main.py` via `create_task`.

### Comportement

```
Toutes les 3 secondes :
  1. Requête DB : battles WHERE is_finished = False
  2. Pour chaque battle active sans WS ouvert :
       → ouvre 2 WebsocketWrapper (un par contender)
       → lance 2 tâches asyncio (continuous_listener)
       → stocke dans dict active[battle_id]
  3. Pour chaque battle devenue terminée (is_finished = True) :
       → ws1.stop() + ws2.stop()
       → annule les tâches asyncio
       → retire de active
  4. sleep(3)
```

> Les erreurs dans la boucle sont catchées silencieusement (log.error) pour ne pas tuer la boucle.

### URL de connexion au pool
```
{API_URL}/shares?address={contender_address}
{API_URL}/shares?address={contender_address}&worker={contender_worker}   ← si un mineur précis est ciblé
```
Construite par `build_shares_url()` (`src/apis/chauffagistes_pool/url.py`). Les deux contenders d'une même battle ont chacun leur propre connexion WS. Quand `battle.contender_N_worker` est renseigné (bataille "Mineur vs Mineur"), le paramètre `worker` est ajouté à l'URL : c'est le pool lui-même qui filtre alors les shares pour ne renvoyer que celles de ce mineur — le referee n'a rien à filtrer côté client. Sans worker ciblé (mode "Pool vs Pool", comportement historique), toutes les shares de l'adresse comptent.

---

## `WebsocketWrapper` — connexion WS persistante

`src/apis/chauffagistes_pool/ws.py`

### Architecture interne

```
continuous_listener()
    │
    ├─ Lance _message_worker() comme tâche asyncio
    │
    └─ Boucle de reconnexion :
         websockets.connect(uri, Authorization: Bearer {API_TOKEN})
         async for message in ws:
             queue.put(message)    ← non-bloquant
         [déconnexion → sleep 5s → reconnect]

_message_worker()
    └─ Boucle :
         message = await queue.get(timeout=1s)
         await hanlde_message(message)
```

### Découpage receive / process
- Le **receive loop** pousse les messages dans une `asyncio.Queue`
- Le **worker** les traite séquentiellement, découplant la réception du traitement
- Évite que `hanlde_message` (qui appelle `Referee.on_share`, donc des requêtes DB) ne bloque la réception de nouveaux messages

### `hanlde_message(message)` *(typo conservée)*
- Parse le JSON
- Si `type == "hello"` → ignoré (message de bienvenue du pool)
- Si `type == "share"` → construit un objet `Share` et appelle `self.on_message(share)`
- Autres types → log warning

### Auto-reconnexion
En cas de déconnexion (`WebSocketException`, `OSError`, autre) :
- Status passe à `DISCONNECTED`
- Attend 5 secondes
- Relance la connexion (tant que `_running = True`)

### `stop()`
Met `_running = False` et ferme le WebSocket actif. La boucle de reconnexion s'arrête naturellement.

### États
```python
class Status(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
```

### Format des messages reçus du pool

```json
{ "type": "hello" }

{
  "type": "share",
  "share": {
    "worker": "worker_name",
    "address": "pool_address",
    "sdiff": 12345,
    "diff": 12345,
    "round": "0x1a2b3c",   ← block height en hexadécimal
    "ts": 1234567890
  }
}
```

Le champ `round` (hex) est converti en `int` par `Referee.on_share` via `int(payload.round, 16)`.

Type `Share` défini dans le package externe `pool_api_types`.
