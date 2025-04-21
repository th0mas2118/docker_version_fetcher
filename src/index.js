/**
 * Docker Version Fetcher
 * Application pour surveiller les mises à jour des images Docker et envoyer des notifications via Gotify
 */

import { CronJob } from 'cron';
import dotenv from 'dotenv';
import { notificationService } from './services/notification.js';
import { dockerVersionService } from './services/docker_version.js';
import { stateService } from './services/state.js';

// Chargement des variables d'environnement
dotenv.config();

// Configuration de l'intervalle de vérification (par défaut: tous les jours à minuit)
const CHECK_INTERVAL = process.env.CHECK_INTERVAL || '0 0 */24 * * *';

/**
 * Vérifie les mises à jour des images Docker
 */
async function checkDockerVersions() {
  console.log('\n=== Début de la vérification des versions Docker ===');
  console.log(`Date: ${new Date().toLocaleString()}`);
  
  try {
    // Exécution de la vérification des versions Docker et récupération des mises à jour
    const updates = await dockerVersionService.checkForUpdates();
    
    // Envoi d'une notification unique si des mises à jour sont disponibles
    if (updates.length > 0) {
      // Délégation de la notification au service approprié
      await notificationService.notifyMultipleUpdates(updates);
      
      // Mise à jour de l'état pour toutes les images notifiées
      for (const update of updates) {
        stateService.updateImageState(update.image, {
          containerName: update.containerName,
          image: update.image,
          currentTag: update.currentTag,
          latestVersion: update.latestVersion,
          lastUpdated: update.lastUpdated
        });
      }
    } else {
      console.log('Aucune mise à jour à notifier.');
    }
    
    console.log('Vérification terminée avec succès');
  } catch (error) {
    console.error('Erreur lors de la vérification des versions Docker:', error);
    
    // Notification en cas d'erreur
    try {
      await notificationService.sendNotification(
        `Erreur lors de la vérification des versions Docker: ${error.message}`
      );
    } catch (notificationError) {
      console.error('Erreur lors de l\'envoi de la notification d\'erreur:', notificationError);
    }
  }
  
  console.log('=== Fin de la vérification des versions Docker ===\n');
}



/**
 * Point d'entrée principal de l'application
 */
async function main() {
  console.log('Docker Version Fetcher - Démarrage');
  console.log(`Date de démarrage: ${new Date().toLocaleString()}`);
  console.log(`Intervalle de vérification: ${CHECK_INTERVAL}`);
  console.log(`Fréquence de notification: ${process.env.NOTIFICATION_FREQUENCY || '7'} jours`);
  
  // Vérification immédiate au démarrage
  await checkDockerVersions();
  
  // Configuration de la tâche cron pour les vérifications périodiques
  const job = new CronJob(
    CHECK_INTERVAL,
    checkDockerVersions,
    null, // onComplete
    true, // start
    'Europe/Paris' // timezone
  );
  
  console.log(`Prochaine vérification prévue: ${job.nextDate().toLocaleString()}`);
  console.log('Application en cours d\'exécution, appuyez sur Ctrl+C pour arrêter.');
}

// Exécution du programme principal avec gestion des erreurs
main().catch(error => {
  console.error('Erreur fatale dans l\'application:', error);
  process.exit(1);
});
