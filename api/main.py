"""OverLLM API.

Truthful public API surface:
- Ollama-backed generation is real when Ollama is reachable.
- C++ library loading is detected but endpoints do not claim C++ inference unless wired.
- Public shell execution is disabled by default.
- File listing is restricted to an explicit allowlisted root.
- Financeable evidence endpoints record receipts/revenue evidence without inventing valuation.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from overllm.gateio_alpha.engine import AlphaEngine
from overllm.gateio_alpha import api as alpha_api

try:
    from api.financeable import router as finance_router, build_finance_summary
except Exception:  # pragma: no cover - supports `python api/main.py`
    from financeable import router as finance_router, build_finance_summary

APP_NAME = "OverLLM API"
API_VERSION = "2.2.0"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
LIB_PATH = os.getenv(
    "OVERLLM_LIB_PATH",
    str((Path(__file__).resolve().parent.parent / "lib" / "liboverllm.dylib")),
)
PUBLIC_TERMINAL_ENABLED = os.getenv("OVERLLM_ENABLE_TERMINAL", "0") == "1"
FILE_ROOT = Path(os.getenv("OVERLLM_FILE_ROOT", str(Path.cwd()))).resolve()
CORS_ORIGINS = [o.strip() for o in os.getenv("OVERLLM_CORS_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(
    title=APP_NAME,
    description="Experimental OverLLM API with truthful runtime labels, locked-down public surface, and financeable evidence exports.",
    version=API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

try:
    overllm_lib = ctypes.CDLL(LIB_PATH)
    print(f"Loaded OverLLM library from {LIB_PATH}")
    try:
        overllm_lib.overllm_create_replay_buffer.argtypes = [ctypes.c_int]
        overllm_lib.overllm_create_replay_buffer.restype = ctypes.c_void_p
        overllm_lib.overllm_get_buffer_size.argtypes = [ctypes.c_void_p]
        overllm_lib.overllm_get_buffer_size.restype = ctypes.c_int
        replay_buffer = overllm_lib.overllm_create_replay_buffer(10000)
    except Exception:
        replay_buffer = None
except Exception as exc:
    print(f"OverLLM C++ library unavailable: {exc}")
    overllm_lib = None
    replay_buffer = None

try:
    alpha_engine = AlphaEngine(interval_seconds=60.0)
    alpha_api.set_engine(alpha_engine)
except Exception as exc:
    print(f"Alpha engine unavailable: {exc}")
    alpha_engine = None

app.include_router(alpha_api.router, prefix="/api")
app.include_router(finance_router, prefix="/api")


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
    include_tokens: Optional[bool] = False


def _truth_labels() -> dict:
    return {
        "runtime": "experimental",
        "cpp_library_loaded": bool(overllm_lib),
        "cpp_inference_endpoint": "not_wired",
        "ollama_generation": "real_if_ollama_reachable",
        "telemetry": "environment_dependent",
        "gateio_data": "real_if_fetched_live",
        "prediction_mode": "paper",
        "live_trading": "disabled",
        "terminal_execution": "disabled_by_default",
        "file_listing": "allowlisted_root_only",
        "receipts": "real_only_when_hashes_are_generated_and_stored",
        "financeable_evidence": "real_local_ledger_not_valuation",
        "poi": "partial_environment_dependent",
    }


def _within_file_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(FILE_ROOT)
        return True
    except ValueError:
        return False


@app.get("/")
async def root():
    return {
        "service": APP_NAME,
        "version": API_VERSION,
        "status": "ready",
        "truth_labels": _truth_labels(),
        "endpoints": {
            "/health": "Health check",
            "/api/status": "Runtime truth/status labels",
            "/api/generate": "Ollama-backed generation when available",
            "/api/finance/summary": "Financeable evidence KPIs, not valuation",
            "/api/finance/receipts": "Signed/tamper-evident work receipts",
            "/api/finance/revenue-events": "Revenue events linked to receipts/contracts",
            "/api/finance/collateral-report": "Diligence packet generated from local evidence ledger",
            "/api/finance/export.csv": "CSV export for lender/buyer/investor diligence",
            "/inference": "Truth-labeled C++ inference placeholder",
            "/train": "Truth-labeled training placeholder",
            "/test": "Truth-labeled test placeholder",
            "/api/files": "Allowlisted file metadata only",
            "/api/terminal": "Disabled unless OVERLLM_ENABLE_TERMINAL=1 and replaced with a safe allowlist",
        },
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "library_loaded": overllm_lib is not None,
        "truth_labels": _truth_labels(),
    }


@app.get("/api/status")
async def status():
    buffer_size = 0
    if overllm_lib and replay_buffer:
        try:
            buffer_size = overllm_lib.overllm_get_buffer_size(replay_buffer)
        except Exception:
            buffer_size = 0
    alpha_status = alpha_engine.status() if alpha_engine else {"initialized": False}
    return {
        "status": "ready",
        "library_loaded": overllm_lib is not None,
        "replay_buffer_size": buffer_size,
        "cpp_backend": "loaded_not_exposed_for_inference" if overllm_lib else "unavailable",
        "alpha_engine": alpha_status,
        "financeable_evidence": build_finance_summary(),
        "truth_labels": _truth_labels(),
    }


@app.post("/inference")
async def inference(request: InferenceRequest):
    """Truth-labeled C++ inference endpoint.

    This no longer returns a fake generated response. Until the C++ model loading
    and inference path is fully wired, the endpoint reports partial status.
    """
    if not overllm_lib:
        raise HTTPException(status_code=503, detail="OverLLM library not loaded")
    return {
        "status": "not_wired",
        "truth_label": "partial",
        "message": "C++ library loaded, but production inference is not wired in this endpoint yet.",
        "prompt_hash": hashlib.sha256(request.prompt.encode()).hexdigest(),
        "requested_tokens": request.max_tokens,
    }


@app.post("/train")
async def train(request: TrainingRequest):
    """Truth-labeled training endpoint."""
    if not overllm_lib:
        raise HTTPException(status_code=503, detail="OverLLM library not loaded")
    return {
        "status": "not_wired",
        "truth_label": "partial",
        "message": "Training request accepted structurally, but C++ online training is not wired here yet.",
        "prompt_hash": hashlib.sha256(request.prompt.encode()).hexdigest(),
        "epochs_requested": request.epochs,
        "learning_rate": request.learning_rate,
    }


@app.post("/test")
async def run_tests():
    """Truth-labeled test endpoint."""
    return {
        "status": "not_executed",
        "truth_label": "partial",
        "message": "This HTTP endpoint does not execute the native test suite. Run repository tests in CI or local shell.",
    }


@app.post("/api/terminal")
async def execute_terminal(request: TerminalRequest):
    """Public shell execution is intentionally disabled.

    This endpoint previously executed arbitrary shell commands. It now returns a
    refusal unless a future safe command allowlist runner is implemented.
    """
    if not PUBLIC_TERMINAL_ENABLED:
        return {
            "success": False,
            "truth_label": "disabled_for_security",
            "error": "Public terminal execution is disabled. Implement a no-shell allowlist runner before enabling.",
            "output": "",
        }
    raise HTTPException(status_code=501, detail="Safe allowlist runner not implemented")


@app.get("/api/files")
async def list_files(path: str = "."):
    """List file metadata only inside OVERLLM_FILE_ROOT."""
    target_path = (FILE_ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not _within_file_root(target_path):
        raise HTTPException(status_code=403, detail=f"Path outside allowlisted root: {FILE_ROOT}")
    if not target_path.exists():
        return {"files": [], "error": "Path does not exist", "file_root": str(FILE_ROOT)}
    if not target_path.is_dir():
        return {"files": [], "error": "Path is not a directory", "file_root": str(FILE_ROOT)}

    files = []
    for item in target_path.iterdir():
        try:
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item.relative_to(FILE_ROOT)),
                "type": "folder" if item.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime * 1000,
            })
        except Exception:
            continue
    return {"file_root": str(FILE_ROOT), "files": files}


@app.post("/api/generate")
async def generate_text(request: GenerateRequest):
    """Generate text using Ollama when reachable."""
    model = request.model or DEFAULT_MODEL
    temperature = request.temperature or 0.7
    system_prompt = "You are an expert coding assistant. Provide clear, accurate, and helpful answers."
    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\nUser: {request.prompt}\nAssistant:",
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 1000},
    }
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60)
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama. Make sure Ollama is running.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation error: {exc}")

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Ollama error: {response.text}")

    result = response.json()
    generated_text = result.get("response", "")
    result_data = {
        "generated_text": generated_text,
        "model": model,
        "temperature": temperature,
        "truth_label": "real_ollama_response",
    }

    token_ids = None
    if request.include_tokens or request.generate_poi:
        payload["stream"] = True
        token_ids = await capture_token_sequences(payload)
        result_data["token_ids"] = token_ids
        result_data["token_truth_label"] = "unavailable" if token_ids is None else "captured"

    if request.generate_poi:
        result_data["poi_receipt"] = await generate_poi_receipt(request.prompt, generated_text, model, token_ids)

    return result_data


async def capture_token_sequences(payload: dict):
    """Try to capture token metadata.

    Ollama generally does not expose raw token IDs through this API, so the
    truthful default is None rather than fabricated token sequences.
    """
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, stream=True, timeout=60)
        for _line in response.iter_lines():
            pass
    except Exception:
        return None
    return None


async def generate_poi_receipt(prompt: str, generated_text: str, model: str, token_ids=None):
    """Generate a truth-labeled PoI-style receipt.

    Real external PoI generation requires `OVERLLM_POI_BINARY`. No hardcoded
    local path or test keypair is used here.
    """
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    output_hash = hashlib.sha256(generated_text.encode()).hexdigest()
    inference_id = f"inf-{hashlib.sha256((prompt + generated_text).encode()).hexdigest()[:16]}"
    poi_binary = os.getenv("OVERLLM_POI_BINARY", "")

    receipt = {
        "receipt": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "truth_label": "partial",
            "inference": {
                "id": inference_id,
                "model": model,
                "prompt_hash": prompt_hash,
                "output_hash": output_hash,
                "runtime": "ollama-backend",
                "token_ids_available": token_ids is not None,
            },
            "proof": None,
            "version": "2.1",
        }
    }

    if not poi_binary:
        receipt["receipt"]["proof_status"] = "not_configured"
        receipt["receipt"]["architecture_note"] = "Set OVERLLM_POI_BINARY to generate an external PoI proof."
        return receipt

    receipt["receipt"]["proof_status"] = "external_binary_configured_not_invoked_by_default"
    receipt["receipt"]["architecture_note"] = "External PoI binary is configured, but invocation is disabled in public API for safety."
    return receipt


@app.get("/api/gate/markets")
async def gate_markets():
    """List Gate.io futures markets."""
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
            "truth_label": "live_public_market_data_if_fetch_succeeded",
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gate.io fetch failed: {exc}")


@app.on_event("startup")
async def startup_event():
    if overllm_lib:
        print("C++ backend loaded, inference endpoint remains truth-labeled partial until wired.")
    else:
        print("C++ backend not loaded; running in API/Ollama mode.")
    if alpha_engine:
        alpha_engine.start()
        print("Alpha engine auto-started in paper/data mode.")


ui_dist_path = Path(__file__).parent.parent / "ui" / "dist"
if ui_dist_path.exists():
    app.mount("/static", StaticFiles(directory=str(ui_dist_path / "assets"), check_dir=False), name="static")

    @app.get("/{full_path:path}")
    async def serve_ui(full_path: str):
        if full_path.startswith("api/") or full_path in ("docs", "openapi.json", "health"):
            raise HTTPException(status_code=404, detail="Not found")
        index_file = ui_dist_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="UI not built")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
