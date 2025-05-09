# RAG Implementation Plan (April 2025)

This document outlines the plan to implement a Retrieval-Augmented Generation (RAG) system using Supabase with `pgvector` for the Psychic Source Transcript Analysis Tool. The goal is to improve the scalability, accuracy, and cost-effectiveness of conversation analysis and enable ad-hoc natural language querying.

**Current Status:** Phase 1 complete. Ready to start Phase 2.

---

## Phase 1: Foundational RAG Setup & Ad-hoc Query Feature

**Goal:** Build the core RAG pipeline and the user-facing natural language query interface.

-   [X] **1. Environment & Database Prep:**
    -   [X] **1a.** Verify `pgvector` extension is enabled in Supabase.
    -   [X] **1b.** Add `embedding vector(1536)` column to the `conversations` table in Supabase (using OpenAI's `text-embedding-3-small` dimension).
    -   [X] **1c.** Update `requirements.txt` with necessary libraries (e.g., `openai`, `supabase-py`).

-   [X] **2. Embedding Pipeline:**
    -   [X] **2a.** Modify Sync Task (`app/tasks/sync.py`): Generate embeddings for conversation **transcripts** during sync and store them in the new Supabase column. Track truncation.
    -   [X] **2b.** Backfill Embeddings: Create and run a script (`scripts/backfill_embeddings.py`) to generate/store **transcript** embeddings for existing conversations, overwriting previous ones. Track truncation.

-   [X] **3. Core RAG Service Logic:**
    -   [X] **3a.** Supabase Service (`app/services/supabase_conversation_service.py`): Implement `find_similar_conversations(query_vector, start_date, end_date, limit=N)` using `pgvector` similarity search, filtering by date, returning IDs and summaries. (Depends on SQL function `match_conversations`).
    -   [X] **3b.** Analysis Service (`app/services/analysis_service.py`): Implement `process_natural_language_query(self, query, start_date, end_date)`.
        -   [X] Generate query embedding.
        -   [X] Call `find_similar_conversations`.
        -   [X] Construct focused LLM prompt (GPT-4o) with retrieved context + query (Lily Persona).
        -   [X] Call LLM via `ConversationAnalyzer` or direct client.
        *   [X] Return answer or error dictionary (User-friendly 0 results message).
    -   [X] **3c.** Create Supabase SQL function `match_conversations` to perform vector search with date filtering and summary check.

-   [X] **4. Ad-hoc Query UI & API:**
    -   [X] **4a.** Frontend (`themes_sentiment_refactored.html` / `.js`): Add UI elements (textarea, button, response area, loader). Implement JS to capture input, call API, display results/errors.
    -   [X] **4b.** Backend (`app/api/routes.py`): Create `POST /api/themes-sentiment/query` endpoint. Receive query/dates, call `analysis_service.process_natural_language_query`, return JSON response.

---

## Phase 2: Refactor Existing Analysis & Refinements

**Goal:** Migrate the pre-canned analyses on the Themes & Sentiment page to use the RAG pipeline and implement UI/UX enhancements.

-   [ ] **5. Refactor Pre-canned Analysis:**
    -   [ ] **5a.** Modify `AnalysisService.get_full_themes_sentiment_analysis` to use RAG: Define internal queries/prompts for each section (Sentiment Overview, Top Themes, Trends, Categories), perform vector search, retrieve context, use targeted LLM prompts, parse results to fit UI.
    -   [ ] **5b.** Update caching strategy for `get_full_themes_sentiment_analysis` based on RAG approach.

-   [ ] **6. Optimization & Evaluation:**
    -   [ ] **6a.** Monitor performance, cost, and accuracy.
    -   [ ] **6b.** Experiment with N (number of retrieved docs) and similarity threshold (currently 0.35).
    *   [ ] **6c.** Refine LLM prompts (including Lily persona consistency).
    -   [ ] **6d.** Consider embedding/retrieving different/more text (e.g., transcript chunks) if needed for specific analyses.
    -   [ ] **6e.** Explore advanced RAG techniques if necessary.

-   [ ] **7. UI/UX Enhancements for RAG Query:** (Based on user feedback)
    -   [ ] **7a. Contextual Linking:** Update RAG context generation and LLM prompt to include conversation `external_id`. Update frontend JS to parse responses and convert `(ID: ...)` into clickable links.
    -   [ ] **7b. Transcript Modal:** Implement or adapt a modal viewer triggered by the links in 7a to display the full transcript for the selected `external_id`.
    -   [ ] **7c. Session History:** Implement JS logic to store and display the user-Lily query/response history for the current browser session.
    -   [ ] **7d. Export/Copy:** Add UI buttons and JS for copying responses/history to clipboard and potentially downloading as a text file.
    -   [ ] **7e. (Optional) Contextual Follow-up:** Explore sending previous user-Lily analysis turns back to the LLM for more conversational follow-up queries.

---

## Appendix: SQL vs. Vector Databases in Supabase

Having both a traditional SQL structure and vector embeddings within Supabase isn't redundant; they serve complementary purposes and work together powerfully:

*   **SQL Database (e.g., Supabase's PostgreSQL):**
    *   **Role:** Manages **structured data** and **exact relationships**.
    *   **Strengths:**
        *   **Precise Filtering:** Efficiently filtering conversations by exact metadata (e.g., `agent_id`, `status = 'completed'`, `created_at BETWEEN 'date1' AND 'date2'`, `cost_credits > 10`).
        *   **Exact Lookups:** Quickly retrieving a conversation by its `id` or `external_id`.
        *   **Aggregations:** Calculating counts, averages, sums (e.g., `COUNT(*)`, `AVG(duration)`).
        *   **Data Integrity:** Enforcing constraints (data types, uniqueness, not null).
        *   **Joins:** Combining data from related tables (e.g., `conversations` and `messages`).
        *   **Pattern Matching:** Finding specific text patterns using `LIKE` or regex (e.g., identifying emails).
    *   **Handles:** The factual, operational data about each conversation – its ID, timestamp, duration, cost, agent, status, etc., and the structured sequence of messages.

*   **Vector Embeddings (`pgvector` within Supabase):**
    *   **Role:** Manages **semantic meaning** and enables **similarity search**.
    *   **Strengths:**
        *   **Semantic Search:** Finding conversations based on the *meaning* of their content, even if keywords don't match exactly (e.g., finding discussions about "feeling lost financially" even if the exact phrase isn't used).
        *   **Natural Language Querying:** Powering the ad-hoc query feature built in Phase 1.
        *   **Recommendation:** Finding conversations similar to a given one.
        *   **Clustering/Topic Modeling:** Grouping conversations by underlying themes based on semantic closeness.
    *   **Handles:** The unstructured text content's *meaning*, allowing you to query based on concepts and similarity.

*   **Why Together in Supabase?**
    *   **Synergy:** You can combine the strengths. For example: "Find conversations *semantically similar* to 'relationship problems' (vector search) that occurred *in the last 30 days* and involved *agent X* (SQL filter)." This is efficiently handled by the `match_conversations` SQL function.
    *   **Efficiency:** `pgvector` allows you to store and query vectors directly alongside your relational data *within the same PostgreSQL database*. This avoids the complexity and potential data consistency issues of managing two separate databases.
    *   **Completeness:** SQL manages the "what, when, who," while vectors manage the "what it means." You need both for a comprehensive understanding and querying capability.

In essence, the SQL structure organizes the *facts* about your conversations, while the vector structure understands the *meaning* of their content. They are partners, not competitors, within your Supabase database.