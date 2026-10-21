# Registre pip privé

Ce projet dépend d'un registre pip privé auto-hébergé (probablement devpi) en plus de PyPI,
pour des paquets internes comme `chauff-cmn`.

## Configuration

Le registre est configuré via variables d'environnement (pas de `pip.conf` dans le repo) :

```bash
PIP_EXTRA_INDEX_URL=http://deploy:<token>@10.10.0.3:8081/simple/
PIP_TRUSTED_HOST=10.10.0.3
```

- Host : `10.10.0.3:8081`, joignable en VPN (~70ms de latence depuis un poste local).
- `PIP_EXTRA_INDEX_URL` embarque des identifiants (`deploy:<token>`) — ne jamais logger ou
  coller cette valeur dans un ticket/PR/chat public.

Vérifier que les variables sont bien prises en compte :

```bash
pip config list
```

Vérifier la connectivité réseau au registre :

```bash
nc -zv 10.10.0.3 8081
```

## Installer les dépendances

`pip install -r requirements.txt` fonctionne sans flag particulier : les variables
d'environnement `PIP_EXTRA_INDEX_URL` / `PIP_TRUSTED_HOST` suffisent pour que pip aille
chercher les paquets internes sur le registre privé en plus de PyPI.

## Régénérer requirements.txt après modification de requirements.in

L'en-tête de `requirements.txt` documente la commande utilisée pour le générer :

```bash
pip-compile --allow-unsafe --generate-hashes --no-emit-index-url \
  --output-file=requirements.txt --trusted-host=10.10.0.3 requirements.in
```

Cette commande est lente (plusieurs minutes) : `--generate-hashes` force pip à faire un
aller-retour réseau vers le registre pour chaque candidat de version de chaque paquet, et le
résolveur peut backtracker sur des paquets à contraintes ouvertes (`aiohttp`,
`testcontainers[postgres]`, `chauff-cmn>=0.1.0`, etc). Une exécution qui tourne plusieurs
minutes en consommant du CPU n'est pas bloquée, c'est normal — vérifier avec `ps aux | grep
pip-compile` que le process avance avant de la tuer.

Si besoin de ne mettre à jour qu'un seul paquet plutôt que de tout recompiler :

```bash
pip-compile --allow-unsafe --generate-hashes --no-emit-index-url \
  --output-file=requirements.txt --trusted-host=10.10.0.3 \
  --upgrade-package <nom-du-paquet> requirements.in
```

## Point ouvert

On ne sait pas comment la CI fait fonctionner la commande avec `--no-index` (elle devrait
échouer de la même façon, sauf si un `--find-links` local ou un cache de paquets est utilisé
en amont). À vérifier dans la config CI si le besoin se présente.
