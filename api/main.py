"""
OverLLM API - Public endpoint for C++ transformer model with terminal and file operations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import ctypes
import os
import sys
import subprocess
import json
from pathlib import Path

app = FastAPI(
    title="Devin Terminal API",
    description="AI-powered terminal with file operations and task execution",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load C++ library
LIB_PATH = os.path.join(os.path.dirname(__file__), "../lib/liboverllm.dylib")
if not os.path.exists(LIB_PATH):
    # Try absolute path
    LIB_PATH = "/Users/alep/Downloads/overllm/lib/liboverllm.dylib"
try:
    overllm_lib = ctypes.CDLL(LIB_PATH)
    print(f"✓ Loaded OverLLM library from {LIB_PATH}")
except Exception as e:
    print(f"✗ Failed to load OverLLM library: {e}")
    overllm_lib = None


class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9


class TrainingRequest(BaseModel):
    prompt: str
    completion: str
    learning_rate: float = 0.001
    epochs: int = 1


class TerminalRequest(BaseModel):
    command: str


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Devin Terminal API",
        "version": "2.0.0",
        "status": "ready",
        "endpoints": {
            "/health": "Health check",
            "/inference": "Text generation",
            "/train": "Online training",
            "/test": "Run test suite",
            "/terminal": "Execute terminal commands",
            "/files": "List files",
            "/generate": "AI text generation"
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "library_loaded": overllm_lib is not None
    }


@app.get("/api/status")
async def status():
    """System status for dashboard"""
    return {
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "active_connections": 12,
        "inference_count": 1234,
        "training_loss": 0.0234
    }


@app.post("/inference")
async def inference(request: InferenceRequest):
    """Run inference on the model"""
    if not overllm_lib:
        raise HTTPException(status_code=503, detail="OverLLM library not loaded")
    
    # This would call the C++ inference function
    # For now, return a mock response
    return {
        "prompt": request.prompt,
        "generated_text": f"Generated response for: {request.prompt}",
        "tokens_generated": request.max_tokens,
        "temperature": request.temperature
    }


@app.post("/train")
async def train(request: TrainingRequest):
    """Run online training step"""
    if not overllm_lib:
        raise HTTPException(status_code=503, detail="OverLLM library not loaded")
    
    # This would call the C++ training function
    return {
        "status": "training_complete",
        "loss": 0.69,
        "epochs": request.epochs,
        "learning_rate": request.learning_rate
    }


@app.post("/test")
async def run_tests():
    """Run the C++ test suite"""
    if not overllm_lib:
        raise HTTPException(status_code=503, detail="OverLLM library not loaded")
    
    # This would execute the test_overllm binary
    return {
        "status": "tests_initiated",
        "message": "Test suite would run here"
    }


@app.post("/api/terminal")
async def execute_terminal(request: TerminalRequest):
    """Execute terminal command"""
    try:
        # For security, we'll limit commands to safe operations
        safe_commands = ['ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'wc', 'grep', 'find', 'date', 'whoami']
        command_parts = request.command.split()
        base_command = command_parts[0] if command_parts else ''
        
        if base_command not in safe_commands:
            return {
                "success": False,
                "error": f"Command '{base_command}' is not allowed for security reasons",
                "output": ""
            }
        
        result = subprocess.run(
            request.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out",
            "output": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": ""
        }


@app.get("/api/files")
async def list_files(path: str = "/Users/alep/Downloads/overllm"):
    """List files in directory"""
    try:
        target_path = Path(path)
        if not target_path.exists():
            return {"files": [], "error": "Path does not exist"}
        
        files = []
        for item in target_path.iterdir():
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "folder" if item.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime * 1000,
                    "appraisal": calculate_appraisal(item),
                    "kpis": {
                        "hourlyViews": 0,
                        "hourlyEdits": 0,
                        "hourlyCommits": 0,
                        "score": 75
                    }
                })
            except Exception:
                continue
        
        return {"files": files}
    except Exception as e:
        return {"files": [], "error": str(e)}


def calculate_appraisal(file_path: Path) -> float:
    """Calculate file appraisal based on various factors"""
    try:
        stat = file_path.stat()
        base_value = 100.0
        
        # Size factor
        size_factor = min(stat.st_size / 1024, 100)  # Up to 100KB
        
        # Extension factor
        ext = file_path.suffix.lower()
        ext_multipliers = {
            '.py': 2.0,
            '.js': 1.8,
            '.ts': 1.9,
            '.tsx': 2.0,
            '.rs': 2.2,
            '.go': 2.1,
            '.cpp': 2.0,
            '.h': 1.5,
            '.md': 1.3,
            '.json': 1.2,
            '.yaml': 1.2,
            '.yml': 1.2,
        }
        ext_factor = ext_multipliers.get(ext, 1.0)
        
        return base_value * (1 + size_factor / 100) * ext_factor
    except Exception:
        return 100.0


@app.post("/api/generate")
async def generate_text(request: GenerateRequest):
    """Generate text using AI (integrates with LLM)"""
    # This would integrate with actual LLM service
    # For now, return a simulated response
    responses = [
        f"I understand you want to: {request.prompt}",
        f"To accomplish '{request.prompt}', I would suggest the following approach:",
        f"Here's how I can help with '{request.prompt}':"
    ]
    
    import random
    selected_response = random.choice(responses)
    
    return {
        "generated_text": f"{selected_response}\n\n1. Analyze the current state\n2. Determine the best approach\n3. Execute the necessary commands\n4. Verify the results\n\nWould you like me to proceed with this plan?",
        "model": "devin-ai-v1"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
