import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add the parent directory to sys.path to import from sibling directories
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the make_elevenlabs_call function from the outbound module
from outbound_calls.outbound import make_elevenlabs_call

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Outbound Call Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CallRequest(BaseModel):
    phone_number: str
    message: str

@app.post("/outbound-call")
async def make_call(request: CallRequest):
    """
    Endpoint to make an outbound call with a specified message
    """
    try:
        logger.info(f"Received outbound call request to: {request.phone_number}")
        
        # Call the make_elevenlabs_call function to process the call
        conversation_id = make_elevenlabs_call(request.phone_number, request.message)
        
        return {
            "status": "success",
            "message": "Call initiated successfully",
            "conversation_id": conversation_id
        }
    except Exception as e:
        logger.error(f"Error processing outbound call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify service is running
    """
    return {"status": "healthy", "service": "outbound-call-service"}

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("OUTBOUND_SERVICE_PORT", 8001))
    
    logger.info(f"Starting outbound call service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 