# ElevenLabs MCP Tool Integration Strategy

This document outlines the agreed-upon strategy for leveraging the official ElevenLabs Model Context Protocol (MCP) server tools within the Psychic Source Transcript Analysis Tool project development workflow.

## 1. Goal

Integrate relevant ElevenLabs MCP tools to improve development workflow, debugging, and potentially enhance application features, while respecting the existing, optimized `ElevenLabsClient` and `sync.py` task for core data fetching.

## 2. Core Data Fetching (`app/tasks/sync.py`)

*   **Strategy:** **DO NOT** replace the existing custom `app.api.elevenlabs_client.ElevenLabsClient` calls within the critical `sync.py` task with MCP tool calls at this time.
*   **Tools Avoided:** `Get_Conversations`, `Get_Conversation_Details` (within `sync.py`).
*   **Rationale:** The existing `sync.py` logic is heavily optimized for incremental updates and minimizing expensive API calls based on conversation summary status stored in our Supabase database. Replicating this precisely with MCP tools is complex, risky, and may negate performance gains. The custom client is working and tailored to this specific need.

## 3. Debugging & Development Workflow Enhancement

*   **Strategy:** Actively use relevant ElevenLabs MCP tools *within the AI development assistant context* (e.g., Cursor Agent/Chat) for ad-hoc debugging, data exploration, and verification.
*   **Tools Used:**
    *   `List_Agents`: Confirm the Agent ID ("Lily") being used is correct.
    *   `Get_Conversations`: List recent conversations directly from the API to compare against the database or troubleshoot sync issues.
    *   `Get_Conversation_Details`: Fetch raw details for a *specific* conversation ID from ElevenLabs to compare with database records or debug parsing issues in `_adapt_conversation_details`.
    *   `Get_Conversation_Audio`: Fetch conversation audio to manually verify quality or content if transcripts seem questionable.
*   **Rationale:** Provides direct access to the ElevenLabs API without running the application or the full sync task, significantly speeding up debugging cycles.

## 4. Potential Future Application Enhancements

*   **Strategy:** Consider integrating specific MCP tools to add new user-facing features in the future.
*   **Potential Tools:**
    *   `Get_Conversation_Audio`: Integrate into the UI to allow users to play back call audio alongside the transcript.
    *   `Send_Conversation_Feedback`: Build a feature allowing users to submit feedback/ratings for conversations directly from the UI.
*   **Status:** These are ideas for future consideration, requiring dedicated backend and frontend development.

## 5. Admin/Management

*   **Strategy:** Use relevant MCP tools via the AI assistant for operational checks or administration as needed.
*   **Tools Used:**
    *   `List_Agents`
    *   `Get_User_Info`
    *   `Get_User_Subscription_Info`

## 6. Out-of-Scope Tools

The following categories of ElevenLabs MCP tools are generally **not relevant** to the current scope of this *transcript analysis* application:

*   Text-to-Speech (TTS) & Speech-to-Speech (STS) tools
*   Voice Cloning & Generation tools
*   Sound Generation tools
*   History tools specifically for *generated* audio items (use Convai tools for agent conversations)
*   Studio Project & Chapter management tools
*   Pronunciation Dictionary tools
*   Dubbing tools
*   Knowledge Base / RAG tools

These should generally be ignored unless the project's core requirements change significantly.

## 7. Implementation

*   This strategy is now adopted.
*   The primary implementation involves using the "Debugging & Development Workflow" tools interactively via the AI assistant as needed during development.
*   No immediate changes to the core application codebase (`sync.py`, `elevenlabs_client.py`) are planned based on this strategy. 