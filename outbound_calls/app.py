"""
FastAPI application for handling outbound calls.

Version: 1.0.0
Description: API server for making outbound calls using ElevenLabs' text-to-speech API
"""

import os
import uuid
import time
import json
import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Models
class CallRequest(BaseModel):
    phone_number: str
    script: str
    voice_id: Optional[str] = Field(default="EXAVITQu4vr4xnSDxMaL")  # Default ElevenLabs voice
    model_id: Optional[str] = Field(default="eleven_turbo_v2")  # Default ElevenLabs model
    webhook_url: Optional[str] = None
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Format phone number to E.164 if it's not already
        if not v.startswith('+'):
            v = f"+{v}"
        return v

class WebhookEvent(BaseModel):
    call_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]

# In-memory storage for active calls
active_calls: Dict[str, Dict[str, Any]] = {}

# Get ElevenLabs API client
async def get_elevenlabs_client():
    """
    Get configured httpx client for ElevenLabs API.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ELEVENLABS_API_KEY not set in environment")
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")
    
    base_url = os.environ.get("ELEVENLABS_API_URL", "https://api.elevenlabs.io/v1")
    
    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"xi-api-key": api_key},
        timeout=60.0
    ) as client:
        yield client

# Create FastAPI app
app = FastAPI(
    title="Outbound Calls API",
    description="API for making outbound phone calls using ElevenLabs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Check if the service is ready."""
    return {
        "status": "ok",
        "ready": True,
        "timestamp": datetime.now().isoformat(),
        "version": app.version
    }

@app.post("/call")
async def start_call(
    call_request: CallRequest,
    background_tasks: BackgroundTasks,
    elevenlabs_client: httpx.AsyncClient = Depends(get_elevenlabs_client),
):
    """
    Start a new outbound call.
    """
    try:
        call_id = str(uuid.uuid4())
        logger.info(f"Starting new call with ID: {call_id} to {call_request.phone_number}")
        
        # Make API call to ElevenLabs to initiate the call
        # In production, this would use their Phone Call API
        # For now we'll simulate the calling flow
        
        # Store call details
        call_data = {
            "call_id": call_id,
            "phone_number": call_request.phone_number,
            "script": call_request.script,
            "voice_id": call_request.voice_id,
            "model_id": call_request.model_id,
            "webhook_url": call_request.webhook_url,
            "status": "initiating",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "events": []
        }
        
        active_calls[call_id] = call_data
        
        # Start call in background
        background_tasks.add_task(
            process_call,
            call_id,
            call_request.phone_number, 
            call_request.script,
            call_request.voice_id,
            call_request.model_id
        )
        
        return {
            "call_id": call_id,
            "status": "initiating",
            "message": f"Call to {call_request.phone_number} is being initiated"
        }
    
    except Exception as e:
        logger.error(f"Error starting call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start call: {str(e)}")

@app.get("/call/{call_id}")
async def get_call_status(call_id: str):
    """
    Get the status of a call.
    """
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail=f"Call with ID {call_id} not found")
    
    call_data = active_calls[call_id]
    return {
        "call_id": call_id,
        "status": call_data["status"],
        "phone_number": call_data["phone_number"],
        "created_at": call_data["created_at"],
        "updated_at": call_data["updated_at"],
        "events": call_data.get("events", [])
    }

@app.post("/call/{call_id}/end")
async def end_call(call_id: str):
    """
    End an active call.
    """
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail=f"Call with ID {call_id} not found")
    
    call_data = active_calls[call_id]
    
    # Don't try to end calls that are already completed or failed
    if call_data["status"] in ["completed", "failed", "terminated"]:
        return {
            "call_id": call_id,
            "status": call_data["status"],
            "message": f"Call already in {call_data['status']} state"
        }
    
    # In production, this would call the ElevenLabs API to end the call
    # For now, just update the status
    call_data["status"] = "terminated"
    call_data["updated_at"] = datetime.now().isoformat()
    
    # Add event
    event = {
        "event_type": "call_terminated",
        "timestamp": datetime.now().isoformat(),
        "data": {"reason": "manual_termination"}
    }
    call_data["events"].append(event)
    
    # Send webhook if configured
    if call_data.get("webhook_url"):
        await send_webhook(
            call_data["webhook_url"],
            {
                "call_id": call_id,
                "event_type": "call_terminated",
                "timestamp": datetime.now().isoformat(),
                "data": {"reason": "manual_termination"}
            }
        )
    
    return {
        "call_id": call_id,
        "status": "terminated",
        "message": "Call has been terminated"
    }

