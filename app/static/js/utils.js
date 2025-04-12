console.log("UTILS.JS LOADED - V1");

// Utility functions for formatting and display
const Formatter = {
    /**
     * Format date objects for display
     * @param {string} dateString - ISO date string to format
     * @returns {string} Formatted date string
     */
    date(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            // Use a more standard locale format that includes date and time
            return date.toLocaleString(undefined, { // Use browser's default locale
                year: 'numeric', month: 'numeric', day: 'numeric',
                hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
            });
        } catch (error) {
            console.error('Error formatting date:', dateString, error);
            return dateString; // Fallback
        }
    },

    /**
     * Format seconds as minutes:seconds
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration string
     */
    duration(seconds) {
        if (seconds === null || seconds === undefined || isNaN(seconds)) {
            return 'N/A';
        }
        seconds = Number(seconds);
        if (seconds < 0) return 'N/A';

        try {
            const totalSeconds = Math.round(seconds);
            const minutes = Math.floor(totalSeconds / 60);
            const remainingSeconds = totalSeconds % 60;
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        } catch (error) {
            console.error('Error formatting duration:', seconds, error);
            return `${Math.round(seconds)}s`; // Fallback
        }
    },

    /**
     * Format an hour (0-23) as HH:00
     * @param {number} hour - Hour of the day (0-23)
     * @returns {string} Formatted hour string or '--:--' if invalid
     */
    hour(hour) {
        if (hour === null || hour === undefined || isNaN(hour) || hour < 0 || hour > 23) {
            return '--:--'; // Return a clear placeholder for invalid input
        }
        try {
            return `${String(hour).padStart(2, '0')}:00`;
        } catch (error) {
            console.error('Error formatting hour:', hour, error);
            return '--:--'; // Fallback
        }
    },

    /**
     * Format a cost value (credits) as a whole number.
     * @param {number} cost - The cost value (can be float or integer).
     * @returns {string} Formatted cost as a whole number string or '--' if invalid.
     */
    cost(cost) {
        if (cost === null || cost === undefined || isNaN(cost)) {
            return '--'; // Placeholder for invalid input
        }
        try {
            // Round to the nearest whole number
            return Math.round(Number(cost)).toString(); 
        } catch (error) {
            console.error('Error formatting cost:', cost, error);
            return '--'; // Fallback
        }
    },

    /**
     * Format a number as a percentage (e.g., 0.75 -> '75%')
     * @param {number} value - The fractional value (0 to 1)
     * @param {number} decimalPlaces - Number of decimal places for the percentage (default 0)
     * @returns {string} Formatted percentage string or '--%' if invalid
     */
    percentage(value, decimalPlaces = 0) {
        if (value === null || value === undefined || isNaN(value)) {
            return '--%'; // Placeholder for invalid input
        }
        try {
            const numberValue = Number(value);
            if (numberValue < 0 || numberValue > 1) {
                 console.warn(`Formatter.percentage received value outside expected 0-1 range: ${value}`);
            } // Proceed anyway, but warn
            
            const percent = (numberValue * 100).toFixed(decimalPlaces);
            return `${percent}%`;
        } catch (error) {
            console.error('Error formatting percentage:', value, error);
            return '--%'; // Fallback
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
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            console.error("Toast container #toastContainer not found. Cannot show toast:", message);
            return;
        }
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
        toastContainer.appendChild(toast);

        try {
            const bsToast = new bootstrap.Toast(toast, { delay: 5000 }); // Add delay
            bsToast.show();
        } catch (e) {
            console.error("Error showing bootstrap toast:", e);
            console.log(`Toast (${type}): ${message}`); // Fallback log
        }

        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            if (toast.parentNode === toastContainer) { // Check parent before removing
                 toastContainer.removeChild(toast);
            }
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
        const loadingIndicator = document.getElementById('loading-indicator'); // General page loader
        // Use classList add/remove for hiding/showing loader (assuming d-none class)
        if (loadingIndicator) loadingIndicator.classList.remove('d-none');

        try {
            // Set default options (original state)
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            };

            // Merge options (original state)
            const fetchOptions = { ...defaultOptions, ...options };

            // Fetch data (original state - no special param handling)
            const response = await fetch(url, fetchOptions);

            // Check if response is ok
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    // If response is not JSON
                    errorData = { error: `HTTP error! Status: ${response.status} ${response.statusText}` };
                }
                throw new Error(errorData.error || errorData.message || `HTTP error! Status: ${response.status}`);
            }

            // Get response as text first
            const responseText = await response.text();
            
            // Check if the response is empty
            if (!responseText || responseText.trim() === '') {
                console.warn(`API.fetch: Empty response from ${url}`);
                return {}; // Return empty object
            }
            
            // Try to parse as JSON
            try {
                return JSON.parse(responseText);
            } catch (jsonError) {
                console.error(`API.fetch: JSON parse error for ${url}:`, jsonError, "Raw response:", responseText);
                throw new Error(`Invalid JSON response from server: ${jsonError.message}`);
            }
        } catch (error) {
            console.error('API fetch error:', error);
            // Show error toast
            UI.showToast(`API Error: ${error.message}`, 'danger');
            throw error; // Re-throw to allow caller to handle
        } finally {
            // Hide loading state (original state)
             if (loadingIndicator) loadingIndicator.classList.add('d-none');
        }
    }
};

