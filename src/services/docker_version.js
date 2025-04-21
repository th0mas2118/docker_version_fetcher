/**
 * Service pour interagir avec Docker
 * Utilise dockerode pour communiquer avec l'API Docker
 */
import Docker from 'dockerode';
import axios from 'axios';
import { stateService } from './state.js';
import { notificationService } from './notification.js';

class DockerService {
    constructor() {
        // Initialisation de la connexion Docker
        // Par défaut, utilise le socket Unix sur Linux
        this.docker = new Docker({socketPath: '/var/run/docker.sock'});
        
        // Stockage des informations sur le conteneur actuel
        this.currentContainerId = null;
        this.currentContainerName = null;
    }
    
    /**
     * Initialise les informations sur le conteneur actuel (ID et nom)
     * Cette fonction est appelée automatiquement lors de la construction de l'objet
     */
    async initCurrentContainerInfo() {
        try {
            const containerInfo = await this.getCurrentContainerInfo();
            
            if (containerInfo) {
                this.currentContainerId = containerInfo.id;
                this.currentContainerName = containerInfo.name;
                console.log(`Conteneur actuel identifié - ID: ${this.currentContainerId}, Nom: ${this.currentContainerName}`);
            } else {
                console.log('Non exécuté dans un conteneur Docker ou impossible de déterminer les informations');
            }
        } catch (error) {
            console.error('Erreur lors de l\'initialisation des informations du conteneur:', error);
        }
    }
    
    /**
     * Récupère les informations sur le conteneur actuel (ID et nom)
     * @returns {Object|null} - Informations sur le conteneur actuel ou null si non exécuté dans un conteneur
     */
    async getCurrentContainerInfo() {
        try {
            // Méthode 1: Lecture du hostname qui correspond à l'ID du conteneur sous Docker
            const fs = require('fs');
            let containerId = null;
            
            // Essayer de lire l'ID depuis les cgroups
            if (fs.existsSync('/proc/self/cgroup')) {
                const cgroupContent = fs.readFileSync('/proc/self/cgroup', 'utf8');
                const dockerIdMatch = cgroupContent.match(/docker[\/\-]([a-f0-9]+)/i);
                if (dockerIdMatch && dockerIdMatch[1]) {
                    containerId = dockerIdMatch[1];
                }
            }
            
            // Si l'ID n'a pas été trouvé, essayer de lire le hostname
            if (!containerId && fs.existsSync('/etc/hostname')) {
                const hostname = fs.readFileSync('/etc/hostname', 'utf8').trim();
                if (hostname && hostname.length >= 12) {
                    containerId = hostname;
                }
            }
            
            // Si on a trouvé un ID, récupérer les détails du conteneur
            if (containerId) {
                // Récupérer tous les conteneurs pour trouver celui qui correspond à notre ID
                const allContainers = await this.docker.listContainers({ all: true });
                const currentContainer = allContainers.find(c => c.Id.includes(containerId));
                
                if (currentContainer) {
                    return {
                        id: currentContainer.Id,
                        name: currentContainer.Names[0].replace('/', ''),
                        image: currentContainer.Image,
                        state: currentContainer.State
                    };
                }
            }
            
            return null;
        } catch (error) {
            console.error('Erreur lors de la récupération des informations du conteneur actuel:', error);
            return null;
        }
    }

