"""
OverLLM API - Vercel serverless function that proxies to the Go agent
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os

app = FastAPI(
    title="OverLLM API",
    description="Proxy to OverLLM Go Agent with DPO/RL Training",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Go agent URL (can be overridden by environment variable)
GO_AGENT_URL = os.getenv("GO_AGENT_URL", "http://localhost:7749")


class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9


class StatusResponse(BaseModel):
    status: str
    queue_size: int
    context_window_size: int


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OverLLM API",
        "version": "1.0.0",
        "status": "ready",
        "go_agent_url": GO_AGENT_URL,
        "endpoints": {
            "/health": "Health check",
            "/status": "Agent status",
            "/generate": "Generate text with full context",
            "/context": "Current telemetry context"
        }
    }


@app.get("/health")
async def health():
    """Health check - tries to connect to Go agent"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GO_AGENT_URL}/api/status", timeout=5.0)
            return {
                "status": "healthy",
                "go_agent_reachable": True,
                "go_agent_status": response.json()
            }
    except Exception as e:
        return {
            "status": "degraded",
            "go_agent_reachable": False,
            "error": str(e)
        }


@app.get("/status")
async def status():
    """Get Go agent status"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GO_AGENT_URL}/api/status", timeout=5.0)
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Go agent unreachable: {e}")


@app.get("/context")
async def context():
    """Get current telemetry context"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GO_AGENT_URL}/api/context", timeout=5.0)
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Go agent unreachable: {e}")


@app.post("/generate")
async def generate(request: InferenceRequest):
    """Generate text with full telemetry context"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GO_AGENT_URL}/api/generate",
                json={
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p
                },
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Go agent unreachable: {e}")


# Vercel serverless function entry point
async def handler(request):
    """
    Vercel serverless function entry point
    """
    from fastapi.responses import JSONResponse
    import json
    
    # Create a mock scope for ASGI
    scope = {
        'type': 'http',
        'method': request.method,
        'headers': [(k.encode(), v.encode()) for k, v in request.headers.items()],
        'query_string': request.query_string.encode(),
        'path': request.path,
    }
    
    # Create a mock receive function
    async def receive():
        return {
            'type': 'http.request',
            'body': request.body.encode() if request.body else b'',
        }
    
    # Create a mock send function
    async def send(message):
        if message['type'] == 'http.response.start':
            pass
        elif message['type'] == 'http.response.body':
            pass
    
    # Call the FastAPI app
    await app(scope, receive, send)
    
    return JSONResponse({"status": "ok"})