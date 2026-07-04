# Multimodal QA API

FastAPI service that accepts a base64-encoded image + a question and returns an
answer extracted from the image, using AI Pipe's OpenAI-compatible vision model.

## Endpoint

`POST /answer-image`

Request:
```json
{"image_base64": "iVBORw0KG...", "question": "What is the total?"}
```

Response:
```json
{"answer": "4089.35"}
```

CORS is open (`*`) so any grader/worker can call it.

## Deploy to Render

1. Push this folder to a GitHub repo (or create a new repo and add these 3 files:
   `main.py`, `requirements.txt`, `render.yaml`).
2. On https://render.com → **New +** → **Web Service** → connect the repo.
   Render will auto-detect `render.yaml`. If it doesn't, set manually:
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add environment variable:
   - `AIPIPE_TOKEN` = your AI Pipe token (from https://aipipe.org, under your profile)
   - (optional) `MODEL` = `gpt-4o-mini` (default) — any AI Pipe vision-capable model works
4. Deploy. Your base URL will look like `https://multimodal-qa-api.onrender.com`.

## Test locally

```bash
pip install -r requirements.txt
export AIPIPE_TOKEN=your_token_here
uvicorn main:app --reload
```

```bash
curl -X POST http://localhost:8000/answer-image \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "<base64 png>", "question": "What is the total?"}'
```

## Submit

Submit your deployed base URL (e.g. `https://multimodal-qa-api.onrender.com`) —
the grader will call `POST <your-url>/answer-image`.

Note: Render's free tier spins down after inactivity, so the first request after
idling may take ~30-50s to respond (cold start). This is normal.
