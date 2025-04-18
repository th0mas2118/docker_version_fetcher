#!/usr/bin/env python3
"""
Module pour gérer les notifications via Gotify.
"""

import requests
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

logger = logging.getLogger('docker_version_fetcher.notification_manager')

class NotificationManager:
    """Classe pour gérer l'envoi de notifications via Gotify."""
    
    def __init__(self, config_path=None):
        """
        Initialise le gestionnaire de notifications.
        
        Args:
            config_path (str, optional): Chemin vers le fichier de configuration Gotify (obsolète, gardé pour compatibilité)
        """
        self.config = self._load_config_from_env()
    
    def _load_config_from_env(self):
        """
        Charge la configuration Gotify depuis les variables d'environnement.
        
        Returns:
            dict: Configuration chargée depuis les variables d'environnement
        """
        try:
            config = {
                'url': os.getenv('GOTIFY_URL', 'https://gotify.example.com'),
                'token': os.getenv('GOTIFY_TOKEN', 'YOUR_GOTIFY_TOKEN'),
                'priority': int(os.getenv('GOTIFY_PRIORITY', '5')),
                'title': os.getenv('GOTIFY_TITLE', 'Docker Version Fetcher')
            }
            
            # Vérifier si la configuration est valide
            if config['url'] == 'https://gotify.example.com' or config['token'] == 'YOUR_GOTIFY_TOKEN':
                logger.warning("Variables d'environnement Gotify non définies ou incomplètes")
                logger.warning("Veuillez configurer les variables GOTIFY_URL et GOTIFY_TOKEN dans le fichier .env")
            else:
                logger.info("Configuration Gotify chargée depuis les variables d'environnement")
                
            return config
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration Gotify: {str(e)}")
            # En cas d'erreur, retourner une configuration par défaut
            return {
                'url': 'https://gotify.example.com',
                'token': 'YOUR_GOTIFY_TOKEN',
                'priority': 5,
                'title': 'Docker Version Fetcher'
            }
    
    def send_notification(self, title, message, priority=None):
        """
        Envoie une notification via Gotify.
        
        Args:
            title (str): Titre de la notification
            message (str): Message de la notification
            priority (int, optional): Priorité de la notification
            
        Returns:
            bool: True si la notification a été envoyée avec succès, False sinon
        """
        # Vérifier si la configuration est valide
        if self.config['url'] == 'https://gotify.example.com' or self.config['token'] == 'YOUR_GOTIFY_TOKEN':
            logger.warning("Configuration Gotify non définie, notification non envoyée")
            logger.warning(f"Veuillez éditer le fichier {self.config_path} avec vos informations Gotify")
            return False
        
        try:
            # Construire l'URL
            url = f"{self.config['url'].rstrip('/')}/message"
            
            # Préparer les données
            data = {
                'title': title,
                'message': message,
                'priority': priority if priority is not None else self.config.get('priority', 5)
            }
            
            # Préparer les headers
            headers = {
                'X-Gotify-Key': self.config['token'],
                'Content-Type': 'application/json'
            }
            
            # Envoyer la requête
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Notification envoyée avec succès: {title}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
            return False
    
    def send_updates_notification(self, updates):
        """
        Envoie une notification pour les mises à jour disponibles.
        
        Args:
            updates (list): Liste des mises à jour disponibles
            
        Returns:
            bool: True si la notification a été envoyée avec succès, False sinon
        """
        if not updates:
            logger.info("Aucune mise à jour à notifier")
            return True
        
        try:
            # Construire le titre
            title = f"{len(updates)} mise(s) à jour Docker disponible(s)"
            
            # Construire le message
            message = f"**Mises à jour Docker détectées le {datetime.now().strftime('%Y-%m-%d à %H:%M')}**\n\n"
            
            for update in updates:
                message += f"📦 **{update['repository']}**\n"
                message += f"  • Version actuelle: {update['current_tag']}\n"
                message += f"  • Nouvelle version: {update['latest_tag']}\n\n"
            
            message += "Pour mettre à jour, utilisez `docker pull [image]:[tag]`"
            
            # Envoyer la notification
            return self.send_notification(title, message, priority=self.config.get('priority', 5))
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la notification: {str(e)}")
            return False
