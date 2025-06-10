from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import logging
import json
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
BACKEND = "http://127.0.0.1:8000"
TIMEOUT = 30.0  # 30 second timeout

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "Internal server error", "type": "server_error"}}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BACKEND}/health")
            return {"status": "healthy", "backend": "connected"}
    except Exception as e:
        logger.warning(f"Backend health check failed: {e}")
        return {"status": "degraded", "backend": "disconnected"}

# 1) List models: we expose your single ADK app as a model named "adk2"
@app.get("/v1/models")
async def list_models():
    try:
        return {
            "object": "list",
            "data": [
                {
                    "id": "adk2",
                    "object": "model",
                    "owned_by": "adk",
                    "permission": []
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error in list_models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")

# 2) Chat completions: translate OpenAI-style to ADK /run
@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    try:
        # Parse and validate request body
        try:
            body = await req.json()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Validate required fields
        if "messages" not in body or not body["messages"]:
            raise HTTPException(status_code=400, detail="Missing or empty 'messages' field")
        
        # Extract user message safely
        last_message = body["messages"][-1]
        if "content" not in last_message:
            raise HTTPException(status_code=400, detail="Missing 'content' in last message")
        
        user_msg = last_message["content"]
        if not isinstance(user_msg, str) or not user_msg.strip():
            raise HTTPException(status_code=400, detail="Empty or invalid message content")
        
        # Package into ADK run payload
        run_payload = {
            "appName": "adk2",
            "userId": "u1",
            "sessionId": body.get("session_id", "s1"),
            "newMessage": {
                "role": "user",
                "parts": [{"text": user_msg}]
            }
        }
        
        # Make request to ADK backend with timeout and error handling
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                logger.info(f"Sending request to ADK backend: {BACKEND}/run")
                resp = await client.post(f"{BACKEND}/run", json=run_payload)
                resp.raise_for_status()
                events = resp.json()
                
        except httpx.TimeoutException:
            logger.error("Request to ADK backend timed out")
            raise HTTPException(status_code=504, detail="Backend request timed out")
        except httpx.ConnectError:
            logger.error("Failed to connect to ADK backend")
            raise HTTPException(status_code=503, detail="Backend service unavailable")
        except httpx.HTTPStatusError as e:
            logger.error(f"ADK backend returned error: {e.response.status_code}")
            raise HTTPException(status_code=502, detail=f"Backend error: {e.response.status_code}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from ADK backend")
            raise HTTPException(status_code=502, detail="Invalid response from backend")
        
        # Validate and extract response
        if not events or not isinstance(events, list):
            logger.error("Invalid or empty events from ADK backend")
            raise HTTPException(status_code=502, detail="Invalid backend response format")
        
        try:
            last_event = events[-1]
            response_text = last_event["content"]["parts"][-1]["text"]
            event_id = last_event.get("id", "")
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to extract response from events: {e}")
            raise HTTPException(status_code=502, detail="Malformed backend response")
        
        # Return OpenAI-compatible response
        return {
            "id": event_id,
            "object": "chat.completion",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat_completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
