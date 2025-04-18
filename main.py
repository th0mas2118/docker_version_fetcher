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
        
        # Regrouper les images par repository pour détecter les versions inférieures
        repo_versions = {}
        for image in local_images:
            # Ignorer l'image du projet elle-même
            if "docker_version_fetcher" in image['repository']:
                logger.info(f"Image du projet ignorée: {image['repository']}:{image['tag']}")
                continue
                
            # Ignorer les mises à jour pour les tags 'latest'
            if image['tag'] == 'latest':
                logger.info(f"Tag 'latest' ignoré pour les mises à jour: {image['repository']}:{image['tag']}")
                continue
            
            # Ajouter l'image au dictionnaire groupé par repository
            if image['repository'] not in repo_versions:
                repo_versions[image['repository']] = []
            repo_versions[image['repository']].append(image)
        
        # Pour chaque repository, trouver la version la plus récente disponible
        updates_available = []
        for repo, images in repo_versions.items():
            # Trouver la version la plus récente disponible pour ce repository
            latest_available = None
            for image in images:
                logger.info(f"Vérification des mises à jour pour {image['repository']}:{image['tag']}")
                version_info = hub_client.get_latest_version(image['repository'], image['tag'])
                
                if version_info:
                    if not latest_available or hub_client._compare_versions(version_info['tag'], latest_available['tag']) > 0:
                        latest_available = version_info
            
            if not latest_available:
                continue
                
            # Vérifier chaque image locale par rapport à la version la plus récente
            for image in images:
                # Si la version locale est inférieure à la version la plus récente
                if hub_client._compare_versions(image['tag'], latest_available['tag']) < 0:
                    logger.info(f"Version inférieure détectée: {image['repository']}:{image['tag']} -> {latest_available['tag']}")
                    
                    # Vérifier si nous avons déjà notifié cette mise à jour
                    image_key = f"{image['repository']}:{image['tag']}"
                    should_notify = state_manager.should_notify(state, image_key, latest_available['digest'])
                    
                    if should_notify:
                        updates_available.append({
                            'repository': image['repository'],
                            'current_tag': image['tag'],
                            'latest_tag': latest_available['tag'],
                            'current_digest': image['digest'],
                            'latest_digest': latest_available['digest']
                        })
                        
                        # Mettre à jour l'état
                        state_manager.update_image_state(
                            state, 
                            image_key, 
                            latest_available['digest'], 
                            latest_available['tag']
                        )
                # Si la version locale est égale à la version la plus récente mais le digest est différent
                elif image['tag'] == latest_available['tag'] and image['digest'] != latest_available['digest']:
                    logger.info(f"Même version mais digest différent: {image['repository']}:{image['tag']}")
                    
                    # Vérifier si nous avons déjà notifié cette mise à jour
                    image_key = f"{image['repository']}:{image['tag']}"
                    should_notify = state_manager.should_notify(state, image_key, latest_available['digest'])
                    
                    if should_notify:
                        updates_available.append({
                            'repository': image['repository'],
                            'current_tag': image['tag'],
                            'latest_tag': latest_available['tag'],
                            'current_digest': image['digest'],
                            'latest_digest': latest_available['digest']
                        })
                        
                        # Mettre à jour l'état
                        state_manager.update_image_state(
                            state, 
                            image_key, 
                            latest_available['digest'], 
                            latest_available['tag']
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