    /**
     * Liste tous les conteneurs avec leurs informations détaillées
     * @param {boolean} running - Si true, n'inclut que les conteneurs en cours d'exécution
     * @param {boolean} excludeSelf - Si true, exclut le conteneur actuel de la liste
     * @returns {Array} - Liste des conteneurs avec leurs informations
     */
    async listContainers(running = true, excludeSelf = true) {
        try {
            // Si on veut exclure le conteneur actuel, on initialise d'abord ses informations
            if (excludeSelf && !this.currentContainerId) {
                console.log('Initialisation des informations du conteneur actuel avant filtrage...');
                await this.initCurrentContainerInfo();
                console.log(`ID du conteneur actuel après initialisation: ${this.currentContainerId || 'non déterminé'}`);
            }
            
            // Récupération de tous les conteneurs
            const containers = await this.docker.listContainers();
            console.log(`Nombre de conteneurs trouvés: ${containers.length}`);
            
            // Transformation des données pour un format plus lisible
            return containers
                // Application des filtres
                .filter(container => {
                    // Filtre par état (running)
                    const stateFilter = !running || container.State === 'running';
                    
                    // Filtre pour exclure le conteneur actuel
                    let selfFilter = true;
                    if (excludeSelf && this.currentContainerId) {
                        selfFilter = !container.Id.includes(this.currentContainerId);
                        
                        // Si on a exclu un conteneur, l'afficher dans les logs
                        if (!selfFilter) {
                            console.log(`Conteneur actuel exclu: ${container.Names.map(n => n.replace('/', '')).join(', ')}`);
                        }
                    }
                    
                    return stateFilter && selfFilter;
                })
                .map(container => {
                    // Séparation de l'image et du tag
                    const [imageName, imageTag] = container.Image.includes(':') 
                        ? container.Image.split(':') 
                        : [container.Image, 'latest'];
                    
                    // Extraction du nom du conteneur (sans le slash initial)
                    const containerNames = container.Names.map(name => name.replace('/', ''));
                    
                    return {
                        id: container.Id.substring(0, 12), // ID court du conteneur
                        names: containerNames,            // Noms sans le slash
                        name: containerNames[0] || '',    // Premier nom (principal)
                        imageWithTag: container.Image,    // Image complète avec tag
                        image: imageName,                // Nom de l'image sans tag
                        tag: imageTag,                   // Tag de l'image
                        state: container.State,          // État du conteneur
                        status: container.Status         // Statut détaillé du conteneur
                    };
                });
        } catch (error) {
            console.error('Erreur lors de la récupération des conteneurs:', error);
            throw error;
        }
    }

    /**
     * Vérifie les mises à jour disponibles pour tous les conteneurs
     * @returns {Array} Liste des mises à jour disponibles
     */
    async checkForUpdates() {
        console.log('Vérification des mises à jour disponibles...');
        const updates = [];
        
        try {
            // Récupération des conteneurs en cours d'exécution
            const containers = await this.listContainers(true);
            console.log(`${containers.length} conteneurs en cours d'exécution`);
            
            // Parcours des conteneurs
            for (const container of containers) {
                try {
                    console.log(`\nAnalyse du conteneur: ${container.name}`);
                    console.log(`Image: ${container.imageWithTag}`);
                    
                    // Récupération des informations sur le dépôt
                    const imageInfo = await this.fetchRepository(container.image, container.tag);
                    
                    if (imageInfo.error) {
                        console.log(`Erreur: ${imageInfo.error}`);
                        continue;
                    }
                    
                    // Affichage du tag valable trouvé
                    if (imageInfo.latest_version_tag) {
                        const tag = imageInfo.latest_version_tag;
                        const date = new Date(tag.last_updated).toLocaleString();
                        
                        console.log(`\nVersion valable trouvée:`);
                        console.log(`  - ${tag.name} (mise à jour le ${date})`);
                        
                        // Vérification si une mise à jour est disponible
                        if (tag.name !== container.tag) {
                            console.log('\n❗ Une mise à jour est disponible!');
                            console.log(`  Version actuelle: ${container.tag}`);
                            console.log(`  Version recommandée: ${tag.name}`);
                            
                            // Vérification si une notification doit être envoyée
                            if (stateService.shouldNotify(container.image, container.tag, tag.name)) {
                                // Ajout de la mise à jour à la liste
                                updates.push({
                                    containerName: container.name,
                                    image: container.image,
                                    currentTag: container.tag,
                                    latestVersion: tag.name,
                                    lastUpdated: tag.last_updated
                                });
                            }
                            
                        } else {
                            console.log('\n✅ Le conteneur utilise déjà la version recommandée.');
                        }
                    } else {
                        console.log('\n⚠️ Aucune version valable trouvée pour cette image.');
                    }
                } catch (error) {
                    console.error(`Erreur lors de l'analyse du conteneur ${container.name}:`, error);
                }
            }
            
            // Nettoyage des images qui ne sont plus en cours d'exécution
            const runningImageNames = containers.map(container => container.image);
            stateService.cleanupImages(runningImageNames);
            
            console.log(`\nAnalyse des conteneurs terminée. ${updates.length} mise(s) à jour disponible(s).`);
            return updates;
        } catch (error) {
            console.error('Erreur lors de la vérification des mises à jour:', error);
            throw error;
        }
    }

