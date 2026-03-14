import logging
import google.generativeai as genai
from sqlalchemy.orm import Session
from typing import List, Dict
from app.models import crud
from app.services import search_service


async def _generate_discovery_queries(paper_titles: List[str], paper_abstracts: List[str]) -> List[str]:
    titles_text = "\n".join(f"- {t}" for t in paper_titles[:10])
    abstracts_text = "\n\n".join(a[:300] for a in paper_abstracts[:5])

    prompt = f"""You are a research assistant. Based on the papers in this project, generate exactly 3 arXiv search queries to discover related papers the researcher might not have yet.
Each query should be 3-6 words, optimized for academic paper search.
Target adjacent topics, related methods, or complementary work — not just the same papers again.
Return only the queries, one per line, no numbering, no explanation.

Project papers:
{titles_text}

Sample abstracts:
{abstracts_text}"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
        return lines[:3]
    except Exception as e:
        logging.error(f"[Discovery] Failed to generate queries: {e}")
        # Fallback: use first paper title words as query
        return [paper_titles[0]] if paper_titles else []


async def get_related_papers(project_id: int, db: Session) -> List[Dict]:
    project = crud.get_project(db, project_id)
    if not project or not project.papers:
        return []

    existing_ids = {str(p.external_id) for p in project.papers}
    paper_titles = [p.title for p in project.papers]
    paper_abstracts = [p.abstract or "" for p in project.papers if p.abstract]

    queries = await _generate_discovery_queries(paper_titles, paper_abstracts)
    logging.info(f"[Discovery] Generated queries: {queries}")

    all_results: List[Dict] = []
    seen_ids = set()
    for q in queries:
        try:
            results = await search_service.search_papers(q, limit=8)
            for r in results:
                if r["id"] not in seen_ids and r["id"] not in existing_ids:
                    all_results.append(r)
                    seen_ids.add(r["id"])
        except Exception as e:
            logging.error(f"[Discovery] Search failed for query '{q}': {e}")

    return all_results[:12]
