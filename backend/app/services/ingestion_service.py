import httpx
import fitz  # PyMuPDF
import logging
from sqlalchemy.orm import Session
from app.models.database import SessionLocal 
from app.models import crud
from app.core.config import settings
from typing import List, Dict, Any

import google.generativeai as genai

try:
    genai.configure(api_key = settings.GEMINI_API_KEY)

    EMBEDDING_MODEL = "models/text-embedding-004"
    EMBEDDING_DIM = 768
    logging.info("Successfully configured Gemini API")

except Exception as e:
    logging.error(f"Failed to configure Gemini API: {str(e)}")
    EMBEDDING_MODEL = None


async def get_embedding(text_chunk: str) -> List[float]:
    if not EMBEDDING_MODEL:
        raise ValueError("Gemini API not configured")
        return [0.0] * EMBEDDING_DIM

    try:
        result = await genai.embed_content_async(
            model = EMBEDDING_MODEL,
            content = text_chunk,
            task_type = "RETRIEVAL_DOCUMENT"
        )
        return result['embedding']

    except Exception as e:
        logging.error(f"Failed to get embedding for {text_chunk}: {str(e)}")
        return [0.0] * EMBEDDING_DIM

def _split_text_into_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - chunk_overlap)
    return chunks

async def _download_and_parse_pdf(pdf_url: str) -> str:

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(pdf_url, follow_redirects = True, timeout = 30.0)
            response.raise_for_status()
            pdf_bytes = response.content

            full_text = ""
            with fitz.open(stream = pdf_bytes, filetype = "pdf") as doc:
                for page in doc:
                    full_text += page.get_text() + "\n" 

            return full_text

        except Exception as e:
            logging.error(f"Failed to parse PDF from {pdf_url}: {str(e)}")
            raise


async def process_paper(paper_id: int, pdf_url: str):

    db: Session = SessionLocal()

    try:
        logging.info(f"[Ingest Task] Starting ingestion for paper {paper_id}")

        full_text = await _download_and_parse_pdf(pdf_url)

        if not full_text:
            raise ValueError("Failed to download or parse PDF")

        text_chunks = _split_text_into_chunks(full_text)

        chunks_with_embeddings: List[Dict[str, Any]] = []
        for chunk in text_chunks:
            embedding = await get_embedding(chunk)
            chunks_with_embeddings.append({
                "chunk_text": chunk,
                "embedding": embedding
            })

        crud.create_chunks(
            db = db,
            paper_id = paper_id,
            chunks_data = chunks_with_embeddings
        )

        crud.update_paper_status(db = db, paper_id = paper_id, status = "ready")

        logging.info(f"[Ingest Task] Completed ingestion for paper {paper_id}")

    except Exception as e:
        logging.error(f"[Ingest Task] Error processing paper {paper_id}: {str(e)}")
        crud.update_paper_status(db = db, paper_id = paper_id, status = "failed")

    finally:
        db.close()

