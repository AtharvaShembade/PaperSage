import httpx
from fastapi import HTTPException
from app.core.config import settings

SEARCH_API_URL = settings.S2_SEARCH_API_URL

async def search_papers(query: str, limit: int = 20) -> list:

    headers = {}

    if settings.S2_API_KEY:
        headers["x-api-key"] = settings.S2_API_KEY
    
    required_fields = "title,authors,year,abstract,openAccessPdf,paperId"

    params = {
        "query": query,
        "fields": required_fields,
        # "openAccessPdf": "true",
        "limit": limit
    } 

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SEARCH_API_URL, headers = headers, params = params)
            response.raise_for_status()
            data = response.json()

            results = []
            for paper in data.get("data", []) or []:
                results.append({
                    "id": paper.get("paperId", ""),
                    "title": paper.get("title", ""),
                    "authors": [a.get("name", "") for a in paper.get("authors", [])],
                    "abstract": paper.get("abstract", ""),
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "openAccessPdf": paper.get("openAccessPdf"),
                })
            return results
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise HTTPException(
                    status_code = 429,
                    detail = "Too many requests."
                )
            raise HTTPException(status_code = e.response.status_code, detail=f"Error from Semantic Scholar API: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code = 500, detail = f"Error searching papers: {str(e)}")
            