from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

# --- Paper Schemas ---

class PaperBase(BaseModel):
    external_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None

class PaperCreate(PaperBase):
    pdf_url: Optional[HttpUrl] = None
    arxiv_id: Optional[str] = None

class Paper(PaperBase):
    id: int
    status: str
    tldr: Optional[str] = None

    class Config:
        orm_mode = True

class PaperSearchDetail(PaperBase):
    openAccessPdf: Optional[dict] = None

# --- Project Schemas ---

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True # This allows Pydantic to read the model's attributes directly from the SQLAlchemy model

class ProjectDetail(Project):
    papers: List[Paper] = []

# --- User Schemas ---

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    projects: List[Project] = []

    class Config:
        orm_mode = True

# --- RAG Chat Schemas ---

class ChatRequest(BaseModel):
    query: str
    project_id: int
    deep: bool = False

class ChatSource(BaseModel):
    title: str
    chunk: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource] = []
    follow_ups: List[str] = []

# --- Annotation Schemas ---

class AnnotationCreate(BaseModel):
    paper_title: str
    chunk_text: str

class AnnotationUpdate(BaseModel):
    user_note: str

class Annotation(BaseModel):
    id: int
    project_id: int
    paper_title: str
    chunk_text: str
    user_note: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

# --- Literature Review Schemas ---

class LitReviewRequest(BaseModel):
    question: str

class LitReviewSearchResponse(BaseModel):
    paper_ids: List[int]
    message: str

class LitReviewGenerateResponse(BaseModel):
    review: str

# --- Comparison Schemas ---

class ComparisonRow(BaseModel):
    paper_id: int
    title: str
    year: Optional[int] = None
    problem: str
    method: str
    dataset: str
    result: str
    limitation: str

class ComparisonResponse(BaseModel):
    rows: List[ComparisonRow]
    skipped: List[str]  # titles of papers skipped (not ready)

# --- Analysis Schemas ---

class GraphNode(BaseModel):
    id: str
    label: str
    year: Optional[int] = None

class GraphEdge(BaseModel):
    source: str
    target: str

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

    class Config:
        orm_mode = True