// Export utilities for global access
window.Formatter = Formatter;
window.Sentiment = Sentiment;
window.UI = UI;
window.API = API;

// Make older function names work for backward compatibility (keep if needed)
window.formatDate = Formatter.date;
window.formatDuration = Formatter.duration;
window.sentimentToText = Sentiment.toText;
window.sentimentToColor = Sentiment.toColor;
window.copyToClipboard = (text) => UI.copyToClipboard(text);

// ==========================================
// Date Utilities
// ==========================================

/**
 * Calculates start and end dates based on a timeframe string.
 * @param {string} timeframe - Timeframe identifier (e.g., 'last_7_days', 'last_30_days', 'all')
 * @returns {Object} Object containing { startDate, endDate } in 'YYYY-MM-DD' format.
 */
function getDatesFromTimeframe(timeframe) {
    const endDate = new Date(); // Today
    let startDate = new Date();
    
    // Helper function to format Date objects to YYYY-MM-DD
    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    switch (timeframe) {
        case 'last_7_days': // Match value from dashboard button
            startDate.setDate(endDate.getDate() - 7);
            break;
        case 'last_30_days': // Match value from dashboard button
            startDate.setDate(endDate.getDate() - 30);
            break;
        case 'last_90_days': // Match value from dashboard button
            startDate.setDate(endDate.getDate() - 90);
            break;
        case 'all_time': // Match value from dashboard button
            // Use a fixed early date (e.g., project start or Unix epoch)
            startDate = new Date(2024, 0, 1); // Example: Jan 1, 2024
            break;
        // Keep compatibility with older usage if necessary (e.g., '7d')
        case '7d':
            startDate.setDate(endDate.getDate() - 7);
            break;
        case '30d':
            startDate.setDate(endDate.getDate() - 30);
            break;
        case '90d':
            startDate.setDate(endDate.getDate() - 90);
            break;
        case 'all':
            startDate = new Date(2024, 0, 1); // Example: Jan 1, 2024
            break;
        default:
            console.warn(`Unrecognized timeframe: ${timeframe}. Defaulting to last 30 days.`);
            startDate.setDate(endDate.getDate() - 30);
            break;
    }

    // Format and return with the original keys
    return {
        startDate: formatDate(startDate),
        endDate: formatDate(endDate)
    };
}

// Expose globally if needed by multiple scripts
window.getDatesFromTimeframe = getDatesFromTimeframe;

// ==========================================
// END Date Utilities
// ========================================== 