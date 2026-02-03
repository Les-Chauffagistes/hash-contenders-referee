# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hash Contenders Referee is a real-time battle referee service for cryptocurrency mining pool competitions. It listens to mining shares from the Chauffagistes pool, tracks battles between two contenders, computes round winners based on best difficulty shares, and broadcasts results via WebSocket.

## Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
prisma generate
```

### Run the Server
```bash
python main.py
```
Requires `SERVER_PORT`, `DATABASE_URL`, and `API_URL` environment variables (use `.env` file).

### Run Tests
```bash
pytest                           # all tests
pytest tests/referee/            # referee tests only
pytest tests/referee/test_compute_pv.py  # single test file
pytest -k test_hits_diff         # single test by name
```

### Database
```bash
prisma generate   # regenerate client after schema changes
prisma db push    # apply schema to database
```

## Architecture

### Core Flow
1. `main.py` starts an aiohttp server and the shares listener
2. `shares_listener` (`src/rules/shares_listener.py`) polls for active battles and opens WebSocket connections to the pool API for each contender
3. When shares arrive, `Referee.on_share()` processes them:
   - Finalizes past rounds (determines winner by comparing best difficulties)
   - Creates new rounds when block height changes
   - Updates best share for the current round
4. `WebsocketBroadcaster` pushes events (`BEST_SHARE_UPDATE`, `ROUND_UPDATE`, `HIT_RESULT`) to connected clients

### Key Components
- **Referee** (`src/rules/Referee.py`): Core game logic - manages rounds, computes PV (health points), determines winners
- **WebsocketWrapper** (`src/apis/chauffagistes_pool/ws.py`): Maintains persistent WebSocket connections to the pool API with auto-reconnect
- **WebsocketBroadcaster** (`src/event_dispatcher/WebsocketBroadcaster.py`): Broadcasts battle events to frontend clients
- **ClientWebsockets** (`state.py`): Manages connected client WebSockets per battle

### Database (Prisma + PostgreSQL)
- `battles`: Active/finished battles with contender info and PV settings
- `rounds`: Per-block-height round data with best difficulties and winner

### Dependency Injection Pattern
Dependencies (`prisma`, `log`, `event_dispatcher`) are injected into `Referee` class attributes at startup in `main.py` rather than passed via constructor.

## Testing

Tests use `prisma_tx` fixture which wraps each test in a transaction that rolls back, keeping the database clean. See `tests/conftest.py` for fixtures.
