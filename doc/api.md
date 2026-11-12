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
  "contender_1_worker": "string",
  "contender_2_address": "string",
  "contender_2_name": "string",
  "contender_2_worker": "string",
  "contenders_pv": 10,
  "rounds": 5,
  "start_height": 123456,
  "are_addresses_privates": false
}
```
`contender_1_worker` / `contender_2_worker` sont optionnels. Absents (ou vides) → bataille "Pool vs Pool" (comportement historique, toute la pool de l'adresse compte). Renseignés → bataille "Mineur vs Mineur", seules les shares de ce mineur précis comptent pour ce contender.
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
      "worker": null,
      "current_round_best_diff": 42000
    },
    { "..." }
  ]
}
```
> Si `are_addresses_privates = true`, le champ `address` est omis de `contender_info`. `worker` reste toujours présent (non `null` uniquement pour les batailles "Mineur vs Mineur") : ce n'est pas la donnée que `are_addresses_privates` masque.

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

## Hashrate des contenders

Le referee interroge `pool-api` via `GET /v1/stats/{adresse}` au démarrage,
puis toutes les 30 secondes pour les combats actifs, une requête par adresse distincte.
Configurer `STATS_API_URL` avec l’origine HTTP de pool-api (sans `/v1`) si elle diffère
de `API_URL`, et éventuellement `STATS_API_TOKEN`. L’intervalle est configurable
avec `HASHRATE_POLL_INTERVAL_SECONDS` (30 par défaut).

Chaque entrée de `contender_info` du statut REST inclut :
- `hashrate_hs` : estimation `hashrate1m` en H/s, total d’adresse ou worker ciblé ;
- `hashrate_window_seconds` : 60, période de lissage ;
- `hashrate_fetched_at` : date UTC de récupération réussie, pas date de mesure ckpool ;
- `hashrate_stale` : vrai si absent, worker introuvable, ou récupération de plus de deux intervalles.

Une panne conserve la dernière valeur connue. Une valeur absente vaut `null`,
une mesure nulle vaut `0`. Le cache est en mémoire et n’ajoute aucun identifiant
privé à la réponse. Les combats terminés ne sont plus collectés et leurs valeurs
sont retirées au prochain passage. Le navigateur doit relire le statut REST pour
obtenir les mesures actualisées ; aucun événement WebSocket hashrate n’est ajouté.
