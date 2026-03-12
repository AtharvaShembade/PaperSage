from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base
from pgvector.sqlalchemy import Vector

# --- User Model ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key = True, index = True)
    email = Column(String, unique = True, index = True, nullable = False)

    projects = relationship("Project", back_populates = "owner")

# --- Project Model ---

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, index = True, nullable = False)
    created_at = Column(DateTime, default = datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="projects")

    papers = relationship("Paper", secondary="project_papers", back_populates="projects")

# --- Association Table (for Many-to-Many) ---

class ProjectPaper(Base):
    __tablename__ = "project_papers"
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key = True)
    paper_id = Column(Integer, ForeignKey("papers.id"), primary_key = True)

# --- Paper Model ---

class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key = True, index = True)

    external_id = Column(String, unique = True,index = True, nullable = False)

    title = Column(String, nullable = False)
    abstract = Column(Text, nullable = True)
    year = Column(Integer, nullable = True)

    status   = Column(String, default="processing", nullable=False, index=True)
    arxiv_id = Column(String, nullable=True, index=True)
    pdf_url  = Column(String, nullable=True)
    source   = Column(String, nullable=True)   # "arxiv" or "s2"
    tldr     = Column(Text, nullable=True)

    projects = relationship("Project", secondary = "project_papers", back_populates = "papers")

    chunks = relationship("Chunk", back_populates = "paper", cascade = "all, delete-orphan")

# --- Chunk Model (for RAG) ---

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key = True, index = True)

    paper_id = Column(Integer, ForeignKey("papers.id"), nullable = False, index = True)
    paper = relationship("Paper", back_populates = "chunks")

    chunk_text = Column(Text, nullable = False)

    embedding = Column(Vector(3072))

# --- Annotation Model ---

class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_title = Column(String, nullable=False)
    chunk_text = Column(Text, nullable=False)
    user_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")

# --- Chat Session Model ---

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, default="New Chat", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = Column(JSON, default=list, nullable=False)

    project = relationship("Project")

# --- Citation Graph Model ---

class CitationLink(Base):
    __tablename__ = "citation_links"

    source_paper_id = Column(String, ForeignKey("papers.external_id"), primary_key=True)
    target_paper_id = Column(String, ForeignKey("papers.external_id"), primary_key=True)

    # You can add this in V2 when you do intent classification
    # intent = Column(String, nullable=True) # "supports", "opposes"

    source_paper = relationship("Paper", foreign_keys=[source_paper_id])
    target_paper = relationship("Paper", foreign_keys=[target_paper_id])