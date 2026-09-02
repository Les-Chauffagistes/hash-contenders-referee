# Base de données (Prisma + PostgreSQL)

→ [README](./README.md) | [Architecture](./architecture.md) | [Referee](./referee.md)

Fichier de schéma : `prisma/schema.prisma`  
Client généré : `prisma-client-py`

## Modèles

### `battles`

Représente une compétition entre deux mineurs.

| Colonne | Type | Description |
|---|---|---|
| `id` | `BigInt` PK autoincrement | Identifiant unique |
| `start_height` | `Int` | Block height à partir duquel les shares sont comptés |
| `rounds` | `Int` | Nombre max de rounds (= max de blocks) |
| `contenders_pv` | `Int` | PV de départ de chaque contender |
| `contender_1_address` | `String` | Adresse pool du contender 1 |
| `contender_2_address` | `String` | Adresse pool du contender 2 |
| `contender_1_name` | `String` | Nom affiché du contender 1 |
| `contender_2_name` | `String` | Nom affiché du contender 2 |
| `contender_1_worker` | `String?` | Mineur ciblé chez contender 1 (`worker` du pool). `NULL` = toute la pool compte (mode "Pool vs Pool") |
| `contender_2_worker` | `String?` | Mineur ciblé chez contender 2. `NULL` = toute la pool compte |
| `is_finished` | `Boolean` | `true` quand la bataille est terminée |
| `are_addresses_privates` | `Boolean` | Si `true`, les adresses ne sont pas exposées dans l'API |

### `rounds`

Représente un block miné pendant la bataille. Clé primaire composite `(battle_id, block_height)`.

| Colonne | Type | Description |
|---|---|---|
| `battle_id` | `BigInt` FK | Référence vers `battles.id` |
| `block_height` | `Int` | Hauteur du block (décodé du champ `round` hexadécimal du share) |
| `contender_1_best_diff` | `Int` | Meilleure difficulté soumise par contender 1 sur ce block |
| `contender_2_best_diff` | `Int` | Meilleure difficulté soumise par contender 2 sur ce block |
| `winner` | `SmallInt?` | `1` ou `2` (ou `NULL` si égalité) — rempli à la finalisation |
| `damage` | `Int?` | Non utilisé actuellement |
| `finalized_at` | `DateTime?` | `NULL` = round encore ouvert ; sinon timestamp de fermeture |

## Requêtes SQL importantes

### Création d'un round (idempotente)
```sql
INSERT INTO rounds (battle_id, block_height)
VALUES ($1, $2)
ON CONFLICT DO NOTHING
RETURNING battle_id
```
Retourne `1` si créé, `0` si déjà existant. Utilisé dans `Referee._try_create_round()`.

### Finalisation des rounds
Un round `N` est finalisé uniquement quand **les deux contenders ont soumis au moins un share sur un block > N** — évite de clore un round prématurément si un pool adverse est lent.

```sql
UPDATE rounds
SET finalized_at = NOW(),
    winner = CASE
        WHEN contender_1_best_diff > contender_2_best_diff THEN 1
        WHEN contender_2_best_diff > contender_1_best_diff THEN 2
        ELSE NULL
    END
WHERE battle_id = $1
AND block_height < $2          -- rounds antérieurs au block courant
AND finalized_at IS NULL
AND EXISTS (SELECT 1 FROM rounds r1 WHERE r1.battle_id = rounds.battle_id
            AND r1.block_height > rounds.block_height AND r1.contender_1_best_diff > 0)
AND EXISTS (SELECT 1 FROM rounds r2 WHERE r2.battle_id = rounds.battle_id
            AND r2.block_height > rounds.block_height AND r2.contender_2_best_diff > 0)
RETURNING block_height, winner, contender_1_best_diff, contender_2_best_diff
```

### Calcul des PV
```sql
-- Hits reçus par contender 1 (rounds gagnés par contender 2)
SELECT * FROM rounds
WHERE battle_id = $1
AND contender_1_best_diff < contender_2_best_diff
AND finalized_at IS NOT NULL AND winner IS NOT NULL
```
`PV_contender_1 = contenders_pv - len(rounds_gagnés_par_contender_2)`

### Mise à jour du meilleur share (atomique, ne régresse pas)
```sql
UPDATE rounds
SET contender_1_best_diff = $2
WHERE battle_id = $1 AND block_height = $3
AND contender_1_best_diff < $2   -- seulement si le nouveau diff est meilleur
RETURNING contender_1_best_diff
```

## Commandes Prisma

```bash
prisma generate      # régénère le client Python après changement de schéma
prisma db push       # applique le schéma à la DB (dev)
prisma migrate deploy  # applique les migrations (prod/tests)
```
