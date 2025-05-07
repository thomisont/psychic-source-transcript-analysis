# ElevenLabs Voice SDK + Flask Integration Guide

_Last Updated: 2025-05-07_

This guide provides step-by-step instructions for integrating the ElevenLabs Conversational AI SDK into a Python/Flask web application to power custom voice interface elements (like voice cards), based on successful implementation patterns.

It assumes you are **not** using the pre-built `<elevenlabs-convai>` widget, but rather the `Conversation.startSession` API for more control.

## 1. Frontend Setup (HTML)

You need to load the ElevenLabs client SDK and your custom JavaScript helper script correctly. The recommended approach is using ES Modules.

**In your base HTML template (e.g., `base.html`) before the closing `</body>` tag:**

```html
    <!-- Other scripts (jQuery, Bootstrap, etc.) -->
    
    <!-- Load Custom Voice SDK helper AS A MODULE -->
    <!-- It will dynamically import the ElevenLabs SDK from a CDN -->
    <script type="module" src="{{ url_for('static', filename='js/your_voice_sdk_helper.js') }}"></script>

</body>
</html> 
```

*   **Remove any direct script tags** loading ElevenLabs SDKs (like `@11labs/client/dist/lib.umd.js` or `convai-widget/index.js`).
*   Load your custom JavaScript file (e.g., `your_voice_sdk_helper.js`) using **`type="module"`**.

## 2. Frontend Setup (JavaScript - `your_voice_sdk_helper.js`)

This script will handle importing the SDK, finding your custom voice elements, attaching listeners, and calling the SDK's `startSession` method.

