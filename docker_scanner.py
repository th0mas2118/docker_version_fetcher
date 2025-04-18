#!/usr/bin/env python3
"""
Module pour scanner les images Docker locales.
"""

import docker
import logging

logger = logging.getLogger('docker_version_fetcher.docker_scanner')

class DockerLocalScanner:
    """Classe pour scanner les images Docker locales."""
    
    def __init__(self):
        """Initialise le client Docker."""
        try:
            self.client = docker.from_env()
            logger.info("Client Docker initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Docker: {str(e)}")
            raise
    
    def get_local_images(self):
        """
        Récupère la liste des images Docker locales.
        
        Returns:
            list: Liste des images avec leurs informations (repository, tag, digest)
        """
        try:
            # Récupérer toutes les images
            images = self.client.images.list()
            logger.debug(f"Récupéré {len(images)} images Docker")
            
            # Extraire les informations pertinentes
            image_info_list = []
            for image in images:
                # Ignorer les images sans tag
                if not image.tags:
                    continue
                
                for tag in image.tags:
                    # Séparer le repository et le tag
                    if ':' in tag:
                        repo, img_tag = tag.split(':', 1)
                    else:
                        repo = tag
                        img_tag = 'latest'
                    
                    # Extraire le digest
                    digest = image.id
                    
                    image_info_list.append({
                        'repository': repo,
                        'tag': img_tag,
                        'digest': digest,
                        'created': image.attrs.get('Created', ''),
                        'size': image.attrs.get('Size', 0)
                    })
            
            return image_info_list
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des images Docker: {str(e)}")
            raise
    
    def get_running_containers(self):
        """
        Récupère la liste des conteneurs en cours d'exécution.
        
        Returns:
            list: Liste des conteneurs avec leurs informations
        """
        try:
            containers = self.client.containers.list()
            
            container_info_list = []
            for container in containers:
                image_tag = container.image.tags[0] if container.image.tags else "unknown"
                
                if ':' in image_tag:
                    repo, tag = image_tag.split(':', 1)
                else:
                    repo = image_tag
                    tag = 'latest'
                
                container_info_list.append({
                    'id': container.id,
                    'name': container.name,
                    'repository': repo,
                    'tag': tag,
                    'status': container.status,
                    'image_id': container.image.id
                })
            
            return container_info_list
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des conteneurs: {str(e)}")
            raise
