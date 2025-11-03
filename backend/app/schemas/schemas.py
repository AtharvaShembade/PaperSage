from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Paper Schemas ---

class Paperbase(BaseModel):
    external_paper_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None

class PaperCreate(PaperBase):
    pdf_url: HttpUrl

class Paper(PaperBase):
    id: int
    status: str

    class Config:
        orm_mode = True

class PaperSearchDetail(PaperBase):
    openAccessPdf: Optional[dict] =- None

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

class ChatResponse(BaseModel):
    answer: str

    