```javascript
// Import the Conversation class directly from an ESM-compatible CDN
// Using esm.sh is generally reliable for this. Specify the desired version.
import { Conversation } from 'https://esm.sh/@11labs/client@0.1.4'; 

console.log('Voice SDK Helper loaded (as module)');

// --- Core Functions ---

async function attachHandlers(cardElement) {
  console.log('[VoiceSDK] attachHandlers called for card.'); 

  // Check if the import worked 
  if (typeof Conversation === 'undefined' || typeof Conversation.startSession !== 'function') {
    console.error('[VoiceSDK] Imported Conversation class is not available/invalid. Cannot attach handlers.');
    return; 
  }

  // Prevent double-binding
  if (cardElement._voiceBound) { 
    console.log('[VoiceSDK] Card already bound – skipping.'); 
    return;
  } 

  const micBtn = cardElement.querySelector('.voice-mic-btn'); // Selector for your mic button
  if (!micBtn) { 
    console.warn('[VoiceSDK] Mic button not found inside card.'); 
    return; 
  }
  
  let currentConversation = null; // Track the active conversation instance
  let isRecording = false;

  // Function to start a new session
  async function initConversation() {
    console.log('[VoiceSDK] Initializing conversation...');
    if (currentConversation) return currentConversation; // Already have one

    // 1. Get Mic Permission
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (permErr) {
      console.error('[VoiceSDK] Microphone permission denied or unavailable.', permErr);
      alert('Microphone access is required. Please grant permission and refresh.'); 
      throw permErr;
    }

    // 2. Prepare Auth Options
    const agentId = cardElement.dataset.agentId; // Get agent ID from the card's data attribute
    if (!agentId) {
        console.error('[VoiceSDK] Missing data-agent-id attribute on card:', cardElement);
        throw new Error('Missing agent ID on voice card.');
    }
    
    const backendOpts = {}; // Options fetched from backend
    let signedUrlFetched = false;

    // 2a. Fetch Signed URL (Preferred for private/authorized agents)
    try {
      console.log(`[VoiceSDK] Fetching signed URL for ${agentId}...`);
      const suResp = await fetch(`/api/voice-sdk/signed-url/${agentId}`); // Your backend endpoint
      if (suResp.ok) {
        const suData = await suResp.json();
        if (suData.signed_url) {
          backendOpts.signedUrl = suData.signed_url;
          signedUrlFetched = true;
          console.log(`[VoiceSDK] Signed URL fetched successfully.`);
        } else {
           console.warn(`[VoiceSDK] Signed URL endpoint OK but no URL returned.`);
        }
      } else {
        console.warn(`[VoiceSDK] Signed URL fetch failed: ${suResp.status}. Falling back.`);
      }
    } catch (e) {
       console.warn(`[VoiceSDK] Error fetching signed URL. Falling back:`, e);
    }

    // 3. Build Final Options for startSession
    const finalSessionOpts = {};
    if (signedUrlFetched) {
      // --- Use Signed URL ---
      finalSessionOpts.signedUrl = backendOpts.signedUrl; 
      console.log(`[VoiceSDK] Using signedUrl for authorization.`);
      // IMPORTANT: Do NOT include a separate 'authorization' token when using signedUrl.
    } else {
      // --- Fallback to Agent ID (for public agents or if signed URL fails) ---
      finalSessionOpts.agentId = agentId;
      console.log(`[VoiceSDK] Using agentId ${agentId} directly.`);
      // Optional: Fetch and add a short-lived JWT token if needed for public agents
      // try {
      //   const tokenResp = await fetch('/api/voice-sdk/token'); // Your backend endpoint
      //   // ... handle response and add to finalSessionOpts.authorization ...
      // } catch (tokenErr) { /* ... handle ... */ }
    }
    
    console.log('[VoiceSDK] Attempting Conversation.startSession...');
    try {
      // 4. Start the Session using the IMPORTED Conversation class
      currentConversation = await Conversation.startSession({
        ...finalSessionOpts, 
        // --- Callbacks ---
        onConnect: () => {
          console.log('[VoiceSDK] SESSION CONNECTED');
          isRecording = true;
          micBtn.classList.add('recording'); // Add visual feedback
        },
        onError: e => {
          console.error('[VoiceSDK] SESSION ERROR:', e);
          // Try to decode common close reasons
          if (e instanceof CloseEvent) {
              console.error(`[VoiceSDK] WebSocket Closed: Code=${e.code}, Reason='${e.reason}', Clean=${e.wasClean}`);
              if (e.code === 3000) { // Example: Check for specific codes
                  alert('Authorization failed. Please ensure the agent is configured correctly.');
              } else {
                  alert(`Voice connection closed unexpectedly (Code: ${e.code}). Please try again.`);
              }
          } else {
             alert('An error occurred with the voice session.');
          }
          isRecording = false;
          micBtn.classList.remove('recording');
          currentConversation = null; // Clear conversation on error
        },
        onMessage: m => { 
            // Handle incoming messages (e.g., display transcripts)
            // console.log('[VoiceSDK] Message:', m); // Very verbose
        }, 
        onModeChange: m => {
            console.log('[VoiceSDK] Mode change:', m.mode); // e.g., 'listening', 'speaking'
            // Update UI based on mode if desired
        },
        onDisconnect: () => {
          console.log('[VoiceSDK] SESSION DISCONNECTED');
          isRecording = false;
          micBtn.classList.remove('recording');
          currentConversation = null; // Clear conversation on disconnect
        }
      });
      console.log('[VoiceSDK] Conversation.startSession call successful (instance created).');
    } catch (startErr) {
       console.error('[VoiceSDK] CRITICAL ERROR calling Conversation.startSession:', startErr);
       alert('Failed to start voice session. Please check console.'); 
       currentConversation = null; // Ensure state is reset
       throw startErr; 
    }

    return currentConversation;
  }

  // --- Click Handler Attachment --- 
  micBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    console.log('[VoiceSDK] Mic button clicked.');
    micBtn.disabled = true; // Prevent double-clicks
    
    try {
      if (!currentConversation) { // Start if not already active
          await initConversation(); 
      } else { // Stop if active
          console.log('[VoiceSDK] Ending session...');
          await currentConversation.endSession(); 
          // State reset happens in onDisconnect callback
      }
    } catch (err) {
      console.error('[VoiceSDK] Error in click handler:', err);
      isRecording = false; 
      micBtn.classList.remove('recording');
      currentConversation = null; // Reset state on error
    } finally {
        micBtn.disabled = false; // Re-enable button
    }
  });
  
  cardElement._voiceBound = true; // Mark card as processed
  console.log(`[VoiceSDK] Event listener attached for card with Agent ID: ${cardElement.dataset.agentId}`);
}

// --- Global Binding Logic --- 
function bindAllVoiceCards() {
  console.log('[VoiceSDK] bindAllVoiceCards called (module)');
  if (typeof Conversation === 'undefined') {
      console.error('[VoiceSDK] bindAllVoiceCards: Conversation class not imported.');
      return;
  }
  // Find all elements with the target class and data attribute
  document.querySelectorAll('.voice-card[data-agent-id]').forEach(attachHandlers);
}

// --- Initialization ---

// Wait for the DOM to be ready before binding initial cards
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindAllVoiceCards);
} else {
    bindAllVoiceCards(); // DOM already loaded
}

// Use MutationObserver to handle dynamically added cards (e.g., in modals/drawers)
// Wait slightly to ensure the Conversation module is likely available
setTimeout(() => {
  if (typeof Conversation !== 'undefined') {
      if (!window.voiceObserver) { // Initialize observer only once
          window.voiceObserver = new MutationObserver((mutationsList) => {
              // Optional: More refined check if needed, otherwise just re-bind
              // for(const mutation of mutationsList) {
              //    if (mutation.type === 'childList') { /* ... */ }
              // }
              console.log('[VoiceSDK] DOM changed, re-running bindAllVoiceCards...');
              bindAllVoiceCards(); 
          });
          window.voiceObserver.observe(document.body, { childList: true, subtree: true });
          console.log('[VoiceSDK] MutationObserver initialized successfully.');
      }
  } else {
      console.error('[VoiceSDK] CRITICAL: Cannot initialize MutationObserver because Conversation class is not defined.');
  }
}, 500); // Adjust delay if needed

```

