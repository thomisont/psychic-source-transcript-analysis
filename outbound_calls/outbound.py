import os
import sys
import json
import logging
import argparse
from dotenv import load_dotenv
import fastapi
import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import websockets
import asyncio
import requests
from twilio.rest import Client
import uuid
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="ElevenLabs Outbound Calling Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for request and response
class OutboundCallRequest(BaseModel):
    number: str
    prompt: str = None
    first_message: str = None
    agent_id: Optional[str] = None

class CallWebhookData(BaseModel):
    conversation_id: str
    status: str
    duration: Optional[int] = None

# Configuration from environment
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Default voice ID
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") 
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Global WebSocket connection pool
ws_connections = {}

# Helper function to validate phone number format
def validate_phone_number(phone_number: str) -> bool:
    """
    Validates phone number format.
    Accepts various formats and returns True if the number is valid.
    """
    # Remove common formatting characters
    cleaned = ''.join(c for c in phone_number if c.isdigit())
    # Simple check: most countries have phone numbers between 10-15 digits
    return 10 <= len(cleaned) <= 15

async def make_elevenlabs_call(phone_number: str, message: str) -> dict:
    """
    Make an outbound call using Twilio and ElevenLabs Text-to-Speech API.
    
    Args:
        phone_number: The recipient's phone number
        message: The message to be spoken during the call
        
    Returns:
        A dictionary with call status and conversation ID
    """
    try:
        conversation_id = str(uuid.uuid4())
        logger.info(f"Initiating call to {phone_number} with conversation ID: {conversation_id}")
        
        # Ensure we have the required credentials
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
            logger.error("Twilio credentials not configured properly")
            return {
                "status": "error", 
                "message": "Twilio credentials not configured", 
                "conversation_id": conversation_id
            }
        
        # Format the phone number (add + if missing)
        if not phone_number.startswith('+'):
            phone_number = '+' + ''.join(c for c in phone_number if c.isdigit())
        
        # Initialize Twilio client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Generate TwiML for the call
        twiml = f"""
        <Response>
            <Say>{message}</Say>
            <Pause length="1"/>
            <Say>This is the end of the automated message. Goodbye.</Say>
        </Response>
        """
        
        # If ElevenLabs API key is available, generate speech for higher quality
        elevenlabs_url = None
        if ELEVENLABS_API_KEY:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
                
                headers = {
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                }
                
                data = {
                    "text": message,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.8
                    }
                }
                
                logger.info(f"Calling ElevenLabs API to generate speech for message: {message[:30]}...")
                
                # Generate the speech audio
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    logger.info("Successfully generated speech from ElevenLabs")
                    
                    # Save the audio file in a publicly accessible location
                    # In a real implementation, you would upload this to a cloud storage service
                    audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_audio")
                    os.makedirs(audio_dir, exist_ok=True)
                    
                    audio_file = os.path.join(audio_dir, f"call_{conversation_id}.mp3")
                    with open(audio_file, "wb") as f:
                        f.write(response.content)
                    
                    # For demo purposes: If we had a public URL for the audio, we would use it here
                    # elevenlabs_url = "https://your-public-url.com/audio/call_{conversation_id}.mp3"
                    
                    logger.info(f"Saved audio to {audio_file}")
                    
                    # Since we don't have a public URL for the demo, we'll use Twilio's TTS
                else:
                    logger.error(f"Error from ElevenLabs API: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error generating speech with ElevenLabs: {str(e)}")
        
        # Make the actual call with Twilio
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml,
            status_callback=f"{os.getenv('SERVICE_BASE_URL', 'http://localhost:8001')}/call-webhook",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST'
        )
        
        logger.info(f"Twilio call initiated with SID: {call.sid}")
        
        return {
            "status": "success",
            "message": "Call initiated successfully",
            "conversation_id": conversation_id,
            "call_sid": call.sid
        }
        
    except Exception as e:
        logger.error(f"Error in make_elevenlabs_call: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "conversation_id": conversation_id if 'conversation_id' in locals() else str(uuid.uuid4())
        }

@app.post("/outbound-call")
async def initiate_outbound_call(call_request: OutboundCallRequest):
    """Initiate an outbound call to the specified number"""
    
    # Validate input
    if not validate_phone_number(call_request.number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    if not call_request.first_message:
        raise HTTPException(status_code=400, detail="First message is required")
    
    try:
        logger.info(f"Initiating outbound call to {call_request.number}")
        
        # Actually attempt to make the call
        call_result = await make_elevenlabs_call(
            call_request.number, 
            call_request.first_message
        )
        
        if call_result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initiate call: {call_result.get('message')}"
            )
        
        return {
            "status": "success",
            "message": "Call initiated successfully",
            "conversation_id": call_result.get("conversation_id"),
            "call_sid": call_result.get("call_sid"),
            "details": {
                "number": call_request.number,
                "agent_id": call_request.agent_id,
                "has_prompt": bool(call_request.prompt),
                "has_first_message": bool(call_request.first_message)
            }
        }
        
    except Exception as e:
        logger.error(f"Error initiating outbound call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")

@app.post("/end-call/{call_sid}")
async def end_call(call_sid: str):
    """End an active call using Twilio"""
    try:
        logger.info(f"Attempting to end call with SID: {call_sid}")
        
        # Ensure we have the required credentials
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            logger.error("Twilio credentials not configured properly")
            raise HTTPException(
                status_code=500,
                detail="Twilio credentials not configured"
            )
        
        # Initialize Twilio client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Update the call to status 'completed' to end it
        call = twilio_client.calls(call_sid).update(status="completed")
        
        logger.info(f"Successfully ended call with SID: {call_sid}")
        
        return {
            "status": "success",
            "message": "Call ended successfully",
            "call_sid": call_sid
        }
        
    except Exception as e:
        logger.error(f"Error ending call with SID {call_sid}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end call: {str(e)}"
        )

@app.post("/call-webhook")
async def call_webhook(data: CallWebhookData):
    """Webhook endpoint for call status updates"""
    logger.info(f"Received webhook for conversation {data.conversation_id}: {data.status}")
    
    # Process webhook data based on status
    if data.status == "completed":
        logger.info(f"Call completed. Duration: {data.duration or 'unknown'} seconds")
    elif data.status == "failed":
        logger.error(f"Call failed for conversation {data.conversation_id}")
    elif data.status == "ringing":
        logger.info(f"Call ringing for conversation {data.conversation_id}")
    elif data.status == "in-progress":
        logger.info(f"Call in progress for conversation {data.conversation_id}")
    
    return {"status": "success", "message": "Webhook received"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "service": "elevenlabs-outbound-calling"}

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ElevenLabs Outbound Calling Service",
        "version": "0.1.0",
        "endpoints": {
            "/outbound-call": "POST - Initiate an outbound call",
            "/call-webhook": "POST - Webhook for call status updates",
            "/health": "GET - Service health check"
        }
    }

# Command-line interface for testing
def main():
    parser = argparse.ArgumentParser(description="ElevenLabs Outbound Calling Service")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    args = parser.parse_args()
    
    # Start the API server
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main() 