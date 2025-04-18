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
        Récupère la dernière version d'une image sur Docker Hub.
        
        Args:
            repository (str): Nom du repository (ex: "library/ubuntu")
            tag (str): Tag de l'image (ex: "20.04")
            
        Returns:
            dict: Informations sur la dernière version ou None si non trouvée
        """
        # Vérifier si le repository existe
        if not self.repository_exists(repository):
            logger.warning(f"Le repository {repository} n'existe pas sur Docker Hub ou est privé")
            return None
        
        try:
            # Construire l'URL pour l'API Docker Hub
            if '/' not in repository:
                # Pour les images officielles, ajouter le préfixe "library/"
                api_repository = f"library/{repository}"
            else:
                api_repository = repository
            
            # Récupérer les tags disponibles
            url = f"https://hub.docker.com/v2/repositories/{api_repository}/tags"
            
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if 'results' not in data or not data['results']:
                logger.warning(f"Aucun tag trouvé pour {repository}")
                return None
            
            # Filtrer les tags pour exclure les versions Windows
            filtered_tags = []
            for tag_info in data['results']:
                tag_name = tag_info.get('name', '')
                if not self._is_windows_version(tag_name) and self.is_valid_version(tag_name):
                    filtered_tags.append(tag_info)
            
            if not filtered_tags:
                logger.warning(f"Aucun tag valide non-Windows trouvé pour {repository}")
                # Essayer sans le filtre de validation si aucun tag valide n'est trouvé
                filtered_tags = [tag_info for tag_info in data['results'] 
                                 if not self._is_windows_version(tag_info.get('name', ''))]
                if not filtered_tags:
                    return None
            
            # Extraire les versions numériques et les trier
            version_tags = []
            for tag_info in filtered_tags:
                tag_name = tag_info.get('name', '')
                if tag_name != 'latest':
                    version_tags.append((tag_name, tag_info))
            
            # Trier les versions par ordre décroissant
            sorted_versions = sorted(version_tags, 
                                     key=lambda x: self._parse_version_for_sorting(x[0]), 
                                     reverse=True)
            
            # Si aucune version numérique n'est trouvée, utiliser le premier tag disponible
            if not sorted_versions:
                logger.warning(f"Aucune version numérique trouvée pour {repository}, utilisation du premier tag disponible")
                latest_tag = filtered_tags[0]
            else:
                # Prendre la version la plus récente
                latest_tag = sorted_versions[0][1]
            
            # Extraire les informations nécessaires
            tag_name = latest_tag.get('name', tag)
            
            # Récupérer le digest
            digest = None
            if 'images' in latest_tag and latest_tag['images']:
                for image in latest_tag['images']:
                    if image.get('architecture') == 'amd64' and image.get('os') == 'linux':
                        digest = image.get('digest')
                        break
                
                if not digest and latest_tag['images']:
                    # Si aucune image amd64/linux n'est trouvée, prendre la première
                    digest = latest_tag['images'][0].get('digest')
            
            if not digest:
                logger.warning(f"Impossible de récupérer le digest pour {repository}:{tag_name}")
                digest = f"sha256:{tag_name}"  # Fallback pour avoir quelque chose
            
            logger.info(f"Version la plus récente trouvée pour {repository}: {tag_name}")
            
            return {
                'tag': tag_name,
                'digest': digest
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des informations depuis Docker Hub: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la dernière version: {str(e)}")
            return None
            
    def _parse_version_for_sorting(self, version_str):
        """
        Parse une chaîne de version pour le tri.
        Convertit chaque partie numérique en entier pour un tri correct.
        
        Args:
            version_str (str): Chaîne de version à parser
            
        Returns:
            tuple: Tuple de composants de version pour le tri
        """
        try:
            # Supprimer le 'v' au début si présent
            if version_str.startswith('v'):
                version_str = version_str[1:]
                
            # Séparer la partie principale de la version des suffixes
            if '-' in version_str:
                main_version, suffix = version_str.split('-', 1)
            else:
                main_version, suffix = version_str, ''
                
            # Diviser la version en composants
            components = []
            for part in main_version.split('.'):
                try:
                    components.append(int(part))
                except ValueError:
                    components.append(part)
                    
            # Ajouter le suffixe comme dernier élément
            if suffix:
                components.append(suffix)
                
            return tuple(components)
        except Exception:
            # En cas d'erreur, retourner une valeur qui sera classée en dernier
            return (-1,)
    
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
                # Supprimer le 'v' au début si présent
                v1 = version1[1:] if version1.startswith('v') else version1
                v2 = version2[1:] if version2.startswith('v') else version2
                
                # Comparer avec packaging.version
                parsed_v1 = version.parse(v1)
                parsed_v2 = version.parse(v2)
                
                if parsed_v1 > parsed_v2:
                    return 1
                elif parsed_v1 < parsed_v2:
                    return -1
                else:
                    return 0
            
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