**Key elements of this JS:**
*   **ES Module Import:** Uses `import { Conversation } from '...'` to load the SDK.
*   **No `sdkReadyPromise`:** Relies on module loading order.
*   **`attachHandlers`:** Finds elements with `.voice-card` and `data-agent-id`.
*   **`initConversation`:**
    *   Gets mic permission.
    *   Fetches `signedUrl` from your backend (preferred).
    *   Falls back to using `agentId` if `signedUrl` fails.
    *   **Crucially:** Only passes *either* `signedUrl` *or* `agentId` to `Conversation.startSession`. Avoid sending both or conflicting tokens.
*   **Click Handler:** Starts/stops the session.
*   **Binding:** Binds on `DOMContentLoaded` and uses `MutationObserver` for dynamic elements.

## 3. Backend Setup (Flask Routes)

You need backend endpoints for your JavaScript to call, primarily to generate the `signedUrl`. This keeps your main ElevenLabs API key secure on the server.

**Example Flask Routes (e.g., in `app/api/routes.py` or similar):**

```python
import os
import requests # Or use your preferred HTTP client library
from flask import Blueprint, jsonify, current_app, request

# Assume 'api_bp' is your Flask Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# --- Route to Get Signed URL ---
@api_bp.route('/voice-sdk/signed-url/<string:agent_id>', methods=['GET'])
def get_signed_url(agent_id):
    """
    Generates a secure, short-lived WebSocket URL for the client 
    to connect directly to a specific ElevenLabs agent.
    """
    api_key = os.environ.get('ELEVENLABS_API_KEY') 
    if not api_key:
        current_app.logger.error("ELEVENLABS_API_KEY not set.")
        return jsonify({"error": "Server configuration error"}), 500
        
    # Ensure the requested agent_id is valid/allowed if necessary
    # (e.g., check against a list in config)
    allowed_agents = current_app.config.get('ELEVENLABS_AGENTS', {}).keys()
    if agent_id not in allowed_agents:
         current_app.logger.warning(f"Attempt to get signed URL for invalid agent ID: {agent_id}")
         return jsonify({"error": "Invalid agent ID"}), 400

    elevenlabs_api_endpoint = f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}"
    
    headers = {
        "xi-api-key": api_key
    }

    try:
        response = requests.get(elevenlabs_api_endpoint, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        signed_url = data.get('signed_url')

        if signed_url:
            current_app.logger.info(f"Generated signed URL for agent {agent_id}")
            return jsonify({"signed_url": signed_url})
        else:
            current_app.logger.error(f"Failed to get signed_url from ElevenLabs response for {agent_id}")
            return jsonify({"error": "Failed to generate signed URL from API response"}), 500

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error requesting signed URL from ElevenLabs for {agent_id}: {e}")
        # Check for specific status codes if needed (e.g., 401 Unauthorized)
        status_code = e.response.status_code if e.response is not None else 500
        error_detail = "Error communicating with ElevenLabs API"
        if status_code == 401:
             error_detail = "ElevenLabs API key is invalid or unauthorized."
        elif status_code == 404:
             error_detail = f"Agent ID {agent_id} not found or invalid at ElevenLabs."
             
        return jsonify({"error": error_detail}), status_code
    except Exception as e:
        current_app.logger.error(f"Unexpected error generating signed URL for {agent_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

# --- (Optional) Route to Get Short-Lived Token --- 
# Useful if you need auth for *public* agents, but signedUrl is generally preferred.
# You might use JWT or another token mechanism here.
@api_bp.route('/voice-sdk/token', methods=['GET'])
def get_voice_sdk_token():
    """
    Generates a short-lived token if needed for other purposes 
    (e.g., authenticating public agent usage, although signedUrl is better).
    """
    # --- Implement your token generation logic here ---
    # Example: Create a JWT token with a short expiry
    # token = create_your_jwt(...) 
    # return jsonify({"token": token})
    # ---
    
    # For now, maybe return nothing or a placeholder if not used
    return jsonify({"token": None}), 200 

# Remember to register this blueprint in your app factory (app/__init__.py)
# e.g., app.register_blueprint(api_bp)
```

