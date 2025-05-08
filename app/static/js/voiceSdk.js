import { Conversation } from 'https://esm.sh/@11labs/client@0.1.4';

console.log('[VoiceSDK] Module loaded');

// Centralized function to attach event handlers to a voice card
async function attachHandlers(card) {
    if (card._voiceBound) { 
        // console.log(`[VoiceSDK] Card already bound: ${card.dataset.agentId}`);
        return; 
    } 
    
    const agentId = card.dataset.agentId;
    const micBtn = card.querySelector('.voice-mic-btn');
    const statusLabel = card.querySelector('.voice-status-label');
    const transcriptArea = card.querySelector('.voice-transcript-area'); // Optional
    let recording = false; // Track state locally
    let isDrawerCard = card.closest('#voice-drawer'); // Check if this card is inside the drawer

    if (!agentId || !micBtn || !statusLabel) {
        console.warn('[VoiceSDK] Skipping card - missing required elements (agentId, micBtn, statusLabel). Card:', card);
        return;
    }

    // console.log(`[VoiceSDK] Attaching handlers to card for agent: ${agentId}`);

    let convo = null;

    async function initConversation() {
        if (convo) {
            console.log(`[VoiceSDK] Conversation already exists for ${agentId}`);
            return convo;
        }
        console.log(`[VoiceSDK] Initializing conversation for ${agentId}...`);
        statusLabel.textContent = 'Connecting...';
        micBtn.disabled = true; // Disable while initializing

        try {
            // 1. Ensure microphone permission
            try {
                await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (permErr) {
                console.error('[VoiceSDK] Microphone permission error:', permErr);
                statusLabel.textContent = 'Mic needed!';
                alert('Microphone access is required. Please grant permission and click the mic again.');
                throw permErr; // Stop initialization
            }

            // 2. Prepare session options (fetch token/signed URL)
            const opts = {};
            let signedUrlFetched = false;
            try {
                 // Prefer signed URL if available
                 const suResp = await fetch(`/api/voice-sdk/signed-url/${agentId}`);
                 if (suResp.ok) {
                     const suData = await suResp.json();
                     if (suData.signed_url) {
                         opts.signedUrl = suData.signed_url;
                         signedUrlFetched = true;
                         console.log(`[VoiceSDK] Using signedUrl for ${agentId}`);
                     }
                 }
                 if (!signedUrlFetched) {
                      console.warn(`[VoiceSDK] No signed URL for ${agentId}, falling back to agentId/API key.`);
                 }
            } catch (e) {
                 console.warn(`[VoiceSDK] Error fetching signed URL for ${agentId}:`, e);
            }

            // Fallback or default: Use agentId and fetch API key if no signed URL
            if (!signedUrlFetched) {
                opts.agentId = agentId;
                try {
                    const tokenResp = await fetch('/api/voice-sdk/token');
                    if (tokenResp.ok) {
                        const tokenData = await tokenResp.json();
                        if (tokenData.token) {
                            opts.apiKey = tokenData.token; // Correct option name is apiKey
                            console.log(`[VoiceSDK] Using API key for ${agentId}`);
                        } else {
                             console.warn(`[VoiceSDK] Token endpoint OK but no token found for ${agentId}. Assuming public agent.`);
                        }
                    } else {
                        console.warn(`[VoiceSDK] Token fetch failed for ${agentId}: ${tokenResp.status}. Assuming public agent.`);
                    }
                } catch (tokErr) {
                    console.warn(`[VoiceSDK] Error fetching token for ${agentId}:`, tokErr);
                }
            }

            // 3. Start the session with the imported class
            convo = await Conversation.startSession({
                ...opts,
                onConnect: () => {
                    console.log(`[VoiceSDK] Connected: ${agentId}`);
                    recording = true;
                    micBtn.classList.add('recording');
                    statusLabel.textContent = 'Listening... (Tap to stop)';
                    if (transcriptArea) transcriptArea.innerHTML = ''; // Clear transcript
                    micBtn.disabled = false; // Re-enable button
                    // If this is the drawer card, mark session as active
                    if (isDrawerCard) {
                        localStorage.setItem('voiceSessionWasActive', 'true');
                        console.log('[VoiceSDK] Drawer session marked as active in localStorage.');
                    }
                },
                onError: (e) => {
                    console.error(`[VoiceSDK] Session Error (${agentId}):`, e);
                    statusLabel.textContent = 'Error! Tap to retry';
                    recording = false;
                    micBtn.classList.remove('recording');
                    convo = null; // Reset convo on error
                    micBtn.disabled = false;
                    // Clear active flag on error for drawer card
                    if (isDrawerCard) {
                        localStorage.setItem('voiceSessionWasActive', 'false');
                         console.log('[VoiceSDK] Drawer session marked as INACTIVE in localStorage due to error.');
                    }
                },
                onMessage: (msg) => {
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
                    // console.log(`[VoiceSDK] Mode change (${agentId}):`, m.mode);
                    if (recording) { // Only update label if we are actively recording
                       statusLabel.textContent = m.mode === 'speaking' ? 'Agent speaking... (Tap to stop)' : 'Listening... (Tap to stop)';
                    }
                },
                onDisconnect: () => {
                    console.log(`[VoiceSDK] Disconnected: ${agentId}`);
                    statusLabel.textContent = 'Tap to talk';
                    recording = false;
                    micBtn.classList.remove('recording');
                    convo = null;
                    micBtn.disabled = false;
                     // Clear active flag on disconnect for drawer card
                    if (isDrawerCard) {
                        localStorage.setItem('voiceSessionWasActive', 'false');
                        console.log('[VoiceSDK] Drawer session marked as INACTIVE in localStorage due to disconnect.');
                    }
                }
            });
            return convo;
        } catch (initErr) {
            console.error(`[VoiceSDK] CRITICAL ERROR initializing session for ${agentId}:`, initErr);
            statusLabel.textContent = 'Failed to start';
            micBtn.disabled = false; // Ensure button is re-enabled on failure
            throw initErr; // Propagate error
        }
    }

    // Attach the single click listener to the mic button
    micBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        micBtn.disabled = true; // Disable during operation
        statusLabel.textContent = 'Processing...';

        try {
            if (!convo) { // If no active conversation, try to start one
                await initConversation(); 
                // Recording state and UI managed by onConnect
            } else { // If conversation exists, end it
                await convo.endSession();
                // Recording state and UI managed by onDisconnect
                console.log(`[VoiceSDK] endSession called for ${agentId}.`);
                // Manually clear flag here too, as onDisconnect might be delayed
                if (isDrawerCard) {
                    localStorage.setItem('voiceSessionWasActive', 'false');
                    console.log('[VoiceSDK] Drawer session marked as INACTIVE in localStorage due to manual stop.');
                }
                convo = null; 
            }
        } catch (err) {
            console.error(`[VoiceSDK] Click handler error for ${agentId}:`, err);
            statusLabel.textContent = 'Error. Tap to retry'; // More informative error state
            recording = false;
            micBtn.classList.remove('recording');
            convo = null;
        } finally {
            micBtn.disabled = false; // Always re-enable
        }
    });

    card._voiceBound = true; // Mark as bound
    console.log(`[VoiceSDK] Handlers attached for agent ${agentId}`);

    // *** NEW: Auto-initiate connection if drawer was open and session was active ***
    if (isDrawerCard && localStorage.getItem('voiceDrawerIsOpen') === 'true' && localStorage.getItem('voiceSessionWasActive') === 'true') {
        console.log(`[VoiceSDK] Drawer was open and session was active. Auto-initiating connection for ${agentId}...`);
        // Wrap in try/catch to prevent blocking other UI
        (async () => { 
            try {
                await initConversation();
                // State should be handled by onConnect
            } catch (autoInitErr) {
                 console.error('[VoiceSDK] Error during auto-initiation:', autoInitErr);
                 // UI should reflect error state via initConversation's error handling
            }
        })();
    }
}

// --- Global Binding Logic --- 
function bindAllVoiceCards() {
    console.log('[VoiceSDK] bindAllVoiceCards running...');
    if (typeof Conversation === 'undefined' || typeof Conversation.startSession !== 'function') {
        console.error('[VoiceSDK] Conversation class not ready yet.');
        // Optionally retry after a delay if needed, but MutationObserver should handle it.
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
    // Find the drawer card and its state (this is less reliable than checking localStorage directly)
    const drawerCard = document.querySelector('#voice-drawer .voice-card[data-agent-id]');
    if (drawerCard && drawerCard._voiceBound) {
        // Need access to the specific `convo` instance for this card.
        // This is difficult here. Let's rely on localStorage flag instead.
        console.warn('[VoiceSDK] Cannot reliably access specific convo instance in beforeunload.');
    }
    
    // Simpler: Just clear the flag. The connection will timeout anyway.
    if (localStorage.getItem('voiceSessionWasActive') === 'true') {
        console.log('[VoiceSDK] Clearing active session flag on page unload.');
        localStorage.setItem('voiceSessionWasActive', 'false');
    }
});

// console.log('[VoiceSDK] End of script execution (module).'); 