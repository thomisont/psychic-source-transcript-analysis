import { Conversation } from 'https://esm.sh/@11labs/client@0.1.4';

console.log('[VoiceSDK] Module loaded');

// Ensure the global instance tracker exists only once
if (typeof window._drawerConvoInstance === 'undefined') {
    window._drawerConvoInstance = null;
}

// --- Central Voice Session Manager ---
// This runs only once and listens for custom events
if (!window._voiceSessionManagerInitialized) {
    console.log('[VoiceSDK Manager] Initializing Voice Session Manager...');
    let isProcessingToggle = false; // Prevent rapid toggles

    // Listener for the custom event to toggle the session
    document.addEventListener('toggleVoiceSession', async (event) => {
        console.log('[VoiceSDK Manager] Received toggleVoiceSession event');
        if (isProcessingToggle) {
            console.warn('[VoiceSDK Manager] Already processing a toggle request, ignoring.');
            return;
        }
        isProcessingToggle = true;

        const agentId = event.detail?.agentId;
        const micBtn = event.detail?.micBtn;
        const statusLabel = event.detail?.statusLabel;
        const transcriptArea = event.detail?.transcriptArea;

        if (!agentId || !micBtn || !statusLabel) {
            console.error('[VoiceSDK Manager] Missing detail in toggleVoiceSession event.');
            isProcessingToggle = false;
            return;
        }

        statusLabel.textContent = 'Processing...';
        micBtn.disabled = true;

        try {
            if (!window._drawerConvoInstance) {
                console.log(`[VoiceSDK Manager] No active session, attempting to start for ${agentId}...`);
                // Call the separate init function (defined below)
                await initializeNewConversation(agentId, micBtn, statusLabel, transcriptArea);
                 // State handled by callbacks within initializeNewConversation
            } else {
                console.log(`[VoiceSDK Manager] Active session found, attempting to end for ${agentId}...`);
                await window._drawerConvoInstance.endSession();
                console.log(`[VoiceSDK Manager] endSession call initiated via manager for ${agentId}.`);
                // Explicitly clear instance and flag here after calling endSession,
                // as onDisconnect might be slow and allow a new session to start.
                window._drawerConvoInstance = null;
                localStorage.setItem('voiceSessionWasActive', 'false');
                console.log('[VoiceSDK Manager] Cleared global instance and flag immediately after endSession call.');
            }
        } catch (err) {
            console.error(`[VoiceSDK Manager] Error during toggle handling for ${agentId}:`, err);
            statusLabel.textContent = 'Error! Tap to retry';
            // Ensure state is reset on error
            micBtn.classList.remove('recording');
            localStorage.setItem('voiceSessionWasActive', 'false');
        } finally {
             micBtn.disabled = false; // Always re-enable button
             isProcessingToggle = false; // Allow next toggle
        }
    });

    console.log('[VoiceSDK Manager] Voice Session Manager initialized and listener attached.');
    window._voiceSessionManagerInitialized = true;
}

