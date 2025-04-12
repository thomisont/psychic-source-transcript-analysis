console.log("MAIN.JS LOADED - V7 - Refactored");
/**
 * Main JavaScript file for Psychic Source Transcript Analysis Tool
 * Contains primarily global initialization and page-specific logic dispatch.
 * Utility functions are in utils.js
 * Dashboard functions are in dashboard.js
 * Transcript Viewer functions are in transcript_viewer.js
 */

// Utility functions are now in utils.js
// They are globally available via window.Formatter, window.Sentiment, window.UI, window.API, window.getDatesFromTimeframe

// Global variable for current conversation ID (used by export)
// This might need a better state management solution if used across modules
let currentConversationId = null;

// ==========================================
// Global Date Range Selector Logic (If needed globally)
// ==========================================

/**
 * Initializes the global date range selector buttons.
 * Assumes buttons with class .date-range-btn and data-timeframe attribute exist.
 * Calls the callback with the selected timeframe key.
 * @param {Function} onDateChangeCallback - Function to call when a timeframe button is clicked.
 */
function initializeGlobalDateRangeSelector(onDateChangeCallback) {
    console.log("Initializing global date range selector [Listeners Only]...");
    const timeframeButtons = document.querySelectorAll('.date-range-btn');
    const dateRangeDisplay = document.getElementById('date-range-display'); // Optional

    if (!timeframeButtons.length) {
        console.warn("Date range buttons (.date-range-btn) not found. Skipping date range initialization.");
        return;
    }

    timeframeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Update visual state
            timeframeButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const timeframe = this.dataset.timeframe;
            console.log("Date range button clicked:", timeframe);

            // Store in session storage
            sessionStorage.setItem('selectedTimeframe', timeframe);

            // Update optional display
            if (dateRangeDisplay) {
                const friendlyName = this.textContent;
                dateRangeDisplay.textContent = friendlyName;
            }

            // Call the page-specific callback
            if (typeof onDateChangeCallback === 'function') {
                onDateChangeCallback(timeframe);
            } else {
                console.error("onDateChangeCallback is not a function or was not provided.");
            }
        });
    });

    // --- Removed logic for triggering initial load --- 
    // The page-specific script is now responsible for its own initial load.

    console.log("Global date range listeners attached.");
}

window.initializeGlobalDateRangeSelector = initializeGlobalDateRangeSelector;

// ==========================================
// Dashboard Specific Logic (REMOVED - Now in dashboard.js)
// ==========================================

// ==========================================
// Transcript Viewer / Data Selection Specific Functions (REMOVED - Now in transcript_viewer.js)
// ==========================================

// ==========================================
// Themes & Sentiment Page Specific Functions
// ==========================================

// This section will likely be refactored or replaced by themes_sentiment.js
// ... (placeholder for any remaining functions specific to this page, if any)


// ==========================================
// Engagement Metrics Page Specific Functions
// ==========================================

// This section will likely be refactored or replaced by engagement_metrics.js
// ... (placeholder for any remaining functions specific to this page, if any)


// ==========================================
// Global Initialization & Event Listeners (Remaining)
// ==========================================

// >>> DEFINE initializeGlobalSyncButton <<<
function initializeGlobalSyncButton() {
     const syncButton = document.getElementById('global-sync-button'); // Corrected ID?
     const syncStatus = document.getElementById('global-sync-status'); // Corrected ID?

     // Check base.html for correct IDs, e.g., #sync-button, #sync-status
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
                         if (typeof updateTotalCount === 'function') {
                            updateTotalCount(result.final_db_count);
                         }
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
                         }
                    }, 5000);
               }
          });
          console.log("Global sync button initialized.");
     } else {
          // console.log("Global sync button #sync-button not found.");
     }
}

// >>> DEFINE updateTotalCount - Global version? <<<
// This updates a potential global display of total conversations in the DB
// Ensure the element ID is correct and exists in base.html or relevant templates
function updateTotalCount(count) {
    const element = document.getElementById('total-conversations-db'); // Example ID
    if (element) {
         element.textContent = `Total Conversations (DB): ${count !== null ? count : 'N/A'}`;
    } else {
        // console.warn("#total-conversations-db element not found for global update.");
    }
}

