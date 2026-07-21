# Hash Contenders Referee — Base de connaissances

Service arbitre temps-réel pour des compétitions de minage de cryptomonnaie.  
Il écoute les shares soumis par deux mineurs en compétition, calcule les vainqueurs de chaque round, gère les points de vie (PV) et diffuse les résultats via WebSocket aux clients frontend.

## Index

| Fichier | Contenu |
|---|---|
| [architecture.md](./architecture.md) | Vue d'ensemble, flux de données, composants |
| [database.md](./database.md) | Schéma Prisma, modèles `battles` et `rounds`, requêtes clés |
| [referee.md](./referee.md) | Logique métier : rounds, PV, KO, fin de bataille |
| [api.md](./api.md) | Endpoints HTTP REST et WebSocket exposés |
| [shares-listener.md](./shares-listener.md) | Connexion WebSocket au pool de minage, auto-reconnect |
| [event-dispatcher.md](./event-dispatcher.md) | Événements WebSocket broadcastés aux clients frontend |
| [testing.md](./testing.md) | Configuration des tests, fixtures, patterns |

## Démarrage rapide

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
prisma generate
python main.py
```

Variables d'environnement requises (`.env`) :

| Variable | Description |
|---|---|
| `SERVER_PORT` | Port du serveur HTTP/WS |
| `DATABASE_URL` | URL PostgreSQL |
| `API_URL` | URL de base du pool de minage (ex: `ws://pool:8080`) |
| `API_TOKEN` | Token Bearer pour l'API du pool |

## Points d'entrée du code

| Fichier | Rôle |
|---|---|
| `main.py` | Bootstrap : démarre le serveur aiohttp + lance `shares_listener` |
| `init.py` | Instancie les singletons globaux : `log`, `app`, `referee`, `event_dispatcher` |
| `state.py` | `ClientWebsockets` — gère les connexions WS des clients frontend par bataille |
