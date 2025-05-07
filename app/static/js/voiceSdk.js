import { Conversation } from 'https://esm.sh/@11labs/client@0.1.4';

console.log('voiceSdk.js loaded (as module)');

// No sdkReadyPromise needed with module imports

async function attachHandlers(card){
  console.log('[VoiceSDK] attachHandlers called for card.');
  
  // Check if the import worked immediately
  if (typeof Conversation === 'undefined' || typeof Conversation.startSession !== 'function') {
    console.error('[VoiceSDK] Imported Conversation class is not available/invalid. Cannot attach handlers.');
    return; 
  }
  // console.log('[VoiceSDK] DEBUG: Imported Conversation class verified within attachHandlers.'); // Optional: keep if needed

  if(card._voiceBound) { console.log('[VoiceSDK] Card already bound – skipping.'); return;} 
  
  const micBtn=card.querySelector('.voice-mic-btn');
  if(!micBtn){ console.warn('[VoiceSDK] Mic button not found inside card.'); return; }
  // console.log('[VoiceSDK] DEBUG: Found micBtn:', micBtn);
  
  let convo=null,recording=false;

  async function initConversation(){
    console.log('[VoiceSDK] Initializing conversation...');
    if(convo) return convo;

    try {
      console.log('[VoiceSDK] Requesting microphone permission...');
      await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[VoiceSDK] Microphone permission granted.');
    } catch (permErr) {
      console.error('[VoiceSDK] Microphone permission denied or unavailable.', permErr);
      alert('Microphone access is required to use voice chat. Please grant permission and refresh.'); // User feedback
      throw permErr;
    }

    const opts = {};
    const agentId = card.dataset.agentId;
    console.log(`[VoiceSDK] Preparing session for Agent ID: ${agentId}`);

    try {
      console.log('[VoiceSDK] Fetching auth token...');
      const resp = await fetch('/api/voice-sdk/token');
      if (resp.ok) {
        const data = await resp.json();
        if (data.token) {
          opts.authorization = data.token; 
          console.log('[VoiceSDK] Auth token fetched successfully.');
        } else {
          console.warn('[VoiceSDK] Auth token endpoint returned OK but no token found.');
        }
      } else {
         console.error(`[VoiceSDK] Auth token fetch failed: ${resp.status} ${resp.statusText}`);
      }
    } catch (tokErr) {
      console.error('[VoiceSDK] Error fetching auth token:', tokErr);
    } 
    
    let signedUrlFetched = false;
    try {
      console.log(`[VoiceSDK] Fetching signed URL for ${agentId}...`);
      const suResp = await fetch(`/api/voice-sdk/signed-url/${agentId}`);
      if (suResp.ok) {
        const suData = await suResp.json();
        if (suData.signed_url) {
          opts.signedUrl = suData.signed_url;
          signedUrlFetched = true;
          console.log(`[VoiceSDK] Signed URL fetched successfully for ${agentId}.`);
        } else {
           console.warn(`[VoiceSDK] Signed URL endpoint OK but no URL for ${agentId}.`);
        }
      } else {
        console.warn(`[VoiceSDK] Signed URL fetch failed for ${agentId}: ${suResp.status} ${suResp.statusText}. Will use agentId directly.`);
      }
    } catch (e) {
       console.warn(`[VoiceSDK] Error fetching signed URL for ${agentId}. Will use agentId directly:`, e);
    }

    // Prepare options ONLY with the required auth method
    const finalOpts = {};
    if (!signedUrlFetched) {
      finalOpts.agentId = agentId;
      // If using agentId directly (public agent?), maybe include token?
      // Let's try WITHOUT token first for simplicity, assuming public agent if no signed URL.
      // if (opts.authorization) finalOpts.authorization = opts.authorization; 
      console.log(`[VoiceSDK] Using agentId ${agentId} directly.`);
    } else {
      finalOpts.signedUrl = opts.signedUrl; // Use only signedUrl if available
      // Do NOT include the separate authorization token when using signedUrl
      console.log(`[VoiceSDK] Using signedUrl for authorization.`);
    }
    
    console.log('[VoiceSDK] Attempting Conversation.startSession with final options:', finalOpts);
    try {
      // Use the imported Conversation directly
      convo = await Conversation.startSession({
        ...finalOpts, // Pass the cleaned options
        onConnect: () => {
          console.log('[VoiceSDK] SESSION CONNECTED');
          recording = true;
          micBtn.classList.add('recording');
        },
        onError: e => {
          console.error('[VoiceSDK] SESSION ERROR:', e);
          recording = false;
          micBtn.classList.remove('recording');
          // Potentially show user feedback here
        },
        onMessage: m => { /* console.log('[VoiceSDK] Message:', m); */ }, // Commented out verbose message log
        onModeChange: m => console.log('[VoiceSDK] Mode change:', m.mode),
        onDisconnect: () => {
          console.log('[VoiceSDK] SESSION DISCONNECTED');
          recording = false;
          micBtn.classList.remove('recording');
          convo = null;
        }
      });
      console.log('[VoiceSDK] Conversation.startSession call successful (instance created). Waiting for onConnect...');
    } catch (startErr) {
       console.error('[VoiceSDK] CRITICAL ERROR calling Conversation.startSession:', startErr);
       alert('Failed to start voice session. Please check console for errors.'); // User feedback
       throw startErr; // Re-throw to be caught by the click handler
    }

    return convo;
  }

  // --- Click Handler --- 
  micBtn.addEventListener('click', async (e) => {
    // console.log('[VoiceSDK] Mic button CLICKED! Starting process...');
    e.preventDefault();
    micBtn.disabled = true; // Prevent double-clicks during init
    
    try {
      if (!convo) { // If no active conversation, start one
          console.log('[VoiceSDK] No active conversation, calling initConversation...');
          convo = await initConversation(); 
          // recording state and UI update are handled by onConnect callback
      } else { // If conversation exists, end it
          console.log('[VoiceSDK] Active conversation exists, calling endSession...');
          await convo.endSession();
          // recording state and UI update are handled by onDisconnect callback
          console.log('[VoiceSDK] endSession call completed.');
          convo = null; // Ensure convo is null after ending
      }
    } catch (err) {
      console.error('[VoiceSDK] Overall error in click handler:', err);
      // Ensure button state is reasonable after error
      recording = false; 
      micBtn.classList.remove('recording');
      convo = null;
    } finally {
        micBtn.disabled = false; // Re-enable button after operation attempt
        // console.log('[VoiceSDK] Click handler finished.');
    }
  });
  // --- End Click Handler --- 
  
  card._voiceBound = true;
  console.log(`[VoiceSDK] Event listener attached for card with Agent ID: ${card.dataset.agentId}`);
}

