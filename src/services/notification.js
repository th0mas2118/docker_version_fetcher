import axios from 'axios';

class NotificationService {
  constructor() {
    this.gotifyUrl = process.env.GOTIFY_URL;
    this.gotifyToken = process.env.GOTIFY_TOKEN;
    this.gotifyPriority = process.env.GOTIFY_PRIORITY;
    this.gotifyTitle = process.env.GOTIFY_TITLE;
  }

  async sendNotification(message) {
    console.log("message envoyé: ", message);
    try {
      const url = `${this.gotifyUrl}/message?token=${this.gotifyToken}`;
      console.log('URL de l\'API Gotify:', url);
      
      const response = await axios.post(url, {
        title: this.gotifyTitle,
        message: message,
        priority: parseInt(this.gotifyPriority) || 5,
      });
      console.log('Notification envoyée avec succès:', response.data);
    } catch (error) {
      console.error('Erreur lors de l\'envoi de la notification:', error);
      console.error('URL utilisée:', `${this.gotifyUrl}/message?token=***`);
      console.error('Données envoyées:', {
        title: this.gotifyTitle,
        priority: parseInt(this.gotifyPriority) || 5
      });
    }
  }
}

export const notificationService = new NotificationService();