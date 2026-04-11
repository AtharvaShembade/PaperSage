import json
import logging
import asyncio
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.models import crud, models
from app.core.config import settings
from app.core.redis import get_redis
from app.schemas.schemas import ComparisonRow, ComparisonResponse

COMPARISON_CACHE_TTL = 86400  # 24 hours

def _comparison_cache_key(project_id: int) -> str:
    return f"comparison:{project_id}"

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    _MODEL = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    logging.error(f"comparison_service: failed to configure Gemini: {e}")
    _MODEL = None

_PROMPT_TEMPLATE = """
You are a research paper analyst. Extract the following fields from the paper excerpts below.
Return ONLY a valid JSON object with exactly these keys:
  "problem"    - the core problem or challenge the paper addresses (1-2 sentences)
  "method"     - the approach, model, or technique proposed (1-2 sentences)
  "dataset"    - datasets or benchmarks used for evaluation (1 sentence, "N/A" if not mentioned)
  "result"     - the key finding or performance result (1-2 sentences)
  "limitation" - stated limitations or future work (1 sentence, "N/A" if not mentioned)

Paper title: {title}

Excerpts:
---
{context}
---

Respond with only the JSON object, no markdown, no explanation.
"""

async def _extract_for_paper(paper: models.Paper, db: Session) -> ComparisonRow:
    chunks = crud.get_chunks_for_paper(db, paper_id=paper.id, limit=20)
    context = "\n\n".join([c.chunk_text for c in chunks])[:6000]

    prompt = _PROMPT_TEMPLATE.format(title=paper.title, context=context)

    try:
        response = await _MODEL.generate_content_async(prompt)
        raw = response.text.strip()
        # strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
    except Exception as e:
        logging.error(f"comparison_service: failed for paper {paper.id}: {e}")
        data = {
            "problem": "N/A", "method": "N/A",
            "dataset": "N/A", "result": "N/A", "limitation": "N/A"
        }

    return ComparisonRow(
        paper_id=paper.id,
        title=paper.title,
        year=paper.year,
        problem=data.get("problem", "N/A"),
        method=data.get("method", "N/A"),
        dataset=data.get("dataset", "N/A"),
        result=data.get("result", "N/A"),
        limitation=data.get("limitation", "N/A"),
    )

async def generate_comparison(project_id: int, db: Session) -> ComparisonResponse:
    if not _MODEL:
        raise RuntimeError("Gemini model is not configured.")

    redis = await get_redis()
    cache_key = _comparison_cache_key(project_id)

    if redis:
        cached = await redis.get(cache_key)
        if cached:
            logging.info(f"comparison_service: cache hit for project {project_id}")
            return ComparisonResponse.model_validate_json(cached)

    project = crud.get_project(db, project_id)
    papers = project.papers or []

    ready = [p for p in papers if p.status == "ready"]
    skipped = [p.title for p in papers if p.status != "ready"]

    rows = await asyncio.gather(*[_extract_for_paper(p, db) for p in ready])
    result = ComparisonResponse(rows=list(rows), skipped=skipped)

    if redis:
        await redis.set(cache_key, result.model_dump_json(), ex=COMPARISON_CACHE_TTL)
        logging.info(f"comparison_service: cached result for project {project_id}")

    return result
