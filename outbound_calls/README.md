# ElevenLabs Outbound Calling Integration

This package provides integration with ElevenLabs' outbound calling capabilities via their MCP (Model Context Protocol) server. It allows you to initiate outbound calls using ElevenLabs' conversational AI agents.

## Installation

1. Install the required dependencies:

```bash
pip install elevenlabs-mcp fastapi uvicorn websockets python-dotenv requests
```

2. Set up your environment variables:

Create a `.env` file with the following variables:

```
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_agent_id
OUTBOUND_SERVICE_URL=http://localhost:8000  # URL for the outbound call service
```

## Usage

This package provides three different ways to use outbound calling:

### 1. FastAPI Service (outbound.py)

The service provides a REST API for outbound calling:

```bash
python outbound.py
```

This starts a FastAPI server on port 8000 with the following endpoints:

- `POST /outbound-call`: Initiate an outbound call
- `POST /call-webhook`: Webhook for call status updates
- `GET /health`: Health check endpoint
- `GET /`: Service information

### 2. Command-line Client (client.py)

A simple command-line client to initiate calls:

```bash
python client.py --number "+1234567890" --first-message "Hello, this is an automated call from ElevenLabs."
```

Options:
- `--number`: Phone number to call (required)
- `--prompt`: Custom system prompt for the agent
- `--first-message`: First message the agent will say
- `--agent-id`: Agent ID to use for the call
- `--server`: Outbound calling service URL

### 3. Direct MCP Integration (mcp_client.py)

A client that uses the ElevenLabs MCP package directly:

```bash
python mcp_client.py --number "+1234567890" --first-message "Hello, this is an automated call."
```

Options:
- `--number`: Phone number to call (required)
- `--prompt`: Custom system prompt for the agent
- `--first-message`: First message the agent will say (required)
- `--agent-id`: Agent ID to use for the call
- `--api-key`: ElevenLabs API key
- `--server`: MCP server URL

## API Reference

### Outbound Call Request

Example request to initiate an outbound call:

```json
POST /outbound-call
{
  "number": "+1234567890",
  "prompt": "You are a helpful assistant calling to...",
  "first_message": "Hello, this is an automated call from...",
  "agent_id": "optional-agent-id-if-not-using-default"
}
```

Example response:

```json
{
  "status": "success",
  "message": "Call initiated successfully",
  "conversation_id": "some-conversation-id",
  "details": {
    "number": "+1234567890",
    "agent_id": "used-agent-id",
    "has_prompt": true,
    "has_first_message": true
  }
}
```

### Webhook for Call Status Updates

Example webhook payload:

```json
POST /call-webhook
{
  "conversation_id": "some-conversation-id",
  "status": "completed",
  "duration": 120
}
```

Valid status values:
- `ringing`: Call is ringing
- `in-progress`: Call is in progress
- `completed`: Call completed successfully
- `failed`: Call failed

## Notes on ElevenLabs MCP

The ElevenLabs MCP server is a local service that provides AI model access to ElevenLabs' API via the Model Control Protocol. It allows Claude, Cursor, and other AI assistants to use ElevenLabs capabilities, including outbound calling.

For more information, see the [ElevenLabs MCP documentation](https://elevenlabs.io/docs/mcp).

## Limitations

1. The current implementation includes placeholder code in some areas where the exact ElevenLabs MCP API specifications are not fully documented.
2. The `convai_outbound_call` method is a placeholder and may need to be adjusted based on the actual ElevenLabs MCP API.
3. This implementation assumes that the ElevenLabs MCP server is running locally or at a specified URL.

## Future Improvements

1. Add support for monitoring the call status via WebSockets
2. Implement call recording and transcription features
3. Add more robust error handling and retries
4. Create a more user-friendly web interface for initiating calls 