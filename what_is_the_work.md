Below is a **single developer brief**—save it as `docs/dev_instructions/roles_holacracy_section.md`.  
It adds a small “GlassFrog‑style” modal that shows *what the work is and where it lives* by listing the three key roles.

---

# “What is the Work & Where Does it Live?” (Holacracy view)  
### Designer → Developer To‑Dos

## 0 · Goal & Placement
* Add a **modal** (`#roleDirectory`) launched from a new sidebar link **Roles (Holacracy)**.  
* Purpose: let any team‑member see the current AI‑related roles, their Purpose, and ongoing Accountabilities—formatted like GlassFrog role cards.

## 1 · Look & Feel (GlassFrog‑inspired)
* White card, drop‑shadow `0 2px 6px rgba(0,0,0,.06)`, rounded `8px`.  
* Header strip in `--psi-deep-purple`; role name in all‑caps, small sub‑label “AI‑filled” or “HI‑filled” (grey).  
* Body uses off‑white `--psi-surface`.  
* Sections: **Purpose** (italic), **Accountabilities** (bullets, verbs), optional **Metrics** (small caps).

## 2 · Static Data File

Create `static/json/role_catalog.json`:

```json
[
  {
    "name": "Intelligence",
    "filler": "HI",
    "purpose": "Intelligence is seamlessly integrated between AI and HI as it fills organisational roles.",
    "accountabilities": [
      "Designing experiments to evolve AI role‑filling capacity",
      "Running those experiments and capturing learnings",
      "Reporting daily results and monthly objectives",
      "Tracking competitor AI deployments",
      "Integrating AI partners into roles alongside humans"
    ],
    "metrics": [
      "Trend of AI FTEs deployed",
      "Impact on customer retention & spend",
      "Impact on visitor‑to‑payer conversion"
    ]
  },
  {
    "name": "Lily‑Concierge",
    "filler": "AI",
    "purpose": "Every visitor feels instantly welcomed and smoothly converted, while each conversation drives smarter service next time.",
    "accountabilities": [
      "Greeting inbound calls / chats within SLA",
      "Triaging intent and routing to next best step",
      "Guiding prospects through signup, top‑up, psychic choice",
      "Recording transcripts & metadata to analytics in <1 min",
      "Escalating red‑flags to humans promptly",
      "Experimenting with conversation variants and sharing results",
      "Tagging novel utterances for model retraining",
      "Upholding brand voice & privacy standards"
    ],
    "metrics": [
      "First‑contact conversion %",
      "Containment %",
      "CSAT score"
    ]
  },
  {
    "name": "Lily‑Whisperer",
    "filler": "HI",
    "purpose": "Turn every Lily conversation into practical insight that boosts conversion, delights customers, and trains smarter AI.",
    "accountabilities": [
      "Reviewing each Lily transcript within 24 h",
      "Tagging intents, emotions & missed‑opportunities",
      "Flagging compliance or distress cases",
      "Compiling weekly Voice‑of‑Customer digest",
      "Proposing prompt & process tweaks to Intelligence",
      "Curating RLHF datasets for model fine‑tuning",
      "Tracking impact of deployed tweaks",
      "Maintaining the tagging guideline"
    ],
    "metrics": [
      "Digest published weekly",
      "Number of fine‑tune data rows curated",
      "Conversion lift from deployed tweaks"
    ]
  }
]
```

## 3 · Modal Implementation Steps

1. **HTML / Jinja**

```html
<!-- Trigger link in sidebar -->
<li class="nav-item">
  <a class="nav-link" data-bs-toggle="modal" data-bs-target="#roleDirectory">
    Roles (Holacracy)
  </a>
</li>

<!-- Modal -->
<div class="modal fade" id="roleDirectory" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">What is the Work &amp; Where does it Live?</h5>
        <button class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="row g-3" id="roleCards"></div>
      </div>
    </div>
  </div>
</div>
```

2. **JS to load roles**

```html
<script>
fetch('/static/json/role_catalog.json')
  .then(r=>r.json())
  .then(data=>{
    const colours={AI:'psi-teal',HI:'psi-deep-purple'}
    const wrap = document.getElementById('roleCards')
    data.forEach(role=>{
      wrap.insertAdjacentHTML('beforeend',`
        <div class="col-12 col-md-6 col-lg-4">
          <div class="card h-100 shadow-sm">
            <div class="card-header text-white" style="background:var(--${colours[role.filler]});">
              <strong>${role.name}</strong>
              <span class="badge bg-light text-dark ms-2">${role.filler}-filled</span>
            </div>
            <div class="card-body small">
              <em>${role.purpose}</em>
              <hr>
              <strong>Accountabilities</strong>
              <ul>${role.accountabilities.map(a=>`<li>${a}</li>`).join('')}</ul>
              ${role.metrics ? `<strong>Metrics</strong><ul>${role.metrics.map(m=>`<li>${m}</li>`).join('')}</ul>`:''}
            </div>
          </div>
        </div>
      `)
    })
})
</script>
```

3. **CSS tweaks**

```css
.card-header{font-size:1rem;padding:.5rem .75rem}
.card-body ul{margin-bottom:.5rem}
```

## 4 · Checklist

- [ ] Add sidebar link & modal markup.  
- [ ] Place `role_catalog.json` in `/static/json/`.  
- [ ] Add JS fetch block (above) or bundle in existing JS file.  
- [ ] Verify colours use tokens (`--psi-teal`, `--psi-deep-purple`).  
- [ ] Test modal scroll & mobile behaviour.  
- [ ] Commit & deploy.

---

### That’s the whole package—once live, everyone can click **Roles (Holacracy)** and instantly see what the work is and where it lives.