console.log("UTILS.JS LOADED - V1");

// Utility functions for formatting and display
if (typeof window.Formatter === 'undefined') { // GUARD
    window.Formatter = {
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
         * Format date objects for display (Date and Time)
         * @param {string} dateString - ISO date string to format
         * @returns {string} Formatted date and time string
         */
        dateTime(dateString) {
            if (!dateString) return 'N/A';
            try {
                const date = new Date(dateString);
                return date.toLocaleString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric', 
                    hour: 'numeric', minute: '2-digit', hour12: true
                });
            } catch (error) {
                console.error('Error formatting dateTime:', dateString, error);
                return dateString; // Fallback
            }
        },

        /**
         * Format date objects for display (Time only)
         * @param {string} dateString - ISO date string to format
         * @returns {string} Formatted time string
         */
        time(dateString) {
            if (!dateString) return 'N/A';
            try {
                const date = new Date(dateString);
                return date.toLocaleTimeString(undefined, {
                    hour: 'numeric', minute: '2-digit', hour12: true
                });
            } catch (error) {
                console.error('Error formatting time:', dateString, error);
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
        },

        /**
         * Format a number using locale-specific settings (e.g., commas).
         * @param {number} value - The number to format.
         * @returns {string} Formatted number string or '--' if invalid.
         */
        number(value) {
            if (value === null || value === undefined || isNaN(value)) {
                return '--'; // Placeholder for invalid input
            }
            try {
                return Number(value).toLocaleString(); // Use default locale
            } catch (error) {
                console.error('Error formatting number:', value, error);
                return '--'; // Fallback
            }
        },

        // ADD Sentiment Label/Class Helpers
        sentimentLabel(score) {
            if (score === null || score === undefined || isNaN(score)) return 'N/A';
            score = Number(score);
            if (score > 0.6) return 'Very Positive';
            if (score > 0.2) return 'Positive';
            if (score >= -0.2) return 'Neutral';
            if (score >= -0.6) return 'Negative';
            return 'Very Negative';
        },
        sentimentColorClass(score) {
            if (score === null || score === undefined || isNaN(score)) return 'secondary'; // Default badge class
            score = Number(score);
            if (score > 0.6) return 'success'; // Very Positive
            if (score > 0.2) return 'success'; // Positive (use success too)
            if (score >= -0.2) return 'warning'; // Neutral
            if (score >= -0.6) return 'danger'; // Negative 
            return 'danger'; // Very Negative (use danger too)
        },
        simpleDate(dateStringYMD) { // Expects 'YYYY-MM-DD'
            if (!dateStringYMD) return 'N/A';
            try {
                // Split the string to avoid timezone issues with `new Date()`
                const parts = dateStringYMD.split('-');
                if (parts.length === 3) {
                    const year = parseInt(parts[0]);
                    const month = parseInt(parts[1]) - 1; // JS months are 0-indexed
                    const day = parseInt(parts[2]);
                    const date = new Date(Date.UTC(year, month, day)); // Use Date.UTC
                    // Format as "Month Day, Year" e.g., "May 14, 2025"
                    return date.toLocaleDateString(undefined, {
                        year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' 
                    });
                }
                return dateStringYMD; // Fallback for unexpected format
            } catch (error) {
                console.error('Error formatting simpleDate:', dateStringYMD, error);
                return dateStringYMD; // Fallback
            }
        }
    };
} // END GUARD

// Sentiment analysis utilities
if (typeof window.Sentiment === 'undefined') { // GUARD
    window.Sentiment = {
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
} // END GUARD

// UI Interaction utilities
if (typeof window.UI === 'undefined') { // GUARD
    window.UI = {
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
        },

        /**
         * Sets the active state for timeframe buttons.
         * @param {string} timeframe - The data-timeframe value of the button to activate.
         */
        setActiveTimeframeButton(timeframe) {
            console.log(`UI.setActiveTimeframeButton called with timeframe: ${timeframe}`);
            const timeframeButtons = document.querySelectorAll('.date-range-btn');
            if (!timeframeButtons.length) {
                console.warn('.date-range-btn elements not found for setActiveTimeframeButton');
                return;
            }
            
            let foundActive = false;
            timeframeButtons.forEach(btn => {
                if (btn.dataset.timeframe === timeframe) {
                    btn.classList.add('active');
                    foundActive = true;
                    console.log(` - Activated button:`, btn);
                } else {
                    btn.classList.remove('active');
                }
            });
            if (!foundActive) {
                 console.warn(`setActiveTimeframeButton: No button found for timeframe '${timeframe}'`);
            }
        }
    };
} // END GUARD

