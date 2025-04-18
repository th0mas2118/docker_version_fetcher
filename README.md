# Docker Version Fetcher

Un outil pour surveiller les mises à jour des images Docker et envoyer des notifications via Gotify.

## Fonctionnalités

- Vérifie périodiquement les images Docker locales
- Compare avec les versions disponibles sur Docker Hub
- Envoie des notifications via Gotify lorsque des mises à jour sont disponibles
- Évite les notifications répétitives pour les mêmes mises à jour
- Peut être exécuté comme un conteneur Docker

## Installation

### Prérequis

- Python 3.8+
- Docker
- Serveur Gotify (pour les notifications)

### Installation manuelle

1. Clonez ce dépôt
2. Installez les dépendances : `pip install -r requirements.txt`
3. Configurez Gotify dans `config/gotify.json`
4. Exécutez l'application : `python main.py`

### Installation avec Docker

1. Construisez l'image Docker :
   ```
   docker build -t docker-version-fetcher .
   ```

2. Exécutez le conteneur :
   ```
   docker run -d \
     --name docker-version-fetcher \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v $(pwd)/data:/app/data \
     --env-file .env \
     docker-version-fetcher
   ```
   
   Ou en spécifiant directement les variables d'environnement :
   ```
   docker run -d \
     --name docker-version-fetcher \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v $(pwd)/data:/app/data \
     -e GOTIFY_URL=https://votre-serveur-gotify.com \
     -e GOTIFY_TOKEN=VOTRE_TOKEN_GOTIFY \
     -e GOTIFY_PRIORITY=5 \
     -e GOTIFY_TITLE="Docker Version Fetcher" \
     -e CHECK_INTERVAL=24 \
     -e NOTIFICATION_FREQUENCY=7 \
     docker-version-fetcher
   ```

## Configuration

### Variables d'environnement

Le projet utilise un fichier `.env` pour la configuration. Copiez le fichier `.env.example` vers `.env` et modifiez-le selon vos besoins :

```bash
# Configuration Gotify
GOTIFY_URL=https://votre-serveur-gotify.com
GOTIFY_TOKEN=VOTRE_TOKEN_GOTIFY
GOTIFY_PRIORITY=5
GOTIFY_TITLE=Docker Version Fetcher

# Configuration de l'application
CHECK_INTERVAL=24  # Heures entre les vérifications
NOTIFICATION_FREQUENCY=7  # Jours entre les rappels pour la même mise à jour
```

**Note**: Le fichier `.env` n'est pas versionné pour des raisons de sécurité. Un fichier `.env.example` est fourni comme modèle.

## Exécution périodique

Pour exécuter l'application périodiquement, vous pouvez utiliser cron ou le script `run_periodic.py` inclus.

### Avec cron

Ajoutez la ligne suivante à votre crontab pour exécuter l'application tous les jours à 9h :

```
0 9 * * * cd /chemin/vers/docker_version_fetcher && python main.py
```

### Avec le script périodique

Exécutez le script `run_periodic.py` avec l'intervalle souhaité :

```
python run_periodic.py --interval 24
```

## Licence

Ce projet est sous licence MIT.
