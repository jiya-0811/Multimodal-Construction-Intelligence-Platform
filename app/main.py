from __future__ import annotations

import io
import json
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

load_dotenv()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
MAX_IMAGE_MB = max(1, min(int(os.getenv("MAX_IMAGE_MB", "8")), 15))
MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024
MAX_IMAGE_DIMENSION = 1280
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI(
    title="Multimodal Construction Intelligence Platform",
    description="AI-assisted construction planning, site safety, crack review, valuation, and site guidance.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class WeatherRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AnalysisResult(BaseModel):
    title: str
    summary: str
    risk_level: str = "Not assessed"
    observations: list[str] = []
    recommendations: list[str] = []
    limitations: list[str] = []
    structured_data: dict[str, Any] = {}


FEATURES = {
    "safety": {
        "title": "Construction Site Safety Review",
        "instructions": """Review the supplied construction-site description and optional image for visible safety concerns.
Return a JSON object with keys: title (string), summary (string), risk_level (Low/Medium/High/Unknown), observations (array of short strings), recommendations (array of short strings), limitations (array of strings), structured_data (object).
Mention only issues supported by the supplied information. Do not claim that a site is safe from a photo. Include practical PPE, access, fall-protection, housekeeping, or equipment checks only when relevant. If the image is unclear, say so.""",
    },
    "cracks": {
        "title": "Crack and Surface Review",
        "instructions": """Review the supplied image and/or description for visible cracks or surface defects.
Return a JSON object with keys: title, summary, risk_level (Low/Medium/High/Unknown), observations (array), recommendations (array), limitations (array), structured_data (object).
Describe visible patterns conservatively; do not infer crack depth, cause, load capacity, or structural integrity from a photo. Recommend documenting location, length, width, progression and getting a qualified structural engineer to inspect concerning or changing cracks. Never certify the structure as safe.""",
    },
    "valuation": {
        "title": "Indicative Real Estate Valuation",
        "instructions": """Estimate a rough indicative property value using only the user-provided inputs. Return JSON with keys: title, summary, risk_level (Informational), observations (array), recommendations (array), limitations (array), structured_data (object).
If the user supplies area and price per area, calculate area × price per area and show the arithmetic. If a price per area is missing, do not invent a market price: explain that local comparable-sale data is needed and return a formula/range only if inputs support it. State currency/units clearly and label the result a rough estimate, not a professional appraisal.""",
    },
    "planning": {
        "title": "Construction Project Plan",
        "instructions": """Create a practical preliminary construction plan from the project details. Return JSON with keys: title, summary, risk_level (Low/Medium/High/Unknown), observations (array), recommendations (array of actionable ordered steps), limitations (array), structured_data (object).
Include sensible phases, dependencies, likely approvals, quality checks, safety checks and risks when relevant. Do not invent local legal requirements, exact costs, or guaranteed timelines. Make assumptions explicit.""",
    },
    "assistant": {
        "title": "Construction Site Assistant",
        "instructions": """Answer the construction question clearly for a project team. Return JSON with keys: title, summary, risk_level (Informational/Unknown), observations (array), recommendations (array), limitations (array), structured_data (object).
Give practical steps and explain assumptions. For structural, electrical, lifting, excavation, fire, or other high-risk work, emphasize qualified professional review and applicable site procedures. Do not present guesses as verified facts.""",
    },
    "weather": {
        "title": "Weather-Aware Site Advisory",
        "instructions": """Use the provided weather information and site context to give cautious, practical construction planning advice. Return JSON with keys: title, summary, risk_level (Low/Medium/High/Unknown), observations (array), recommendations (array), limitations (array), structured_data (object).
Consider rain, wind, heat, lightning or cold only when supported by the supplied forecast. Do not claim to issue official warnings. Tell the user to follow local official alerts and site procedures.""",
    },
}


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _fallback_parse(raw: str, title: str) -> dict[str, Any]:
    return {
        "title": title,
        "summary": raw[:4000] or "The model returned an empty response.",
        "risk_level": "Unknown",
        "observations": [],
        "recommendations": [],
        "limitations": ["The response could not be parsed as structured JSON."],
        "structured_data": {},
    }


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "replace_with_your_gemini_api_key":
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured. Add GEMINI_API_KEY to your .env file and restart the app.",
        )
    return genai.Client(api_key=api_key)


