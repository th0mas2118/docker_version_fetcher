#!/usr/bin/env python3
"""
Module pour interagir avec Docker Hub et récupérer les informations sur les images.
"""

import requests
import logging
import json
import time
from urllib.parse import quote_plus

logger = logging.getLogger('docker_version_fetcher.docker_hub_client')

class DockerHubClient:
    """Classe pour interagir avec l'API Docker Hub."""
    
    def __init__(self, api_url="https://hub.docker.com/v2"):
        """
        Initialise le client Docker Hub.
        
        Args:
            api_url (str): URL de base de l'API Docker Hub
        """
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DockerVersionFetcher/1.0',
            'Content-Type': 'application/json'
        })
        
        # Taux de requêtes pour éviter les limitations d'API
        self.request_delay = 1  # secondes entre les requêtes
        self.last_request_time = 0
    
    def _rate_limit_request(self):
        """Applique une limitation de taux pour les requêtes API."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def repository_exists(self, repository):
        """
        Vérifie si un repository existe sur Docker Hub.
        
        Args:
            repository (str): Nom du repository (ex: 'nginx')
            
        Returns:
            bool: True si le repository existe, False sinon
        """
        try:
            # Déterminer si c'est une image officielle ou un repository utilisateur
            if '/' not in repository:
                # Image officielle
                repo_path = f"library/{repository}"
            else:
                # Repository utilisateur
                repo_path = repository
            
            # Appliquer la limitation de taux
            self._rate_limit_request()
            
            # Construire l'URL
            url = f"{self.api_url}/repositories/{quote_plus(repo_path)}"
            
            # Faire la requête
            logger.debug(f"Vérification de l'existence du repository: {url}")
            response = self.session.get(url)
            
            # Si le code de statut est 200, le repository existe
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'existence du repository {repository}: {str(e)}")
            return False
    
    def get_latest_version(self, repository, tag):
        """
        Récupère la dernière version disponible pour une image Docker.
        
        Args:
            repository (str): Nom du repository (ex: 'nginx')
            tag (str): Tag de l'image (ex: '1.21')
            
        Returns:
            dict: Informations sur la dernière version disponible
        """
        try:
            # Vérifier si le repository existe
            if not self.repository_exists(repository):
                logger.warning(f"Le repository {repository} n'existe pas sur Docker Hub ou est privé")
                return None
            
            # Déterminer si c'est une image officielle ou un repository utilisateur
            if '/' not in repository:
                # Image officielle
                repo_path = f"library/{repository}"
            else:
                # Repository utilisateur
                repo_path = repository
            
            # Appliquer la limitation de taux
            self._rate_limit_request()
            
            # Construire l'URL
            url = f"{self.api_url}/repositories/{quote_plus(repo_path)}/tags"
            
            # Faire la requête
            logger.debug(f"Requête vers Docker Hub: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Trouver la dernière version correspondant au tag de base
            # Par exemple, si tag='1.21', trouver la dernière version '1.21.x'
            base_tag_prefix = tag.split('.')[0]
            
            latest_version = None
            latest_tag = None
            
            for result in data.get('results', []):
                current_tag = result.get('name')
                
                # Si on cherche exactement 'latest' ou une correspondance exacte
                if tag == 'latest' and current_tag == 'latest':
                    latest_tag = current_tag
                    latest_version = result
                    break
                
                # Si on cherche une version spécifique (ex: '1.21')
                elif current_tag.startswith(base_tag_prefix + '.'):
                    # Prendre la version la plus récente dans la même branche
                    if not latest_tag or self._compare_versions(current_tag, latest_tag) > 0:
                        latest_tag = current_tag
                        latest_version = result
            
            # Si aucune version correspondante n'est trouvée, vérifier la dernière version globale
            if not latest_version and tag != 'latest':
                logger.info(f"Aucune version correspondant à {tag} trouvée, vérification de 'latest'")
                return self.get_latest_version(repository, 'latest')
            
            if latest_version:
                # Extraire le digest
                digest = None
                if 'images' in latest_version and latest_version['images']:
                    for image in latest_version['images']:
                        if image.get('architecture') == 'amd64':  # Architecture la plus courante
                            digest = image.get('digest')
                            break
                    
                    # Si aucun digest amd64 n'est trouvé, prendre le premier disponible
                    if not digest and latest_version['images']:
                        digest = latest_version['images'][0].get('digest')
                
                return {
                    'repository': repository,
                    'tag': latest_tag,
                    'digest': digest,
                    'last_updated': latest_version.get('last_updated')
                }
            
            logger.warning(f"Aucune version trouvée pour {repository}:{tag}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête vers Docker Hub: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la dernière version: {str(e)}")
            return None
    
    def _compare_versions(self, version1, version2):
        """
        Compare deux versions sémantiques.
        
        Args:
            version1 (str): Première version
            version2 (str): Deuxième version
            
        Returns:
            int: 1 si version1 > version2, -1 si version1 < version2, 0 si égales
        """
        try:
            # Gérer les versions avec des parties non numériques
            # D'abord, essayer de comparer les versions sémantiques standard (x.y.z)
            v1_parts = version1.split('.')
            v2_parts = version2.split('.')
            
            # Comparer chaque partie de la version
            for i in range(min(len(v1_parts), len(v2_parts))):
                # Essayer de convertir en entier si possible
                try:
                    # Extraire la partie numérique au début de la chaîne
                    v1_numeric = ''.join([c for c in v1_parts[i] if c.isdigit()])
                    v2_numeric = ''.join([c for c in v2_parts[i] if c.isdigit()])
                    
                    # Si les deux parties sont numériques, comparer en tant qu'entiers
                    if v1_numeric and v2_numeric:
                        v1 = int(v1_numeric)
                        v2 = int(v2_numeric)
                        
                        if v1 > v2:
                            return 1
                        elif v1 < v2:
                            return -1
                    else:
                        # Si l'une des parties n'est pas numérique, comparer lexicographiquement
                        if v1_parts[i] > v2_parts[i]:
                            return 1
                        elif v1_parts[i] < v2_parts[i]:
                            return -1
                except (ValueError, TypeError):
                    # Si la conversion échoue, comparer lexicographiquement
                    if v1_parts[i] > v2_parts[i]:
                        return 1
                    elif v1_parts[i] < v2_parts[i]:
                        return -1
            
            # Si toutes les parties communes sont égales, la version avec plus de parties est considérée comme plus récente
            if len(v1_parts) > len(v2_parts):
                return 1
            elif len(v1_parts) < len(v2_parts):
                return -1
            
            return 0
        except Exception as e:
            logger.warning(f"Erreur lors de la comparaison des versions {version1} et {version2}: {str(e)}")
            # En cas d'erreur, comparer lexicographiquement
            if version1 > version2:
                return 1
            elif version1 < version2:
                return -1
            return 0
