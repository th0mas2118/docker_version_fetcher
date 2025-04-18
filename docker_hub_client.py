#!/usr/bin/env python3
"""
Module pour interagir avec Docker Hub et récupérer les informations sur les images.
"""

import requests
import logging
import json
import time
import re
from urllib.parse import quote_plus

# Utiliser packaging.version pour une meilleure comparaison des versions
try:
    from packaging import version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False
    logging.warning("Le module 'packaging' n'est pas installé. La comparaison des versions sera moins précise.")

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
            
            # Filtrer les versions Windows
            windows_keywords = ['windows', 'nanoserver', 'windowsltsc', 'windowsservercore']
            filtered_versions = []
            for v in data.get('results', []):
                version_tag = v.get('name', '')
                is_windows = any(keyword in version_tag.lower() for keyword in windows_keywords)
                if not is_windows:
                    filtered_versions.append(v)
            
            # Si toutes les versions sont des versions Windows, utiliser les versions non filtrées
            if not filtered_versions and data.get('results', []):
                logger.warning(f"Toutes les versions de {repository} sont des versions Windows")
                filtered_versions = data.get('results', [])
            
            # Trouver la version la plus récente
            latest_tag = tag
            latest_version = None
            
            for version_info in filtered_versions:
                version_tag = version_info.get('name')
                
                # Si le tag est exactement le même, utiliser celui-ci
                if version_tag == tag:
                    latest_tag = version_tag
                    latest_version = version_info
                    break
                
                # Sinon, comparer les versions
                if self._compare_versions(version_tag, latest_tag) > 0:
                    latest_tag = version_tag
                    latest_version = version_info
            
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
    
    def is_valid_version(self, version_str):
        """
        Vérifie si une chaîne est une version valide.
        
        Args:
            version_str (str): Chaîne de version à vérifier
            
        Returns:
            bool: True si la version est valide, False sinon
        """
        # Ignorer les versions qui ne sont pas des versions sémantiques ou numériques
        if version_str in ['latest', 'stable', 'master', 'main', 'sts', 'beta']:
            return False
            
        # Vérifier si la version contient au moins un chiffre
        if not any(c.isdigit() for c in version_str):
            return False
            
        # Vérifier les formats de version courants
        version_patterns = [
            r'^\d+\.\d+\.\d+$',  # 1.2.3
            r'^\d+\.\d+$',       # 1.2
            r'^v\d+\.\d+\.\d+$', # v1.2.3
            r'^\d+\.\d+\.\d+-[a-zA-Z0-9]+$'  # 1.2.3-alpha1
        ]
        
        for pattern in version_patterns:
            if re.match(pattern, version_str):
                return True
                
        # Si aucun pattern ne correspond mais qu'il y a des chiffres, c'est peut-être une version valide
        return True
    
    def _compare_versions(self, version1, version2):
        """
        Compare deux versions sémantiques.
        
        Args:
            version1 (str): Première version
            version2 (str): Deuxième version
            
        Returns:
            int: 1 si version1 > version2, -1 si version1 < version2, 0 si égales
        """
        # Si les versions sont identiques, elles sont égales
        if version1 == version2:
            return 0
            
        # Vérifier si les versions sont valides
        if not self.is_valid_version(version1) or not self.is_valid_version(version2):
            logger.warning(f"Comparaison de versions non valides: {version1} et {version2}")
            return 0  # Considérer comme égales si l'une des versions n'est pas valide
        
        try:
            # Utiliser packaging.version si disponible (meilleure gestion des versions sémantiques)
            if HAS_PACKAGING:
                try:
                    # Extraire la partie principale de la version (avant les tirets)
                    # Par exemple, pour "2.29.0-alpine", on prend "2.29.0"
                    v1_main = version1.split('-')[0] if '-' in version1 else version1
                    v2_main = version2.split('-')[0] if '-' in version2 else version2
                    
                    # Supprimer le 'v' au début si présent
                    v1_main = v1_main[1:] if v1_main.startswith('v') else v1_main
                    v2_main = v2_main[1:] if v2_main.startswith('v') else v2_main
                    
                    # Comparer avec packaging.version
                    parsed_v1 = version.parse(v1_main)
                    parsed_v2 = version.parse(v2_main)
                    
                    if parsed_v1 > parsed_v2:
                        return 1
                    elif parsed_v1 < parsed_v2:
                        return -1
                    
                    # Si les versions principales sont égales, comparer les suffixes
                    if '-' in version1 and '-' not in version2:
                        return -1  # La version sans suffixe est considérée comme plus récente
                    elif '-' not in version1 and '-' in version2:
                        return 1   # La version sans suffixe est considérée comme plus récente
                    
                    return 0
                except Exception as e:
                    logger.debug(f"Erreur lors de la comparaison avec packaging.version: {str(e)}. Utilisation de la méthode de secours.")
                    # En cas d'erreur, on utilise la méthode de secours ci-dessous
            
            # Méthode de secours si packaging n'est pas disponible
            # Gérer les versions avec des parties non numériques
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
            return 0  # En cas d'erreur, considérer comme égales
