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

# Créer un utilisateur non-root
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copier uniquement les fichiers nécessaires de l'étape de construction
COPY --from=builder /app/dist /app
COPY --from=builder /app/package.json /app/

# Installer uniquement les dépendances de production
RUN bun install --production

# Créer le répertoire de données et définir les permissions
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

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