**Key points for the backend:**
*   **Keep API Key Secure:** Never expose your main `ELEVENLABS_API_KEY` to the frontend. Use it only in the backend route.
*   **Signed URL Endpoint:** This is the crucial endpoint. It takes an `agent_id`, calls the ElevenLabs API (`/v1/convai/conversation/get_signed_url`) using your backend key, and returns the temporary WebSocket URL to the client.
*   **Error Handling:** Implement robust error handling for the API call to ElevenLabs.
*   **Agent ID Validation (Optional but Recommended):** Prevent users from requesting signed URLs for arbitrary agent IDs by checking against a configuration list.
*   **Token Endpoint (Optional):** Only implement `/api/voice-sdk/token` if you have a specific need for it (e.g., a separate auth layer for public agents). The `signedUrl` method is generally the standard way to authorize WebSocket sessions.

## 4. Configuration

*   **HTML Element:** Ensure your clickable voice card element has:
    *   The class `voice-card` (or whatever you use in `querySelectorAll`).
    *   A `data-agent-id="..."` attribute containing the correct ElevenLabs Agent ID.
    *   An inner element with the class `voice-mic-btn` (or adjust the selector in JS).
*   **Flask:**
    *   Set the `ELEVENLABS_API_KEY` environment variable for your server.
    *   Register the API Blueprint.
    *   Configure CORS properly if your frontend and backend are on different origins (Flask-CORS extension is helpful).

## 5. Troubleshooting

*   **Check Console:** Look for errors related to module loading, `Conversation` class being undefined, WebSocket connection failures (especially `CloseEvent` code 3000 for auth errors), or microphone permissions.
*   **Check Network Tab:** Verify the `signedUrl` endpoint is called and returns a valid URL. Check for WebSocket connection attempts and their status. Look for CORS errors.
*   **Check Backend Logs:** Look for errors related to API key issues, agent ID validity, or failures when contacting the ElevenLabs `get_signed_url` API.
*   **Simplify:** Temporarily use a known *public* agent ID directly in the JS (`finalSessionOpts.agentId = 'PUBLIC_AGENT_ID';`) and bypass the `signedUrl` logic to isolate if the issue is with the signed URL generation or the basic session establishment.

---

This guide covers the essential steps based on our successful troubleshooting. Remember to adapt selectors, endpoints, and error handling to your specific application structure. 