#!/bin/bash
# Script d'entrée pour appliquer les correctifs avant de lancer l'application

set -e

# Vérifier si le répertoire de correctifs existe
if [ -d "/app/patches" ]; then
  echo "Application des correctifs..."
  
  # Appliquer le correctif pour la vérification des images
  if [ -f "/app/patches/fix_image_check.py" ]; then
    echo "Application du correctif fix_image_check.py"
    python /app/patches/fix_image_check.py
  fi
  
  echo "Correctifs appliqués avec succès"
fi

# Exécuter la commande originale
exec "$@"
