#!/usr/bin/env python3
"""
Docker Version Fetcher
Un outil pour surveiller les mises à jour des images Docker et envoyer des notifications via Gotify.
"""

import logging
import time
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('docker_version_fetcher')

# Import des modules personnalisés
from docker_scanner import DockerLocalScanner
from docker_hub_client import DockerHubClient
from notification_manager import NotificationManager
from state_manager import StateManager

def main():
    """Point d'entrée principal du programme."""
    logger.info("Démarrage de Docker Version Fetcher")
    
    # Initialisation des composants
    try:
        scanner = DockerLocalScanner()
        hub_client = DockerHubClient()
        state_manager = StateManager("data/state.json")
        notification_manager = NotificationManager()
        
        # Chargement de l'état précédent
        state = state_manager.load_state()
        
        # Récupération des images locales
        logger.info("Récupération des images Docker locales...")
        local_images = scanner.get_local_images()
        logger.info(f"Trouvé {len(local_images)} images locales")
        
        # Pour chaque image locale, vérifier les mises à jour
        updates_available = []
        for image in local_images:
            logger.info(f"Vérification des mises à jour pour {image['repository']}:{image['tag']}")
            latest_version = hub_client.get_latest_version(image['repository'], image['tag'])
            
            if latest_version and latest_version['digest'] != image['digest']:
                logger.info(f"Mise à jour disponible pour {image['repository']}:{image['tag']} -> {latest_version['tag']}")
                
                # Vérifier si nous avons déjà notifié cette mise à jour
                image_key = f"{image['repository']}:{image['tag']}"
                should_notify = state_manager.should_notify(state, image_key, latest_version['digest'])
                
                if should_notify:
                    updates_available.append({
                        'repository': image['repository'],
                        'current_tag': image['tag'],
                        'latest_tag': latest_version['tag'],
                        'current_digest': image['digest'],
                        'latest_digest': latest_version['digest']
                    })
                    
                    # Mettre à jour l'état
                    state_manager.update_image_state(
                        state, 
                        image_key, 
                        latest_version['digest'], 
                        latest_version['tag']
                    )
        
        # Envoyer les notifications
        if updates_available:
            logger.info(f"Envoi de notifications pour {len(updates_available)} mises à jour")
            notification_manager.send_updates_notification(updates_available)
        else:
            logger.info("Aucune nouvelle mise à jour à notifier")
        
        # Sauvegarder l'état
        state_manager.save_state(state)
        
        logger.info("Exécution terminée avec succès")
        
    except Exception as e:
        logger.error(f"Une erreur est survenue: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
