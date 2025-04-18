#!/usr/bin/env python3
"""
Module pour gérer l'état des images et éviter les notifications répétitives.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

logger = logging.getLogger('docker_version_fetcher.state_manager')

class StateManager:
    """Classe pour gérer l'état des images Docker surveillées."""
    
    def __init__(self, state_file_path):
        """
        Initialise le gestionnaire d'état.
        
        Args:
            state_file_path (str): Chemin vers le fichier d'état
        """
        self.state_file_path = state_file_path
        # Récupérer la fréquence des notifications depuis les variables d'environnement
        self.notification_frequency = int(os.getenv('NOTIFICATION_FREQUENCY', '7'))  # jours entre les rappels
    
    def load_state(self):
        """
        Charge l'état depuis le fichier.
        
        Returns:
            dict: État chargé ou état par défaut si le fichier n'existe pas
        """
        try:
            # Vérifier si le fichier existe
            if os.path.exists(self.state_file_path):
                with open(self.state_file_path, 'r') as f:
                    state = json.load(f)
                logger.info(f"État chargé depuis {self.state_file_path}")
                return state
            else:
                # Créer le répertoire parent si nécessaire
                os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
                
                # Retourner un état par défaut
                default_state = {
                    'images': {},
                    'settings': {
                        'notification_frequency': self.notification_frequency,
                        'last_check': datetime.now().isoformat()
                    }
                }
                logger.info(f"Fichier d'état non trouvé, création d'un nouvel état")
                return default_state
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'état: {str(e)}")
            # En cas d'erreur, retourner un état par défaut
            return {
                'images': {},
                'settings': {
                    'notification_frequency': self.notification_frequency,
                    'last_check': datetime.now().isoformat()
                }
            }
    
    def save_state(self, state):
        """
        Sauvegarde l'état dans le fichier.
        
        Args:
            state (dict): État à sauvegarder
        """
        try:
            # Mettre à jour la date de dernière vérification
            state['settings']['last_check'] = datetime.now().isoformat()
            
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            
            # Sauvegarder l'état
            with open(self.state_file_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"État sauvegardé dans {self.state_file_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'état: {str(e)}")
    
    def should_notify(self, state, image_key, latest_digest):
        """
        Détermine si une notification doit être envoyée pour une image.
        
        Args:
            state (dict): État actuel
            image_key (str): Clé de l'image (repository:tag)
            latest_digest (str): Digest de la dernière version disponible
            
        Returns:
            bool: True si une notification doit être envoyée, False sinon
        """
        # Extraire le repository à partir de image_key
        repository = image_key.split(':')[0] if ':' in image_key else image_key
        tag = image_key.split(':')[1] if ':' in image_key else 'latest'
        
        # Si le repository n'est pas dans l'état, on doit notifier
        if repository not in state['images']:
            logger.info(f"Nouveau repository {repository}, notification requise")
            return True
        
        repo_state = state['images'][repository]
        
        # Vérifier si ce tag spécifique a déjà été notifié
        current_tags = repo_state.get('current_tags', {})
        if tag in current_tags and current_tags[tag].get('notified', False):
            # Vérifier la date de dernière notification pour ce tag
            tag_last_notified = datetime.fromisoformat(current_tags[tag].get('last_notified', '2000-01-01T00:00:00'))
            notification_frequency = state['settings'].get('notification_frequency', self.notification_frequency)
            
            # Calculer la date du prochain rappel
            next_reminder = tag_last_notified + timedelta(days=notification_frequency)
            
            # Si la date du prochain rappel est passée, on doit notifier
            if datetime.now() >= next_reminder:
                logger.info(f"Rappel pour {image_key}, dernière notification le {tag_last_notified.isoformat()}")
                return True
            else:
                logger.info(f"Pas de notification requise pour {image_key} (déjà notifié récemment)")
                return False
        
        # Si le tag n'a jamais été notifié, on doit notifier
        if tag not in current_tags:
            logger.info(f"Nouveau tag {tag} pour {repository}, notification requise")
            return True
        
        # Si le repository a été notifié récemment, vérifier la fréquence
        if repo_state.get('notified', False):
            repo_last_notified = datetime.fromisoformat(repo_state.get('last_notified', '2000-01-01T00:00:00'))
            notification_frequency = state['settings'].get('notification_frequency', self.notification_frequency)
            
            # Calculer la date du prochain rappel
            next_reminder = repo_last_notified + timedelta(days=notification_frequency)
            
            # Si la date du prochain rappel est passée, on doit notifier
            if datetime.now() >= next_reminder:
                logger.info(f"Rappel pour {repository}, dernière notification le {repo_last_notified.isoformat()}")
                return True
        
        logger.info(f"Pas de notification requise pour {image_key}")
        return False
    
    def update_repository_state(self, state, repository, latest_digest, latest_tag):
        """
        Met à jour l'état d'un repository avec la dernière version disponible.
        
        Args:
            state (dict): État actuel
            repository (str): Nom du repository
            latest_digest (str): Digest de la dernière version disponible
            latest_tag (str): Tag de la dernière version disponible
        """
        # Initialiser l'état du repository si nécessaire
        if repository not in state['images']:
            state['images'][repository] = {}
        
        # Mettre à jour l'état du repository
        state['images'][repository].update({
            'latest_digest': latest_digest,
            'latest_tag': latest_tag,
            'current_tags': state['images'][repository].get('current_tags', {}) or {},
            'notified': True,
            'last_notified': datetime.now().isoformat()
        })
        
        logger.info(f"État du repository mis à jour: {repository} -> {latest_tag}")
    
    def update_tag_state(self, state, repository, tag, latest_digest, latest_tag):
        """
        Met à jour l'état d'un tag spécifique après notification.
        
        Args:
            state (dict): État actuel
            repository (str): Nom du repository
            tag (str): Tag de l'image
            latest_digest (str): Digest de la dernière version disponible
            latest_tag (str): Tag de la dernière version disponible
        """
        # Initialiser l'état du repository si nécessaire
        if repository not in state['images']:
            state['images'][repository] = {}
        
        # Initialiser la structure des tags si nécessaire
        if 'current_tags' not in state['images'][repository]:
            state['images'][repository]['current_tags'] = {}
        
        # Mettre à jour l'état du tag spécifique
        state['images'][repository]['current_tags'][tag] = {
            'notified': True,
            'last_notified': datetime.now().isoformat(),
            'latest_tag': latest_tag
        }
        
        logger.info(f"État du tag mis à jour: {repository}:{tag} -> {latest_tag}")
    
    def update_image_state(self, state, image_key, latest_digest, latest_tag):
        """
        Met à jour l'état d'une image après notification (méthode de compatibilité).
        
        Args:
            state (dict): État actuel
            image_key (str): Clé de l'image (repository:tag)
            latest_digest (str): Digest de la dernière version disponible
            latest_tag (str): Tag de la dernière version disponible
        """
        # Extraire le repository et le tag à partir de image_key
        if ':' in image_key:
            repository, tag = image_key.split(':', 1)
            self.update_repository_state(state, repository, latest_digest, latest_tag)
            self.update_tag_state(state, repository, tag, latest_digest, latest_tag)
        else:
            self.update_repository_state(state, image_key, latest_digest, latest_tag)
        
        logger.info(f"État mis à jour pour {image_key}")
