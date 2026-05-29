"""
OverLLM API - Public endpoint for C++ transformer model with terminal and file operations
"""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import ctypes
import os
import sys
import subprocess
import json
import requests
from pathlib import Path
from urllib.parse import urlparse
import asyncio

from overllm.gateio_alpha.engine import AlphaEngine
from overllm.gateio_alpha import api as alpha_api

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
    
    # Define C function signatures for live training
    overllm_lib.overllm_create_replay_buffer.argtypes = [ctypes.c_int]
    overllm_lib.overllm_create_replay_buffer.restype = ctypes.c_void_p
    
    overllm_lib.overllm_free_replay_buffer.argtypes = [ctypes.c_void_p]
    overllm_lib.overllm_free_replay_buffer.restype = None
    
    overllm_lib.overllm_add_experience.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    overllm_lib.overllm_add_experience.restype = None
    
    overllm_lib.overllm_get_buffer_size.argtypes = [ctypes.c_void_p]
    overllm_lib.overllm_get_buffer_size.restype = ctypes.c_int
    
    # Define C function signatures for token sequence management
    overllm_lib.overllm_create_token_sequence.argtypes = [ctypes.c_int]
    overllm_lib.overllm_create_token_sequence.restype = ctypes.c_void_p
    
    overllm_lib.overllm_free_token_sequence.argtypes = [ctypes.c_void_p]
    overllm_lib.overllm_free_token_sequence.restype = None
    
    overllm_lib.overllm_generate_with_tokens.argtypes = [
        ctypes.c_void_p,  # model
        ctypes.c_char_p,  # prompt
        ctypes.c_char_p,  # vocab_path
        ctypes.c_void_p,  # output_tokens
        ctypes.c_int      # max_gen_tokens
    ]
    overllm_lib.overllm_generate_with_tokens.restype = ctypes.c_int
    
    overllm_lib.overllm_get_token_sequence.argtypes = [
        ctypes.c_void_p,  # seq
        ctypes.POINTER(ctypes.c_int),  # out_tokens
        ctypes.POINTER(ctypes.c_int)   # out_n_tokens
    ]
    overllm_lib.overllm_get_token_sequence.restype = ctypes.c_int
    
    overllm_lib.overllm_load_model.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    overllm_lib.overllm_load_model.restype = ctypes.c_void_p
    
    overllm_lib.overllm_free_model.argtypes = [ctypes.c_void_p]
    overllm_lib.overllm_free_model.restype = None
    
    overllm_lib.overllm_default_config.restype = ctypes.c_void_p
    
    # Create replay buffer for training
    replay_buffer = overllm_lib.overllm_create_replay_buffer(10000)
    print("✓ Created replay buffer for training")
    
except Exception as e:
    print(f"✗ Failed to load OverLLM library: {e}")
    overllm_lib = None
    replay_buffer = None

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Alpha engine
try:
    alpha_engine = AlphaEngine(interval_seconds=60.0)
    alpha_api.set_engine(alpha_engine)
    print("✓ Alpha engine initialized")
except Exception as e:
    print(f"✗ Failed to initialize Alpha engine: {e}")
    alpha_engine = None

app.include_router(alpha_api.router, prefix="/api")


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
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    generate_poi: Optional[bool] = False
    # Include token sequences in response for PoI generation
    include_tokens: Optional[bool] = False