// API interaction utilities
if (typeof window.API === 'undefined') { // GUARD
    window.API = {
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
} // END GUARD

// Function to initialize toast container (needs to be called AFTER DOM is ready)
if (typeof window.initializeToastContainer === 'undefined') { // GUARD
    window.initializeToastContainer = function() {
        // Check if container exists, create if not (though should be in base.html)
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            console.warn('#toastContainer not found, creating it.');
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        } else {
            console.log('#toastContainer found.');
        }
    }
} // END GUARD

// Function to initialize the debug panel (assuming it exists here or is globally available)
if (typeof window.initializeGlobalDebugPanel === 'undefined') { // GUARD
    window.initializeGlobalDebugPanel = function() {
        console.log("Initializing Global Debug Panel...");
        const panel = document.getElementById('debug-panel');
        const closeBtn = document.getElementById('close-debug');

        if (!panel || !closeBtn) {
            console.warn("Debug panel elements not found.");
            return;
        }

        // Toggle visibility with Alt+D
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'd') {
                panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
                console.log(`Debug panel toggled ${panel.style.display === 'block' ? 'ON' : 'OFF'}`);
            }
        });

        // Close button
        closeBtn.addEventListener('click', () => {
            panel.style.display = 'none';
            console.log("Debug panel closed via button.");
        });
        console.log("Global Debug Panel initialized.");
    }
} // END GUARD

// >>> DEFINE initializeGlobalSyncButton HERE <<<
if (typeof window.initializeGlobalSyncButton === 'undefined') { // GUARD
    window.initializeGlobalSyncButton = function() {
         console.log("Initializing Global Sync Button...");
         const actualSyncButton = document.getElementById('sync-button');
         const actualSyncStatus = document.getElementById('sync-status');

         if (actualSyncButton) {
              actualSyncButton.addEventListener('click', async () => {
                   if (actualSyncStatus) actualSyncStatus.textContent = 'Syncing...';
                   actualSyncButton.disabled = true;
                   try {
                        // Use API utility
                        const result = await API.fetch('/api/sync-conversations', { method: 'POST' }); 
                        console.log("Sync result:", result);

                        if (result.status === 'success') {
                             // --- NEW: Populate and show modal --- 
                             const modalElement = document.getElementById('syncStatusModal');
                             if (modalElement) {
                                 document.getElementById('modal-db-initial').textContent = result.initial_db_count;
                                 document.getElementById('modal-db-final').textContent = result.final_db_count;
                                 document.getElementById('modal-added').textContent = result.added;
                                 document.getElementById('modal-updated').textContent = result.updated;
                                 document.getElementById('modal-skipped').textContent = result.skipped;
                                 document.getElementById('modal-checked-api').textContent = result.checked_api;
                                 
                                 const failedSection = document.getElementById('modal-failed-section');
                                 const failedCountSpan = document.getElementById('modal-failed');
                                 if (result.failed > 0) {
                                     failedCountSpan.textContent = result.failed;
                                     failedSection.classList.remove('d-none');
                                 } else {
                                     failedSection.classList.add('d-none');
                                 }

                                 // Use Bootstrap's JS to show the modal
                                 const modal = new bootstrap.Modal(modalElement);
                                 modal.show();
                             } else {
                                 // Fallback to toast if modal element not found
                                 console.error("Sync Status Modal element not found. Falling back to toast.");
                                 let msg = `Sync finished. DB: ${result.initial_db_count}->${result.final_db_count}. Added:${result.added}, Updated:${result.updated}, Skipped:${result.skipped}, Failed:${result.failed}.`;
                                 UI.showToast(msg, 'success', 10000); 
                             }
                             // --- END MODAL LOGIC ---
                             
                             if (actualSyncStatus) actualSyncStatus.textContent = 'Sync Complete';
                             // Removed call to updateTotalCount as it's not defined globally here
                             // if (typeof updateTotalCount === 'function') { ... }
                        } else {
                             throw new Error(result.message || 'Sync failed with unknown error');
                        }
                   } catch (error) {
                        console.error("Sync error:", error);
                        // UI.showToast is handled by API.fetch
                        if (actualSyncStatus) actualSyncStatus.textContent = 'Sync Failed';
                   } finally {
                        actualSyncButton.disabled = false;
                        // Optionally reset status text after a delay
                        setTimeout(() => {
                             if (actualSyncStatus && actualSyncStatus.textContent !== 'Syncing...') { // Avoid clearing if another sync started
                                  actualSyncStatus.textContent = '';
                             }                    }, 5000);
                   }
              });
              console.log("Global sync button initialized.");
         } else {
               console.warn("Global sync button #sync-button not found.");
         }
    }
} // END GUARD

