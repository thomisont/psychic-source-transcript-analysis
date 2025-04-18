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
    // +++ Add Debug Log +++
    console.log("DEBUG (main.js): ENTERING initializeGlobalDateRangeSelector function.");
    // +++ End Debug Log +++
    console.log("Initializing global date range selector [Listeners Only]...");
    const timeframeButtons = document.querySelectorAll('.date-range-btn');
    const dateRangeDisplay = document.getElementById('date-range-display'); // Optional

    if (!timeframeButtons.length) {
        console.warn("Date range buttons (.date-range-btn) not found. Skipping date range initialization.");
        return;
    }

    // *** DEFINE initiallyActiveButton earlier ***
    const initiallyActiveButton = document.querySelector('.date-range-btn.active');
    const buttons = timeframeButtons; // Alias for clarity in later fallback

    timeframeButtons.forEach(button => {
        // *** ADD LOG ***
        console.log(`Attaching listener to date button: ${button.dataset.timeframe}`, button);
        button.addEventListener('click', function(event) { // Pass event to handler
            // Use the specific handler function defined below
            handleTimeframeChange(event, onDateChangeCallback); 
        });
    });

    // Set initial active state (now variable is defined)
    if (initiallyActiveButton) {
        // initiallyActiveButton.classList.add('active'); // Already has class
        console.log("Initial active button found in global selector");
        // Trigger initial load *only* if a callback is provided
        if (onDateChangeCallback) { 
            const initialTimeframe = initiallyActiveButton.dataset.timeframe || 'last_30_days';
            console.log(`Triggering initial load via callback with timeframe: ${initialTimeframe}`);
            onDateChangeCallback(initialTimeframe);
        } else {
             console.log("No initial load callback provided to global date selector.");
        }
    } else if (buttons.length > 0) {
        // Fallback: activate the first button if none are marked active
        buttons[0].classList.add('active');
        console.log("Fallback: Activated first button in global selector");
        if (onDateChangeCallback) {
            const initialTimeframe = buttons[0].dataset.timeframe || 'last_30_days';
            console.log(`Triggering initial load via callback with timeframe: ${initialTimeframe}`);
            onDateChangeCallback(initialTimeframe);
        }
    }

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
async function updateApiStatus() {
    console.log("Fetching API status...");
    const statusUrl = '/api/status';
    if (typeof API === 'undefined') {
        console.error("API utility is not defined. Cannot fetch status.");
        return;
    }

    // NEW: Function to update icon class based on status
    const setIconStatus = (iconId, isConnected) => {
        const iconElement = document.getElementById(iconId);
        // Only log if the element is actually found
        if (iconElement) {
            console.log(`[setIconStatus] Target: #${iconId}, Element found: true, isConnected: ${isConnected}`);
        } else {
            // Silently return if the element doesn't exist on this page
            return;
        }
        
        if (iconElement) {
            console.log(`[setIconStatus] Current classes for #${iconId} (before change): ${iconElement.className}`); // Log current classes BEFORE change
            // Ensure initial placeholder class is also removed
            iconElement.classList.remove('bi-check-circle-fill', 'bi-x-circle-fill', 'bi-question-circle', 'text-success', 'text-danger', 'text-warning');
            if (isConnected === true) {
                iconElement.classList.add('bi-check-circle-fill', 'text-success');
            } else if (isConnected === false) {
                iconElement.classList.add('bi-x-circle-fill', 'text-danger');
            } else { // null or other indicates warning/unknown
                iconElement.classList.add('bi-question-circle', 'text-warning');
            }
            // ADDED LOG: Confirm classes after modification
            console.log(`[setIconStatus] Final classes for #${iconId} (after change): ${iconElement.className}`);
        } else {
            // console.warn(`Status icon #${iconId} not found.`);
        }
    };

    try {
        const statusData = await API.fetch(statusUrl);
        // Log raw data safely
        try {
             console.log("API Status raw data received:", JSON.stringify(statusData)); 
        } catch (e) {
            console.error("Could not stringify statusData:", statusData, e);
        }

        // Log specific status values being checked safely
        console.log(`Checking DB status: ${statusData?.database?.status ?? 'N/A'}`);
        console.log(`Checking EL status: ${statusData?.elevenlabs?.status ?? 'N/A'}`);
        console.log(`Checking AN status: ${statusData?.analysis?.status ?? 'N/A'}`);
        console.log(`Checking SB status: ${statusData?.supabase?.status ?? 'N/A'}`);
        console.log(`Checking OA status: ${statusData?.openai?.status ?? 'N/A'}`);

        // Update status icons using the new function and IDs
        setIconStatus('databaseStatusIcon', statusData?.database?.status === 'connected');
        setIconStatus('elevenlabsStatusIcon', statusData?.elevenlabs?.status === 'connected');
        setIconStatus('analysisStatusIcon', statusData?.analysis?.status === 'available'); // Note: Check for 'available'
        setIconStatus('supabaseStatusIcon', statusData?.supabase?.status === 'connected');
        setIconStatus('openaiStatusIcon', statusData?.openai?.status === 'available'); // Added OpenAI check (assuming 'available')

        // Update global total count (remains the same)
        if (typeof updateTotalCount === 'function') {
            if (statusData.total_conversations !== undefined) {
                 updateTotalCount(statusData.total_conversations);
            } else {
                 console.warn("Total conversations count missing from API status response.");
                 updateTotalCount(null);
            }
        } else {
             console.warn("updateTotalCount function not defined globally.");
        }

    } catch (error) {
        console.error("Failed to fetch API status:", error);
        // Set all icons to error state
        setIconStatus('databaseStatusIcon', false);
        setIconStatus('elevenlabsStatusIcon', false);
        setIconStatus('analysisStatusIcon', false);
        setIconStatus('supabaseStatusIcon', false);
        setIconStatus('openaiStatusIcon', null); // Set OpenAI to unknown/warning on general error
        if (typeof updateTotalCount === 'function') {
             updateTotalCount(null); // Show N/A on error
        }
    }
}

// Final check: Ensure DOMContentLoaded listeners inside page-specific files 
// correctly identify their page and execute.

// --- Shared Event Handler ---
// This function is called when a date range button is clicked.
function handleTimeframeChange(event, loadDataCallback) {
    // *** ADD LOG ***
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
        console.warn("loadDataCallback is not a function or was not provided.");
    }
}