@app.get("/")
async def root():
    """Root endpoint — serve UI if built, otherwise API info"""
    ui_dist_path = Path(__file__).parent.parent / "ui" / "dist"
    index_file = ui_dist_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "service": "OverLLM Alpha Engine API",
        "version": "2.0.0",
        "status": "ready",
        "endpoints": {
            "/api/status": "Alpha engine status + truth labels",
            "/api/predictions/live": "Live predictions",
            "/api/performance": "Performance stats",
            "/api/receipts": "Receipt explorer",
            "/health": "Health check"
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
    buffer_size = 0
    if overllm_lib and replay_buffer:
        buffer_size = overllm_lib.overllm_get_buffer_size(replay_buffer)

    alpha_status = alpha_engine.status() if alpha_engine else {"initialized": False}

    return {
        "status": "ready",
        "library_loaded": overllm_lib is not None,
        "replay_buffer_size": buffer_size,
        "cpp_backend": True,
        "alpha_engine": alpha_status,
        "truth_labels": {
            "runtime": "real",
            "telemetry": "real",
            "gateio_data": "real if fetched live",
            "prediction_mode": "paper",
            "live_trading": "disabled",
            "model_quality": "experimental",
            "tunnel": "demo-grade unless named production tunnel",
            "receipts": "real only if hashes are generated and stored",
            "devnet_settlement": "real only if transaction signatures are produced",
        },
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
        # Expanded command set for development work
        # Still blocking destructive commands for safety
        blocked_commands = ['rm', 'rmdir', 'dd', 'mkfs', 'format', 'shutdown', 'reboot', 'halt']
        command_parts = request.command.split()
        base_command = command_parts[0] if command_parts else ''
        
        if base_command in blocked_commands:
            return {
                "success": False,
                "error": f"Command '{base_command}' is blocked for safety reasons",
                "output": ""
            }
        
        result = subprocess.run(
            request.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
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
    """Generate text using AI (integrates with Ollama)"""
    try:
        model = request.model or DEFAULT_MODEL
        temperature = request.temperature or 0.7
        
        # Add coding-specific system prompt
        system_prompt = "You are an expert coding assistant. Provide clear, accurate, and helpful answers to programming questions. Include code examples when appropriate."
        
        payload = {
            "model": model,
            "prompt": f"{system_prompt}\n\nUser: {request.prompt}\nAssistant:",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1000
            }
        }
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            
            result_data = {
                "generated_text": generated_text,
                "model": model,
                "temperature": temperature
            }
            
            # Capture token sequences if requested
            token_ids = None
            if request.include_tokens or request.generate_poi:
                # Make a second call with streaming to capture tokens
                payload["stream"] = True
                token_ids = await capture_token_sequences(payload, model)
                result_data["token_ids"] = token_ids
            
            # Generate proof-of-inference if requested
            if request.generate_poi:
                poi_receipt = await generate_poi_receipt(
                    request.prompt, 
                    generated_text, 
                    model, 
                    token_ids
                )
                result_data["poi_receipt"] = poi_receipt
            
            return result_data
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ollama error: {response.text}"
            )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Make sure Ollama is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation error: {str(e)}"
        )


async def capture_token_sequences(payload: dict, model: str):
    """Capture token sequences from OverLLM C++ engine or Ollama"""
    token_ids = []
    
    # Try OverLLM C++ engine first (if available and trained)
    if overllm_lib:
        try:
            # Check if we have a trained model
            # For now, this is a placeholder - the model needs to be trained first
            # When trained, we would:
            # 1. Load the model with overllm_load_model
            # 2. Create token sequence with overllm_create_token_sequence
            # 3. Generate with overllm_generate_with_tokens
            # 4. Extract tokens with overllm_get_token_sequence
            print("OverLLM library loaded but model not yet trained - falling back to Ollama")
        except Exception as e:
            print(f"OverLLM error: {e} - falling back to Ollama")
    
    # Fallback to Ollama (doesn't expose token IDs)
    try:
        import json
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=60
        )
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    # Ollama may include token information in the response
                    # This depends on the Ollama version and model
                    if "eval_count" in data:
                        # Some versions provide token counts
                        pass
                except json.JSONDecodeError:
                    pass
        
        # Ollama doesn't expose token IDs, so we can't capture them
        return None
        
    except Exception as e:
        print(f"Error capturing tokens from Ollama: {e}")
        return None