// --- Global Binding Logic --- 
function bindAllVoiceCards(){
  console.log('[VoiceSDK] bindAllVoiceCards called (module)');
  // Check if Conversation was imported successfully before trying to bind
  if (typeof Conversation === 'undefined') {
      console.error('[VoiceSDK] bindAllVoiceCards: Conversation class not imported.');
      return;
  }
  document.querySelectorAll('.voice-card[data-agent-id]').forEach(attachHandlers);
}

// Execute binding when the DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindAllVoiceCards);
} else {
    // DOMContentLoaded has already fired
    bindAllVoiceCards();
}

// Observe DOM mutations (important for dynamically added cards like in modals/drawers)
// We need to wait slightly longer because the module script itself needs to execute
// and define Conversation before we check for it here.
setTimeout(() => {
  if (typeof Conversation !== 'undefined') {
      if(!window.voiceObserver) {
          window.voiceObserver = new MutationObserver(bindAllVoiceCards);
          window.voiceObserver.observe(document.body, { childList: true, subtree: true });
          console.log('[VoiceSDK] MutationObserver initialized successfully (module).');
      } else {
          console.log('[VoiceSDK] MutationObserver already initialized.');
      }
  } else {
      console.error('[VoiceSDK] CRITICAL: Cannot initialize MutationObserver because Conversation class is still not defined after timeout.');
  }
}, 500); // Wait 500ms after initial script exec to init observer

// console.log('[VoiceSDK] End of script execution (module).'); 