// >>> MOVE initializeGlobalDateRangeSelector definition here <<<
if (typeof window.initializeGlobalDateRangeSelector === 'undefined') { // GUARD
    window.initializeGlobalDateRangeSelector = function(onDateChangeCallback) {
        console.log("Initializing global date range selector [Listeners Only - in utils.js]...");
        const timeframeButtons = document.querySelectorAll('.date-range-btn');
        const dateRangeDisplay = document.getElementById('date-range-display'); // Optional

        if (!timeframeButtons.length) {
            console.warn("Date range buttons (.date-range-btn) not found. Skipping date range initialization.");
            return;
        }

        const initiallyActiveButton = document.querySelector('.date-range-btn.active');
        const buttons = timeframeButtons; // Alias for clarity

        timeframeButtons.forEach(button => {
            console.log(`Attaching listener to date button: ${button.dataset.timeframe}`, button);
            button.addEventListener('click', function(event) {
                // Call handler defined below
                handleTimeframeChange(event, onDateChangeCallback); 
            });
        });

        // Set initial active state (if needed globally, pages might handle their own initial load)
        // Removed the initial call to onDateChangeCallback from here as it should be handled by page-specific logic
        if (!initiallyActiveButton && buttons.length > 0) {
            // Fallback: activate the first button if none are marked active
            buttons[0].classList.add('active');
            console.log("Fallback: Activated first button in global selector");
        } else if (initiallyActiveButton) {
            console.log("Initial active button found in global selector");
        }

        console.log("Global date range listeners attached.");
    }
} // END GUARD

// >>> MOVE handleTimeframeChange definition here <<<
// This function is called when a date range button is clicked.
if (typeof window.handleTimeframeChange === 'undefined') { // GUARD
    window.handleTimeframeChange = function(event, loadDataCallback) {
        console.log("handleTimeframeChange triggered!"); 
        const clickedButton = event.target.closest('.date-range-btn');
        if (!clickedButton) return; // Ignore clicks not on a button

        const timeframe = clickedButton.dataset.timeframe;
        if (!timeframe) return;

        console.log(`Date range button clicked: ${timeframe}`);

        // Remove active class from all buttons in this group
        const parentGroup = clickedButton.closest('.btn-group');
        if (parentGroup) {
            parentGroup.querySelectorAll('.date-range-btn').forEach(btn => btn.classList.remove('active'));
        }
        // Add active class to the clicked button
        clickedButton.classList.add('active');

        // Trigger the data loading callback if provided
        if (typeof loadDataCallback === 'function') {
            console.log(`Calling loadDataCallback with timeframe: ${timeframe}`);
            loadDataCallback(timeframe);
        } else {
            console.warn("loadDataCallback is not a function or was not provided to handleTimeframeChange.");
        }
    }
} // END GUARD

// ==========================================
// Date Utilities
// ==========================================
if (typeof window.getDatesFromTimeframe === 'undefined') { // GUARD
    window.getDatesFromTimeframe = function(timeframe) {
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
} // END GUARD

// ==========================================
// END Date Utilities
// ========================================== 

// Call Initialization on DOMContentLoaded within utils.js itself
// Ensure this listener only runs once
if (!window.utilsJsDOMLoaded) {
    document.addEventListener('DOMContentLoaded', () => {
        console.log("UTILS.JS: DOMContentLoaded - Initializing Toast, Debug, Sync & Date Range");
        if(typeof initializeToastContainer === 'function') initializeToastContainer();
        if(typeof initializeGlobalDebugPanel === 'function') initializeGlobalDebugPanel();
        if(typeof initializeGlobalSyncButton === 'function') initializeGlobalSyncButton(); 
        if(typeof initializeGlobalDateRangeSelector === 'function') initializeGlobalDateRangeSelector(null); // Attach listeners globally
    });
    window.utilsJsDOMLoaded = true;
} 