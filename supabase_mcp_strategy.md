# Supabase MCP Tool Integration Strategy

This document outlines the agreed-upon strategy for leveraging the official Supabase Model Context Protocol (MCP) server tools within the Psychic Source Agent project development workflow.

## 1. Core Data Access (Application Backend)

*   **Strategy:** Continue using the `supabase-py` library within the Python/Flask backend services (`supabase_conversation_service.py`, `analysis_service.py`, etc.) and background tasks (`sync.py`).
*   **Tools Used:** `supabase-py` methods (`select`, `insert`, `update`, `rpc`, etc.).
*   **Rationale:** `supabase-py` provides a more idiomatic, maintainable, and potentially performant interface for standard application database operations compared to constructing raw SQL for the `execute_sql` MCP tool for every interaction. The existing implementation relies on this.
*   **MCP Tool Avoidance:** Do **not** replace routine `supabase-py` calls with `mcp_supabase_execute_sql`.

## 2. Database Modifications & State Verification

*   **Strategy (Schema Changes):** Use **Alembic** as the primary tool for version-controlled database schema migrations (e.g., adding tables/columns, modifying constraints). Follow standard Alembic workflows (`alembic revision`, `alembic upgrade`).
*   **Strategy (Complex/Direct Changes):** For complex changes (e.g., updating RLS policies, creating/modifying database functions, applying specific DDL/DML that is difficult via Alembic or `supabase-py`), use the **`mcp_supabase_execute_sql`** tool *within the AI development assistant context* (e.g., Cursor Agent/Chat).
    *   **Rationale:** This provides a direct, reliable way to apply specific SQL without generating intermediate Python code or requiring manual execution in the Supabase dashboard.
*   **Strategy (Verification):** Use MCP tools like **`mcp_supabase_list_tables`**, **`mcp_supabase_list_migrations`**, **`mcp_supabase_list_extensions`** to verify the database state before and after applying modifications via *any* method (Alembic or `execute_sql`).
*   **Strategy (Tracked One-off DDL):** Only consider using **`mcp_supabase_apply_migration`** if a specific DDL change needs to be registered within Supabase's internal migration tracking system *separately* from Alembic. This is expected to be rare.

## 3. Debugging & Querying

*   **Strategy (Troubleshooting):** Use **`mcp_supabase_get_logs`** to fetch logs directly from Supabase services (API, Postgres, Auth, etc.) when diagnosing platform-level errors.
*   **Strategy (Dev Queries):** Use **`mcp_supabase_execute_sql`** frequently *within the AI development assistant context* for ad-hoc data exploration, verifying data state, and debugging application logic (e.g., searching for specific patterns in tables).
*   **Future Idea (User-Facing SQL):** The concept of allowing users ("Ask Lily SQL") to run ad-hoc queries via natural language is noted but **deferred**. Implementing this securely requires significant design effort around prompt engineering, SQL validation, schema restriction, and resource limiting, far beyond simply calling `execute_sql`.

## 4. Development Workflow Enhancement

*   **Strategy:** Regularly generate TypeScript types from the Supabase schema using **`mcp_supabase_generate_typescript_types`**.
*   **Action:** Store the generated types in a designated file within the project (e.g., `types/supabase.ts`).
*   **Process:** Re-run the generation command after applying significant database schema changes (via Alembic or `execute_sql`) to keep frontend types synchronized with the backend data structures.
*   **Rationale:** Improves frontend development by providing type safety, editor autocomplete, and explicit documentation of expected data structures, reducing runtime errors.

## 5. Management/Ops Tools

*   **Strategy:** Use other MCP tools like `mcp_supabase_list_projects`, `get_project`, `pause_project`, `list_organizations`, etc., on an as-needed basis for administrative or operational tasks related to managing the Supabase project itself, usually invoked directly via the AI assistant. These are generally not integrated into the application code. 