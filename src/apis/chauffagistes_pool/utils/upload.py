from asyncpg import Pool
from apis.chauffagistes_pool.models.User import User
from apis.chauffagistes_pool.models.Repartition import Repartition
from utils.converter import from_string_to_number
from init import app, log
from typing import List, Tuple



async def archive_stats(user_id: str, user: User, repartition: dict[str, Repartition]):
    """Archive les statistiques des workers dans la base de données."""
    pool: Pool = app["db_pool"]

    # Préparer les données
    records: List[Tuple[str, float, float, float, float, float, float, str]] = []

    for worker in user.get("worker", []):
        # Extraction du nom du worker
        worker_name_parts = worker["workername"].split(".")
        worker_name = (
            worker_name_parts[1] if len(worker_name_parts) > 1 else "worker sans nom"
        )

        # Récupération du pourcentage de répartition
        worker_repartition = repartition.get(worker["workername"], {})
        percentage = float(worker_repartition.get("percentage", 0.0))

        # Construction du tuple
        records.append(
            (
                worker_name,
                from_string_to_number(worker.get("hashrate1m", "0")),
                from_string_to_number(worker.get("hashrate5m", "0")),
                from_string_to_number(worker.get("hashrate1hr", "0")),
                from_string_to_number(worker.get("hashrate1d", "0")),
                from_string_to_number(worker.get("hashrate7d", "0")),
                percentage,
                user_id,
            )
        )

    if not records:
        log.info(f"Aucun worker à archiver pour l'utilisateur {user_id}")
        return

    try:
        # Utilisation correcte du pool
        async with pool.acquire() as connection:
            async with connection.transaction():
                # Utiliser copy_records_to_table avec la connexion acquise
                await connection.copy_records_to_table(
                    "worker_stats_raw",
                    records=records,
                    columns=[
                        "worker_id",
                        "avg_hashrate1m",
                        "avg_hashrate5m",
                        "avg_hashrate1h",
                        "avg_hashrate1d",
                        "avg_hashrate7d",
                        "avg_weight",
                        "user",
                    ],
                    timeout=30,  # Timeout optionnel
                )

        log.info(f"Archivé {len(records)} records pour l'utilisateur {user_id}")

    except Exception as e:
        log.error(f"Erreur lors de l'archivage pour {user_id}: {str(e)}")
        raise


# Version alternative avec gestion d'erreurs améliorée
async def archive_stats_with_retry(
    user_id: str, user: User, repartition: dict[str, Repartition], max_retries: int = 3
):
    """Archive avec mécanisme de retry."""
    pool: Pool = app["db_pool"]

    # Préparer les données (même logique)
    records: List[Tuple[str, float, float, float, float, float, float, str]] = []

    for worker in user.get("worker", []):
        worker_name_parts = worker["workername"].split(".")
        worker_name = (
            worker_name_parts[1] if len(worker_name_parts) > 1 else "worker sans nom"
        )

        records.append(
            (
                worker_name,
                from_string_to_number(worker.get("hashrate1m", "0")),
                from_string_to_number(worker.get("hashrate5m", "0")),
                from_string_to_number(worker.get("hashrate1hr", "0")),
                from_string_to_number(worker.get("hashrate1d", "0")),
                from_string_to_number(worker.get("hashrate7d", "0")),
                float(repartition.get(worker["workername"], {}).get("percentage", 0.0)),
                user_id,
            )
        )

    if not records:
        return

    last_exception = None

    for attempt in range(max_retries):
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.copy_records_to_table(
                        "worker_stats_raw",
                        records=records,
                        columns=[
                            "worker_id",
                            "avg_hashrate1m",
                            "avg_hashrate5m",
                            "avg_hashrate1h",
                            "avg_hashrate1d",
                            "avg_hashrate7d",
                            "avg_weight",
                            "user",
                        ],
                    )
            log.info(f"Archivage réussi (tentative {attempt + 1}) pour {user_id}")
            return

        except Exception as e:
            last_exception = e
            log.warn(
                f"Tentative {attempt + 1}/{max_retries} échouée pour {user_id}: {str(e)}"
            )
            if attempt < max_retries - 1:
                import asyncio

                await asyncio.sleep(2**attempt)  # Backoff exponentiel

    # Si on arrive ici, toutes les tentatives ont échoué
    raise Exception(
        f"Échec de l'archivage après {max_retries} tentatives pour {user_id}"
    ) from last_exception


# Version batch pour plusieurs utilisateurs
async def archive_stats_batch(
    users_data: List[Tuple[str, User, dict[str, Repartition]]],
):
    """Archive les statistiques de plusieurs utilisateurs en une transaction."""
    pool: Pool = app["db_pool"]
    all_records: List[Tuple[str, float, float, float, float, float, float, str]] = []

    for user_id, user, repartition in users_data:
        for worker in user.get("worker", []):
            worker_name_parts = worker["workername"].split(".")
            worker_name = (
                worker_name_parts[1]
                if len(worker_name_parts) > 1
                else "worker sans nom"
            )

            all_records.append(
                (
                    worker_name,
                    from_string_to_number(worker.get("hashrate1m", "0")),
                    from_string_to_number(worker.get("hashrate5m", "0")),
                    from_string_to_number(worker.get("hashrate1hr", "0")),
                    from_string_to_number(worker.get("hashrate1d", "0")),
                    from_string_to_number(worker.get("hashrate7d", "0")),
                    float(
                        repartition.get(worker["workername"], {}).get("percentage", 0.0)
                    ),
                    user_id,
                )
            )

    if not all_records:
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.copy_records_to_table(
                "worker_stats_raw",
                records=all_records,
                columns=[
                    "worker_id",
                    "avg_hashrate1m",
                    "avg_hashrate5m",
                    "avg_hashrate1h",
                    "avg_hashrate1d",
                    "avg_hashrate7d",
                    "avg_weight",
                    "user",
                ],
            )

    log.info(
        f"Archivé {len(all_records)} records pour {len(users_data)} utilisateurs"
    )


# Version avec insertion batch alternative (INSERT multiple)
async def archive_stats_batch_insert(
    user_id: str, user: User, repartition: dict[str, Repartition]
):
    """Alternative utilisant INSERT multiple au lieu de copy_records_to_table."""
    pool: Pool = app["db_pool"]

    if not user.get("worker"):
        return

    # Construire la requête INSERT batch
    values = []
    params = []
    param_counter = 1

    for worker in user["worker"]:
        worker_name_parts = worker["workername"].split(".")
        worker_name = (
            worker_name_parts[1] if len(worker_name_parts) > 1 else "worker sans nom"
        )

        values.append(
            f"(${param_counter}, ${param_counter+1}, ${param_counter+2}, "
            f"${param_counter+3}, ${param_counter+4}, ${param_counter+5}, "
            f"${param_counter+6}, ${param_counter+7})"
        )

        params.extend(
            [
                worker_name,
                from_string_to_number(worker.get("hashrate1m", "0")),
                from_string_to_number(worker.get("hashrate5m", "0")),
                from_string_to_number(worker.get("hashrate1hr", "0")),
                from_string_to_number(worker.get("hashrate1d", "0")),
                from_string_to_number(worker.get("hashrate7d", "0")),
                float(repartition.get(worker["workername"], {}).get("percentage", 0.0)),
                user_id,
            ]
        )

        param_counter += 8

    query = f"""
        INSERT INTO worker_stats_raw 
        (worker_id, avg_hashrate1m, avg_hashrate5m, avg_hashrate1h, 
         avg_hashrate1d, avg_hashrate7d, avg_weight, "user")
        VALUES {', '.join(values)}
    """

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(query, *params)