// --- Main Initialization Logic (Revised) ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed. Running main initializations.");

    // Initialize components common to all pages
    initializeGlobalSyncButton();
    updateApiStatus(); // Fetch initial API status

    // Page-specific initializations are now handled by including the specific JS file 
    // (e.g., dashboard.js, transcript_viewer.js) which contain their own 
    // DOMContentLoaded listeners.

});

// ==========================================
// API Status Check
// ==========================================

// Function to fetch and update API status indicators
// This remains global as status might be shown on multiple pages or in the header
async function updateApiStatus() {
    console.log("Fetching API status...");
    const statusUrl = '/api/status'; // Ensure this endpoint exists and is correct

    // Use global API utility
    if (typeof API === 'undefined') {
        console.error("API utility is not defined. Cannot fetch status.");
        return;
    }

    const setStatus = (elementId, text, isConnected) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
            element.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-secondary');
            if (isConnected === true) {
                element.classList.add('bg-success');
            } else if (isConnected === false) {
                element.classList.add('bg-danger');
            } else { // Use warning for indeterminate/error states
                 element.classList.add('bg-warning');
            }
        } else {
             // console.warn(`Status element #${elementId} not found.`);
        }
    };

    try {
        const statusData = await API.fetch(statusUrl);
        console.log("API Status data received:", statusData);

        // Update status badges (ensure IDs exist in base.html or relevant templates)
        setStatus('databaseStatus', statusData.database?.message || 'Unknown', statusData.database?.status === 'connected');
        setStatus('elevenlabsStatus', statusData.elevenlabs?.message || 'Unknown', statusData.elevenlabs?.status === 'connected');
        setStatus('analysisStatus', statusData.analysis?.message || 'Unknown', statusData.analysis?.status === 'available');
        setStatus('supabaseStatus', statusData.supabase?.message || 'Unknown', statusData.supabase?.status === 'connected');

        // Update global total count if the function exists
        if (typeof updateTotalCount === 'function') {
            if (statusData.total_conversations !== undefined) {
                 updateTotalCount(statusData.total_conversations);
            } else {
                 console.warn("Total conversations count missing from API status response.");
                 updateTotalCount(null); // Show N/A
            }
        } else {
             console.warn("updateTotalCount function not defined globally.");
        }

    } catch (error) {
        console.error("Failed to fetch API status:", error);
        // Set all to error state
        setStatus('databaseStatus', `Error`, null);
        setStatus('elevenlabsStatus', 'Error', null);
        setStatus('analysisStatus', 'Error', null);
        setStatus('supabaseStatus', 'Error', null);
        if (typeof updateTotalCount === 'function') {
             updateTotalCount(null); // Show N/A on error
        }
    }
}


// Export button functionality (assuming it might be used globally or on multiple pages)
// This can stay global if the modal/button is in base.html
document.addEventListener('click', async (event) => {
    if (event.target.matches('#export-json, #export-csv, #export-markdown')) {
        // Use the globally scoped currentConversationId
        if (!currentConversationId) { 
            if (window.UI) UI.showToast('No conversation selected for export.', 'warning');
            return;
        }
        
        const format = event.target.id.split('-')[1]; // json, csv, or markdown
        const button = event.target;
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Exporting...';

        try {
            // Use native fetch as API utility might not be needed here unless we want global loading indicator
            const response = await fetch(`/api/export/${currentConversationId}?format=${format}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: `HTTP ${response.status}` }));
                throw new Error(errorData.message || `Failed to export conversation`);
            }

            const blob = await response.blob();
            const filename = response.headers.get('Content-Disposition')?.split('filename=')[1] || `${currentConversationId}.${format}`;
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename.replace(/"/g, ''); // Clean filename
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            if (window.UI) UI.showToast(`Conversation exported as ${format}`, 'success');

        } catch (error) {
            console.error(`Export failed for format ${format}:`, error);
            if (window.UI) UI.showToast(`Export failed: ${error.message}`, 'danger');
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
});

// Final check: Ensure DOMContentLoaded listeners inside page-specific files 
// correctly identify their page and execute.

