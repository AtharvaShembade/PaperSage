# PaperSage

An agentic RAG research assistant for academics. Add papers, ask questions, find research gaps, and generate literature reviews. All grounded in actual paper content.

**Live:** https://papersage-research.vercel.app

## Features

- **Agentic RAG Chat**:Ask anything about your papers. The AI agent retrieves relevant passages on its own, issues multiple search queries if needed, and answers with cited sources.
- **Research Gaps**:Scans all papers for open problems, contradictions, methodological gaps, and future directions. Evidence is verbatim:nothing fabricated.
- **Literature Review**:Type a research question, get a structured review: overview, key findings, methods, gaps, and future directions.
- **Paper Comparison**:Side-by-side table of problem, method, dataset, results, and limitations across all papers.
- **Related Papers**:AI reads your existing papers and discovers related work on arXiv.
- **Chat Sessions**:DB-backed sessions with history that persists across devices.
- **Notes & Annotations**:Pin source chunks from chat to notes, add commentary.
- **Citation Export**:Copy APA or BibTeX citation per paper.

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript, Vite, TailwindCSS, shadcn/ui |
| Backend | FastAPI, SQLAlchemy, PostgreSQL + pgvector |
| Auth | Supabase |
| LLM | Google Gemini (`gemini-2.5-flash` + `gemini-embedding-001`) |
| Deployment | Google Cloud Run (backend) + Vercel (frontend) |

## How It Works

1. **Add a paper**:Search arXiv, click add. The backend downloads the PDF, parses it with PyMuPDF, splits into 800-char chunks, embeds each chunk with Gemini (`gemini-embedding-001`, 3072 dims), and stores vectors in pgvector.
2. **Chat**:Ask a question. A Gemini function-calling agent decides what to search for, retrieves relevant chunks from pgvector, and generates a grounded answer with cited sources. The agent can issue multiple retrieval calls for complex questions.
3. **Research Gaps**:Each of 4 sections runs a targeted retrieval, passes verbatim chunks to Gemini, and extracts only claims supported by direct quotes from the papers.
4. **Literature Review**:Searches arXiv, adds papers to the project, then synthesises a structured review using the same agentic retrieval loop.

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project with PostgreSQL + pgvector enabled
- A [Google Gemini](https://aistudio.google.com) API key

### 1. Clone the repo

```bash
git clone https://github.com/AtharvaShembade/PaperSage.git
cd PaperSage
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=your_supabase_postgres_connection_string
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
S2_API_KEY=                          # optional, Semantic Scholar
```

Run migrations and start:

```bash
python create_tables.py
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Frontend runs on `http://localhost:5173`.

### 4. Open the app

Visit `http://localhost:5173`, sign up, and start adding papers.