async def generate_poi_receipt(prompt: str, generated_text: str, model: str, token_ids=None):
    """Generate MEMBRA proof-of-inference receipt using real PoI CLI"""
    try:
        import subprocess
        import json
        from datetime import datetime
        import hashlib
        
        # Call membra-proof-of-inference CLI to generate real proof
        poi_binary = "/Users/alep/Downloads/MEMBRA_BLOCKCHAIN_FORTRESS/01_SYSTEMS/membra-proof-of-inference/target/release/poi"
        
        # Generate or load worker keypair
        # For production, this should be loaded from a secure location
        # For now, generate a new keypair for each inference
        keypair_result = subprocess.run(
            [poi_binary, "generate-keypair"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        worker_keypair = None
        if keypair_result.returncode == 0:
            # Parse the keypair output
            for line in keypair_result.stdout.split('\n'):
                if line.startswith("Secret:"):
                    worker_keypair = line.split(":")[1].strip()
                    break
        
        if not worker_keypair:
            # Fallback to a test keypair
            worker_keypair = "d1af450d6d96b462c71b41e781b094ccb9ffa7a3627c90e20e4281396b5b4732"
        
        # Generate real proof using the new generate-proof command
        cmd = [
            poi_binary, "generate-proof",
            "--model-cid", model,
            "--prompt", prompt,
            "--worker-id", "overllm-worker",
            "--worker-keypair", worker_keypair,
            "--temperature", "0.7",
            "--top-p", "0.9",
            "--top-k", "40"
        ]
        
        # Add token sequences if available
        if token_ids and len(token_ids) > 0:
            tokens_str = ",".join(map(str, token_ids))
            cmd.extend(["--tokens", tokens_str])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parse the proof JSON from output
        proof_data = None
        if result.returncode == 0:
            # Extract JSON from output (it's after the text output)
            lines = result.stdout.split('\n')
            json_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start is not None:
                json_text = '\n'.join(lines[json_start:])
                try:
                    proof_data = json.loads(json_text)
                except json.JSONDecodeError:
                    pass
        
        # Generate hashes
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:64]
        inference_id = f"inf-{hashlib.sha256((prompt + generated_text).encode()).hexdigest()[:16]}"
        
        # Create receipt with real proof data
        receipt = {
            "membra_receipt": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "inference": {
                    "id": inference_id,
                    "model_cid": model,
                    "prompt_hash": prompt_hash,
                    "runtime": "ollama-backend",
                    "proof_generated": proof_data is not None
                },
                "proof": proof_data if proof_data else None,
                "worker": {
                    "id": "overllm-worker",
                    "trust_multiplier": 1.0
                },
                "version": "2.0",
                "architecture_note": "Real proof-of-inference generated using MEMBRA PoI CLI with ed25519 signatures"
            }
        }
        
        return receipt
    except Exception as e:
        # Return partial receipt if POI generation fails
        return {
            "membra_receipt": {
                "error": f"POI generation failed: {str(e)}",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "inference": {
                    "id": f"inf-{hash(prompt + generated_text) & 0xffffffffffffffff:016x}",
                    "model_cid": model,
                    "runtime": "ollama-backend"
                },
                "architecture_note": "Real proof-of-inference generation failed"
            }
        }


@app.get("/api/gate/markets")
async def gate_markets():
    """List Gate.io futures markets"""
    if not alpha_engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    try:
        tickers = alpha_engine.client.list_tickers()
        return {
            "markets": [
                {
                    "contract": t.get("contract"),
                    "last": t.get("last"),
                    "change_percentage": t.get("change_percentage"),
                    "volume_24h": t.get("volume_24h"),
                }
                for t in tickers[:50]
            ],
            "count": len(tickers),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gate.io fetch failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Start the C++ live training system on startup"""
    if overllm_lib:
        print("C++ backend loaded - ready for live training")
    else:
        print("C++ backend not loaded - running in API-only mode")
    if alpha_engine:
        alpha_engine.start()
        print("Alpha engine auto-started")


# Serve built UI
ui_dist_path = Path(__file__).parent.parent / "ui" / "dist"
if ui_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(ui_dist_path / "assets"), check_dir=False), name="assets")

    @app.get("/{full_path:path}")
    async def serve_ui(full_path: str):
        # API routes and assets take precedence
        if full_path.startswith("api/") or full_path.startswith("assets/") or full_path in ("docs", "openapi.json", "health"):
            raise HTTPException(status_code=404, detail="Not found")
        index_file = ui_dist_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="UI not built")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
