import google.generativeai as genai
import logging
from sqlalchemy.orm import Session
from app.models import crud, models
from app.core.config import settings
from typing import List

try:
    GENERATIVE_MODEL = genai.GenerativeModel("gemini-2.5-pro")

    EMBEDDING_MODEL = "models/text-embedding-004"
    EMBEDDING_DIM = 768

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

async def answer_question(project_id: int, query: str, db: Session) -> str:
    
    if not GENERATIVE_MODEL:
        logging.error("Gemini model not available.")
        raise HTTPException(status_code = 500, detail = "Generative model is not configured.")

    query_vector = await _get_query_embedding(query)

    relevant_chunks = crud.get_relevant_chunks(
        db =db,
        project_id = project_id,
        query_vector = query_vector,
        limit = 3
    )

    if not relevant_chunks:
        return "I'm sorry, I couldn't find any relevant information in your project's papers to answer that question."

    prompt = _build_rag_prompt(query, relevant_chunks)

    try:
        response = await GENERATIVE_MODEL.generate_content_async(prompt)
        return response.text
    
    except Exception as e:
        logging.error(f"Failed to generate response: {e}")
        return "I'm sorry, I encountered an error while processing your question. Please try again later."
