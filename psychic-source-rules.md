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

# Core Project Requirements - NO SAMPLE DATA

1. NEVER include sample, mock, or demo data generation in the codebase
2. Always use real data from API endpoints or proper fallbacks
3. Handle missing data with appropriate empty states, not generated data
4. Show informative error messages rather than placeholder data
5. Ensure all visualizations show empty states for missing data
6. Display actual API counts - do not fabricate statistics
7. Use loading indicators instead of placeholder content
8. Implement proper error boundaries and recovery options

# Implementation Guidelines

## Development Workflow

- NEVER start the server inside Cursor until the user explicitly requests it
- Always wait for user approval before applying changes that affect the running application
- Allow the user to review and accept/reject proposed changes before restarting the server
- Make code changes in a way that allows proper review before execution

## Data Handling

- Never generate random data for charts or displays
- Show "No data available" messages when API returns empty results
- Validate all API responses before displaying
- Log errors but don't generate fake data to compensate

## User Interface

- Design proper empty states for all data visualizations
- Create informative error messages for API failures
- Use standard Bootstrap components for consistent styling
- Implement loading indicators during API requests

## JavaScript Best Practices

- Validate data before rendering charts
- Display empty state UI instead of generating random data
- Add timeout handling for all async operations
- Use feature detection rather than browser detection
- Separate concerns between JS, templates, and Flask routes 

## LLM Integration Best Practices

- Set ConversationAnalyzer's lightweight_mode to false for full LLM-powered analysis
- Implement comprehensive normalization for LLM responses to handle various output formats
- Add robust error handling for OpenAI API failures with appropriate fallbacks
- Use specific prompt templates designed for each analysis type (themes, questions, concerns)
- Implement response data structure parsing that can handle inconsistent outputs
- Apply a modular approach to LLM analysis with dedicated methods for different insights
- Handle incomplete or unexpected LLM responses gracefully
- Add detailed error logging for easier debugging of LLM integration issues
- For UI components showing LLM-generated insights:
  - Use appropriate component types for different data structures (accordions for questions, lists for concerns)
  - Ensure responsive design for complex nested components
  - Implement specialized empty states for each analysis section
  - Create timeline-style displays for conversation excerpts 

  Agent Session Summary
Initial Issues
The application was failing to start due to syntax errors in the app/utils/analysis.py file
After fixing initial errors, the Themes & Sentiment page was not receiving data with errors like: "ConversationAnalyzer object has no attribute 'analyze_sentiment'"
What We Fixed
Critical Syntax Errors:
Fixed syntax errors in try/except blocks that had incorrect indentation in app/utils/analysis.py
Added proper exception handling for OpenAI API calls with both new and legacy clients
Restored Missing Methods:
Added back the following critical methods that were missing:
analyze_sentiment: Basic TextBlob-based sentiment analysis for conversation transcripts
extract_aggregate_topics: Extraction of common topics across conversations
analyze_theme_sentiment_correlation: Analysis of sentiment aligned with specific themes
analyze_sentiment_over_time: Time-series analysis of sentiment trends
analyze_aggregate_sentiment: Aggregated sentiment metrics across conversations
Enhanced Development Guidelines:
Added new development workflow rules to psychic-source-rules.md:
Never start the server in Cursor until user explicitly requests it
Always wait for user approval before applying changes
Never delete or overwrite backup files without explicit permission
Create backups before making significant changes to critical files
Current Task
We're now working on enhancing the sentiment analysis capabilities in the analyze_sentiment method, as it currently uses a very basic TextBlob approach. The goal is to implement a more sophisticated sentiment analysis system that:
Is more accurate than the simple TextBlob implementation
Considers context and psychic reading domain-specific language
Can detect more nuanced emotions beyond just positive/negative
Works well with the existing architecture of the application
Codebase Learnings
The application uses a dual approach for NLP tasks:
Basic rule-based analysis with TextBlob when in lightweight mode
Advanced LLM-based analysis when OpenAI API is available
The ConversationAnalyzer class is central to all analysis features
The system has backup mechanisms that allow working in "lightweight_mode" when API access isn't available
Error handling is critical for the OpenAI integration, with support for both new and legacy client libraries
Next Steps
Implement more sophisticated sentiment analysis in the analyze_sentiment method
Consider integrating VADER (Valence Aware Dictionary and sEntiment Reasoner) for better sentiment analysis
Add domain-specific language understanding for psychic readings
Update the Project_Summary_Updates.md file with these changes (completed)
