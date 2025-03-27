/**
 * Main JavaScript file for Psychic Source Transcript Analysis Tool
 * Uses modern ES6+ features and modular organization
 */

// Utility functions for formatting and display
const Formatter = {
    /**
     * Format date objects for display
     * @param {string} dateString - ISO date string to format
     * @returns {string} Formatted date string
     */
    date(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (error) {
            console.error('Error formatting date:', error);
            return dateString || 'N/A';
        }
    },

    /**
     * Format seconds as minutes:seconds
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration string
     */
    duration(seconds) {
        if (!seconds && seconds !== 0) return 'N/A';
        
        try {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        } catch (error) {
            console.error('Error formatting duration:', error);
            return `${seconds}s`;
        }
    }
};

// Sentiment analysis utilities
const Sentiment = {
    /**
     * Map sentiment score to text description
     * @param {number} score - Sentiment score (-1 to 1)
     * @returns {string} Text description of sentiment
     */
    toText(score) {
        if (score === null || score === undefined) return 'Unknown';
        
        if (score > 0.5) return 'Very Positive';
        if (score > 0.1) return 'Positive';
        if (score > -0.1) return 'Neutral';
        if (score > -0.5) return 'Negative';
        return 'Very Negative';
    },

    /**
     * Get color for sentiment score
     * @param {number} score - Sentiment score (-1 to 1)
     * @returns {string} Hex color code
     */
    toColor(score) {
        if (score === null || score === undefined) return '#6c757d'; // gray for unknown
        
        if (score > 0.5) return '#28a745'; // green
        if (score > 0.1) return '#5cb85c'; // light green
        if (score > -0.1) return '#ffc107'; // yellow
        if (score > -0.5) return '#ff9800'; // orange
        return '#dc3545'; // red
    }
};

// UI Interaction utilities
const UI = {
    /**
     * Copy text to clipboard with visual feedback
     * @param {string} text - Text to copy
     */
    copyToClipboard(text) {
        if (!text) {
            this.showToast('No text to copy', 'warning');
            return;
        }
        
        navigator.clipboard.writeText(text)
            .then(() => {
                this.showToast('Copied to clipboard!', 'success');
            })
            .catch(err => {
                console.error('Failed to copy text:', err);
                this.showToast('Failed to copy text', 'danger');
            });
    },
    
    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Bootstrap alert type (success, danger, warning, info)
     */
    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.classList.add('toast', 'align-items-center', 'text-white', `bg-${type}`, 'border-0');
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Add icon based on type
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'danger') icon = 'exclamation-circle';
        if (type === 'warning') icon = 'exclamation-triangle';
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${icon} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add to document and show
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    }
};

// API interaction utilities
const API = {
    /**
     * Fetch data from an API endpoint with error handling
     * @param {string} url - API endpoint URL
     * @param {Object} options - Fetch options
     * @returns {Promise} Promise resolving to JSON data
     */
    async fetch(url, options = {}) {
        try {
            // Show loading state
            document.body.classList.add('api-loading');
            
            // Set default options
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            };
            
            // Merge options
            const fetchOptions = { ...defaultOptions, ...options };
            
            // Fetch data
            const response = await fetch(url, fetchOptions);
            
            // Check if response is ok
            if (!response.ok) {
                const error = await response.json().catch(() => ({
                    error: `HTTP error! Status: ${response.status}`
                }));
                throw new Error(error.error || error.message || `HTTP error! Status: ${response.status}`);
            }
            
            // Parse JSON response
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API fetch error:', error);
            // Show error toast
            UI.showToast(`API Error: ${error.message}`, 'danger');
            throw error;
        } finally {
            // Hide loading state
            document.body.classList.remove('api-loading');
        }
    }
};

// Export utilities for global access
window.Formatter = Formatter;
window.Sentiment = Sentiment;
window.UI = UI;
window.API = API;

// Make older function names work for backward compatibility
// These can be removed once all templates are updated
window.formatDate = Formatter.date;
window.formatDuration = Formatter.duration;
window.sentimentToText = Sentiment.toText;
window.sentimentToColor = Sentiment.toColor;
window.copyToClipboard = (text) => UI.copyToClipboard(text); 