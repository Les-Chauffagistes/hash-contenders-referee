# Tests

→ [README](./README.md) | [Referee](./referee.md) | [Database](./database.md)

Fichiers : `tests/conftest.py`, `tests/referee/`

## Lancer les tests

```bash
pytest                                        # tous les tests
pytest tests/referee/                         # referee uniquement
pytest tests/referee/test_compute_pv.py       # un fichier
pytest -k test_hits_diff                      # un test par nom
```

## Infrastructure de test

Les tests utilisent **testcontainers** pour démarrer un vrai PostgreSQL Docker éphémère, puis appliquent les migrations Prisma.

### Fixtures (`tests/conftest.py`)

#### `database_url` — scope `session`
- Démarre un conteneur `postgres:18.1-alpine3.23`
- Applique `prisma migrate deploy`
- Yield l'URL de connexion
- Le conteneur est détruit à la fin de la session de test

#### `prisma_client` — scope `function`
- Connecte un client Prisma à `database_url`
- Déconnecte après le test

> ⚠️ Ne pas utiliser directement. Utiliser `prisma_tx` à la place.

#### `prisma_tx` — scope `function` ⭐ (fixture principale)
- Ouvre une **transaction** sur `prisma_client`
- Yield la transaction (utilisée comme client Prisma dans les tests)
- **Rollback systématique** en fin de test → la DB reste propre entre chaque test

#### `log` — scope `function`
- Instance fraîche de `Logger`

#### `referee` — scope `function`
- Instance de `Referee` avec `prisma = prisma_tx` et `log = log` injectés
- Pas d'`event_dispatcher` injecté par défaut (à injecter dans les tests qui en ont besoin)

## Pattern des tests

```python
@pytest.mark.asyncio
async def test_example(referee: Referee, prisma_tx: Prisma):
    # Arrange : créer les données de test
    battle = await prisma_tx.battles.create(data={
        "contender_1_address": "addr1",
        "contender_2_address": "addr2",
        "contender_1_name": "Alice",
        "contender_2_name": "Bob",
        "contenders_pv": 10,
        "rounds": 5,
        "start_height": 100,
    })

    # Act
    result = await referee.compute_pv(battle)

    # Assert
    assert result == (10, 10)
    # Pas besoin de cleanup : prisma_tx rollback automatiquement
```

## Fichiers de tests

| Fichier | Ce qui est testé |
|---|---|
| `test_compute_pv.py` | Calcul des PV à partir de l'historique des rounds |
| `test_create_round.py` | Création de rounds, contrainte `ON CONFLICT DO NOTHING` |
| `test_finalize_rounds.py` | Logique de finalisation différée des rounds |
| `test_battle_ko.py` | Détection du KO (PV ≤ 0) |
| `test_get_current_round_block_height.py` | Récupération du round courant |
| `test_get_current_round_number.py` | Comptage des rounds créés |
| `test_ignore_shares_after_end.py` | Shares ignorés si bataille terminée |
| `test_ignore_shares_before_start.py` | Shares ignorés si block < start_height |

## Notes

- Tous les tests referee sont **async** (`pytest-asyncio`)
- `pytest.ini` contient la configuration asyncio mode
- Pas de mock DB : tests d'intégration sur vraie DB via testcontainers
