import google.generativeai as genai
from google.generativeai import protos
import logging
import json
import hashlib
from sqlalchemy.orm import Session
from app.models import crud, models
from app.core.config import settings
from app.core.redis import get_redis
from typing import List, Dict, Any, AsyncGenerator
from fastapi import HTTPException

RAG_CACHE_TTL = 3600  # 1 hour

def _rag_cache_key(project_id: int, query: str, deep: bool) -> str:
    h = hashlib.sha256(f"{project_id}:{query}:{deep}".encode()).hexdigest()[:16]
    return f"rag:{project_id}:{h}"

MAX_AGENT_ITERATIONS = 3

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)

    EMBEDDING_MODEL = "models/gemini-embedding-001"
    EMBEDDING_DIM = 3072

    RETRIEVE_TOOL = protos.Tool(function_declarations=[
        protos.FunctionDeclaration(
            name="retrieve_context",
            description="Search the research papers in this project for passages relevant to a query. Call this whenever you need information from the papers.",
            parameters=protos.Schema(
                type=protos.Type.OBJECT,
                properties={
                    "search_query": protos.Schema(type=protos.Type.STRING, description="The search query to find relevant passages")
                },
                required=["search_query"]
            )
        )
    ])

    logging.info("Successfully configured Gemini API")

except Exception as e:
    logging.error(f"Failed to configure Gemini API: {e}")
    EMBEDDING_MODEL = None
    RETRIEVE_TOOL = None

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

