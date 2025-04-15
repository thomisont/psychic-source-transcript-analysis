"""
Client for the Outbound Call API.

This module provides a client for interacting with the Outbound Call API.
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class OutboundCallApiClient:
    """
    Client for the Outbound Call API.
    
    This client provides methods to interact with the Outbound Call API for making
    phone calls to real phone numbers using ElevenLabs' voice synthesis technology.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        test_connection: bool = True
    ):
        """
        Initialize the Outbound Call API client.
        
        Args:
            base_url: The base URL of the Outbound Call API.
                If not provided, it will be read from the OUTBOUND_CALL_API_URL environment variable.
            test_connection: Whether to test the connection to the API during initialization.
        """
        self.base_url = base_url or os.environ.get("OUTBOUND_CALL_API_URL", "http://localhost:8000")
        
        # Ensure the base URL has a trailing slash
        if not self.base_url.endswith("/"):
            self.base_url += "/"
        
        if test_connection:
            self._test_connection()
    
    def _test_connection(self) -> bool:
        """
        Test the connection to the Outbound Call API.
        
        Returns:
            True if the connection is successful, False otherwise.
        """
        try:
            response = self._make_request("GET", "")
            if response.status_code == 200:
                logger.info(f"Successfully connected to Outbound Call API at {self.base_url}")
                return True
            else:
                logger.error(f"Failed to connect to Outbound Call API: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to Outbound Call API: {str(e)}")
            return False
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make a request to the Outbound Call API.
        
        Args:
            method: The HTTP method to use.
            endpoint: The API endpoint to call.
            json_data: Optional JSON data to send in the request body.
            params: Optional query parameters to include in the request.
            
        Returns:
            The HTTP response.
            
        Raises:
            requests.exceptions.RequestException: If the request fails.
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=60
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    def start_call(
        self,
        phone_number: str,
        script: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start an outbound call.
        
        Args:
            phone_number: The phone number to call in E.164 format (e.g., +12345678901).
            script: The script for the call.
            voice_id: Optional voice ID to use for the call.
            model_id: Optional model ID to use for the call.
            webhook_url: Optional webhook URL to receive call events.
            
        Returns:
            The call information including call ID and status.
            
        Raises:
            ValueError: If the request fails.
        """
        # Ensure phone number is in E.164 format
        if not phone_number.startswith('+'):
            phone_number = f"+{phone_number}"
        
        logger.info(f"Starting call to {phone_number}")
        
        payload = {
            "phone_number": phone_number,
            "script": script
        }
        
        if voice_id:
            payload["voice_id"] = voice_id
        
        if model_id:
            payload["model_id"] = model_id
            
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        try:
            response = self._make_request("POST", "call", json_data=payload)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Call initiated successfully: {json.dumps(result)}")
                return result
            else:
                error_msg = f"Failed to start call: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Error starting call: {str(e)}")
            raise ValueError(f"Failed to start call: {str(e)}")
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get the status of a call.
        
        Args:
            call_id: The ID of the call.
            
        Returns:
            The call information including call ID and status.
            
        Raises:
            ValueError: If the request fails.
        """
        logger.info(f"Getting status for call {call_id}")
        
        try:
            response = self._make_request("GET", f"call/{call_id}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Call status: {result['status']}")
                return result
            else:
                error_msg = f"Failed to get call status: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Error getting call status: {str(e)}")
            raise ValueError(f"Failed to get call status: {str(e)}")
    
    def end_call(self, call_id: str) -> Dict[str, Any]:
        """
        End an active call.
        
        Args:
            call_id: The ID of the call to end.
            
        Returns:
            The result of ending the call.
            
        Raises:
            ValueError: If the request fails.
        """
        logger.info(f"Ending call {call_id}")
        
        try:
            response = self._make_request("POST", f"call/{call_id}/end")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Call ended: {json.dumps(result)}")
                return result
            else:
                error_msg = f"Failed to end call: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Error ending call: {str(e)}")
            raise ValueError(f"Failed to end call: {str(e)}")

def make_test_call(
    phone_number: str,
    script: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    wait_for_completion: bool = True,
    base_url: Optional[str] = None,
    timeout: int = 180
) -> Dict[str, Any]:
    """
    Make a test call and optionally wait for its completion.
    
    Args:
        phone_number: The phone number to call in E.164 format.
        script: The script for the call.
        voice_id: Optional voice ID to use for the call.
        model_id: Optional model ID to use for the call.
        wait_for_completion: Whether to wait for the call to complete.
        base_url: Optional base URL for the Outbound Call API.
        timeout: Maximum time in seconds to wait for call completion.
        
    Returns:
        The call information after completion or timeout.
    """
    client = OutboundCallApiClient(base_url=base_url)
    
    # Start the call
    call_info = client.start_call(
        phone_number=phone_number,
        script=script,
        voice_id=voice_id,
        model_id=model_id
    )
    
    call_id = call_info["call_id"]
    logger.info(f"Call initiated with ID: {call_id}")
    
    if not wait_for_completion:
        return call_info
    
    # Wait for call completion
    start_time = time.time()
    terminal_states = ["completed", "failed", "terminated"]
    
    while time.time() - start_time < timeout:
        try:
            call_info = client.get_call_status(call_id)
            status = call_info["status"]
            
            logger.info(f"Call status: {status}")
            
            if status in terminal_states:
                logger.info(f"Call {call_id} reached terminal state: {status}")
                return call_info
            
            time.sleep(5)  # Poll every 5 seconds
            
        except Exception as e:
            logger.error(f"Error polling call status: {str(e)}")
            time.sleep(5)  # Continue polling even if there's an error
    
    logger.warning(f"Call {call_id} did not complete within {timeout} seconds")
    
    try:
        # Try to end the call if it timed out
        client.end_call(call_id)
        logger.info(f"Call {call_id} manually terminated after timeout")
    except Exception as e:
        logger.error(f"Error ending call after timeout: {str(e)}")
    
    # Return final status
    try:
        return client.get_call_status(call_id)
    except Exception:
        return {"call_id": call_id, "status": "unknown", "error": "Timed out and failed to get final status"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outbound Call API Client CLI")
    parser.add_argument("phone_number", help="Phone number to call in E.164 format (e.g., +12345678901)")
    parser.add_argument("script", help="Script for the call")
    parser.add_argument("--voice-id", help="Voice ID for the call")
    parser.add_argument("--model-id", help="Model ID for the call")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for call completion")
    parser.add_argument("--base-url", help="Base URL for the Outbound Call API")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds when waiting for call completion")
    
    args = parser.parse_args()
    
    result = make_test_call(
        phone_number=args.phone_number,
        script=args.script,
        voice_id=args.voice_id,
        model_id=args.model_id,
        wait_for_completion=not args.no_wait,
        base_url=args.base_url,
        timeout=args.timeout
    )
    
    print(json.dumps(result, indent=2)) 