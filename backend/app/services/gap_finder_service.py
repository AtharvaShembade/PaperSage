import json
import logging
import asyncio
import google.generativeai as genai
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.models import crud
from app.services.rag_service import _get_query_embedding

SECTIONS = [
    {
        "type": "open_problems",
        "title": "Open Problems",
        "queries": [
            "future work open questions remaining challenges unsolved",
            "remains unclear unanswered limitation not addressed",
        ],
        "instruction": (
            "Identify questions these papers raise but leave unanswered, "
            "or problems they explicitly acknowledge as unsolved."
        ),
    },
    {
        "type": "contradictions",
        "title": "Contradictions",
        "queries": [
            "however unlike previous work contradicts results differ inconsistent",
            "in contrast debate controversy conflicting findings",
        ],
        "instruction": (
            "Identify places where papers disagree with each other, "
            "contradict prior work, or present conflicting findings or conclusions."
        ),
    },
    {
        "type": "methodological_gaps",
        "title": "Methodological Gaps",
        "queries": [
            "only evaluated limited to not tested untested settings missing evaluation",
            "no benchmark dataset absent cannot handle out of scope",
        ],
        "instruction": (
            "Identify datasets, settings, metrics, or conditions that are notably absent "
            "from evaluation or explicitly acknowledged as untested."
        ),
    },
    {
        "type": "future_directions",
        "title": "Future Directions",
        "queries": [
            "future work promising direction could be extended next steps we plan",
            "leave for future investigate potential extension",
        ],
        "instruction": (
            "Identify explicit future directions, extensions, or next steps "
            "the authors themselves mention."
        ),
    },
]

SECTION_PROMPT = """You are a rigorous research analyst performing a gap analysis.

Your task: {instruction}

STRICT RULES — read carefully:
1. Only report gaps that are directly evidenced by the EXACT passages provided below.
2. The "evidence" field MUST be a verbatim quote copied from the passages — do not paraphrase.
3. Do NOT use any knowledge outside these passages.
4. If no clear gap is found in the passages, return an empty entries array.
5. Include between 0 and 4 entries — only real, well-evidenced gaps.
6. Be conservative: 2 strong entries beat 4 weak ones.
{focus_instruction}

Passages (each prefixed with its paper title):
---
{context}
---

Return ONLY a valid JSON object with this exact structure, no markdown, no explanation:
{{
  "entries": [
    {{
      "claim": "One clear sentence describing the gap",
      "evidence": "Exact verbatim quote from the passages above",
      "paper_title": "Title of the paper this evidence comes from",
      "paper_year": 2023
    }}
  ]
}}
"""


async def _retrieve_chunks_for_queries(
    queries: List[str], project_id: int, db: Session, limit: int = 5
) -> List[Dict]:
    seen_ids = set()
    chunks = []
    for query in queries:
        vec = await _get_query_embedding(query)
        results = crud.get_relevant_chunks(db=db, project_id=project_id, query_vector=vec, limit=limit)
        for c in results:
            if c.id not in seen_ids:
                chunks.append(c)
                seen_ids.add(c.id)
    return chunks


async def _analyze_section(
    section: Dict,
    project_id: int,
    focus: Optional[str],
    db: Session,
) -> Dict:
    chunks = await _retrieve_chunks_for_queries(section["queries"], project_id, db)

    if not chunks:
        return {"type": section["type"], "title": section["title"], "entries": []}

    context = "\n\n".join([
        f"[{c.paper.title} ({c.paper.year or 'n.d.'})]\n{c.chunk_text}"
        for c in chunks
    ])[:8000]

    focus_instruction = (
        f'Focus specifically on gaps related to: "{focus}"' if focus else ""
    )

    prompt = SECTION_PROMPT.format(
        instruction=section["instruction"],
        focus_instruction=focus_instruction,
        context=context,
    )

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        entries = data.get("entries", [])

        # Validate entries — drop any missing required fields
        valid = [
            e for e in entries
            if e.get("claim") and e.get("evidence") and e.get("paper_title")
        ]

        return {
            "type": section["type"],
            "title": section["title"],
            "entries": valid[:4],
        }

    except Exception as e:
        logging.error(f"[GapFinder] Section '{section['type']}' failed: {e}")
        return {"type": section["type"], "title": section["title"], "entries": []}


async def run_gap_analysis(
    project_id: int,
    db: Session,
    focus: Optional[str] = None,
) -> Dict[str, Any]:
    results = []
    for section in SECTIONS:
        result = await _analyze_section(section, project_id, focus, db)
        results.append(result)
        await asyncio.sleep(0.5)  # avoid rate limits between sections

    return {"sections": results, "focus": focus}