    /**
     * Fonction de test pour afficher les conteneurs en cours d'exécution
     * et la première version valable disponible
     */
    async test() {
        try {
            // Récupération des conteneurs en cours d'exécution
            const containers = await this.listContainers();
            console.log('Conteneurs en cours d\'exécution trouvés:', containers.length);
            

            if (containers.length === 0) {
                console.log('Aucun conteneur en cours d\'exécution.');
                return;
            }
            
            console.log('\nListe des conteneurs en cours d\'exécution:');
            
            // Traitement de chaque conteneur séquentiellement
            for (let i = 0; i < containers.length; i++) {
                const container = containers[i];
                try {
                    console.log(`\n=== Conteneur ${i + 1}/${containers.length} ===`);
                    console.log(`Nom: ${container.names.join(', ')}`);
                    console.log(`Image complète: ${container.imageWithTag}`);
                    console.log(`Nom de l'image: ${container.image}`);
                    console.log(`Tag actuel: ${container.tag}`);
                    
                    // Récupération du premier tag numéroté valable
                    // On passe le nom de l'image et le tag actuel
                    console.log('Recherche de la première version valable compatible...');
                    const imageInfo = await this.fetchRepository(container.image, container.tag);
                    
                    if (imageInfo.error) {
                        console.log(`Erreur: ${imageInfo.error}`);
                        continue;
                    }
                    
                    // Affichage du tag valable trouvé
                    if (imageInfo.latest_version_tag) {
                        const tag = imageInfo.latest_version_tag;
                        const date = new Date(tag.last_updated).toLocaleString();
                        console.log(`\nVersion valable trouvée:`);
                        console.log(`  - ${tag.name} (mise à jour le ${date})`);
                        
                        
                        // Vérification si une mise à jour est disponible
                        if (tag.name !== container.tag) {
                            console.log('\n❗ Une mise à jour est disponible!');
                            console.log(`  Version actuelle: ${container.tag}`);
                            console.log(`  Version recommandée: ${tag.name}`);
                            
                            // Pour la méthode test(), on notifie directement
                            // Note: Cette méthode est maintenue pour compatibilité, mais checkForUpdates() est préférée
                            if (stateService.shouldNotify(container.image, container.tag, tag.name)) {
                                // Préparation du message de notification
                                const message = `## 🔴 Mise à jour Docker disponible\n\n` +
                                               `### ${container.name}\n` +
                                               `- **Image**: ${container.imageWithTag}\n` +
                                               `- **Version actuelle**: ${container.tag}\n` +
                                               `- **Nouvelle version**: ${tag.name}\n` +
                                               `- **Date de publication**: ${new Date(tag.last_updated).toLocaleDateString('fr-FR')}\n\n` +
                                               `---\n*Docker Version Fetcher - Notification automatique*`;
                                
                                // Envoi de la notification
                                const title = `Mise à jour disponible pour ${container.name}`;
                                await notificationService.sendNotification(message, title);
                                
                                // Mise à jour de l'état après notification
                                stateService.updateImageState(container.image, {
                                    containerName: container.name,
                                    image: container.image,
                                    currentTag: container.tag,
                                    latestVersion: tag.name,
                                    lastUpdated: tag.last_updated
                                });
                            }
                        } else {
                            console.log('\n✅ Le conteneur utilise déjà la version recommandée.');
                        }
                    } else {
                        console.log('\nAucune version numérotée valable trouvée pour cette image.');
                    }
                } catch (containerError) {
                    console.error(`Erreur lors du traitement du conteneur:`, containerError);
                }
            }
            
            // Nettoyage des images qui ne sont plus en cours d'exécution
            const runningImageNames = containers.map(container => container.image);
            stateService.cleanupImages(runningImageNames);
            
            console.log('\nAnalyse des conteneurs terminée.');
        } catch (error) {
            console.error('Erreur dans la fonction test:', error);
        }
    }

