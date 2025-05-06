# Lilly Voice Agents – Configuration & Status Guide

_Last updated: 2025-04-26_

This document explains how to pull live configuration data for **all Lilly Conversational Voice Agents** running in ElevenLabs and how to consolidate that data into an easy-to-read status report.

---

## 1. Identify the Agents

1. Check `config.py` for `AGENT_CONFIGS` / environment variables (e.g. `ELEVENLABS_AGENT_ID_CURIOUS`).
2. Review the `agents` table in Supabase (if normalised).
3. Build a mapping of **friendly name → agent_id + voice_id**.

```python
AGENTS = {
    "Lilly Curious": {
        "agent_id": "3HFVw3nTZfIivPaHr3ne",
        "voice_id": "pFZP5JQG7iQjIQuC4Bku"
    },
    "Lilly Members": {
        "agent_id": "fVh9yE8yV6eTumn8hZ3K",
        "voice_id": "pFZP5JQG7iQjIQuC4Bku"  # same voice, diff. prompt
    }
}
```

---

## 2. Pull Voice-Level Metadata

| Endpoint | Purpose |
|----------|---------|
| `mcp_elevenlabs_Get_Voice` | descriptive fields, category, fine-tuning state |
| `mcp_elevenlabs_Get_Voice_Settings` | slider settings (`stability`, `similarity_boost`, …) |

Example call:

```python
voice     = mcp_elevenlabs_Get_Voice(voice_id="pFZ...")
settings  = mcp_elevenlabs_Get_Voice_Settings(voice_id="pFZ...")
```

---

## 3. Pull ConvAI Agent Metadata

Add a small helper in `tools/elevenlabs_client.py`:

```python
def get_agent_config(agent_id):
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    r = self.session.get(url, headers=self.headers)
    r.raise_for_status()
    return r.json()
```

Fields returned include:
* `name`, `voice_id`, `model_id`
* full **system prompt** & variables
* LLM tuning (`temperature`, `top_p`, …)
* Widget options (button text, colours, suggestions)

---

## 4. Enrich with Operational Stats

Use Supabase to compute month-to-date usage:

```sql
select
  agent_id,
  count(*)                             as total_conversations,
  sum(cost)                            as month_to_date_credits,
  avg(duration)                        as avg_duration_secs,
  sum(case when status='done' then 1 end) as completed_calls
from conversations
where agent_id = :agent_id
  and created_at >= date_trunc('month', current_date)
group by agent_id;
```

---

## 5. Compose a Status Block

Example output:

```
=== Lilly Curious (agent_id: 3HF... / voice_id: pFZ...)
Voice description : warm, middle-aged British female
Voice settings    : stability=0.32  similarity=0.71
Prompt model      : gpt-4o  (temperature 0.7)
Widget mode       : Floating button – "Chat with Lilly"
Month-to-date     : 824 calls, 6 324 credits (31.6 % of 2M budget)
Avg call duration : 38 s     Completion rate: 93 %
```

Generate one block per agent and expose it via `/api/agent-status` so the Admin Panel can render the data.

---

## 6. Automation Checklist

- [ ] Add voice & agent fetch helpers to `ElevenLabsClient`.
- [ ] Create `/api/agent-status` route returning merged JSON.
- [ ] Cache results for 5 min (Flask-Caching) to avoid rate limits.
- [ ] Update Dashboard Admin Panel to display the status blocks.

---

### Related Files
* `tools/elevenlabs_client.py`
* `app/api/routes.py` – add new route
* `dashboard.js` – Admin Panel rendering 