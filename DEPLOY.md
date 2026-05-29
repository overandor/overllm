# OverLLM Gate.io Alpha Engine — Deploy to Render

## What was pushed

Branch: `feat/overagent-autonomous`
Commit: `3507eaa` — OverLLM Gate.io 3-Minute Self-Judging Alpha Engine

## Deploy to Render (3 steps)

### 1. Create a new Web Service on Render
- Go to https://dashboard.render.com/
- Click **New +** → **Web Service**
- Connect your GitHub repo: `overandor/overllm`
- Select branch: `feat/overagent-autonomous`

### 2. Configure the service
Render will auto-detect the `render.yaml` blueprint. If not, use these manual settings:

| Setting | Value |
|---------|-------|
| Name | `overllm-alpha` |
| Runtime | `Python` |
| Build Command | `cd ui && npm install && npm run build && cd ../api && pip install -r requirements.txt` |
| Start Command | `cd /opt/render/project/src && PYTHONPATH=/opt/render/project/src uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Plan | `Starter` (or free tier for testing) |

### 3. Environment Variables
Add these in the Render dashboard under **Environment**:

```
PYTHONPATH=/opt/render/project/src
OVERLLM_MODE=paper
LIVE_TRADING=disabled
LIVE_TRADING_ENABLED=false
```

### 4. Deploy
Click **Create Web Service**. Render will build the React UI, install Python deps, and start the FastAPI server. The alpha engine auto-starts on boot.

## Verify after deploy

```bash
curl https://<your-render-url>/api/status
curl https://<your-render-url>/api/predictions/pending
curl -X POST https://<your-render-url>/api/predict/once -H "Content-Type: application/json" -d '{"symbol":"BTC_USDT"}'
```

## What the public URL shows

- **Dashboard**: Root `/` serves the React UI
- **Truth Labels**: `/api/status` exposes all runtime truth labels
- **Live Predictions**: `/api/predictions/live`, `/api/predictions/pending`
- **Performance**: `/api/performance` — accuracy, calibration, net bps
- **Receipts**: `/api/receipts` — SHA256 chain of all predictions and outcomes

## Hard rules (enforced in code)

- `live_trading_enabled = False` — no live trades ever
- Paper-mode only — every prediction is public with a receipt
- Append-only history — no deletion of losses
- 3-minute self-judging — every prediction is scored after exactly 180s
