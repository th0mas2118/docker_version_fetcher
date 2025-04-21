/**
 * Service de gestion d'état pour Docker Version Fetcher
 * Stocke les informations sur les images suivies dans un fichier JSON
 */
import fs from 'fs';
import path from 'path';

class StateService {
    constructor() {
        // Chemin du fichier de stockage des données
        this.dataDir = process.env.DATA_DIR || path.join(process.cwd(), 'data');
        this.stateFile = path.join(this.dataDir, 'state.json');
        
        // Fréquence de notification en jours (par défaut: 7 jours)
        this.notificationFrequency = parseInt(process.env.NOTIFICATION_FREQUENCY || '7', 10);
        
        // Initialisation du service
        this.initStateFile();
    }
    
    /**
     * Initialise le fichier d'état s'il n'existe pas
     */
    initStateFile() {
        try {
            // Création du répertoire de données s'il n'existe pas
            if (!fs.existsSync(this.dataDir)) {
                console.log(`Création du répertoire de données: ${this.dataDir}`);
                fs.mkdirSync(this.dataDir, { recursive: true });
            }
            
            // Création du fichier d'état s'il n'existe pas
            if (!fs.existsSync(this.stateFile)) {
                console.log(`Création du fichier d'état: ${this.stateFile}`);
                this.saveState({
                    images: {},
                    lastCheck: new Date().toISOString()
                });
            }
        } catch (error) {
            console.error('Erreur lors de l\'initialisation du fichier d\'\u00e9tat:', error);
        }
    }
    
    /**
     * Charge l'état actuel depuis le fichier
     * @returns {Object} - État actuel
     */
    loadState() {
        try {
            if (fs.existsSync(this.stateFile)) {
                const data = fs.readFileSync(this.stateFile, 'utf8');
                return JSON.parse(data);
            }
            return { images: {}, lastCheck: new Date().toISOString() };
        } catch (error) {
            console.error('Erreur lors du chargement de l\'\u00e9tat:', error);
            return { images: {}, lastCheck: new Date().toISOString() };
        }
    }
    
    /**
     * Sauvegarde l'état dans le fichier
     * @param {Object} state - État à sauvegarder
     */
    saveState(state) {
        try {
            fs.writeFileSync(this.stateFile, JSON.stringify(state, null, 2), 'utf8');
        } catch (error) {
            console.error('Erreur lors de la sauvegarde de l\'\u00e9tat:', error);
        }
    }
    
    /**
     * Vérifie si une notification doit être envoyée pour une image
     * @param {string} image - Nom de l'image Docker (sans tag)
     * @param {string} currentTag - Tag actuel de l'image
     * @param {string} latestVersion - Dernière version disponible
     * @returns {boolean} - True si une notification doit être envoyée
     */
    shouldNotify(image, currentTag, latestVersion) {
        const state = this.loadState();
        const now = new Date();
        
        // Si l'image n'est pas dans l'état, on doit notifier
        if (!state.images[image]) {
            console.log(`Nouvelle image détectée: ${image}:${currentTag}`);
            return true;
        }
        
        const imageState = state.images[image];
        
        // Si la dernière version disponible a changé, on doit notifier
        if (imageState.latestVersion !== latestVersion) {
            console.log(`Nouvelle version disponible pour ${image}: ${latestVersion} (actuelle: ${currentTag})`);
            return true;
        }
        
        // Si la dernière notification est plus ancienne que la fréquence de notification, on doit notifier
        const lastNotification = new Date(imageState.lastNotification);
        const daysSinceLastNotification = Math.floor((now - lastNotification) / (1000 * 60 * 60 * 24));
        
        if (daysSinceLastNotification >= this.notificationFrequency) {
            console.log(`Délai de notification atteint pour ${image}:${currentTag} (${daysSinceLastNotification} jours)`);
            return true;
        }
        
        console.log(`Pas de notification nécessaire pour ${image}:${currentTag} (dernière: il y a ${daysSinceLastNotification} jours)`);
        return false;
    }
    
    /**
     * Met à jour l'état d'une image après notification
     * @param {string} image - Nom de l'image Docker (sans tag)
     * @param {Object} imageInfo - Informations sur l'image
     */
    updateImageState(image, imageInfo) {
        const state = this.loadState();
        const now = new Date();
        
        // Mise à jour ou création de l'état de l'image
        state.images[image] = {
            ...imageInfo,
            lastCheck: now.toISOString(),
            lastNotification: now.toISOString()
        };
        
        // Mise à jour de la date de dernière vérification globale
        state.lastCheck = now.toISOString();
        
        // Sauvegarde de l'état
        this.saveState(state);
        console.log(`État mis à jour pour ${image}`);
    }
    
    /**
     * 
     * Nettoie les images qui ne sont plus en cours d'exécution
     * @param {Array} runningImages - Liste des noms d'images en cours d'exécution
     */
    cleanupImages(runningImages) {
        const state = this.loadState();
        const imageNames = Object.keys(state.images);
        let changed = false;
        
        // Parcourir toutes les images dans l'état
        for (const imageName of imageNames) {
            // Si l'image n'est plus en cours d'exécution, la supprimer
            if (!runningImages.includes(imageName)) {
                console.log(`Suppression de l'image inactive: ${imageName}`);
                delete state.images[imageName];
                changed = true;
            }
        }
        
        // Si des changements ont été effectués, sauvegarder l'état
        if (changed) {
            state.lastCheck = new Date().toISOString();
            this.saveState(state);
        }
    }
}

export const stateService = new StateService();