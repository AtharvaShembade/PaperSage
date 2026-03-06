# PaperSage

A RAG-based research assistant. Add academic papers to projects, ask questions, and get answers grounded in the source — no more skimming 40-page PDFs.

## Features

- **Paper search** — Search arXiv and add papers to projects
- **Automatic ingestion** — PDFs are downloaded, parsed, chunked, and embedded automatically
- **RAG chat** — Ask questions about your papers and get cited answers with expandable source passages
- **Paper comparison** — Side-by-side breakdown of problem, method, dataset, results, and limitations across all papers in a project

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript, Vite, TailwindCSS, shadcn/ui |
| Backend | FastAPI, SQLAlchemy, PostgreSQL + pgvector |
| Auth | Supabase |
| LLM | Google Gemini (`gemini-2.5-flash` + `gemini-embedding-001`) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project with PostgreSQL + pgvector enabled
- A [Google Gemini](https://aistudio.google.com) API key

## Local Setup

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

Create a `.env` file in `backend/`:

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=your_supabase_postgres_connection_string
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
S2_API_KEY=                          # optional, Semantic Scholar
```

Run database migrations:

```bash
python create_tables.py
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

### 4. Open the app

Visit `http://localhost:5173`, sign up, and start adding papers.

## How It Works

1. **Add a paper** — Search arXiv, click add. The backend downloads the PDF, splits it into chunks, embeds each chunk with Gemini, and stores the vectors in pgvector.
2. **Chat** — Ask a question. The backend embeds your query, retrieves the most relevant chunks via similarity search, and sends them as context to Gemini. The answer includes expandable source citations.
3. **Compare** — Generate a structured comparison table across all papers in a project (problem, method, dataset, results, limitations).
