#!/usr/bin/env python3
"""
Script de correction pour améliorer la vérification des images Docker.
À placer dans le répertoire du projet et à monter dans le conteneur.
"""

import os
import json
import re
import logging
from typing import List, Dict, Any, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('docker_version_fetcher.patch')

# Nom du projet à ignorer dans les vérifications
PROJECT_IMAGE = "docker_version_fetcher"

def should_ignore_image(image_name: str) -> bool:
    """Détermine si une image doit être ignorée dans les vérifications."""
    # Ignorer l'image du projet elle-même
    if PROJECT_IMAGE in image_name:
        logger.info(f"Image du projet ignorée: {image_name}")
        return True
    
    return False

def filter_windows_versions(versions: List[str]) -> List[str]:
    """Filtre les versions Windows des résultats."""
    windows_keywords = ['windows', 'nanoserver', 'windowsservercore', 'ltsc']
    
    filtered_versions = []
    for version in versions:
        is_windows = any(keyword in version.lower() for keyword in windows_keywords)
        if not is_windows:
            filtered_versions.append(version)
    
    if len(filtered_versions) < len(versions):
        logger.info(f"Filtré {len(versions) - len(filtered_versions)} versions Windows")
    
    return filtered_versions

def should_notify_for_latest(current_tag: str, new_tag: str) -> bool:
    """Détermine si une notification doit être envoyée pour les tags 'latest'."""
    if current_tag == 'latest' and new_tag == 'latest':
        logger.info("Pas de notification pour latest -> latest")
        return False
    return True

def patch_docker_hub_client():
    """
    Patch pour le client Docker Hub pour gérer correctement les images GHCR.
    Cette fonction doit être appelée avant d'utiliser le client.
    """
    try:
        # Importer le module original
        from docker_version_fetcher.docker_hub_client import DockerHubClient
        
        # Sauvegarder la méthode originale
        original_get_latest_version = DockerHubClient.get_latest_version
        
        def patched_get_latest_version(self, repository, tag):
            """Version patchée de get_latest_version qui gère GHCR et filtre les versions Windows."""
            # Gérer les images GHCR
            if repository.startswith('ghcr.io/'):
                logger.info(f"Image GHCR détectée: {repository}")
                # Pour l'instant, retourne None pour les images GHCR
                # Dans une version future, implémenter l'API GitHub
                return None
            
            # Appeler la méthode originale pour les autres images
            result = original_get_latest_version(self, repository, tag)
            
            # Si un résultat est trouvé et ce n'est pas None
            if result and isinstance(result, str):
                # Filtrer les versions Windows si on est sur Linux
                if os.name != 'nt':  # Si on n'est pas sur Windows
                    if any(keyword in result.lower() for keyword in ['windows', 'nanoserver', 'windowsservercore', 'ltsc']):
                        logger.info(f"Version Windows ignorée: {result}")
                        # Essayer de trouver une version non-Windows
                        all_versions = self.get_all_versions(repository)
                        filtered_versions = filter_windows_versions(all_versions)
                        if filtered_versions:
                            result = filtered_versions[0]
                            logger.info(f"Utilisation de la version alternative: {result}")
                        else:
                            logger.info("Aucune version alternative trouvée")
                            return None
            
            return result
        
        # Remplacer la méthode originale par la version patchée
        DockerHubClient.get_latest_version = patched_get_latest_version
        logger.info("DockerHubClient patché avec succès")
        
    except ImportError as e:
        logger.error(f"Impossible de patcher DockerHubClient: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur lors du patch de DockerHubClient: {str(e)}")

def patch_main_module():
    """
    Patch pour le module principal pour ignorer certaines images.
    Cette fonction doit être appelée avant d'exécuter le module principal.
    """
    try:
        import docker_version_fetcher.main
        
        # Sauvegarder la fonction originale
        original_check_for_updates = docker_version_fetcher.main.check_for_updates
        
        def patched_check_for_updates(image_name, current_tag):
            """Version patchée de check_for_updates qui ignore certaines images."""
            # Ignorer l'image du projet
            if should_ignore_image(image_name):
                return None
            
            # Ignorer les notifications pour latest -> latest
            result = original_check_for_updates(image_name, current_tag)
            if result and current_tag == 'latest' and result == 'latest':
                logger.info(f"Ignoré mise à jour inutile pour {image_name}:{current_tag} -> {result}")
                return None
            
            return result
        
        # Remplacer la fonction originale par la version patchée
        docker_version_fetcher.main.check_for_updates = patched_check_for_updates
        logger.info("Module principal patché avec succès")
        
    except ImportError as e:
        logger.error(f"Impossible de patcher le module principal: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur lors du patch du module principal: {str(e)}")

def apply_patches():
    """Applique tous les patches."""
    logger.info("Application des patches...")
    patch_docker_hub_client()
    patch_main_module()
    logger.info("Patches appliqués avec succès")

if __name__ == "__main__":
    apply_patches()
