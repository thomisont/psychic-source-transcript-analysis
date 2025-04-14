# Dashboard Enhancement Plan

## 1. Overview & Goals

This plan outlines the phased development of new features for the application dashboard. The primary goals are:

1.  **Multi-Agent Support:** Adapt the dashboard to display metrics for different "Lilly" agents.
2.  **Agent Administration:** Provide tools to view agent configurations (prompt, email templates) and interact directly via an embedded widget.
3.  **Ad-Hoc SQL Querying:** Enable users to query the Supabase database using natural language.

## 2. Phased Implementation

### Phase 1: Foundation - Multi-Agent Support & Filtering

*   **Objective:** Enable selection between different Lilly agents and filter existing dashboard metrics (KPIs, charts) accordingly.
*   **Key Tasks:**
    *   **Backend:**
        *   **Data Prerequisite:** Verify/Implement association of an `agent_id` with `conversations` and `messages` in the Supabase database. Update `sync.py` if necessary to store this.
        *   **Configuration:** Define agent IDs and names (e.g., in `config.py`).
        *   **Agent API:** Create `/api/agents` endpoint to list configured agents.
        *   **Data Filtering:** Update `SupabaseConversationService` methods and the `get_message_activity_in_range` RPC function to accept and filter by `agent_id`.
        *   **Dashboard API:** Update `/api/dashboard/stats` to accept and pass `agent_id`.
    *   **Frontend (`dashboard.js`, `index.html`):
        *   **Agent Selector:** Implement a UI dropdown, populate via `/api/agents`.
        *   **State Management:** Store selected `agent_id` (e.g., `sessionStorage`).
        *   **API Calls:** Pass selected `agent_id` to `/api/dashboard/stats`.
        *   **Default:** Load "Curious Caller" agent data by default.
*   **Outcome:** Dashboard displays data filtered by the selected agent.

### Phase 2: Agent Administration Panel (View-Only & Interaction)

*   **Objective:** Add a dashboard section for viewing agent details and direct interaction.
*   **Key Tasks:**
    *   **UI Structure:** Add a new collapsible section/row to `index.html` for "Agent Administration".
    *   **Backend:**
        *   **Widget Config API:** Create `/api/agents/<agent_id>/widget-config` endpoint. (Implementation: May need to call `mcp_elevenlabs_Get_Agent_Widget_Config` or similar ElevenLabs API).
        *   **Prompt API:** Create `/api/agents/<agent_id>/prompt` endpoint. (Implementation: Fetch from ElevenLabs API or internal config; mock if needed initially).
        *   **Email Template APIs:** Create `/api/email-templates/team` and `/api/email-templates/caller` endpoints. (Implementation: Read static HTML template files from the project, e.g., `app/templates/email/`).
    *   **Frontend (`dashboard.js`, `index.html`):
        *   **Widget Display:** Add UI element (e.g., button opening a modal) to embed the ElevenLabs widget using config from `/widget-config` API.
        *   **Prompt Viewer:** Fetch prompt text from `/prompt` API and display in a designated area (e.g., `<pre>` tag or basic Markdown viewer).
        *   **Email Viewers:** Fetch HTML content from `/email-templates/*` APIs and display in designated areas (e.g., `<iframe>` or `<div>` using `innerHTML`).
        *   **Data Fetching:** Trigger API calls for the selected agent's details on load/agent change.
*   **Outcome:** New dashboard section allows users to interact with the selected agent via the widget and view its system prompt (as Markdown) and outbound email templates (as HTML).

### Phase 3: Ad-Hoc SQL Interface (Basic Implementation)

*   **Objective:** Implement a natural language interface for querying the Supabase database.
*   **Key Tasks:**
    *   **UI Structure:** Add a new collapsible section/row to `index.html` for "Ask Lilly SQL". Include prompt input, submit button, and results area.
    *   **Backend:**
        *   **SQL Query API:** Create `/api/sql-query` endpoint accepting natural language text.
        *   **LLM Integration (Recommended):** Use LLM to translate natural language to a safe, read-only (`SELECT`) SQL query targeting known tables (`conversations`, `messages`).
        *   **SQL Validation (CRITICAL):** Implement strict validation: **MUST** be `SELECT` only. Reject all other statement types. Consider complexity/resource limits.
        *   **Query Execution:** Use `supabase-py` client (`supabase.sql()` or RPC `execute_sql`) within Flask to run the *validated* SQL. **DO NOT** call MCP `execute_sql` tool from backend code.
        *   **Response:** Return JSON results or errors.
    *   **Frontend (`dashboard.js`, `index.html`):
        *   **API Call:** Send prompt text to `/api/sql-query` on submit.
        *   **Display:** Render JSON results or errors in the results area (e.g., `<pre>` tag or simple table).
*   **Outcome:** Users can ask database questions in natural language (e.g., "show me messages with emails"), and the dashboard displays the raw SQL results.

### Phase 4: Refinements & Enhancements

*   **Objective:** Improve the functionality, usability, and robustness of features from Phases 1-3.
*   **Potential Tasks:**
    *   **Agent Admin:** Implement *editing* for prompts/email templates (if feasible). Improve display formatting.
    *   **SQL Interface:** Enhance LLM for SQL generation/result formatting. Improve validation. Add query history.
    *   **Agent-Specific Features:** Develop unique dashboard views/metrics for other agent types.
    *   **Error Handling:** Improve feedback for API/SQL/LLM errors.
    *   **UI Polish:** Refine layout, styling, responsiveness.

## 3. Key Considerations

*   **Agent ID Data:** Confirm `agent_id` association in DB/sync task before starting Phase 1.
*   **API Capabilities:** Feasibility of viewing/editing prompts, widget config, etc., depends on ElevenLabs API.
*   **SQL Security:** Phase 3 validation is paramount. Start restrictively.
*   **LLM Integration:** Adds cost/latency; consider caching.
*   **UI Density:** Use collapsible sections and clear hierarchy.

## 4. Progress Tracking

*(To be updated as phases/tasks are completed)*

*   [ ] Phase 1: Multi-Agent Support & Filtering
*   [ ] Phase 2: Agent Administration Panel
*   [ ] Phase 3: Ad-Hoc SQL Interface
*   [ ] Phase 4: Refinements & Enhancements 