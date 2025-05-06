Below is a **single, self‑contained Markdown brief**—no prior versions needed.  
Save it as `docs/dev_instructions/competitive_intel_section.md` (or equivalent) so the Cursor‑based developer can execute the tasks.

---

# “How’s Lily Doing?” – Competitive‑Intelligence Section  
### Designer → Developer To‑Dos

## 0 · Purpose & Scope  

Add an **Urgent Competitive‑Intelligence** module to the existing Flask + Jinja dashboard.  
It must surface five PDF reports, display the synthesized findings, and call out six ranked critical‑path actions—with unmistakable urgency—while preserving the site’s violet/teal aesthetic.

---

## 1 · Storage & Asset Conventions  

* **No Supabase CDN yet** – serve assets straight from `/static/intel/`.  
* Place these files there (already uploaded):  

```
competitive_analysis_openai_o3_2025.pdf
competitive_analysis_grok_2025.pdf
competitive_analysis_perplexity_2025.pdf
competitive_analysis_gemini_2025.pdf
competitive_analysis_synthesis_2025.pdf
```

* Future images (infographic, meme) will arrive later—create placeholders.

---

## 2 · Information Architecture  

```
Dashboard
 └─ Competitive Intelligence  (new route + sidebar link)
     ├─ Urgency Banner            (red tint, dismissable)
     ├─ Executive Snapshot        (2‑column card)
     ├─ Critical‑Path Actions     (accordion list)
     ├─ Full‑Report Library       (lazy‑loaded PDF viewers)
     ├─ Infographic Placeholder   (shows ‘Coming Soon’)
     └─ Meme of the Day           (hidden until file exists)
```

---

## 3 · Component Specs  

| Component | Behaviour & Styling |
|-----------|---------------------|
| **Urgency Banner** | Fixed top within panel; text: “🏃 Competitive runway ≈ 9–18 months – act now!”  `background: var(--psi-urgent-red)`; CSS pulse on icon.  Auto‑dismiss after 10 s; persists via `localStorage` key `psi_intel_banner_ack`. |
| **Executive Snapshot** | Violet card (`--psi-deep-purple` header, `--psi-surface` body). Text block below. |
| **Critical‑Path Accordion** | Bootstrap 5 `accordion-flush`; left border colour signifies priority (map below). |
| **Full‑Report Library** | Tabbed list; each tab embeds pdf.js viewer (600 px height on ≥ lg, collapses to link on sm).  |
| **Infographic / Meme** | `<img>` with overlay “Coming Soon”; `d-none` until file exists. |

### Priority → Border Class  

| critical | high | medium‑high | medium |
|----------|------|-------------|--------|
| `border-danger` | `border-warning` | `border-info` | `border-secondary` |

---

## 4 · Style‑Guide Additions  

```css
:root{
  --psi-urgent-red:#ff5252;
  --psi-deep-purple:#311b92;
  --psi-teal:#00bfa5;
  --psi-surface:#f7f9fc;
}
@keyframes urgent-blink{0%,100%{opacity:1}50%{opacity:.2}}
```

Add `.urgent-blink` class for the banner icon.

---

## 5 · Static Data Files  

### 5.1 Executive Snapshot (verbatim)

> **Lead at risk, window is closing.**  
> Psychic Source holds the only production‑grade conversational‑AI (“Lily”) in our market, but Ingenio’s Keen/Kasamba stack can plausibly reach parity **within 6–12 months**; other challengers (Purple Garden, Oranum, California Psychics) could follow inside **18 months**. Our moat is our **30‑year proprietary dataset** and **Holacratic agility**. We must scale Lily, weaponize data, and harden brand trust *immediately*.  citeturn0file0turn0file1turn0file2turn0file3turn0file4

### 5.2 Critical‑Path JSON → `static/json/psi_critical_actions.json`

