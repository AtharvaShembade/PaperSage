from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Paper schemas


# Project Schemas

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