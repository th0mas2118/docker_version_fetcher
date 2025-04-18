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

- [Bun](https://bun.sh/) 1.0+ (pour le développement local)
- Docker (pour l'exécution en conteneur)
- Serveur Gotify (pour les notifications)

### Installation manuelle pour le développement

1. Clonez ce dépôt
2. Installez Bun si ce n'est pas déjà fait :
   ```bash
   curl -fsSL https://bun.sh/install | bash
   ```
3. Installez les dépendances :
   ```bash
   bun install
   ```
4. Créez un fichier `.env` basé sur `.env.example`
5. Exécutez l'application en mode développement :
   ```bash
   bun dev
   ```

### Installation avec Docker

1. Construisez l'image Docker :
   ```bash
   docker build -t docker-version-fetcher .
   ```

2. Exécutez le conteneur :
   ```bash
   docker run -d \
     --name docker-version-fetcher \
     -v /var/run/docker.sock:/var/run/docker.sock:ro \
     -v $(pwd)/data:/app/data \
     --env-file .env \
     docker-version-fetcher
   ```
   
   Ou en spécifiant directement les variables d'environnement :
   ```bash
   docker run -d \
     --name docker-version-fetcher \
     -v /var/run/docker.sock:/var/run/docker.sock:ro \
     -v $(pwd)/data:/app/data \
     -e GOTIFY_URL=https://votre-serveur-gotify.com \
     -e GOTIFY_TOKEN=VOTRE_TOKEN_GOTIFY \
     -e GOTIFY_PRIORITY=5 \
     -e GOTIFY_TITLE="Docker Version Fetcher" \
     -e CHECK_INTERVAL="0 0 */24 * * *" \
     -e NOTIFICATION_FREQUENCY=7 \
     docker-version-fetcher
   ```

### Utilisation avec Docker Compose

Un fichier `docker-compose.yml` est fourni pour faciliter le déploiement :

```bash
# Créez d'abord un fichier .env avec vos variables
docker-compose up -d
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
CHECK_INTERVAL="0 0 */24 * * *"  # Expression cron pour les vérifications (ici toutes les 24h)
NOTIFICATION_FREQUENCY=7  # Jours entre les rappels pour la même mise à jour
```

**Note**: Le fichier `.env` n'est pas versionné pour des raisons de sécurité. Un fichier `.env.example` est fourni comme modèle.

## Développement

### Commandes disponibles

```bash
# Démarrer l'application en mode développement (avec rechargement automatique)
bun dev

# Démarrer l'application
bun start

# Exécuter les tests
bun test

# Analyser le code avec ESLint
bun lint

# Construire l'application pour la production
bun run build
```

### Structure du projet

```
├── src/                # Code source
│   ├── config/         # Configuration
│   ├── services/       # Services (Docker, notifications, etc.)
│   ├── utils/          # Utilitaires
│   └── index.js        # Point d'entrée
├── dist/               # Code compilé (généré par bun build)
├── data/               # Données persistantes
├── .env.example        # Exemple de variables d'environnement
├── Dockerfile          # Configuration Docker
└── docker-compose.yml  # Configuration Docker Compose
```

## Licence

Ce projet est sous licence MIT.
