from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
from pgvector.sqlalchemy import Vector

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key = True, index = True)
    email = Column(String, unique = True, index = True, nullable = False)

    projects = relationship("Project", back_populates = "owner")

# Project model
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, index = True, nullable = False)
    created_at = Column(DateTime, default = datetime.now)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="projects")

    papers = relationship("Paper", secondary="project_papers", back_populates="projects")

# projectPaper model

# Paper model

# PaperChunk model
