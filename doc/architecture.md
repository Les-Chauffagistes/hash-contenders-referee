# Architecture

→ [README](./README.md) | [Referee](./referee.md) | [Shares Listener](./shares-listener.md) | [API](./api.md) | [Event Dispatcher](./event-dispatcher.md)

## Flux global

```
Pool de minage (WS)
        │  shares (address, sdiff, round/block_height)
        ▼
  WebsocketWrapper          ← src/apis/chauffagistes_pool/ws.py
  (une instance par contender par battle)
        │
        ▼
  shares_listener()         ← src/rules/shares_listener.py
  (boucle poll toutes les 3s, démarre/arrête les WS)
        │
        ▼
  Referee.on_share()        ← src/rules/Referee.py
  (logique métier principale)
        │
        ├─► PostgreSQL (Prisma)  ← prisma/schema.prisma
        │   rounds + battles
        │
        └─► WebsocketBroadcaster ← src/event_dispatcher/WebsocketBroadcaster.py
              │  BEST_SHARE_UPDATE / ROUND_UPDATE / HIT_RESULT / BATTLE_END
              ▼
         ClientWebsockets        ← state.py
         (clients frontend connectés via WS HTTP)
```

## Composants principaux

### `main.py`
Point d'entrée. Démarre le serveur `aiohttp`, injecte les dépendances dans `Referee` (classe-level), puis lance la coroutine `shares_listener`.

### `init.py`
Module importé en premier. Crée les **singletons globaux** :
- `log` : `Logger`
- `app` : Application aiohttp (avec middleware `error_handler`)
- `referee` : instance `Referee`
- `event_dispatcher` : instance `WebsocketBroadcaster`
- `API_URL`, `api_token` : variables d'env lues ici (exit si absentes)

> ⚠️ Les modules utilisant Prisma doivent être importés **après** `app.on_startup` (i.e., dans `main()`), car Prisma est initialisé au démarrage de l'app.

### Injection de dépendances
`Referee` utilise des **attributs de classe** (pas de constructeur) injectés dans `main()` :

```python
Referee.prisma = app["prisma"]   # client Prisma connecté
Referee.log = log
Referee.event_dispatcher = event_dispatcher
```

Même pattern pour `WebsocketBroadcaster` :
```python
event_dispatcher.client_websockets = client_webosckets
```

### Concurrence
- Le serveur HTTP et les listeners WebSocket tournent dans le **même event loop asyncio**.
- Chaque battle active a **2 tâches asyncio** : une par contender (un listener WS chacun).
- Les shares d'une même battle peuvent donc arriver en parallèle → `finalize_rounds` utilise `ON CONFLICT DO NOTHING` et des conditions SQL atomiques pour éviter les races.

## Cycle de vie d'une bataille

```
1. Création via POST /battle (HTTP API)
2. shares_listener détecte la battle (is_finished=False)
3. Ouverture de 2 WS vers le pool (un par adresse contender)
4. Réception des shares → Referee.on_share()
5. Fin de bataille : KO (PV ≤ 0) ou max rounds atteint
6. shares_listener ferme les 2 WS au prochain poll (3s)
```