@app.post("/webhook")
async def handle_webhook(event: WebhookEvent):
    """
    Handle webhooks from the ElevenLabs API.
    """
    call_id = event.call_id
    
    if call_id not in active_calls:
        logger.warning(f"Received webhook for unknown call ID: {call_id}")
        return {"success": False, "error": "Call ID not found"}
    
    call_data = active_calls[call_id]
    
    # Update call status based on event type
    if event.event_type == "call_started":
        call_data["status"] = "in_progress"
    elif event.event_type == "call_ended":
        call_data["status"] = "completed"
    elif event.event_type == "call_failed":
        call_data["status"] = "failed"
    
    call_data["updated_at"] = datetime.now().isoformat()
    
    # Add event to call history
    call_data["events"].append({
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "data": event.data
    })
    
    # Forward webhook to client's webhook URL if configured
    if call_data.get("webhook_url"):
        await send_webhook(
            call_data["webhook_url"],
            {
                "call_id": call_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
        )
    
    return {"success": True}

async def send_webhook(webhook_url: str, payload: Dict[str, Any]):
    """
    Send webhook to the client's webhook URL.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10.0
            )
            if response.status_code >= 400:
                logger.warning(f"Webhook failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error sending webhook: {str(e)}")

async def process_call(
    call_id: str, 
    phone_number: str, 
    script: str,
    voice_id: str,
    model_id: str
):
    """
    Process an outbound call in the background.
    
    In a production environment, this would make the actual API call to a
    service like ElevenLabs to place the phone call. For demonstration
    purposes, this simulates the call lifecycle.
    """
    try:
        # Simulating call connection
        logger.info(f"Connecting call {call_id} to {phone_number}")
        
        # Update status to connecting
        active_calls[call_id]["status"] = "connecting"
        active_calls[call_id]["updated_at"] = datetime.now().isoformat()
        
        # Simulating connection delay
        await asyncio.sleep(2)
        
        # Update status to in_progress
        active_calls[call_id]["status"] = "in_progress"
        active_calls[call_id]["updated_at"] = datetime.now().isoformat()
        
        # TODO: In production, integrate with real phone calling service
        # If using ElevenLabs, this would use their API to place the call
        
        # Add event
        event = {
            "event_type": "call_started",
            "timestamp": datetime.now().isoformat(),
            "data": {"phone_number": phone_number}
        }
        active_calls[call_id]["events"].append(event)
        
        # Send webhook if configured
        if active_calls[call_id].get("webhook_url"):
            await send_webhook(
                active_calls[call_id]["webhook_url"],
                {
                    "call_id": call_id,
                    "event_type": "call_started",
                    "timestamp": datetime.now().isoformat(),
                    "data": {"phone_number": phone_number}
                }
            )
        
        # Simulate call duration based on script length (1 second per 20 characters)
        call_duration = min(max(len(script) / 20, 10), 120)
        logger.info(f"Call {call_id} in progress, estimated duration: {call_duration} seconds")
        
        # Simulate call progress
        await asyncio.sleep(call_duration)
        
        # Check if call was manually terminated
        if active_calls[call_id]["status"] == "terminated":
            logger.info(f"Call {call_id} was manually terminated")
            return
        
        # Update status to completed
        active_calls[call_id]["status"] = "completed"
        active_calls[call_id]["updated_at"] = datetime.now().isoformat()
        
        # Add event
        event = {
            "event_type": "call_ended",
            "timestamp": datetime.now().isoformat(),
            "data": {"duration": call_duration}
        }
        active_calls[call_id]["events"].append(event)
        
        # Send webhook if configured
        if active_calls[call_id].get("webhook_url"):
            await send_webhook(
                active_calls[call_id]["webhook_url"],
                {
                    "call_id": call_id,
                    "event_type": "call_ended",
                    "timestamp": datetime.now().isoformat(),
                    "data": {"duration": call_duration}
                }
            )
        
        logger.info(f"Call {call_id} completed successfully")
        
    except Exception as e:
        # Update status to failed
        if call_id in active_calls:
            active_calls[call_id]["status"] = "failed"
            active_calls[call_id]["updated_at"] = datetime.now().isoformat()
            
            # Add event
            event = {
                "event_type": "call_failed",
                "timestamp": datetime.now().isoformat(),
                "data": {"error": str(e)}
            }
            active_calls[call_id]["events"].append(event)
            
            # Send webhook if configured
            if active_calls[call_id].get("webhook_url"):
                await send_webhook(
                    active_calls[call_id]["webhook_url"],
                    {
                        "call_id": call_id,
                        "event_type": "call_failed",
                        "timestamp": datetime.now().isoformat(),
                        "data": {"error": str(e)}
                    }
                )
        
        logger.error(f"Error processing call {call_id}: {str(e)}")

@app.on_event("startup")
async def startup():
    logger.info("Starting outbound calls service")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down outbound calls service")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True) 