async def _generate_follow_ups(query: str, answer: str) -> List[str]:
    """Generate 3 natural follow-up questions based on the query and answer."""
    prompt = f"""You are a research assistant. Based on the question and answer below, suggest 3 concise follow-up questions a researcher might ask next.
Return only the 3 questions, one per line, no numbering, no explanation.

Question: {query}
Answer: {answer}"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
        return lines[:3]
    except Exception as e:
        logging.error(f"Follow-up generation failed: {e}")
        return []


async def answer_question(project_id: int, query: str, db: Session, deep: bool = False) -> Dict[str, Any]:

    if not RETRIEVE_TOOL:
        logging.error("Gemini API not configured.")
        raise HTTPException(status_code=500, detail="Generative model is not configured.")

    # --- Cache check ---
    redis = await get_redis()
    cache_key = _rag_cache_key(project_id, query, deep)
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            logging.info(f"[RAG cache] hit: {cache_key}")
            return json.loads(cached)

    chunk_limit = 8 if deep else 4
    seen_ids: set = set()
    all_chunks: List[models.Chunk] = []

    system_prompt = (
        "You are a helpful AI research assistant. Answer the user's question using only "
        "information retrieved from their research papers via the retrieve_context tool. "
        "Call retrieve_context one or more times with focused search queries to gather relevant passages. "
        "Once you have enough context, provide a clear, well-structured answer. "
        "If the papers don't contain enough information, say so honestly."
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        tools=[RETRIEVE_TOOL]
    )

    try:
        chat = model.start_chat()
        response = await chat.send_message_async(query)

        for _ in range(MAX_AGENT_ITERATIONS):
            part = response.candidates[0].content.parts[0]

            if not hasattr(part, "function_call") or not part.function_call.name:
                break

            fc = part.function_call
            if fc.name == "retrieve_context":
                search_query = fc.args.get("search_query", query)
                logging.info(f"[Agent] retrieve_context called with: {search_query}")

                vec = await _get_query_embedding(search_query)
                chunks = crud.get_relevant_chunks(db=db, project_id=project_id, query_vector=vec, limit=chunk_limit)

                for chunk in chunks:
                    if chunk.id not in seen_ids:
                        all_chunks.append(chunk)
                        seen_ids.add(chunk.id)

                context_text = "\n\n".join([
                    f"[{chunk.paper.title}]\n{chunk.chunk_text}" for chunk in chunks
                ])

                response = await chat.send_message_async(
                    protos.Part(function_response=protos.FunctionResponse(
                        name="retrieve_context",
                        response={"result": context_text if context_text else "No relevant passages found."}
                    ))
                )

        answer = response.candidates[0].content.parts[0].text

        if not all_chunks:
            return {
                "answer": "I'm sorry, I couldn't find any relevant information in your project's papers to answer that question.",
                "sources": [],
                "follow_ups": []
            }

        sources = [{"title": c.paper.title, "chunk": c.chunk_text} for c in all_chunks]
        follow_ups = await _generate_follow_ups(query, answer)
        result = {"answer": answer, "sources": sources, "follow_ups": follow_ups}

        if redis:
            await redis.set(cache_key, json.dumps(result), ex=RAG_CACHE_TTL)

        return result

    except Exception as e:
        logging.error(f"Failed to generate response: {e}")
        return {
            "answer": "I'm sorry, I encountered an error while processing your question. Please try again later.",
            "sources": [],
            "follow_ups": []
        }


async def answer_question_stream(
    project_id: int, query: str, db: Session, deep: bool = False
) -> AsyncGenerator[str, None]:
    """
    Same agent loop as answer_question, but streams the final synthesis via SSE.
    Yields SSE-formatted strings:
      data: {"type": "token", "content": "..."}
      data: {"type": "done", "sources": [...], "follow_ups": [...]}
      data: {"type": "error", "detail": "..."}
    """
    if not RETRIEVE_TOOL:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'Generative model is not configured.'})}\n\n"
        return

    # --- Cache check: on hit, stream cached answer instantly ---
    redis = await get_redis()
    cache_key = _rag_cache_key(project_id, query, deep)
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            logging.info(f"[RAG stream cache] hit: {cache_key}")
            data = json.loads(cached)
            yield f"data: {json.dumps({'type': 'token', 'content': data['answer']})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'sources': data['sources'], 'follow_ups': data['follow_ups']})}\n\n"
            return

    chunk_limit = 8 if deep else 4
    seen_ids: set = set()
    all_chunks: List[models.Chunk] = []

    system_prompt = (
        "You are a helpful AI research assistant. Answer the user's question using only "
        "information retrieved from their research papers via the retrieve_context tool. "
        "Call retrieve_context one or more times with focused search queries to gather relevant passages. "
        "Once you have enough context, provide a clear, well-structured answer. "
        "If the papers don't contain enough information, say so honestly."
    )

    yield f"data: {json.dumps({'type': 'status', 'content': 'searching'})}\n\n"

    # --- Agent loop (tool calls, non-streaming) ---
    agent_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        tools=[RETRIEVE_TOOL]
    )

    try:
        chat = agent_model.start_chat()
        response = await chat.send_message_async(query)

        for _ in range(MAX_AGENT_ITERATIONS):
            part = response.candidates[0].content.parts[0]
            if not hasattr(part, "function_call") or not part.function_call.name:
                break

            fc = part.function_call
            if fc.name == "retrieve_context":
                search_query = fc.args.get("search_query", query)
                logging.info(f"[Stream Agent] retrieve_context: {search_query}")

                vec = await _get_query_embedding(search_query)
                chunks = crud.get_relevant_chunks(db=db, project_id=project_id, query_vector=vec, limit=chunk_limit)

                for chunk in chunks:
                    if chunk.id not in seen_ids:
                        all_chunks.append(chunk)
                        seen_ids.add(chunk.id)

                context_text = "\n\n".join([
                    f"[{chunk.paper.title}]\n{chunk.chunk_text}" for chunk in chunks
                ])

                response = await chat.send_message_async(
                    protos.Part(function_response=protos.FunctionResponse(
                        name="retrieve_context",
                        response={"result": context_text if context_text else "No relevant passages found."}
                    ))
                )

        if not all_chunks:
            yield f"data: {json.dumps({'type': 'token', 'content': 'I could not find any relevant information in your project papers to answer that question.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'sources': [], 'follow_ups': []})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'status', 'content': 'generating'})}\n\n"

        # --- Stream final synthesis ---
        context_text = "\n\n".join([
            f"[{c.paper.title}]\n{c.chunk_text}" for c in all_chunks
        ])
        synthesis_prompt = (
            f"Using the retrieved context below, answer the following question clearly and thoroughly.\n\n"
            f"Question: {query}\n\n"
            f"Context:\n{context_text}"
        )

        synthesis_model = genai.GenerativeModel("gemini-2.5-flash")
        full_answer_parts = []

        async for chunk in await synthesis_model.generate_content_async(
            synthesis_prompt, stream=True
        ):
            if chunk.text:
                full_answer_parts.append(chunk.text)
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\n\n"

        full_answer = "".join(full_answer_parts)
        sources = [{"title": c.paper.title, "chunk": c.chunk_text} for c in all_chunks]
        follow_ups = await _generate_follow_ups(query, full_answer)

        if redis:
            result = {"answer": full_answer, "sources": sources, "follow_ups": follow_ups}
            await redis.set(cache_key, json.dumps(result), ex=RAG_CACHE_TTL)

        yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'follow_ups': follow_ups})}\n\n"

    except Exception as e:
        logging.error(f"Streaming RAG failed: {e}")
        yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"