// Separate function to initialize a *new* conversation (called by manager or auto-init)
async function initializeNewConversation(agentId, micBtn, statusLabel, transcriptArea) {
     console.log(`[VoiceSDK Init] Starting NEW conversation for ${agentId}...`);
     let newConvo = null;

     // Make sure any previous instance ref is cleared before starting
     // This prevents potential race conditions if disconnect was slow
     window._drawerConvoInstance = null;
     localStorage.setItem('voiceSessionWasActive', 'false');

     try {
        // 1. Ensure microphone permission
         try {
             await navigator.mediaDevices.getUserMedia({ audio: true });
         } catch (permErr) {
             console.error('[VoiceSDK Init] Microphone permission error:', permErr);
             statusLabel.textContent = 'Mic needed!';
             alert('Microphone access is required. Please grant permission and click the mic again.');
             throw permErr; 
         }

         // 2. Prepare session options (fetch token/signed URL)
         const opts = {};
         let signedUrlFetched = false;
         try {
             const suResp = await fetch(`/api/voice-sdk/signed-url/${agentId}`);
             if (suResp.ok) {
                 const suData = await suResp.json();
                 if (suData.signed_url) {
                     opts.signedUrl = suData.signed_url;
                     signedUrlFetched = true;
                     console.log(`[VoiceSDK Init] Using signedUrl for ${agentId}`);
                 }
             }
             if (!signedUrlFetched) {
                 console.warn(`[VoiceSDK Init] No signed URL for ${agentId}, falling back.`);
             }
         } catch (e) {
              console.warn(`[VoiceSDK Init] Error fetching signed URL for ${agentId}:`, e);
         }

         if (!signedUrlFetched) {
             opts.agentId = agentId;
             // Optional API key fetch logic remains the same
             try {
                const tokenResp = await fetch('/api/voice-sdk/token');
                if (tokenResp.ok) {
                    const tokenData = await tokenResp.json();
                    if (tokenData.token) opts.apiKey = tokenData.token;
                }
             } catch (tokErr) { console.warn(`[VoiceSDK Init] Token fetch error:`, tokErr); }
         }

        // 3. Start the session
         newConvo = await Conversation.startSession({
             ...opts,
             onConnect: () => {
                 console.log(`[VoiceSDK Init] Connected: ${agentId}`);
                 micBtn.classList.add('recording');
                 statusLabel.textContent = 'Listening... (Tap to stop)';
                 if (transcriptArea) transcriptArea.innerHTML = ''; 
                 micBtn.disabled = false; 
                 // Session is live - CONFIRM instance is stored and set flag
                 if (window._drawerConvoInstance === newConvo) { // Confirm it's the one we just created
                     localStorage.setItem('voiceSessionWasActive', 'true');
                     console.log('[VoiceSDK Init] Drawer session confirmed active. Flag set.');
                 } else {
                     console.warn('[VoiceSDK Init] onConnect fired but global instance doesn\'t match? Overwriting.');
                     window._drawerConvoInstance = newConvo; // Ensure it's set anyway
                     localStorage.setItem('voiceSessionWasActive', 'true');
                 }
             },
             onError: (e) => {
                 console.error(`[VoiceSDK Init] Session Error (${agentId}):`, e);
                 statusLabel.textContent = 'Error! Tap to retry';
                 micBtn.classList.remove('recording');
                 micBtn.disabled = false;
                 window._drawerConvoInstance = null; // Clear global instance
                 localStorage.setItem('voiceSessionWasActive', 'false');
                 console.log('[VoiceSDK Init] Drawer session INACTIVE (error). Instance cleared.');
             },
             onMessage: (msg) => {
                 // ... (same message handling) ...
                 if (transcriptArea && msg) {
                    if (msg.type === 'user_transcript' && msg.user_transcription_event?.user_transcript) {
                        transcriptArea.innerHTML = `<strong>You:</strong> ${msg.user_transcription_event.user_transcript}`;
                    }
                    if (msg.type === 'agent_response' && msg.agent_response_event?.agent_response) {
                        transcriptArea.innerHTML += `<br><strong>Lily:</strong> ${msg.agent_response_event.agent_response}`;
                        transcriptArea.scrollTop = transcriptArea.scrollHeight; 
                    }
                 }
             },
             onModeChange: (m) => {
                 // Update label only if connection is active (check instance)
                 if(window._drawerConvoInstance) {
                    statusLabel.textContent = m.mode === 'speaking' ? 'Agent speaking... (Tap to stop)' : 'Listening... (Tap to stop)';
                 }
             },
             onDisconnect: () => {
                 console.log(`[VoiceSDK Init] Disconnected: ${agentId}`);
                 statusLabel.textContent = 'Tap to talk';
                 micBtn.classList.remove('recording');
                 micBtn.disabled = false;
                 window._drawerConvoInstance = null; // Clear global instance
                 localStorage.setItem('voiceSessionWasActive', 'false');
                 console.log('[VoiceSDK Init] Drawer session INACTIVE (disconnect). Instance cleared.');
             }
         });
         // Assign to global instance IMMEDIATELY after session starts
         window._drawerConvoInstance = newConvo;
         console.log(`[VoiceSDK Init] Conversation object created and assigned to global instance for ${agentId}. Waiting for onConnect.`);
         // Don't return convo here, callbacks handle state update
     } catch (initErr) {
         console.error(`[VoiceSDK Init] CRITICAL ERROR initializing session for ${agentId}:`, initErr);
         statusLabel.textContent = 'Failed to start';
         micBtn.disabled = false; 
         window._drawerConvoInstance = null; // Ensure cleared on failure
         localStorage.setItem('voiceSessionWasActive', 'false');
         throw initErr; // Propagate error
     }
}


