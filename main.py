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
        
        # Récupération des conteneurs en cours d'exécution
        logger.info("Récupération des conteneurs Docker en cours d'exécution...")
        running_containers = scanner.get_running_containers()
        logger.info(f"Trouvé {len(running_containers)} conteneurs en cours d'exécution")
        
        # Récupération des images utilisées par les conteneurs
        logger.info("Récupération des images Docker utilisées par les conteneurs...")
        container_images = []
        for container in running_containers:
            # Ignorer l'image du projet elle-même
            if "docker_version_fetcher" in container['repository']:
                logger.info(f"Image du projet ignorée: {container['repository']}:{container['tag']}")
                continue
                
            # Ignorer les mises à jour pour les tags 'latest'
            if container['tag'] == 'latest':
                logger.info(f"Tag 'latest' ignoré pour les mises à jour: {container['repository']}:{container['tag']}")
                continue
                
            container_images.append({
                'repository': container['repository'],
                'tag': container['tag'],
                'digest': container['image_id'],
                'container_name': container['name']
            })
        
        logger.info(f"Trouvé {len(container_images)} images utilisées par des conteneurs")
        
        # Regrouper les images par repository pour détecter les versions inférieures
        repo_versions = {}
        for image in container_images:
            # Ajouter l'image au dictionnaire groupé par repository
            if image['repository'] not in repo_versions:
                repo_versions[image['repository']] = []
            repo_versions[image['repository']].append(image)
        
        # Pour chaque repository, trouver la version la plus récente disponible sur Docker Hub
        updates_available = []
        for repo, images in repo_versions.items():
            # Vérifier les mises à jour pour chaque image
            logger.info(f"Recherche de la dernière version disponible pour {repo}")
            
            # Obtenir la dernière version disponible pour ce repository
            # Nous utilisons la première image pour obtenir les informations de base
            latest_version_info = hub_client.get_latest_version(repo, "latest")
            
            if not latest_version_info:
                logger.warning(f"Impossible de trouver la dernière version pour {repo}")
                continue
                
            latest_tag = latest_version_info['tag']
            latest_digest = latest_version_info['digest']
            
            logger.info(f"Dernière version disponible pour {repo}: {latest_tag}")
            
            # Mettre à jour l'état du repository avec la dernière version disponible
            # Cela garantit que le repository a toujours la dernière version, même si aucune image locale n'est mise à jour
            state_manager.update_repository_state(state, repo, latest_digest, latest_tag)
            
            # Vérifier chaque image locale par rapport à la version la plus récente
            for image in images:
                # Si la version locale est inférieure à la version la plus récente
                if hub_client._compare_versions(image['tag'], latest_tag) < 0:
                    logger.info(f"Version inférieure détectée: {image['repository']}:{image['tag']} -> {latest_tag}")
                    
                    # Vérifier si nous avons déjà notifié cette mise à jour
                    image_key = f"{image['repository']}:{image['tag']}"
                    should_notify = state_manager.should_notify(state, image_key, latest_digest)
                    
                    if should_notify:
                        updates_available.append({
                            'repository': image['repository'],
                            'current_tag': image['tag'],
                            'latest_tag': latest_tag,
                            'current_digest': image['digest'],
                            'latest_digest': latest_digest,
                            'container_name': image.get('container_name', '')
                        })
                        
                        # Mettre à jour l'état du tag spécifique
                        state_manager.update_tag_state(
                            state, 
                            image['repository'],
                            image['tag'],
                            latest_digest, 
                            latest_tag
                        )
                # Si la version locale est égale à la version la plus récente mais le digest est différent
                elif image['tag'] == latest_tag and image['digest'] != latest_digest:
                    logger.info(f"Même version mais digest différent: {image['repository']}:{image['tag']}")
                    
                    # Vérifier si nous avons déjà notifié cette mise à jour
                    image_key = f"{image['repository']}:{image['tag']}"
                    should_notify = state_manager.should_notify(state, image_key, latest_digest)
                    
                    if should_notify:
                        updates_available.append({
                            'repository': image['repository'],
                            'current_tag': image['tag'],
                            'latest_tag': latest_tag,
                            'current_digest': image['digest'],
                            'latest_digest': latest_digest,
                            'container_name': image.get('container_name', '')
                        })
                        
                        # Mettre à jour l'état du tag spécifique
                        state_manager.update_tag_state(
                            state, 
                            image['repository'],
                            image['tag'],
                            latest_digest, 
                            latest_tag
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
