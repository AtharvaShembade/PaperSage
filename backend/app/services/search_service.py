import httpx
import feedparser
from fastapi import HTTPException

ARXIV_API_URL = "https://export.arxiv.org/api/query"

async def search_papers(query: str, limit: int = 20) -> list:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(ARXIV_API_URL, params=params, timeout=15.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"arXiv API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error searching papers: {str(e)}")

    feed = feedparser.parse(response.text)
    results = []

    for entry in feed.entries:
        # Strip version suffix: http://arxiv.org/abs/2301.12345v2 → 2301.12345
        raw_id = entry.get("id", "")
        arxiv_id = raw_id.split("/abs/")[-1].split("v")[0]

        results.append({
            "id": arxiv_id,
            "title": entry.get("title", "").replace("\n", " ").strip(),
            "authors": [a.get("name", "") for a in entry.get("authors", [])],
            "abstract": entry.get("summary", "").replace("\n", " ").strip(),
            "year": int(entry.get("published", "0000")[:4]) or None,
            "citations": None,
            "arxiv_id": arxiv_id,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        })

    return results
