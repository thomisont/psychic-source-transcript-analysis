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

# Deployment Guide for How's Lily Doing

This guide provides instructions for deploying the application to production and switching between development and production environments.

## Environment Setup

### Required Environment Variables

For both development and production, you need these core environment variables:

```
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_agent_id
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=a_strong_random_key
```

### Development Environment (Default)

In development mode, the application runs with:
- Debug mode enabled
- CORS allowing all origins
- Default URL: http://localhost:5000

To run in development mode:
```
FLASK_ENV=development
# BASE_URL is optional in development, defaults to http://localhost:5000
```

### Production Environment

In production mode, the application:
- Disables debug mode
- Restricts CORS to the production domain
- Uses https://howislilydoing.org as the default URL

To configure for production:
```
FLASK_ENV=production
# Optional: BASE_URL defaults to https://howislilydoing.org
```

## Replit Deployment Procedure

1. Go to your Replit project dashboard
2. Navigate to the "Secrets" tab
3. Add the following secrets:
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = (generate a strong random key)
   - `ELEVENLABS_API_KEY` = (your ElevenLabs API key)
   - `ELEVENLABS_AGENT_ID` = (your agent ID)
   - `OPENAI_API_KEY` = (your OpenAI API key)
   - `BASE_URL` = (optional, defaults to https://howislilydoing.org)

4. Deploy using the Replit deployment feature
5. Set up your custom domain (howislilydoing.org) in Replit's domain settings

## Switching Between Environments

### Local Development After Deployment

After deploying to production, you can continue local development by:

1. Using a `.env` file with:
   ```
   FLASK_ENV=development
   SECRET_KEY=dev_key_for_testing
   ELEVENLABS_API_KEY=your_key
   ELEVENLABS_AGENT_ID=your_agent_id
   OPENAI_API_KEY=your_key
   ```

2. Run the application locally:
   ```
   flask run
   ```

### Updating Production

To update the production deployment:

1. Push your changes to the repository
2. In Replit, pull the latest changes
3. Click "Deploy" in the Replit interface

The application will automatically detect that it's in production mode and configure itself accordingly.

## Troubleshooting

If your deployment has issues:

1. Check the Replit logs for errors
2. Verify all required secrets are set
3. Ensure FLASK_ENV is set to "production"
4. If CORS issues occur, verify your domain is properly configured in the BASE_URL 