    /**
     * Récupère le premier tag numéroté valable pour une image Docker
     * @param {string} image - Nom de l'image (format: user/repo ou library/repo pour les images officielles)
     * @param {string} currentTag - Tag actuel de l'image
     * @param {number} maxPages - Nombre maximum de pages à parcourir
     * @returns {Object} - Information sur le premier tag numéroté valable
     */
    async fetchRepository(image, currentTag = 'latest', maxPages = 5) {
        try {
            // Traitement spécial pour les images officielles (sans namespace)
            if (!image.includes('/')) {
                image = `library/${image}`;
            }
            
            // Déterminer si le tag actuel est purement numérique ou contient des lettres
            const isCurrentTagNumeric = !/[a-zA-Z]/.test(currentTag);
            console.log(`Tag actuel (${currentTag}) est ${isCurrentTagNumeric ? 'purement numérique' : 'avec des lettres'}`);
            
            // Taille de page fixée à 10 pour éviter de surcharger l'API
            const pageSize = 10;
            let totalTagsCount = 0;
            let nextUrl = null;
            
            // Fonction pour vérifier si un tag est numéroté et utilisable
            const isVersionTag = (tagName) => {
                // Patterns pour identifier les tags numérotés
                // Exemples: 1.0, v1.0, 1.0.0, v1.0.0, 1.0.0-alpha, 1, v1, etc.
                const versionPatterns = [
                    /^v?\d+(\.\d+)*(-[a-zA-Z0-9._-]+)?$/, // Format standard: 1.0.0, v1.0.0, 1.0.0-alpha
                    /^\d{4}\.\d{2}(\.\d+)?$/, // Format date: 2023.01, 2023.01.1
                    /^\d{8}$/ // Format date compact: 20230101
                ];
                
                // Vérifie si le tag correspond à l'un des patterns
                return versionPatterns.some(pattern => pattern.test(tagName));
            };
            
            
            // Fonction pour vérifier si un tag correspond au même type que le tag actuel
            const matchesCurrentTagType = (tagName) => {
                // Si le tag actuel est purement numérique, on ne veut que des tags purement numériques
                if (isCurrentTagNumeric) {
                    return !/[a-zA-Z]/.test(tagName);
                }
                // Sinon, on accepte tous les tags
                return true;
            };
            
            // Parcourir les pages jusqu'à trouver un tag valable ou atteindre maxPages
            for (let page = 1; page <= maxPages; page++) {
                // Construire l'URL pour la page courante
                const url = nextUrl || `https://registry.hub.docker.com/v2/repositories/${image}/tags?page_size=${pageSize}&ordering=last_updated`;
                console.log(`Récupération des tags (page ${page}/${maxPages}) depuis: ${url}`);
                
                // Récupérer les tags de la page
                const response = await axios.get(url);
                totalTagsCount = response.data.count;
                
                // Chercher le premier tag numéroté valable dans cette page
                for (const tag of response.data.results) {
                    // Vérifier si le tag est numéroté et correspond au même type que le tag actuel
                    if (isVersionTag(tag.name) && matchesCurrentTagType(tag.name)) {
                        console.log(`Tag valable trouvé: ${tag.name} (compatible avec le type du tag actuel)`);
                        
                        // Retourner directement le premier tag valable
                        return {
                            name: image,
                            latest_version_tag: {
                                name: tag.name,
                                last_updated: tag.last_updated,
                                full_size: tag.full_size,
                                digest: tag.digest?.substring(0, 16) || 'N/A'
                            },
                            total_tags_count: totalTagsCount
                        };
                    } else if (isVersionTag(tag.name)) {
                        console.log(`Tag valable ignoré: ${tag.name} (type incompatible avec le tag actuel)`);
                    }
                }
                
                // Aucun tag valable dans cette page, vérifier s'il y a une page suivante
                nextUrl = response.data.next;
                if (!nextUrl) {
                    console.log('Fin des pages disponibles.');
                    break;
                }
            }
            
            // Aucun tag valable trouvé après avoir parcouru toutes les pages
            console.log(`Aucun tag numéroté valable trouvé pour ${image} après ${maxPages} pages.`);
            return {
                name: image,
                latest_version_tag: null,
                total_tags_count: totalTagsCount
            };
        } catch (error) {
            console.error(`Erreur lors de la récupération des tags pour ${image}:`, error.message);
            return {
                name: image,
                error: error.message,
                latest_version_tag: null
            };
        }
    }

    // Fonction pour trier les tags par version sémantique
    sortVersionTags(tags) {
        return tags.sort((a, b) => {
            const versionA = a.name.replace(/^v/, '');
            const versionB = b.name.replace(/^v/, '');
            
            const versionPartsA = versionA.split('.').map(Number);
            const versionPartsB = versionB.split('.').map(Number);
            
            for (let i = 0; i < Math.max(versionPartsA.length, versionPartsB.length); i++) {
                const partA = versionPartsA[i] || 0;
                const partB = versionPartsB[i] || 0;
                
                if (partA !== partB) {
                    return partB - partA;
                }
            }
            
            return 0;
        });
    }
}

export const dockerVersionService = new DockerService();
