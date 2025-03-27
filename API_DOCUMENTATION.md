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