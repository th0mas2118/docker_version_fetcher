import axios from 'axios';
import fs from 'fs';
import path from 'path';

class NotificationService {
  constructor() {
    this.gotifyUrl = process.env.GOTIFY_URL;
    this.gotifyToken = process.env.GOTIFY_TOKEN;
    this.gotifyPriority = process.env.GOTIFY_PRIORITY;
    this.gotifyTitle = process.env.GOTIFY_TITLE;
    this.serverName = process.env.SERVER_NAME || 'Serveur Principal';
    
    // Chargement des icônes personnalisées depuis le fichier de configuration
    this.containerIcons = this.loadIcons();
  }
  
  /**
   * Charge les icônes personnalisées depuis le fichier de configuration
   * @returns {Object} - Mapping des icônes pour les conteneurs
   */
  loadIcons() {
    // Icône par défaut pour tous les conteneurs
    const defaultIcons = {
      'default': '📦'  // Package (défaut)
    };
    
    try {
      const iconsPath = path.join(process.cwd(), 'config', 'icons.json');
      
      if (fs.existsSync(iconsPath)) {
        console.log(`Chargement des icônes personnalisées depuis ${iconsPath}`);
        const iconsData = fs.readFileSync(iconsPath, 'utf8');
        const customIcons = JSON.parse(iconsData);
        
        // Si aucune icône par défaut n'est définie dans le fichier de configuration,
        // on s'assure qu'il y en a une
        if (!customIcons.default) {
          customIcons.default = '📦';
        }
        
        return customIcons;
      }
    } catch (error) {
      console.error('Erreur lors du chargement des icônes personnalisées:', error);
    }
    
    return defaultIcons;
  }

  /**
   * Détermine l'icône à utiliser pour un conteneur
   * @param {string} imageName - Nom de l'image Docker
   * @returns {string} - Icône à utiliser
   */
  getContainerIcon(imageName) {
    // Recherche d'une correspondance dans le mapping des icônes
    for (const [key, icon] of Object.entries(this.containerIcons)) {
      if (key !== 'default' && imageName.toLowerCase().includes(key.toLowerCase())) {
        return icon;
      }
    }
    
    // Icône par défaut si aucune correspondance n'est trouvée
    return this.containerIcons.default;
  }
  
  /**
   * Crée un message formaté pour une mise à jour unique
   * @param {Object} update - Informations sur la mise à jour
   * @returns {string} - Message formaté
   */
  createSingleUpdateMessage(update) {
    const now = new Date();
    const formattedDate = now.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    });
    
    const updateDate = new Date(update.lastUpdated).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
    
    const containerIcon = this.getContainerIcon(update.image);
    
    let message = `## 📢 Mise à jour Docker disponible\n\n`;
    message += `📅 *Détecté le ${formattedDate} à ${now.toLocaleTimeString('fr-FR')}*\n\n`;
    message += `### ${containerIcon} ${update.containerName}\n`;
    message += `🏷️ **Image**: \`${update.image}\`\n`;
    message += `🔻 **Version actuelle**: \`${update.currentTag}\`\n`;
    message += `🔺 **Nouvelle version**: \`${update.latestVersion}\`\n`;
    message += `📆 **Date de publication**: ${updateDate}\n\n`;
    message += `---\n🚀 *Docker Version Fetcher - Notification automatique*`;
    
    return message;
  }
  
  /**
   * Crée un message formaté pour plusieurs mises à jour
   * @param {Array} updates - Liste des mises à jour
   * @returns {string} - Message formaté
   */
  createMultiUpdateMessage(updates) {
    if (updates.length === 0) return '';
    
    const now = new Date();
    const formattedDate = now.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    });
    
    // Construction du message avec une belle présentation et des icônes
    let message = `## 📢 Mises à jour Docker disponibles\n\n`;
    message += `📅 *Détecté le ${formattedDate} à ${now.toLocaleTimeString('fr-FR')}*\n\n`;
    
    // Ajout de chaque mise à jour au message avec des icônes
    updates.forEach((update, index) => {
      const updateDate = new Date(update.lastUpdated).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
      
      const containerIcon = this.getContainerIcon(update.image);
      
      message += `### ${containerIcon} ${index + 1}. ${update.containerName} \n`;
      message += `🏷️ **Image**: \`${update.image}\`\n`;
      message += `🔻 **Version actuelle**: \`${update.currentTag}\`\n`;
      message += `🔺 **Nouvelle version**: \`${update.latestVersion}\`\n`;
      message += `📆 **Date de publication**: ${updateDate}\n\n`;
    });
    
    // Ajout d'un pied de page avec icône
    message += `---\n🚀 *Docker Version Fetcher - Notification automatique*`;
    
    return message;
  }
  
  /**
   * Envoie une notification pour une mise à jour unique
   * @param {Object} update - Informations sur la mise à jour
   */
  async notifySingleUpdate(update) {
    const message = this.createSingleUpdateMessage(update);
    const title = `[${this.serverName}] Mise à jour disponible pour ${update.containerName}`;
    await this.sendNotification(message, title);
  }
  
  /**
   * Envoie une notification pour plusieurs mises à jour
   * @param {Array} updates - Liste des mises à jour
   */
  async notifyMultipleUpdates(updates) {
    if (updates.length === 0) return;
    
    const message = this.createMultiUpdateMessage(updates);
    const title = updates.length === 1 
      ? `[${this.serverName}] Mise à jour disponible pour ${updates[0].containerName}` 
      : `[${this.serverName}] ${updates.length} mises à jour disponibles`;
    
    console.log(`Envoi d'une notification pour ${updates.length} mise(s) à jour`);
    await this.sendNotification(message, title);
  }
  
  /**
   * Envoie une notification via Gotify
   * @param {string} message - Message à envoyer
   * @param {string} customTitle - Titre personnalisé (optionnel)
   * @returns {Promise<Object>} - Réponse de l'API Gotify
   */
  async sendNotification(message, customTitle = null) {
    console.log("Message envoyé: ", message.substring(0, 100) + '...');
    try {
      const url = `${this.gotifyUrl}/message?token=${this.gotifyToken}`;
      console.log('URL de l\'API Gotify:', url);
      
      const response = await axios.post(url, {
        title: customTitle || this.gotifyTitle,
        message: message,
        priority: parseInt(this.gotifyPriority) || 5,
      });
      console.log('Notification envoyée avec succès:', response.data);
    } catch (error) {
      console.error('Erreur lors de l\'envoi de la notification:', error);
      console.error('URL utilisée:', `${this.gotifyUrl}/message?token=***`);
      console.error('Données envoyées:', {
        title: customTitle || this.gotifyTitle,
        priority: parseInt(this.gotifyPriority) || 5
      });
    }
  }
}

export const notificationService = new NotificationService();