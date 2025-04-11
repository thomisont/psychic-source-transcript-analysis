## Project Reflection (April 9, 2025)

1.  **Core Business Function:**
    *   The application analyzes conversation transcripts (likely sourced from ElevenLabs) to provide insights into sentiment, themes, topics, and user interactions. The primary goal appears to be understanding customer/caller experiences, identifying common issues or questions, and tracking sentiment trends over time, likely for a service like Psychic Source.

2.  **Original Technical Stack & Architecture:**
    *   Python Flask web application.
    *   SQLAlchemy ORM for interacting with a local or traditional PostgreSQL database.
    *   Direct API integrations with ElevenLabs (for conversation data) and potentially OpenAI (for analysis).
    *   Services (`ConversationService`, `AnalysisService`) handling business logic.
    *   Flask routes (`app/routes.py`, `app/api/routes.py`) serving HTML templates and JSON data.
    *   Basic HTML/CSS/JavaScript frontend, likely using Bootstrap and jQuery, for displaying dashboards and analysis results.

3.  **Supabase Refactoring Initiative:**
    *   **Goal:** Migrate the primary data store from the existing SQLAlchemy-managed database to Supabase (PostgreSQL backend) to improve scalability, reduce direct API load on ElevenLabs, and enable future features like vector search (`pgvector`).
    *   **Strategy:** Implement a hybrid approach during the transition:
        *   Create a new `SupabaseConversationService` to handle interactions with Supabase tables (`conversations`, `messages`).
        *   Modify the data synchronization task (`run_sync_task.py`) to write data to *both* the old database and Supabase.
        *   Refactor application components (API routes, services) to *prioritize* using `SupabaseConversationService` but fall back to the original `ConversationService` if Supabase isn't available or fails.
        *   Inject the appropriate conversation service instance into dependent services like `AnalysisService`.

4.  **Current State & Recent Actions:**
    *   `SupabaseConversationService` has been created and integrated.
    *   The sync task (`run_sync_task.py`) writes to Supabase.
    *   A custom Supabase SQL function `execute_sql` was created to handle specific query needs.
    *   The main Dashboard (`/`) and API Status (`/api/status`) have been updated to use the new service structure and reflect Supabase status. They appear to be working correctly, retrieving conversation counts from Supabase.
    *   `AnalysisService` was refactored to accept a generic `conversation_service` dependency in its `__init__` method, aiming to decouple it from direct database access. Methods within `AnalysisService` (`get_conversation_ids`, `get_conversations_with_transcripts`) were updated to call the injected `conversation_service`.
    *   The application factory (`create_app` in `app/__init__.py`) was updated to inject the primary `conversation_service` instance into `AnalysisService`.
    *   A startup script (`start_supabase_app.sh`) was created to manage dependencies, checks, and server startup.

5.  **Current Challenges & Blockers:**
    *   **Themes & Sentiment Page:** This page (`/themes-sentiment`) remains broken. It fails to load data, showing errors like "Network response was not ok" and JavaScript console errors (`Cannot read properties of undefined (reading 'then')`).
    *   **Service Initialization Errors:** Console logs reveal critical errors during application startup after recent refactoring attempts:
        *   `TypeError: ConversationService.__init__() got an unexpected keyword argument 'db_session'` (Seen at 23:09, 23:17): This indicates that despite efforts to switch to Supabase, the *original* `ConversationService` (expecting `db` or `db_session`) is still being instantiated incorrectly in `app/__init__.py`, likely due to misconfiguration or the application not correctly selecting the Supabase service implementation.
        *   `AttributeError: 'SupabaseClient' object has no attribute 'client'` (Seen at 23:14): This error occurs within the `SupabaseConversationService` when trying to use the `execute_sql` function via the `SupabaseClient` utility. It suggests an initialization or attribute access problem within the `SupabaseClient` wrapper (`tools/supabase_client.py`).
    *   **Inconsistent Service Usage:** The application seems to be struggling to consistently use the intended `SupabaseConversationService`. Routes like `/api/themes-sentiment/data` rely on `AnalysisService`, which *should* be using the injected `SupabaseConversationService`, but the underlying errors suggest either the wrong service is being injected/used or the Supabase service itself has internal errors (`AttributeError`). The logs show `ConversationService initialized (Database Mode)` during startup, confirming the old service is still being activated, likely overriding or conflicting with the intended Supabase integration path for some parts of the app.

6.  **Technical Guidance Summary:**
    *   Continue adhering to PEP 8, type hinting, and clear documentation (docstrings).
    *   Prioritize completing the Supabase migration for data fetching and analysis.
    *   Focus on correctly initializing and injecting the `SupabaseConversationService` throughout the application, ensuring the old `ConversationService` is only used as a fallback if explicitly designed for, or phased out entirely.
    *   Resolve the internal `AttributeError` within the `SupabaseClient` or `SupabaseConversationService`.
    *   Ensure all data-accessing components (routes, services) consistently use the designated service layer (`SupabaseConversationService`).
    *   Maintain comprehensive tests, especially around the service layer and data interactions.
    *   Keep files concise (under 200-300 lines) and refactor where necessary.

---
(Previous content below this line is potentially outdated or needs integration)
---

