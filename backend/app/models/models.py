from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
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

    status = Column(String, default = "processing", nullable = False, index = True)

    projects = relationship("Project", secondary = "project_papers", back_populates = "papers")

    chunks = relationship("Chunk", back_populates = "paper", cascade = "all, delete-orphan")

# --- Chunk Model (for RAG) ---

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key = True, index = True)

    paper_id = Column(Integer, ForeignKey("papers.id"), nullable = False, index = True)
    paper = relationship("Paper", back_populates = "chunks")

    chunk_text = Column(Text, nullable = False)

    embedding = Column(Vector(768))

# --- Citation Graph Model ---

class CitationLink(Base):
    __tablename__ = "citation_links"

    source_paper_id = Column(String, ForeignKey("papers.external_id"), primary_key=True)
    target_paper_id = Column(String, ForeignKey("papers.external_id"), primary_key=True)

    # You can add this in V2 when you do intent classification
    # intent = Column(String, nullable=True) # "supports", "opposes"

    source_paper = relationship("Paper", foreign_keys=[source_paper_id])
    target_paper = relationship("Paper", foreign_keys=[target_paper_id])