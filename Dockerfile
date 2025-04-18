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

# Variables d'environnement par défaut
ENV GOTIFY_URL=https://gotify.example.com \
    GOTIFY_TOKEN=YOUR_GOTIFY_TOKEN \
    GOTIFY_PRIORITY=5 \
    GOTIFY_TITLE="Docker Version Fetcher" \
    CHECK_INTERVAL=24 \
    NOTIFICATION_FREQUENCY=7

# Volume pour le socket Docker et les données persistantes
VOLUME ["/var/run/docker.sock", "/app/data"]

# Exécuter l'application
CMD ["python", "main.py"]
