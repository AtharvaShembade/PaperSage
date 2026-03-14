import logging
import google.generativeai as genai
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.models import crud, models
from app.schemas import schemas
from app.services import search_service, ingestion_service, rag_service

MAX_SEARCH_QUERIES = 3
MAX_PAPERS_TO_ADD = 8


async def _generate_search_queries(question: str) -> List[str]:
    """LLM generates focused arXiv search queries from a research question."""
    prompt = f"""You are a research assistant. Given the research question below, generate exactly {MAX_SEARCH_QUERIES} focused arXiv search queries that together cover the scope of the question.
Each query should be 3-6 words, optimized for academic paper search.
Return only the queries, one per line, no numbering, no explanation.

Research question: {question}"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
        return lines[:MAX_SEARCH_QUERIES]
    except Exception as e:
        logging.error(f"Failed to generate search queries: {e}")
        return [question]


async def _select_papers(question: str, candidates: List[Dict]) -> List[Dict]:
    """LLM selects the most relevant papers from search results."""
    papers_text = "\n".join([
        f"[{i}] {p['title']} ({p['year']}) — {p['abstract'][:200]}..."
        for i, p in enumerate(candidates)
    ])

    prompt = f"""You are a research assistant selecting papers for a literature review.

Research question: {question}

Candidate papers:
{papers_text}

Select the {MAX_PAPERS_TO_ADD} most relevant papers for answering this research question.
Return only the index numbers (e.g. 0, 3, 5, 7), comma-separated, no explanation."""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await model.generate_content_async(prompt)
        indices = [int(x.strip()) for x in response.text.strip().split(",") if x.strip().isdigit()]
        return [candidates[i] for i in indices if i < len(candidates)][:MAX_PAPERS_TO_ADD]
    except Exception as e:
        logging.error(f"Failed to select papers: {e}")
        return candidates[:MAX_PAPERS_TO_ADD]


async def search_and_add_papers(
    project_id: int,
    question: str,
    db: Session,
) -> List[int]:
    """Search arXiv, LLM selects best papers, adds them to project. Returns paper IDs."""

    # 1. Generate search queries
    queries = await _generate_search_queries(question)
    logging.info(f"[LitReview] Generated queries: {queries}")

    # 2. Search arXiv for each query, deduplicate
    all_results: List[Dict] = []
    seen_ids = set()
    for q in queries:
        try:
            results = await search_service.search_papers(q, limit=10)
            for r in results:
                if r["id"] not in seen_ids:
                    all_results.append(r)
                    seen_ids.add(r["id"])
        except Exception as e:
            logging.error(f"[LitReview] Search failed for query '{q}': {e}")

    if not all_results:
        return []

    # 3. LLM selects best papers
    selected = await _select_papers(question, all_results)
    logging.info(f"[LitReview] Selected {len(selected)} papers")

    # 4. Add each paper to the project (create records only, don't ingest yet)
    paper_ids = []
    ingestion_tasks = []
    for paper in selected:
        try:
            paper_create = schemas.PaperCreate(
                external_id=paper["id"],
                title=paper["title"],
                abstract=paper.get("abstract"),
                year=paper.get("year"),
                arxiv_id=paper.get("arxiv_id"),
                pdf_url=paper.get("pdf_url"),
            )

            db_paper = crud.get_paper(db, paper_create.external_id)
            if db_paper:
                crud.link_paper_to_project(db=db, project_id=project_id, paper_id=db_paper.id)
                paper_ids.append(db_paper.id)
                # Re-trigger ingestion if stuck in processing
                if db_paper.status == "processing":
                    ingestion_tasks.append((
                        db_paper.id,
                        db_paper.arxiv_id,
                        db_paper.pdf_url,
                    ))
                continue

            db_paper = crud.create_paper(db, paper=paper_create, status="processing")
            crud.link_paper_to_project(db=db, project_id=project_id, paper_id=db_paper.id)
            paper_ids.append(db_paper.id)

            ingestion_tasks.append((
                db_paper.id,
                paper_create.arxiv_id,
                str(paper_create.pdf_url) if paper_create.pdf_url else None,
            ))

        except Exception as e:
            logging.error(f"[LitReview] Failed to add paper '{paper['title']}': {e}")

    return paper_ids, ingestion_tasks


async def generate_review(project_id: int, question: str, db: Session) -> str:
    """Generate a structured literature review from all ready papers in the project."""

    system_prompt = (
        "You are an expert academic researcher writing a literature review. "
        "Use the retrieve_context tool to search the papers in this project. "
        "Call it multiple times with different queries to gather comprehensive evidence. "
        "Then write a structured literature review with these sections:\n"
        "1. **Overview** — Brief introduction to the research question\n"
        "2. **Key Findings** — Main contributions from the papers\n"
        "3. **Methods** — Common approaches and methodologies used\n"
        "4. **Gaps & Contradictions** — What's missing or debated\n"
        "5. **Future Directions** — Open questions and potential next steps\n\n"
        "Cite papers by title inline. Be thorough but concise. "
        "Never mention tool names, function names, or internal processes in your responses."
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        tools=[rag_service.RETRIEVE_TOOL],
    )

    try:
        chat = model.start_chat()
        response = await chat.send_message_async(
            f"Write a literature review on the topic: {question}. "
            f"If you need clarification, ask the user directly without mentioning any tools or internal functions."
        )

        for _ in range(5):  # more iterations for thorough review
            part = response.candidates[0].content.parts[0]

            if not hasattr(part, "function_call") or not part.function_call.name:
                break

            fc = part.function_call
            if fc.name == "retrieve_context":
                search_query = fc.args.get("search_query", question)
                logging.info(f"[LitReview] retrieve_context: {search_query}")

                vec = await rag_service._get_query_embedding(search_query)
                chunks = crud.get_relevant_chunks(db=db, project_id=project_id, query_vector=vec, limit=8)

                from google.generativeai import protos
                context_text = "\n\n".join([
                    f"[{c.paper.title}]\n{c.chunk_text}" for c in chunks
                ])

                response = await chat.send_message_async(
                    protos.Part(function_response=protos.FunctionResponse(
                        name="retrieve_context",
                        response={"result": context_text if context_text else "No relevant passages found."}
                    ))
                )

        return response.candidates[0].content.parts[0].text

    except Exception as e:
        logging.error(f"[LitReview] Review generation failed: {e}")
        raise
