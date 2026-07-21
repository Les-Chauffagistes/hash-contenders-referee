# Referee — Logique métier

→ [README](./README.md) | [Architecture](./architecture.md) | [Database](./database.md) | [Event Dispatcher](./event-dispatcher.md)

Fichier : `src/rules/Referee.py`

## Responsabilités

- Recevoir les shares du pool et décider quoi en faire
- Créer les rounds au fil des nouveaux block heights
- Finaliser les rounds passés et déterminer le vainqueur de chaque round
- Calculer les PV restants de chaque contender
- Détecter les KO (fin par PV ≤ 0) ou la fin par max rounds
- Déclencher les événements WebSocket via `event_dispatcher`

## Attributs de classe (injectés au démarrage)

```python
Referee.prisma          # Prisma  — client DB
Referee.log             # Logger
Referee.event_dispatcher  # WebsocketBroadcaster
```

Voir `main.py` pour l'injection et [Architecture](./architecture.md) pour le pattern.

## Méthode principale : `on_share(battle, payload)`

Point d'entrée pour chaque share reçu du pool.

```
on_share(battle, payload)
│
├─ Ignorer si battle.is_finished
├─ Ignorer si block_height < battle.start_height
│
├─ _finalize_and_broadcast(battle, block_height)
│    ├─ finalize_rounds()           → ferme les rounds antérieurs en DB
│    ├─ compute_pv()                → recalcule les PV
│    ├─ event_dispatcher.hit_result()  → broadcast HIT_RESULT
│    └─ _check_ko()                 → si PV ≤ 0 : termine la battle
│         └─ Si KO → return True (stoppe le traitement)
│
├─ Re-vérifier battle.is_finished (une autre task peut avoir déclenché un KO)
│
├─ _ensure_round_exists(battle, block_height, payload)
│    ├─ Si round existe déjà → OK, continue
│    ├─ Sinon : vérifier si max rounds atteint
│    │    └─ Si max atteint → return False
│    └─ _try_create_round() + event_dispatcher.new_round()
│         └─ Si return False :
│              ├─ _force_finalize_last_round()
│              ├─ _check_ko() ou _finish_by_max_rounds()
│              └─ close client websockets
│
└─ _update_best_share(battle, block_height, payload)
     ├─ Identifie le contender (par adresse)
     ├─ UPDATE atomique (ne régresse pas)
     └─ event_dispatcher.new_best_share()
```

## Méthodes détaillées

### `finalize_rounds(battle_id, next_block_height)`
Ferme tous les rounds `< next_block_height` qui ne sont pas encore finalisés, à condition que les **deux** contenders aient soumis au moins un share sur un block supérieur.  
→ Retourne la liste des rounds fermés (avec `winner`, `block_height`, diffs).

### `_force_finalize_last_round(battle_id, block_height)`
Variante utilisée quand le **max de rounds est atteint** : aucun round supérieur ne sera jamais créé, donc on finalise directement le dernier round si les deux diffs sont > 0.

### `compute_pv(battle) → (pv1, pv2)`
Compte les rounds finalisés gagnés par chaque contender :
```
pv1 = battle.contenders_pv - nombre_de_rounds_gagnés_par_contender_2
pv2 = battle.contenders_pv - nombre_de_rounds_gagnés_par_contender_1
```

### `_check_ko(battle) → bool`
Si `pv1 ≤ 0` ou `pv2 ≤ 0` :
1. Met `is_finished = True` en DB et sur l'objet local
2. Supprime les rounds non finalisés (race condition entre 2 tâches WS)
3. Appelle `event_dispatcher.battle_end()`
4. Retourne `True`

### `_finish_by_max_rounds(battle)`
Quand le nombre max de rounds est atteint sans KO.  
Vainqueur = contender avec le plus de PV. Égalité → `winner = None`.

### `_update_best_share(battle, block_height, payload)`
Identifie le contender par `payload.address` comparé à `battle.contender_1_address` / `battle.contender_2_address`.  
Effectue un `UPDATE ... WHERE contender_X_best_diff < $new_diff` (atomique, sans régression).  
Si la ligne est mise à jour → `event_dispatcher.new_best_share()`.

### `get_current_round(battle_id) → rounds | None`
Retourne le round avec le `block_height` le plus élevé (round en cours).

### `get_current_round_number(battle_id) → int`
Compte le nombre total de rounds créés pour cette bataille.

## Règles métier clés

| Règle | Détail |
|---|---|
| Un round = un block height | Chaque nouveau `block_height` dans les shares crée un round |
| Finalisation différée | Un round N n'est clos que quand les deux contenders ont soumis sur un block > N |
| PV = points de vie | Chaque round perdu = -1 PV. Départ : `contenders_pv` |
| KO | PV ≤ 0 → fin immédiate, l'autre contender gagne |
| Max rounds | Si `rounds` atteint sans KO → vainqueur aux PV restants |
| Idempotence | `INSERT ON CONFLICT DO NOTHING` + `UPDATE WHERE diff < new_diff` = safe en concurrence |
