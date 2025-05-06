console.log('voiceSdk.js loaded');

// Wait until ElevenLabs Conversation global is available
function onSdkReady(cb) {
  if (window.Conversation && typeof window.Conversation.startSession === 'function') {
    cb();
    return;
  }
  const int = setInterval(() => {
    if (window.Conversation && typeof window.Conversation.startSession === 'function') {
      clearInterval(int);
      cb();
    }
  }, 100);
}

onSdkReady(() => {
  const card = document.querySelector('.voice-card[data-agent-id]');
  if (!card) return;

  const micBtn = card.querySelector('.voice-mic-btn');
  if (!micBtn) {
    console.warn('mic button not found');
    return;
  }

  let convo = null;
  let recording = false;

  async function initConversation() {
    if (convo) return convo;
    // For public agents, token not required. If backend provides token, include.
    let opts = { agentId: card.dataset.agentId };
    try {
      const resp = await fetch('/api/voice-sdk/token');
      const data = await resp.json();
      if (data.token) opts.apiKey = data.token;
    } catch (_) {}

    convo = await window.Conversation.startSession({
      ...opts,
      onConnect: () => {
        console.log('Voice connected');
      },
      onError: (e) => console.error('Voice error', e),
      onModeChange: (m)=> console.log('mode', m.mode)
    });

    convo.on('message', (msg) => console.log(msg));
    convo.on('end', () => {
      recording = false;
      micBtn.classList.remove('recording');
      convo = null;
    });
    return convo;
  }

  micBtn.addEventListener('click', async () => {
    try {
      const conv = await initConversation();
      if (!recording) {
        recording = true;
        micBtn.classList.add('recording');
      } else {
        await conv.endSession();
        recording = false;
        micBtn.classList.remove('recording');
      }
    } catch (err) {
      console.error('Voice SDK error', err);
    }
  });
}); 