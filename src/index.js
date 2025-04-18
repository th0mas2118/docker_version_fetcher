/**
 * Docker Version Fetcher
 * Application pour surveiller les mises à jour des images Docker et envoyer des notifications via Gotify
 */

import { notificationService } from './services/notification.js';

console.log('Docker Version Fetcher - Démarrage');
console.log('Cette version est un placeholder pour tester le build Docker');

// Point d'entrée minimal pour le test de build
function main() {
  console.log('Application prête à être développée');

  notificationService.sendNotification('Test de notification');
}

main();
