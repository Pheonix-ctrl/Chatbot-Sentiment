"""
FastAPI application for client sentiment analytics
Replaces the n8n webhook with Python-based processing
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openai_handler import process_chat_message
from memory import get_session_info, clear_session
from database import test_database_connection

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Client Sentiment Analytics API",
    description="Natural language interface for client feedback analysis",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    sessionId: str

class ChatResponse(BaseModel):
    message: Dict[str, Any]

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Client Sentiment Analytics API",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    db_status = test_database_connection()
    openai_key_present = bool(os.getenv('OPENAI_API_KEY'))
    
    return {
        "database": "connected" if db_status else "disconnected",
        "openai": "configured" if openai_key_present else "missing_key",
        "overall": "healthy" if (db_status and openai_key_present) else "unhealthy"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint - processes user messages and returns AI responses
    This replaces your n8n webhook
    """
    try:
        logger.info(f"Received chat request for session {request.sessionId}")

        
        # Validate inputs
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if not request.sessionId:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        # Process the message
        result = process_chat_message(request.message, request.sessionId)
        
        # Format response to match your React interface expectations
        # Format response to match your React interface expectations
        response = {
            "role": "assistant",
            "content": {
                "response": result["response"]
            }
        }

        logger.info(f"Successfully processed message for session {request.sessionId}")

        return ChatResponse(message=response)
        


        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/clear-session")
async def clear_session_endpoint(request: Dict[str, str]):
    """Clear memory for a specific session"""
    session_id = request.get("sessionId")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    
    clear_session(session_id)
    return {"message": f"Session {session_id[:8]} cleared successfully"}

@app.get("/session/{session_id}")
async def get_session_endpoint(session_id: str):
    """Get information about a session"""
    return {
        "session_id": session_id,
        "info": get_session_info(session_id)
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "path": str(request.url.path)}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": str(exc)}

if __name__ == "__main__":
    import uvicorn
    
    # Verify environment setup
    if not os.getenv('DATABASE_URL'):
        logger.error("DATABASE_URL not found in environment")
        exit(1)
    
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY not found in environment")
        exit(1)
    
    # Test database connection
    if not test_database_connection():
        logger.error("Database connection failed")
        exit(1)
    
    logger.info("Starting Client Sentiment Analytics API...")
    
    # Run the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
    )