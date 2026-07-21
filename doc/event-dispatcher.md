# Event Dispatcher — Événements WebSocket vers les clients

→ [README](./README.md) | [Architecture](./architecture.md) | [Referee](./referee.md) | [API](./api.md)

Fichiers : `src/event_dispatcher/WebsocketBroadcaster.py`, `state.py`

## `WebsocketBroadcaster`

Broadcast les événements de bataille aux clients frontend connectés via WebSocket (`/ws/{battle_id}`).

Attribut de classe injecté au démarrage :
```python
event_dispatcher.client_websockets = client_webosckets  # ClientWebsockets
```

### Événements émis

#### `BEST_SHARE_UPDATE`
Émis quand un contender soumet un share **avec une meilleure difficulté** que sa précédente sur le round courant.

```json
{
  "type": "BEST_SHARE_UPDATE",
  "user": "contender_1",
  "diff": 42000,
  "block_height": "0x1a2b3c"
}
```

#### `ROUND_UPDATE`
Émis quand un **nouveau round** est créé (premier share sur un nouveau block height).

```json
{
  "type": "ROUND_UPDATE",
  "round": 3,
  "block_height": "0x1a2b3c"
}
```

#### `HIT_RESULT`
Émis quand un round est **finalisé** (les deux contenders ont joué sur un block supérieur).

```json
{
  "type": "HIT_RESULT",
  "block_height": "0x1a2b3c",
  "winner": 1,
  "date": "2024-01-15 14:30:00",
  "contender_1_best_diff": 55000,
  "contender_2_best_diff": 42000,
  "contender_1_pv": 9,
  "contender_2_pv": 8
}
```
> `winner` = `1`, `2`, ou `null` (égalité)

#### `BATTLE_END`
Émis quand la bataille se termine (KO ou max rounds atteint).

```json
{
  "type": "BATTLE_END",
  "winner": 1,
  "contender_1_pv": 5,
  "contender_2_pv": 0
}
```

---

## `ClientWebsockets` — Gestion des connexions frontend

`state.py`

Dictionnaire `battle_id → list[WebSocketResponse]` gérant les connexions des clients frontend.

### Méthodes

| Méthode | Description |
|---|---|
| `add(battle_id, ws)` | Enregistre un nouveau client WS pour une bataille |
| `broadcast(battle_id, data)` | Envoie `data` (JSON) à tous les clients de la bataille. Supprime et ferme les connexions en erreur. |
| `close(battle_id)` | Ferme toutes les connexions d'une bataille et retire l'entrée du dict |

> `close()` est appelé par `Referee` à la fin d'une bataille (KO ou max rounds).

### Sécurité des connexions cassées
Dans `broadcast`, si `ws.send_json()` lève une exception, le client est retiré de la liste et sa connexion est fermée proprement.
