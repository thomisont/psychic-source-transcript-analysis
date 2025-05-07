// voice_overlay.js – mounts ElevenLabs Convai widget in a Bootstrap off-canvas
// ---------------------------------------------------------------
(() => {
  const openBtn = document.getElementById('openVoiceOverlayBtn');
  const offcanvasEl = document.getElementById('voiceOverlay');
  if (!openBtn || !offcanvasEl) return; // safety

  const offcanvas = new bootstrap.Offcanvas(offcanvasEl);
  const widgetContainer = document.getElementById('voice-overlay-widget');

  function ensureConvaiScript() {
    if (!document.querySelector('script[src*="elevenlabs.io/convai-widget"]')) {
      const s = document.createElement('script');
      s.src = 'https://elevenlabs.io/convai-widget/index.js';
      s.async = true;
      document.body.appendChild(s);
    }
  }

  async function mountWidget() {
    if (!widgetContainer) return;
    if (widgetContainer.querySelector('.voice-card')) return; // already mounted
    widgetContainer.innerHTML = '<p class="text-muted">Loading voice interface...</p>';
    try {
      const agentResp = await fetch('/api/agents');
      const { default_agent_id, agents } = await agentResp.json();

      const agent = (agents || []).find(a => a.id === default_agent_id) || {};

      // Build custom voice-card markup (same as index.html test section)
      const cardHtml = `
        <div class="voice-card shadow-lg mx-auto" data-agent-id="${default_agent_id}" style="max-width:340px;">
            <div class="text-center mb-3">
                <img src="/static/images/lily_avatar.png" alt="Lily Avatar" class="rounded-circle voice-avatar">
            </div>
            <h5 class="fw-bold mb-1">Ask ${agent.name || 'Lily'}</h5>
            <div class="voice-mic-btn my-3 mx-auto" role="button">
                <i class="bi bi-mic-fill fs-2"></i>
            </div>
            <p class="mb-3">Tap to connect</p>
            <ul class="voice-prompts text-start list-unstyled mx-auto mb-4">
                <li>• What's the vibe around my career path?</li>
                <li>• Which advisor suits my needs today?</li>
                <li>• How do I raise my spiritual energy?</li>
            </ul>
            <p class="voice-powered-by small mb-0">Powered by ElevenLabs Conversational AI</p>
        </div>`;
      widgetContainer.innerHTML = cardHtml;
    } catch (err) {
      console.error('Voice overlay load failed', err);
      widgetContainer.innerHTML = '<p class="text-danger">Error loading widget.</p>';
    }
  }

  openBtn.addEventListener('click', async () => {
    ensureConvaiScript();
    await mountWidget();
    offcanvas.show();
  });

  offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
    if (widgetContainer) widgetContainer.innerHTML = '';
  });
})(); 