```json
[
  {
    "id": 1,
    "priority": "critical",
    "title": "Accelerate AI Deployment & Differentiation",
    "actions": [
      "Move Lily from pilot to full‑scale deployment; add personalised guidance and ethical sample‑insights.",
      "Exploit the 30‑year data trove for Lily, backend personalisation & new AI features."
    ],
    "rationale": "Locks in first‑mover advantage before Keen/Ingenio parity (6‑18 mos); creates data‑driven moat."
  },
  {
    "id": 2,
    "priority": "high",
    "title": "Leverage Human‑AI Synergy & Enhance UX",
    "actions": [
      "Keep AI firmly positioned as advisor companion, not replacement.",
      "Ship community features (e.g., peer ‘Journeys’) & richer UI across web/app."
    ],
    "rationale": "Deepens loyalty and counters Purple Garden‑style engagement plays."
  },
  {
    "id": 3,
    "priority": "high",
    "title": "Monitor & Pre‑empt Competitor Moves",
    "actions": [
      "Stand‑up continuous CI scraper (sites, job‑posts, press) with alerting.",
      "Spin‑up rapid‑response pilots to neutralise new competitor features within weeks."
    ],
    "rationale": "Holacracy agility is useless without real‑time intel."
  },
  {
    "id": 4,
    "priority": "medium-high",
    "title": "Emphasise Culture, Trust & Agility in Marketing",
    "actions": [
      "Blend 30‑year heritage with responsible‑AI narrative in all comms.",
      "Showcase Holacracy as customer‑centric innovation engine.",
      "Highlight advisor screening, satisfaction guarantee & data‑ethics."
    ],
    "rationale": "Protects brand equity as rivals push shiny‑tech messaging."
  },
  {
    "id": 5,
    "priority": "medium",
    "title": "Explore Strategic Partnerships & Data Opportunities",
    "actions": [
      "Scout AI labs/universities & niche vendors (voice, emotion AI).",
      "Assess licensing a ‘Powered by Psychic Source AI’ widget."
    ],
    "rationale": "Extends reach, pre‑empts Ingenio exclusivity deals."
  },
  {
    "id": 6,
    "priority": "medium",
    "title": "Continue Multi‑Platform Expansion & Adjacent Offers",
    "actions": [
      "Ensure flawless omnichannel (web, iOS, Android, voice assistants).",
      "Pilot AI‑supported life‑coaching & spiritual‑wellness add‑ons."
    ],
    "rationale": "Broadens revenue and hedges against mobile‑first insurgents."
  }
]
```
_Source: synthesized report_ citeturn0file4

---

## 6 · Flask / Jinja Implementation Steps  

1. **Route & Template**  
   ```python
   @dashboard_bp.route('/competitive‑intel')
   def competitive_intel():
       import json, os
       with open('static/json/psi_critical_actions.json') as f:
           actions = json.load(f)
       reports = [
         ('OpenAI o3','competitive_analysis_openai_o3_2025.pdf'),
         ('Grok','competitive_analysis_grok_2025.pdf'),
         ('Perplexity','competitive_analysis_perplexity_2025.pdf'),
         ('Gemini','competitive_analysis_gemini_2025.pdf'),
         ('Synthesis','competitive_analysis_synthesis_2025.pdf')
       ]
       return render_template('competitive_intel.html', actions=actions, reports=reports)
   ```

2. **Template Skeleton** (key parts)  
   *Urgency Banner* → conditionally hidden via JS `localStorage`.  
   *Accordion* → loop through `actions`.  
   *PDF Tabs* → for each `reports` tuple.

3. **pdf.js**  
   ```html
   <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
   ```

4. **CSS** – extend `static/css/theme.css` with tokens & banner animation.

---

## 7 · Developer Checklist  

- [ ] Create route, template, accordion, tabs.  
- [ ] Copy PDFs into `/static/intel/`.  
- [ ] Add `psi_critical_actions.json`.  
- [ ] Implement urgency banner (pulse + dismiss).  
- [ ] Insert colour tokens & update SCSS/CSS.  
- [ ] Responsive QA (<375 px).  
- [ ] Hide infographic/meme placeholders until assets exist.  
- [ ] Commit & deploy on Replit.

---

## 8 · Next‑Phase Ideas (not in scope v1)

* Voiceover of Executive Snapshot using Lily’s ElevenLabs voice.  
* Drag‑and‑drop Kanban view for critical actions.  
* Auto‑populated competitor alert log fed by scraper.

---

**End of To‑Dos**