// Centralized function to attach event handlers to a voice card
// Now *only* attaches the click listener that dispatches the custom event
function attachHandlers(card) { // REMOVED async as it doesn't await now
    if (card._voiceBound) { 
        return; 
    } 
    
    const agentId = card.dataset.agentId;
    const micBtn = card.querySelector('.voice-mic-btn');
    const statusLabel = card.querySelector('.voice-status-label');
    const transcriptArea = card.querySelector('.voice-transcript-area');
    let isDrawerCard = card.closest('#voice-drawer');

    if (!agentId || !micBtn || !statusLabel) {
        console.warn('[VoiceSDK Attach] Skipping card - missing required elements. Card:', card);
        return;
    }

    // Attach the single click listener to the mic button
    micBtn.addEventListener('click', (e) => {
        e.preventDefault();
        console.log(`[VoiceSDK Attach] Mic button clicked for ${agentId}. Dispatching toggleVoiceSession event.`);
        // Dispatch custom event with necessary details
        document.dispatchEvent(new CustomEvent('toggleVoiceSession', { 
            detail: { 
                agentId: agentId, 
                micBtn: micBtn, 
                statusLabel: statusLabel,
                transcriptArea: transcriptArea
                // Pass any other elements the manager needs
            }
        }));
    });

    card._voiceBound = true; // Mark as bound
    console.log(`[VoiceSDK Attach] Event dispatcher attached for agent ${agentId}`);

    // *** REVISED Auto-initiation check ***
    // Log the state *before* the check
    console.log(`[VoiceSDK Attach] Auto-init check for ${agentId}. DrawerOpen: ${localStorage.getItem('voiceDrawerIsOpen')}, SessionActive: ${localStorage.getItem('voiceSessionWasActive')}, LiveInstance: ${!!window._drawerConvoInstance}`);
    
    if (isDrawerCard && 
        localStorage.getItem('voiceDrawerIsOpen') === 'true' && 
        localStorage.getItem('voiceSessionWasActive') === 'true' && 
        !window._drawerConvoInstance) { // CHECK the GLOBAL instance
        
        console.log(`[VoiceSDK Attach] Drawer open, session was active, NO live global connection. Auto-initiating connection for ${agentId}...`);
        // Wrap in try/catch to prevent blocking other UI
        (async () => { 
            try {
                // Directly call the new init function
                await initializeNewConversation(agentId, micBtn, statusLabel, transcriptArea);
            } catch (autoInitErr) {
                 console.error('[VoiceSDK Attach] Error during auto-initiation:', autoInitErr);
            }
        })();
    }
}

// --- Global Binding Logic --- 
function bindAllVoiceCards() {
    console.log('[VoiceSDK] bindAllVoiceCards running...');
    if (typeof Conversation === 'undefined' || typeof Conversation.startSession !== 'function') {
        console.error('[VoiceSDK] Conversation class not ready yet.');
        return;
    }
    document.querySelectorAll('.voice-card[data-agent-id]').forEach(attachHandlers);
}

// --- Initialization --- 

// Wait for the DOM to be ready before binding initial cards
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[VoiceSDK] DOMContentLoaded fired. Running initial bindAllVoiceCards.');
        bindAllVoiceCards();
    });
} else {
    console.log('[VoiceSDK] DOM already loaded. Running initial bindAllVoiceCards.');
    bindAllVoiceCards(); // DOM already loaded
}

// Use MutationObserver to handle dynamically added cards (e.g., in modals/drawers)
// Initialize observer
/* // --- TEMPORARILY DISABLE MutationObserver ---
function initializeVoiceObserver() {
     console.log('[VoiceSDK] Initializing MutationObserver...');
     if (typeof Conversation === 'undefined') {
          console.error('[VoiceSDK] CRITICAL: Cannot initialize MutationObserver because Conversation class is not defined.');
          return;
     }
     if (!window.voiceObserver) { // Initialize observer only once
          window.voiceObserver = new MutationObserver((mutationsList) => {
              console.log('[VoiceSDK] DOM changed, re-running bindAllVoiceCards...');
              bindAllVoiceCards(); 
          });
          window.voiceObserver.observe(document.body, { childList: true, subtree: true });
          console.log('[VoiceSDK] MutationObserver initialized successfully.');
     } else {
          console.log('[VoiceSDK] MutationObserver already initialized.');
     }
}

// Wait slightly before initializing observer
// Increased delay slightly to ensure module is definitely ready
setTimeout(initializeVoiceObserver, 750); 
*/ // --- END TEMPORARY DISABLE --- 


// --- NEW: Accordion Listener --- 
// Explicitly re-bind cards when the Agent Admin accordion opens
document.addEventListener('DOMContentLoaded', () => {
    const adminAccordionBody = document.getElementById('collapseAdmin');
    if (adminAccordionBody) {
        console.log('[VoiceSDK] Found Admin Accordion Body. Attaching shown.bs.collapse listener.');
        adminAccordionBody.addEventListener('shown.bs.collapse', () => {
            console.log('[VoiceSDK] Agent Admin accordion shown. Re-running bindAllVoiceCards.');
            bindAllVoiceCards();
        });
    } else {
        console.warn('[VoiceSDK] Could not find #collapseAdmin to attach accordion listener.');
    }
});

// --- NEW: Beforeunload listener --- 
// Attempt to end session gracefully if drawer session is active when navigating away
window.addEventListener('beforeunload', () => {
    console.log('[VoiceSDK] beforeunload event triggered.');
    if (localStorage.getItem('voiceSessionWasActive') === 'true') {
        console.log('[VoiceSDK] Clearing active session flag on page unload.');
        localStorage.setItem('voiceSessionWasActive', 'false');
    }
});

// console.log('[VoiceSDK] End of script execution (module).'); 