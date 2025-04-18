#!/usr/bin/env python3
"""
Script pour exécuter l'application périodiquement.
"""

import argparse
import logging
import time
import subprocess
import sys
import os
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
logger = logging.getLogger('docker_version_fetcher.periodic')

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    # Récupérer l'intervalle par défaut depuis les variables d'environnement
    default_interval = int(os.getenv('CHECK_INTERVAL', '24'))
    
    parser = argparse.ArgumentParser(description='Exécute Docker Version Fetcher périodiquement')
    # parser.add_argument('--interval', type=int, default=default_interval,
    #                     help=f'Intervalle en heures entre les exécutions (défaut: {default_interval})')
    parser.add_argument('--seconds', type=int, default=None,
                        help='Intervalle en secondes entre les exécutions (prioritaire sur --interval)')
    parser.add_argument('--daemon', action='store_true',
                        help='Exécuter en arrière-plan comme un daemon')
    return parser.parse_args()

def run_main_script():
    """Exécute le script principal."""
    try:
        logger.info("Démarrage de l'exécution périodique")
        
        # Chemin vers le script principal
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
        
        # Exécuter le script
        result = subprocess.run([sys.executable, script_path], 
                               capture_output=True, 
                               text=True)
        
        if result.returncode == 0:
            logger.info("Exécution terminée avec succès")
            if result.stdout:
                logger.info(f"Sortie: {result.stdout}")
        else:
            logger.error(f"Erreur lors de l'exécution: {result.stderr}")
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script principal: {str(e)}")
        return False

def main():
    """Point d'entrée principal."""
    args = parse_arguments()
    
    # Convertir l'intervalle en secondes
    if args.seconds is not None:
        interval_seconds = args.seconds
        logger.info(f"Utilisation de l'intervalle en secondes: {interval_seconds} secondes")
    else:
        interval_seconds = args.interval * 3600
        logger.info(f"Utilisation de l'intervalle en heures: {args.interval} heures ({interval_seconds} secondes)")
    
    if args.daemon:
        if args.seconds is not None:
            logger.info(f"Démarrage en mode daemon avec un intervalle de {args.seconds} secondes")
        else:
            logger.info(f"Démarrage en mode daemon avec un intervalle de {args.interval} heures")
        
        while True:
            success = run_main_script()
            
            next_run = datetime.now().timestamp() + interval_seconds
            next_run_str = datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Prochaine exécution prévue à {next_run_str}")
            
            # Attendre jusqu'à la prochaine exécution
            time.sleep(interval_seconds)
    else:
        logger.info(f"Exécution unique")
        run_main_script()

if __name__ == "__main__":
    main()