def _prepare_image(data: bytes, content_type: Optional[str]) -> tuple[bytes, str]:
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"Image is too large. Maximum upload size is {MAX_IMAGE_MB} MB.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        if image.width < 1 or image.height < 1:
            raise ValueError("Invalid dimensions")
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
        # JPEG is broadly supported and usually much smaller than the source image.
        if image.mode not in ("RGB",):
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                alpha = image.getchannel("A") if "A" in image.getbands() else None
                if alpha:
                    background.paste(image.convert("RGBA"), mask=alpha)
                else:
                    background.paste(image.convert("RGB"))
                image = background
            else:
                image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=82, optimize=True)
        return output.getvalue(), "image/jpeg"
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Please upload a valid image file such as JPG, PNG, or WEBP.")


async def _read_image(upload: Optional[UploadFile]) -> Optional[tuple[bytes, str]]:
    if upload is None or not upload.filename:
        return None
    content_type = upload.content_type or ""
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="The uploaded file must be an image.")
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    return _prepare_image(data, content_type)


def _normalize_result(parsed: dict[str, Any], title: str) -> dict[str, Any]:
    def as_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item)[:500] for item in value[:12]]
        if isinstance(value, str) and value.strip():
            return [value[:500]]
        return []

    level = str(parsed.get("risk_level", "Unknown"))[:40]
    return {
        "title": str(parsed.get("title") or title)[:120],
        "summary": str(parsed.get("summary") or "No summary returned.")[:4000],
        "risk_level": level,
        "observations": as_list(parsed.get("observations")),
        "recommendations": as_list(parsed.get("recommendations")),
        "limitations": as_list(parsed.get("limitations")),
        "structured_data": parsed.get("structured_data") if isinstance(parsed.get("structured_data"), dict) else {},
    }


@app.get("/", response_class=HTMLResponse)
async def home():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": "Multimodal Construction Intelligence Platform",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())
        and os.getenv("GEMINI_API_KEY", "").strip() != "replace_with_your_gemini_api_key",
        "model": MODEL_NAME,
        "local_model_loaded": False,
    }


@app.post("/api/analyze")
async def analyze(
    feature: str = Form(...),
    prompt: str = Form(""),
    project_data: str = Form("{}"),
    image: Optional[UploadFile] = File(None),
):
    if feature not in FEATURES:
        raise HTTPException(status_code=400, detail="Unknown feature selected.")
    if len(prompt) > 12000:
        raise HTTPException(status_code=413, detail="Please keep the description under 12,000 characters.")
    try:
        data = json.loads(project_data or "{}")
        if not isinstance(data, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Project details must be valid JSON.")
    image_data = await _read_image(image)
    if not prompt.strip() and not data and image_data is None:
        raise HTTPException(status_code=400, detail="Enter project details, a question, or upload an image.")

    spec = FEATURES[feature]
    prompt_parts = [
        spec["instructions"],
        "\nUser-provided description/question:\n" + (prompt.strip() or "No additional description supplied."),
        "\nUser-provided structured project data:\n" + json.dumps(data, ensure_ascii=False)[:12000],
        "\nOutput requirements: Return only valid JSON. Do not use Markdown fences. Keep advice concise and actionable.",
    ]
    contents: list[Any] = ["\n".join(prompt_parts)]
    if image_data:
        contents.append(types.Part.from_bytes(data=image_data[0], mime_type=image_data[1]))

    client = _get_client()
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=1200,
            ),
        )
        raw = response.text or ""
        try:
            parsed = json.loads(_clean_json_text(raw))
        except json.JSONDecodeError:
            parsed = _fallback_parse(raw, spec["title"])
        return _normalize_result(parsed, spec["title"])
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc)
        # Avoid returning keys or other sensitive configuration in error messages.
        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            raise HTTPException(status_code=429, detail="Gemini API quota/rate limit reached. Wait a little and try again.")
        if "404" in message or "NOT_FOUND" in message:
            raise HTTPException(status_code=502, detail=f"Gemini model '{MODEL_NAME}' was not found or is unavailable. Check GEMINI_MODEL in .env.")
        raise HTTPException(status_code=502, detail="AI request failed. Check your API key, internet connection, model availability, and server logs.")


@app.post("/api/weather")
async def weather(request: WeatherRequest):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
        "forecast_days": 2,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        return {"source": "Open-Meteo", "data": data}
    except Exception:
        raise HTTPException(status_code=502, detail="Weather service is temporarily unavailable. Please try again later.")


@app.get("/api/features")
async def features():
    return [{"id": key, "title": value["title"]} for key, value in FEATURES.items()]