# Psychic Source Transcript Analysis Tool - Refactoring Plan

## 1. Overall Goals

1.  **Scalability:** Handle thousands of conversations efficiently without significant performance degradation.
2.  **Maintainability:** Simplify the codebase, improve structure, adhere to best practices (PEP 8, file size limits), making future development easier.
3.  **Performance:** Reduce page load times, optimize data fetching and analysis processing.
4.  **Robustness:** Eliminate persistent UI bugs (scrolling, layout) and improve overall stability.
5.  **Modernization:** Update the architecture (database backend, optional vector storage) and potentially the UI for better long-term viability.

## 2. Proposed Architecture

*   **Backend:** Python/Flask (as is)
*   **Database:** PostgreSQL via Supabase (for conversations, transcripts, analysis results, vector embeddings).
*   **Data Processing:** Refined Python services interacting with the database. Consider a background task queue (Celery/RQ) for initial data ingestion and intensive analysis tasks.
*   **Frontend:** Refactored Jinja2 templates, cleaned CSS, and modular JavaScript. (Future: Consider modern JS framework or HTMX).
*   **Vector Storage:** Utilize Supabase's `pgvector` extension for storing and querying conversation embeddings.

## 3. Detailed Refactoring Phases

### Phase 1: Backend & Data Layer Refactoring

1.  **Supabase Setup & Schema Design:**
    *   Set up Supabase project.
    *   Design PostgreSQL schema (e.g., `conversations`, `messages`, `analysis_themes`, `analysis_sentiments`, `analysis_questions`, `analysis_concerns`, `analysis_positive_interactions`, potentially `embeddings`, analysis cache table).
    *   Define primary keys, foreign keys, and appropriate indexes (timestamps, IDs).

2.  **Data Ingestion & Synchronization:**
    *   **Initial Bulk Import Script:** Create a resumable script (Flask CLI command preferred) to fetch historical data from ElevenLabs and populate Supabase tables.
    *   **Ongoing Synchronization Service:** Modify/Create a service to periodically fetch *new* conversations and insert/update them in Supabase (potentially via background tasks).

3.  **Vector Embeddings Integration (Optional but Recommended):**
    *   Enable `pgvector` extension in Supabase.
    *   Add `vector` column to relevant table(s).
    *   Integrate embedding generation (e.g., Sentence Transformers, OpenAI) into the data sync process.
    *   Create vector index (HNSW/IVFFlat).

4.  **Service Layer Refactoring:**
    *   Adapt services (`ConversationService`, `ThemesSentimentService`, etc.) to query Supabase (using SQLAlchemy or similar).
    *   Implement logic to check for/store analysis results in the database to avoid redundant LLM calls.
    *   Break down large service files into smaller modules.

5.  **API Endpoint Refactoring:**
    *   Update Flask routes (`/api/...`) to interact with the refactored services and query Supabase.
    *   Implement database-level pagination, filtering, and sorting.
    *   Remove bulk data processing from route handlers.

6.  **Caching Strategy Review:**
    *   Prioritize caching expensive analysis results in the database.
    *   Use Flask-Caching for endpoint caching only if database queries remain bottlenecks.

### Phase 2: Frontend Refactoring

1.  **HTML Template Cleanup:**
    *   Refactor large templates (like `themes_sentiment.html`) using Jinja macros or includes.
    *   Ensure semantic HTML.
    *   Remove dead code/comments.

2.  **CSS Cleanup (`style.css`):**
    *   Reset/remove conflicting custom styles (especially for scrolling, accordions).
    *   Apply simple, standard Bootstrap patterns first (e.g., `.accordion-body .list-group { max-height: 300px; overflow-y: auto; }`).
    *   Remove unused rules, simplify selectors, minimize `!important`.

3.  **JavaScript Cleanup (`main.js` & Inline Scripts):**
    *   Remove custom logic trying to fix CSS issues (e.g., forcing scrollbars, complex height calculations). Rely on CSS.
    *   Modularize JS code. Minimize inline scripts.
    *   Ensure robust event handling for UI interactions, considering dynamically loaded content.
    *   Update API call functions to match refactored endpoints.

### Phase 3: Code Quality, Structure & Testing

1.  **Enforce File Size Limits:** Refactor Python/HTML files > ~300 lines. Use Flask Blueprints effectively.
2.  **Linting & Formatting:** Enforce `flake8` and `black`.
3.  **Testing:**
    *   Unit tests (`pytest`) for service layer functions.
    *   Integration tests for API endpoints and database interactions.
    *   Consider basic UI tests (Selenium/Playwright) for critical UI flows.
4.  **Documentation:**
    *   Update `README.md` (architecture, setup, Supabase, deployment).
    *   Ensure clear docstrings for functions/classes.
    *   Document environment variables.

## 4. Tooling & Library Suggestions

*   **Database ORM:** SQLAlchemy + `asyncpg`
*   **Background Tasks:** Celery or RQ
*   **Vector Embeddings:** Sentence Transformers or OpenAI API
*   **Code Quality:** `black`, `flake8`, `isort`
*   **Testing:** `pytest`, `pytest-cov`, Selenium/Playwright
*   **Dependencies:** `pip-tools` 