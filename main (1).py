import os
import base64
import binascii

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

AIPIPE_TOKEN = os.environ.get("AIPIPE_TOKEN", "")
AIPIPE_BASE_URL = os.environ.get("AIPIPE_BASE_URL", "https://aipipe.org/openai/v1")
MODEL = os.environ.get("MODEL", "gpt-4o-mini")

app = FastAPI(title="Multimodal QA API")

# CORS: allow the grader (running from a Cloudflare Worker or browser) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswerImageRequest(BaseModel):
    image_base64: str
    question: str


class AnswerImageResponse(BaseModel):
    answer: str


def _normalize_base64_image(raw: str) -> str:
    """Return a data URL, accepting either a raw base64 string or an existing data URL."""
    raw = raw.strip()
    if raw.startswith("data:"):
        return raw
    # Validate it's plausible base64 (allow padding-less input, fix if needed)
    try:
        base64.b64decode(raw + "=" * (-len(raw) % 4), validate=False)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="image_base64 is not valid base64 data")
    return f"data:image/png;base64,{raw}"


SYSTEM_PROMPT = (
    "You are a precise data-extraction assistant. You will be shown an image of a "
    "scanned document (chart, table, receipt, invoice, or similar) and asked a question "
    "about it. Answer using ONLY what is visible in the image. "
    "Respond with ONLY the final answer value - no explanation, no extra words, "
    "no currency symbols, no units, no commas as thousand separators. "
    "If the answer is a number, output just the number (e.g. 4089.35). "
    "If the answer is text, output just that text."
)


@app.post("/answer-image", response_model=AnswerImageResponse)
async def answer_image(payload: AnswerImageRequest):
    if not AIPIPE_TOKEN:
        raise HTTPException(status_code=500, detail="Server misconfigured: AIPIPE_TOKEN not set")

    data_url = _normalize_base64_image(payload.image_base64)

    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": payload.question},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        "temperature": 0,
    }

    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{AIPIPE_BASE_URL}/chat/completions", json=body, headers=headers
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502, detail=f"Upstream error: {e.response.status_code} {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}")

    data = resp.json()
    try:
        answer = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError):
        raise HTTPException(status_code=502, detail=f"Unexpected upstream response: {data}")

    # Strip any accidental currency symbols/units the model might still add
    answer = answer.strip().strip('"').strip()

    return AnswerImageResponse(answer=answer)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Multimodal QA API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
