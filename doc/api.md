# API HTTP & WebSocket

→ [README](./README.md) | [Architecture](./architecture.md) | [Event Dispatcher](./event-dispatcher.md)

Serveur : `aiohttp` | Handlers : `src/server/handlers/v1/`

## Endpoints HTTP

### `POST /battle`
Crée une nouvelle bataille.

**Body JSON :**
```json
{
  "contender_1_address": "string",
  "contender_1_name": "string",
  "contender_2_address": "string",
  "contender_2_name": "string",
  "contenders_pv": 10,
  "rounds": 5,
  "start_height": 123456,
  "are_addresses_privates": false
}
```
**Réponse :** objet `battles` formaté (BigInt sérialisés en string).  
**Erreurs :** `400` si JSON invalide ou champs manquants.

Fichier : `src/server/handlers/v1/create.py`  
Validation : `zon` (équivalent Python de Zod)

---

### `GET /battles`
Liste toutes les batailles.

**Réponse :** liste d'objets `battles`.

---

### `GET /battles/by-ids`
Retourne les batailles dont les IDs sont passés dans le body.

**Body JSON :**
```json
{ "ids": [1, 2, 3] }
```

---

### `GET /status/{battle_id}`
Retourne l'état détaillé d'une bataille.

**Query params :**
- `includes=hits` → inclut la liste des rounds finalisés

**Réponse :**
```json
{
  "battle_id": 1,
  "rounds": 5,
  "contenders_base_pv": 10,
  "start_height": 123456,
  "is_finished": false,
  "current_round": 3,
  "hits": [],
  "contender_info": [
    {
      "address": "...",
      "pv": 8,
      "name": "Contender 1",
      "current_round_best_diff": 42000
    },
    { "..." }
  ]
}
```
> Si `are_addresses_privates = true`, le champ `address` est omis de `contender_info`.

Fichier : `src/server/handlers/v1/status.py` → `src/server/core/status/v1.py`

---

### `GET /hits/{battle_id}`
Retourne tous les rounds (finalisés ou non) d'une bataille, triés par `block_height` décroissant.

---

### `GET /health`
Health check. Retourne `200 OK`.

Fichier : `src/server/health.py`

---

## WebSocket client

### `GET /ws/{battle_id}`

Connexion WebSocket pour recevoir les événements d'une bataille en temps réel.

- Heartbeat : 20s (autoping activé)
- Messages entrants ignorés (réponse `ack` en texte)
- La connexion est enregistrée dans `ClientWebsockets` et reçoit tous les broadcasts de cette bataille

**Événements reçus :** voir [event-dispatcher.md](./event-dispatcher.md)

Fichier : `src/server/handlers/v1/ws.py`

---

## Serialisation

Les `BigInt` Prisma sont convertis en `string` par le formatter (`src/server/utils/formatter.py`) avant sérialisation JSON.

## CORS

Activé sur toutes les routes via `aiohttp_cors` (`src/server/cors.py`). Configuré dans `main.py` après l'ajout des routes.
