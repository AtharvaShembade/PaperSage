import google.generativeai as genai
import logging
from sqlalchemy.orm import Session
from app.models import crud, models
from app.core.config import settings
from typing import List, Dict, Any
from fastapi import HTTPException

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    GENERATIVE_MODEL = genai.GenerativeModel("gemini-2.5-flash")

    EMBEDDING_MODEL = "models/gemini-embedding-001"
    EMBEDDING_DIM = 3072

    logging.info("Successfully configured Gemini API")

except Exception as e:
    logging.error(f"Failed to get query embedding: {e}")
    GENERATIVE_MODEL = None
    EMBEDDING_MODEL = None

async def _get_query_embedding(query: str) -> List[float]:
    if not EMBEDDING_MODEL:
        logging.error("RAG embedding model is not configured.")
        return [0.0] * EMBEDDING_DIM
        
    try:
        # Note the task_type is 'RETRIEVAL_QUERY'.
        # This is different from the 'RETRIEVAL_DOCUMENT' in your ingestion service.
        result = await genai.embed_content_async(
            model=EMBEDDING_MODEL,
            content=query,
            task_type="RETRIEVAL_QUERY"
        )
        return result['embedding']
        
    except Exception as e:
        logging.error(f"Failed to get query embedding: {e}")
        return [0.0] * EMBEDDING_DIM

async def _decompose_query(query: str) -> List[str]:
    """Break a complex query into 2 focused sub-questions for better retrieval coverage."""
    prompt = f"""You are a research assistant helping retrieve information from academic papers.
    Break the following research question into exactly 2 specific sub-questions that together cover the full intent.
    Each sub-question should be self-contained and optimized for retrieving relevant text passages.

    Return only the 2 sub-questions, one per line, no numbering, no explanation.

    Question: {query}"""

    try:
        response = await GENERATIVE_MODEL.generate_content_async(prompt)
        lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
        sub_questions = lines[:2]
        # Fall back to original query if decomposition fails or returns nothing useful
        if not sub_questions:
            return [query]
        return sub_questions
    except Exception as e:
        logging.error(f"Query decomposition failed: {e}")
        return [query]


def _build_rag_prompt(query: str, chunks: List[models.Chunk]) -> str:

    context = "\n\n".join([chunk.chunk_text for chunk in chunks])

    prompt = f"""
    You are a helpful AI research assistant. Your task is to answer the user's question 
    based *only* on the context provided below.

    Do not use any outside knowledge. If the context does not contain the answer,
    you must state: "I'm sorry, I don't have enough information from the provided 
    documents to answer that."

    Context:
    ---
    {context}
    ---

    Question: {query}

    Answer:
    """
    return prompt

async def answer_question(project_id: int, query: str, db: Session) -> Dict[str, Any]:

    if not GENERATIVE_MODEL:
        logging.error("Gemini model not available.")
        raise HTTPException(status_code = 500, detail = "Generative model is not configured.")

    sub_questions = await _decompose_query(query)
    logging.info(f"Query decomposed into: {sub_questions}")

    seen_ids = set()
    relevant_chunks = []
    for sq in sub_questions:
        vec = await _get_query_embedding(sq)
        chunks = crud.get_relevant_chunks(db=db, project_id=project_id, query_vector=vec, limit=4)
        for chunk in chunks:
            if chunk.id not in seen_ids:
                relevant_chunks.append(chunk)
                seen_ids.add(chunk.id)

    if not relevant_chunks:
        return {
            "answer": "I'm sorry, I couldn't find any relevant information in your project's papers to answer that question.",
            "sources": []
        }

    prompt = _build_rag_prompt(query, relevant_chunks)

    try:
        response = await GENERATIVE_MODEL.generate_content_async(prompt)
        sources = [
            {"title": chunk.paper.title, "chunk": chunk.chunk_text}
            for chunk in relevant_chunks
        ]
        return {"answer": response.text, "sources": sources}

    except Exception as e:
        logging.error(f"Failed to generate response: {e}")
        return {
            "answer": "I'm sorry, I encountered an error while processing your question. Please try again later.",
            "sources": []
        }
