# Release Notes – How Is Lily Doing

## [Unreleased]

## [v1.1.0] – 2025-04-18
### Added
### Changed
### Fixed
### Removed

---

## 
## [v1.0.4] – 2025-04-19
### Added
- Unified total conversation count font size to h3 on the Themes & Sentiment Analysis page.

### Changed
- Moved AI model info directly beneath the main header on the Themes & Sentiment Analysis page.

### Fixed
- Removed duplicate conversation count display.
- Corrected misalignment of the total count badge in the header area.

### Removed
- Deleted the obsolete `#conversation-count-display` `<div>` from the Themes & Sentiment template.

---

## [v1.0] – 2025‑04‑18
### Highlights
- **Production‑Ready Dashboard**: KPI cards (total conversations, avg duration, completion rate) with interactive bar/line charts for hourly, weekday, daily volume & duration trends.
- **Multi‑Agent Support**: dashboard, analytics & sync filterable by `agent_id`; agent selector stored in session.
- **Supabase ↔ ElevenLabs Sync**: background task to import/merge conversations & messages, incremental or full‑sync, skip‑if‑summary logic for speed.
- **Service‑Oriented Backend**: `SupabaseConversationService`, `AnalysisService`, `ElevenLabsClient`, clean dependency‑injection via `create_app()`.
- **Themes & Sentiment Page (LLM‑powered)**: unified full‑analysis endpoint, cached results (FileSystemCache), donut & trend charts, scrollable accordions for common questions / concerns / interactions.
- **Natural‑Language SQL Interface**: `/api/sql‑query` translates NL → safe `SELECT` via OpenAI, validates, executes through Supabase RPC, returns results + executed SQL.
- **Agent Administration Panel**: embeds live ElevenLabs widget, shows system prompt & email templates, accordion‑based UI.
- **Cost Tracking**: Month‑to‑Date credit spend vs 2 M credit budget with progress bar KPI.
- **Daily Lily Report**: generates summary text & MP3 via ElevenLabs TTS (Nichalia voice), downloadable in UI.
- **API Status Widget**: checks ElevenLabs, Supabase and database connectivity, colour‑coded list.
- **iMessage‑style Transcript Viewer & Modal**: conversation list with search, detailed transcript with avatars, timestamps, highlight support.
- **Global Sync Button**: navbar button to trigger incremental sync from any page, modal feedback on completion.
- **Environment‑Aware Config**: SQLite for dev, Supabase/Postgres for prod; `.env` secrets loaded automatically; startup documented in `STARTUP.md`.
- **Testing & Tooling**: NLTK data auto‑download, lint‑safe code, pygments log formatting, `scripts/bump_release.py` for automated changelog + git tagging.

### Fixed
- Initial port conflict (5000 → 8080 default, custom via `--port`).
- Multiple widget embed issues (now using `<elevenlabs-convai>` with `variant="expanded"`).
- Supabase RPC alias errors & date filtering bugs producing empty dashboard charts.
- Segmentation faults on Replit by enforcing SQLite for dev.

### Removed / Deprecated
- Old Engagement Metrics page (consolidated into Dashboard).
- DEMO_MODE and mock‑data paths; fallback data now labelled "generate_fallback_*" and only used when API fails.