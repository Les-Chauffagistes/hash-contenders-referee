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
       → ouvre 1 WebsocketWrapper par filtre *distinct* (`contender_streams`, voir plus bas)
       → chaque wrapper reçoit son StreamCursor (curseur de reprise en base)
       → lance une tâche asyncio par connexion (continuous_listener)
       → stocke dans dict active[battle_id]
  3. Pour chaque battle devenue terminée (is_finished = True) :
       → stop() de chaque connexion
       → annule les tâches asyncio
       → retire de active
  4. sleep(3)
```

> Les erreurs dans la boucle sont catchées silencieusement (log.error) pour ne pas tuer la boucle.

### Flux par filtre (`contender_streams`, `src/utils/shares.py`)

Un flux par filtre `(adresse, worker)` distinct, la casse du worker étant ignorée comme côté pool :

| Bataille | Flux |
|---|---|
| Pool vs Pool (deux adresses, sans worker) | un par adresse |
| Mineur vs Mineur, même adresse, workers différents | un par worker |
| Mêmes adresse et worker pour les deux contenders | un seul, partagé (sinon chaque share serait traité deux fois) |

### URL de connexion au pool
```
{API_URL}/v1/shares/stream?workername={adresse}.{worker}[&from={epoch}:{seq}]   # contender ciblant un mineur
{API_URL}/v1/shares/stream?address={adresse}[&from={epoch}:{seq}]               # toute la pool de l'adresse
```
Le filtrage est fait côté serveur (workername insensible à la casse). Le `from` est le curseur de reprise, voir ci-dessous.

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
- Le **receive loop** pousse les messages dans une `asyncio.Queue` **bornée** (`queue_size`, 5000), pour continuer à lire le socket (et répondre aux pings) pendant un traitement lent
- Le **worker** les traite séquentiellement. Une queue par connexion, vidée avant de se reconnecter
- Si la queue est pleine, on ferme la connexion (en continuant de lire pour laisser passer le close) et on repart du curseur en base: le pool rejoue ce qui a été jeté

### Reprise par curseur (`src/database/share_cursors.py`, table `share_cursors`)
Chaque share porte un curseur `(epoch, seq)` (ordre lexicographique). Le curseur du dernier share **traité** est stocké en base par `(battle_id, stream_key)`, où `stream_key` est le filtre (`address=…` ou `workername=…`): un curseur n'est valable qu'avec le même filtre.

- À chaque connexion: lecture du curseur en base, puis `?from=<epoch>:<seq>`. Aucun état de reprise en local.
- Premier démarrage (pas de curseur): connexion sans `from` (flux live), et le curseur de départ donné par `hello` est enregistré.
- Après chaque `on_share` réussi: avance du curseur en base. L'écriture est monotone (`WHERE (epoch, seq) < …`), jamais avant le traitement.
- Livraison au moins une fois: un share `(epoch, seq) <=` curseur est ignoré. Le traitement du Referee est idempotent (meilleur diff seulement s'il augmente, round `ON CONFLICT DO NOTHING`), donc un crash entre `on_share` et l'écriture rejoue au plus un share sans effet.
- `on_share` en échec: 5 essais avec backoff, sans avancer le curseur. Au-delà le share est abandonné (log d'erreur), le curseur avance et `gap_count` est incrémenté pour ne pas bloquer la bataille.

### Messages
- `hello`: initialise le curseur au premier démarrage, ou après une perte (voir ci-dessous); log du retard de rattrapage (`head`)
- `share`: traité comme ci-dessus
- `heartbeat`, `watermark`: ignorés
- autres types → log warning

### Auto-reconnexion
En cas de déconnexion (`WebSocketException`, `OSError`, autre) :
- Status passe à `DISCONNECTED`
- Attend `reconnect_delay` (5 s, doublé à chaque tentative consécutive sans `hello`, plafonné à 60 s, avec jitter)
- Relance la connexion (tant que `_running = True`)

Codes de fermeture envoyés par le pool:

| Code | Signification | Comportement |
|---|---|---|
| 4408 | client trop lent | reconnexion avec le curseur en base |
| 4410 | curseur hors rétention: des shares sont **perdus** | log d'erreur, `gap_count + 1`, reconnexion sans `from`, curseur remplacé par celui de `hello` |
| 4400 | curseur invalide ou epoch inconnue | avec curseur: comme 4410. Sans curseur (erreur de configuration): attente de 60 s |
| 1013 | trop de clients | backoff exponentiel |

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

Voir `x-websocket-routes` dans l'`openapi.yaml` de pool-api. Le modèle `PoolWebsocketShareElement` est dans `chauff-cmn`.

```json
{ "type": "hello", "cursor": "1:100", "head": "1:250" }

{
  "type": "share",
  "share_id": "debian:000ed6bd/6ab2eef0000145f3.sharelog:1923",
  "epoch": 1, "seq": 20773258,
  "instance": "debian",
  "created_at": "2026-10-21T12:20:51.262066+00:00",
  "workinfoid": 7688470228434503155,
  "block_height": 970429,
  "username": "bc1q…", "workername": "bc1q….Hugo",
  "diff": 1000.0, "sdiff": 20286.9, "result": true, "parse_error": false
}

{ "type": "heartbeat", "time": "…" }
{ "type": "watermark", "watermark": "…" }
```

`block_height` est utilisé par `Referee.on_share` pour rattacher le share à un round.
