FROM oven/bun:1 AS builder

WORKDIR /app

# Copier les fichiers de dépendances
COPY package*.json ./

# Installer les dépendances
RUN bun install

# Copier le reste des fichiers
COPY . .

# Construire l'application
RUN bun run build

# Étape de production avec une image minimale
FROM oven/bun:1-slim

WORKDIR /app

# Créer un utilisateur non-root avec accès au socket Docker
# Le groupe 996 correspond au groupe docker sur l'hôte
RUN groupadd -r -g 996 dockergroup && \
    useradd -r -g dockergroup -G dockergroup appuser

# Copier uniquement les fichiers nécessaires de l'étape de construction
COPY --from=builder /app/dist /app
COPY --from=builder /app/package.json /app/

# Copier les fichiers de configuration
COPY --from=builder /app/config /app/config

# Installer uniquement les dépendances de production
RUN bun install --production

# Créer le répertoire de données et définir les permissions
RUN mkdir -p /app/data && chown -R appuser:dockergroup /app

# Utiliser l'utilisateur non-root
USER appuser

# Définir les variables d'environnement par défaut
ENV NODE_ENV=production
ENV CHECK_INTERVAL="0 0 */24 * * *"
ENV GOTIFY_PRIORITY=5
ENV GOTIFY_TITLE="Docker Version Fetcher"

# Exposer le volume pour les données persistantes
VOLUME /app/data

# Commande d'exécution
CMD ["bun", "index.js"]
