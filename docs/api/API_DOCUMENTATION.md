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

# Psychic Source Transcript Analysis Tool - API Documentation

## Overview

This document provides detailed information about the API endpoints available in the Psychic Source Transcript Analysis Tool. The application provides a RESTful API for retrieving and analyzing conversation data from the ElevenLabs Conversational Voice Agent.

## Authentication

The API uses the ElevenLabs API key for authentication. This key is configured in the `.env` file and is automatically used by the internal API client.

## Base URL

All API endpoints are relative to the base URL of the application. For local development, this is typically:

```
http://localhost:3000
```

## Response Format

All API responses are in JSON format. Successful responses include the requested data, while error responses include an error message.

Error response example:

```json
{
  "error": "Error message details"
}
```

## API Endpoints

### Conversations

#### Get Conversations

Retrieves a list of conversations, with optional filtering by date range.

```
GET /api/conversations
```

**Query Parameters:**

| Parameter  | Type   | Description                           | Required |
|------------|--------|---------------------------------------|----------|
| start_date | string | Start date filter in ISO format (YYYY-MM-DD) | No       |
| end_date   | string | End date filter in ISO format (YYYY-MM-DD)   | No       |
| limit      | integer| Maximum number of conversations to return | No       |
| offset     | integer| Offset for pagination                 | No       |

**Response:**

```json
{
  "conversations": [
    {
      "conversation_id": "string",
      "start_time": "string (ISO datetime)",
      "end_time": "string (ISO datetime)",
      "duration": "integer (seconds)",
      "turn_count": "integer",
      "status": "string",
      "agent_id": "string",
      "agent_name": "string"
    }
  ],
  "total_count": "integer"
}
```

#### Get Conversation Details

Retrieves details for a specific conversation.

```
GET /api/conversations/:conversation_id
```

**Path Parameters:**

| Parameter      | Type   | Description              | Required |
|----------------|--------|--------------------------|----------|
| conversation_id| string | ID of the conversation   | Yes      |

**Response:**

```json
{
  "conversation_id": "string",
  "start_time": "string (ISO datetime)",
  "end_time": "string (ISO datetime)",
  "duration": "integer (seconds)",
  "status": "string",
  "transcript": [
    {
      "speaker": "string",
      "text": "string",
      "timestamp": "string (ISO datetime)",
      "sentiment": "number"
    }
  ]
}
```

### Analysis

#### Get Themes and Sentiment Data

Analyzes themes and sentiment across multiple conversations.

```
GET /api/themes-sentiment/data
```

**Query Parameters:**

| Parameter  | Type   | Description                           | Required |
|------------|--------|---------------------------------------|----------|
| start_date | string | Start date filter in ISO format (YYYY-MM-DD) | No       |
| end_date   | string | End date filter in ISO format (YYYY-MM-DD)   | No       |
| timeframe  | string | Timeframe for aggregation (day, week, month) | No       |

**Response:**

```json
{
  "status": "string",
  "data": {
    "sentiment_over_time": "object",
    "topics_over_time": "object",
    "timeframe": "string",
    "conversation_count": "integer"
  },
  "metadata": {
    "start_date": "string",
    "end_date": "string",
    "timeframe": "string",
    "conversation_count": "integer"
  }
}
```

### Dashboard

#### Get Dashboard Statistics

Provides summary statistics for the dashboard.

```
GET /api/dashboard/stats
```

**Query Parameters:**

| Parameter  | Type   | Description                           | Required |
|------------|--------|---------------------------------------|----------|
| start_date | string | Start date filter in ISO format (YYYY-MM-DD) | No       |
| end_date   | string | End date filter in ISO format (YYYY-MM-DD)   | No       |
| timeframe  | string | Preset timeframe (last_7_days, last_30_days, last_90_days) | No |

**Response:**

```json
{
  "total_conversations": "integer",
  "total_duration": "integer (seconds)",
  "avg_duration": "number (seconds)",
  "daily_counts": "object (date: count)",
  "hour_distribution": "object (hour: count)",
  "weekday_distribution": "object (day: count)",
  "completion_rate": "number (percentage)"
}
```

### Visualization

#### Get Visualization Data

Provides data for visualizations.

```
GET /api/visualization/data
```

**Query Parameters:**

| Parameter  | Type   | Description                           | Required |
|------------|--------|---------------------------------------|----------|
| start_date | string | Start date filter in ISO format (YYYY-MM-DD) | No       |
| end_date   | string | End date filter in ISO format (YYYY-MM-DD)   | No       |
| timeframe  | string | Preset timeframe (last_7_days, last_30_days, last_90_days) | No |

**Response:**

```json
{
  "volume": {
    "labels": "array of dates",
    "data": "array of counts"
  },
  "duration": {
    "labels": "array of dates",
    "data": "array of durations"
  },
  "time_of_day": {
    "labels": "array of hours",
    "data": "array of counts"
  },
  "day_of_week": {
    "labels": "array of days",
    "data": "array of counts"
  },
  "completion": {
    "labels": "array of dates",
    "data": "array of percentages"
  }
}
```

### Export

#### Export Data

Exports data in different formats.

```
GET /api/export/:format
```

**Path Parameters:**

| Parameter | Type   | Description                  | Required |
|-----------|--------|------------------------------|----------|
| format    | string | Export format (json, csv, md)| Yes      |

**Query Parameters:**

| Parameter      | Type   | Description                      | Required |
|----------------|--------|----------------------------------|----------|
| type           | string | Data type (conversation, conversations) | No |
| conversation_id| string | ID of the conversation (for type=conversation) | No |
| start_date     | string | Start date filter in ISO format (for type=conversations) | No |
| end_date       | string | End date filter in ISO format (for type=conversations) | No |

**Response:**

File download with appropriate MIME type.

## Error Codes

| Status Code | Description           | Possible Cause                                |
|-------------|-----------------------|----------------------------------------------|
| 400         | Bad Request           | Invalid parameters or missing required fields |
| 404         | Not Found             | Resource not found                           |
| 500         | Internal Server Error | Server-side error during processing          |

## Rate Limiting

The ElevenLabs API may enforce rate limits. The application implements caching to minimize API calls and handle rate limiting gracefully.

## Caching

API responses are cached to improve performance:

- `test_connection`: Cached for 10 minutes
- `get_conversations`: Cached for 1 hour
- `get_conversation_details`: Cached for 24 hours

Cache can be cleared by restarting the application.

## Service Layer

The API endpoints are implemented through a service layer that provides:

- `ConversationService`: Handles retrieving and processing conversation data
- `AnalysisService`: Handles analyzing conversation data
- `ExportService`: Handles exporting data in different formats

## Examples

### Example: Get Recent Conversations

```bash
curl -X GET "http://localhost:3000/api/conversations?limit=10"
```

### Example: Get Conversation Details

```bash
curl -X GET "http://localhost:3000/api/conversations/abc123"
```

### Example: Export Conversation as JSON

```bash
curl -X GET "http://localhost:3000/api/export/json?type=conversation&conversation_id=abc123"
```

### Example: Get Theme and Sentiment Analysis

```bash
curl -X GET "http://localhost:3000/api/themes-sentiment/data?timeframe=day"
```

## Troubleshooting

### Common Issues

1. **API Key Issues**: Ensure your ElevenLabs API key is correctly set in the `.env` file.
2. **No Data Returned**: Check that the date range specified contains data.
3. **Slow Responses**: For large data sets, consider using pagination with the `limit` and `offset` parameters.

### Debugging

Enable debug logging by setting the `LOG_LEVEL` environment variable to `DEBUG` in the `.env` file. 