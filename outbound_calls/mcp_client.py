"""
Client for making outbound calls using the ElevenLabs MCP API.
"""

import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class OutboundCallClient:
    """
    Client for interacting with the ElevenLabs MCP Calling API.
    Handles making outbound calls, checking status, and processing webhooks.
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None) -> None:
        """
        Initialize the client with API credentials.
        
        Args:
            api_key: ElevenLabs API key
            base_url: Base URL for the ElevenLabs MCP API (optional)
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.elevenlabs.io/v1/mcp"
        self.session = requests.Session()
        self.session.headers.update({
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        logger.info(f"Initialized OutboundCallClient with base URL: {self.base_url}")
    
    def start_call(
        self, 
        phone_number: str, 
        script: str, 
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_monolingual_v1",
        webhook_url: Optional[str] = None,
        assistant_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start an outbound call to the specified phone number.
        
        Args:
            phone_number: The recipient's phone number in E.164 format
            script: Initial script to be read to the recipient
            voice_id: ElevenLabs voice ID to use
            model_id: ElevenLabs model ID to use
            webhook_url: URL to receive webhook events (optional)
            assistant_config: Additional assistant configuration (optional)
            
        Returns:
            Dict containing call information including the call_id
        """
        try:
            logger.info(f"Starting call to {phone_number}")
            
            # Build the request payload
            payload = {
                "phone_number": phone_number,
                "voice_id": voice_id,
                "model_id": model_id,
                "initial_message": script,
            }
            
            # Add optional parameters if provided
            if webhook_url:
                payload["webhook_url"] = webhook_url
                
            if assistant_config:
                payload["assistant_config"] = assistant_config
            
            # Make the API request
            response = self.session.post(
                f"{self.base_url}/call",
                json=payload,
                timeout=30,  # 30 second timeout
            )
            
            # Check for successful response
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Call started successfully with ID: {result.get('call_id')}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            
            # Handle different types of request exceptions
            if hasattr(e, 'response') and e.response is not None:
                # If we have a response, try to get the error details
                try:
                    error_detail = e.response.json()
                    logger.error(f"API error response: {error_detail}")
                    
                    # Raise a more informative error
                    error_message = error_detail.get('detail', str(e))
                    raise ValueError(f"Failed to start call: {error_message}")
                except (ValueError, json.JSONDecodeError):
                    # If we can't parse the JSON response
                    logger.error(f"Non-JSON error response: {e.response.text}")
                    raise ValueError(f"Failed to start call: {e.response.status_code} - {e.response.text}")
            else:
                # Network error, timeout, etc.
                raise ValueError(f"Failed to start call: {str(e)}")
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get the status of an ongoing call.
        
        Args:
            call_id: The ID of the call to check
            
        Returns:
            Dict containing call status information
        """
        try:
            logger.info(f"Getting status for call {call_id}")
            
            # Make the API request
            response = self.session.get(
                f"{self.base_url}/call/{call_id}",
                timeout=10,  # 10 second timeout
            )
            
            # Check for successful response
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Call status retrieved: {result.get('status', 'unknown')}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get call status: {str(e)}")
            
            # Handle different types of exceptions
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_message = error_detail.get('detail', str(e))
                    raise ValueError(f"Failed to get call status: {error_message}")
                except (ValueError, json.JSONDecodeError):
                    raise ValueError(f"Failed to get call status: {e.response.status_code} - {e.response.text}")
            else:
                raise ValueError(f"Failed to get call status: {str(e)}")
    
    def end_call(self, call_id: str) -> Dict[str, Any]:
        """
        End an active call.
        
        Args:
            call_id: The ID of the call to end
            
        Returns:
            Dict containing the call ending status
        """
        try:
            logger.info(f"Ending call {call_id}")
            
            # Make the API request
            response = self.session.post(
                f"{self.base_url}/call/{call_id}/end",
                timeout=10,  # 10 second timeout
            )
            
            # Check for successful response
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Call ended successfully: {call_id}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to end call: {str(e)}")
            
            # Handle different types of exceptions
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_message = error_detail.get('detail', str(e))
                    raise ValueError(f"Failed to end call: {error_message}")
                except (ValueError, json.JSONDecodeError):
                    raise ValueError(f"Failed to end call: {e.response.status_code} - {e.response.text}")
            else:
                raise ValueError(f"Failed to end call: {str(e)}")
    
    def process_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a webhook event from the calling service.
        
        Args:
            event: The webhook event data
            
        Returns:
            Dict containing the processed event status
        """
        event_type = event.get("event_type")
        call_id = event.get("call_id")
        
        logger.info(f"Processing webhook event: {event_type} for call {call_id}")
        
        # Handle different event types
        if event_type == "call.started":
            logger.info(f"Call {call_id} has started")
        elif event_type == "call.ended":
            reason = event.get("data", {}).get("reason", "unknown")
            logger.info(f"Call {call_id} has ended. Reason: {reason}")
        elif event_type == "call.failed":
            error = event.get("data", {}).get("error", "unknown error")
            logger.error(f"Call {call_id} failed: {error}")
        elif event_type == "message.received":
            message = event.get("data", {}).get("text", "")
            logger.info(f"Received message in call {call_id}: {message}")
        elif event_type == "message.sent":
            message = event.get("data", {}).get("text", "")
            logger.info(f"Sent message in call {call_id}: {message}")
        else:
            logger.warning(f"Unknown event type: {event_type} for call {call_id}")
        
        return {
            "status": "processed",
            "event_type": event_type,
            "call_id": call_id,
            "timestamp": time.time()
        } 