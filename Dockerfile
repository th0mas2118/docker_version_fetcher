FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/data

# Variables d'environnement par défaut (non sensibles)
ENV GOTIFY_PRIORITY=5 \
    GOTIFY_TITLE="Docker Version Fetcher" \
    CHECK_INTERVAL=24 \
    NOTIFICATION_FREQUENCY=7

# Note: Les variables sensibles comme GOTIFY_URL et GOTIFY_TOKEN doivent être fournies
# via le fichier .env ou des variables d'environnement lors de l'exécution

# Volume pour le socket Docker et les données persistantes
VOLUME ["/var/run/docker.sock", "/app/data"]

# Exécuter l'application
CMD ["python", "main.py"]
