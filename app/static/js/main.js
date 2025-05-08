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
if (typeof window.currentConversationId === 'undefined') {
    window.currentConversationId = null;
}

// ==========================================
// Global Date Range Selector Logic (MOVED TO UTILS.JS)
// ==========================================

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

// >>> REMOVE initializeGlobalSyncButton definition (moved to utils.js) <<<

// >>> REMOVE updateTotalCount definition (not used globally here) <<<

// ==========================================
// Persistent Voice Drawer Logic 
// ==========================================
if (typeof window.initializePersistentVoiceDrawer === 'undefined') {
    window.initializePersistentVoiceDrawer = function() {
        console.log("[Drawer Init] Running initializePersistentVoiceDrawer..."); // Log Entry
        const drawer = document.getElementById('voice-drawer');
        const trigger = document.getElementById('voice-drawer-trigger');
        const closeBtn = document.getElementById('voice-drawer-close-btn');

        // Log element finding results
        console.log(`[Drawer Init] Drawer found: ${!!drawer}`);
        console.log(`[Drawer Init] Trigger found: ${!!trigger}`);
        console.log(`[Drawer Init] Close Btn found: ${!!closeBtn}`);

        if (!drawer || !trigger || !closeBtn) {
            console.warn("[Drawer Init] Voice drawer elements missing. Feature disabled.");
            return;
        }

        const storageKey = 'voiceDrawerIsOpen';

        // Check initial state from localStorage
        if (localStorage.getItem(storageKey) === 'true') {
            drawer.classList.add('drawer-open');
            console.log("Voice drawer initially open based on localStorage.");
        } else {
            drawer.classList.remove('drawer-open');
        }

        // Trigger button opens/closes
        trigger.addEventListener('click', () => {
            console.log("[Drawer Trigger] Click detected!"); // Log Click
            const isOpen = drawer.classList.toggle('drawer-open');
            localStorage.setItem(storageKey, isOpen);
            console.log(`[Drawer Trigger] Drawer class toggled. New state: ${isOpen}`);
            // Potentially trigger voice SDK initialization *if* opening and not already init
            // e.g., if (isOpen && typeof initializeVoiceSdkIfNeeded === 'function') { initializeVoiceSdkIfNeeded(); }
        });

        // Close button closes
        closeBtn.addEventListener('click', () => {
            console.log("[Drawer Close] Click detected!"); // Log Click
            drawer.classList.remove('drawer-open');
            localStorage.setItem(storageKey, 'false');
            console.log("Voice drawer closed via button.");
            // Potentially trigger voice SDK endSession if needed
        });

        // Optional: Close on Escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && drawer.classList.contains('drawer-open')) {
                console.log("[Drawer Escape] Escape key detected while open."); // Log Escape
                closeBtn.click(); // Simulate click on close button
            }
        });

        // Optional: Close on click outside (more complex, might skip for now)
        /*
        document.addEventListener('click', (event) => {
            if (drawer.classList.contains('drawer-open') && 
                !drawer.contains(event.target) && 
                !trigger.contains(event.target)) {
                closeBtn.click();
            }
        });
        */
       console.log("Persistent Voice Drawer initialized.");
    }
}

// ==========================================
// Initialization on DOMContentLoaded
// ==========================================
// Prevent multiple runs of this listener too
if (!window.mainJsDOMLoaded) {
    document.addEventListener('DOMContentLoaded', () => {
        console.log("MAIN.JS: DOMContentLoaded");
        // Initialize global features
        // initializeGlobalDateRangeSelector(); // REMOVE THIS CALL (now in utils.js)
        if(typeof initializePersistentVoiceDrawer === 'function') initializePersistentVoiceDrawer(); 
        if(typeof updateApiStatus === 'function') updateApiStatus(); // Fetch initial API status

        console.log("Global initializations complete (main.js).");
    });
    window.mainJsDOMLoaded = true;
}

// ==========================================
// API Status Check
// ==========================================

// Function to fetch and update API status indicators
if (typeof window.updateApiStatus === 'undefined') {
    window.updateApiStatus = async function() {
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
}

// Final check: Ensure DOMContentLoaded listeners inside page-specific files 
// correctly identify their page and execute.

// --- REMOVE Shared Event Handler handleTimeframeChange (moved to utils.js) ---

