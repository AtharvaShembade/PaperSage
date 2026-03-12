from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast
from pgvector.sqlalchemy import Vector
from app.models import models
from app.schemas import schemas
from typing import List, Dict, Any

# --- User CRUD ---

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, email: str):

    db_user = models.User(email=email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Project CRUD ---

def get_project(db: Session, project_id: int):
    return db.query(models.Project).options(joinedload(models.Project.papers)).filter(models.Project.id == project_id).first()

def get_projects_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Project).filter(models.Project.owner_id == user_id).offset(skip).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate, user_id: int):
    db_project = models.Project(**project.dict(), owner_id = user_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id = int):
    db_project = db.get(models.Project, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
    return db_project

# --- Paper & Ingestion CRUD ---

def get_paper(db: Session, paper_id: str):
    return db.query(models.Paper).filter(models.Paper.external_id == paper_id).first()



def create_paper(db: Session, paper: schemas.PaperCreate, status: str = "processing"):
    db_paper = models.Paper(
        external_id = paper.external_id,
        title       = paper.title,
        abstract    = paper.abstract,
        year        = paper.year,
        arxiv_id    = paper.arxiv_id,
        status      = status
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper

def update_paper_pdf(db: Session, paper_id: int, pdf_url: str, source: str):
    db_paper = db.get(models.Paper, paper_id)
    if db_paper:
        db_paper.pdf_url = pdf_url
        db_paper.source  = source
        db.commit()

def link_paper_to_project(db: Session, project_id: int, paper_id: int):
    existing_link = db.query(models.ProjectPaper).filter_by(
        project_id = project_id,
        paper_id = paper_id
    ).first()

    if not existing_link:
        db_link = models.ProjectPaper(project_id = project_id, paper_id = paper_id)
        db.add(db_link)
        db.commit()

def update_paper_tldr(db: Session, paper_id: int, tldr: str):
    db_paper = db.get(models.Paper, paper_id)
    if db_paper:
        db_paper.tldr = tldr
        db.commit()

def update_paper_status(db: Session, paper_id: int, status: str):
    db_paper = db.get(models.Paper, paper_id)
    if db_paper:
        db_paper.status = status
        db.commit()
        db.refresh(db_paper)
    return db_paper

# --- Chunk & RAG CRUD ---

def create_chunks(db: Session, paper_id: int, chunks_data: List[Dict[str, Any]]):
    db_chunks = [
        models.Chunk(
            paper_id = paper_id,
            chunk_text = item["chunk_text"],
            embedding = item["embedding"]
        ) for item in chunks_data
    ]
    db.add_all(db_chunks)
    db.commit()

def get_relevant_chunks(
    db: Session,
    project_id: int,
    query_vector: list[float],
    limit: int = 5
) -> List[models.Chunk]:

    relevant_chunks = db.query(models.Chunk).join(models.Paper).join(models.ProjectPaper).filter(
        models.ProjectPaper.project_id == project_id,
        models.Paper.status == 'ready'
    ).order_by(
        models.Chunk.embedding.l2_distance(cast(query_vector, Vector(3072)))
    ).limit(limit).all()

    return relevant_chunks

def remove_paper_from_project(db: Session, project_id: int, paper_id: int):
    db_link = db.query(models.ProjectPaper).filter_by(
        project_id=project_id,
        paper_id=paper_id
    ).first()
    if db_link:
        db.delete(db_link)
        db.commit()

    remaining = db.query(models.ProjectPaper).filter_by(paper_id=paper_id).count()
    if remaining == 0:
        db_paper = db.get(models.Paper, paper_id)
        if db_paper:
            db.delete(db_paper)
            db.commit()

def get_chunks_for_paper(db: Session, paper_id: int, limit: int = 20) -> List[models.Chunk]:
    return db.query(models.Chunk).filter(
        models.Chunk.paper_id == paper_id
    ).limit(limit).all()

# --- Annotation CRUD ---

def create_annotation(db: Session, project_id: int, paper_title: str, chunk_text: str) -> models.Annotation:
    annotation = models.Annotation(project_id=project_id, paper_title=paper_title, chunk_text=chunk_text)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation

def get_annotations(db: Session, project_id: int) -> List[models.Annotation]:
    return db.query(models.Annotation).filter(models.Annotation.project_id == project_id).order_by(models.Annotation.created_at.desc()).all()

def get_annotation(db: Session, annotation_id: int) -> models.Annotation:
    return db.get(models.Annotation, annotation_id)

def update_annotation(db: Session, annotation_id: int, user_note: str) -> models.Annotation:
    annotation = db.get(models.Annotation, annotation_id)
    if annotation:
        annotation.user_note = user_note
        db.commit()
        db.refresh(annotation)
    return annotation

def delete_annotation(db: Session, annotation_id: int):
    annotation = db.get(models.Annotation, annotation_id)
    if annotation:
        db.delete(annotation)
        db.commit()

# --- Chat Session CRUD ---

def get_chat_sessions(db: Session, project_id: int, user_id: int) -> List[models.ChatSession]:
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.project_id == project_id, models.ChatSession.user_id == user_id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )

def create_chat_session(db: Session, project_id: int, user_id: int, name: str = "New Chat") -> models.ChatSession:
    session = models.ChatSession(project_id=project_id, user_id=user_id, name=name, messages=[])
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_chat_session(db: Session, session_id: int) -> models.ChatSession:
    return db.get(models.ChatSession, session_id)

def update_chat_session(db: Session, session_id: int, name: str = None, messages: List[dict] = None) -> models.ChatSession:
    session = db.get(models.ChatSession, session_id)
    if not session:
        return None
    if name is not None:
        session.name = name
    if messages is not None:
        session.messages = list(messages)  # reassign to trigger SQLAlchemy change detection
    db.commit()
    db.refresh(session)
    return session

def delete_chat_session(db: Session, session_id: int):
    session = db.get(models.ChatSession, session_id)
    if session:
        db.delete(session)
        db.commit()

# --- Citation Graph CRUD ---

def create_citation_links(db: Session, links_data: List[Dict[str, str]]):

    from sqlalchemy.dialects.postgresql import insert

    insert_stmt = insert(models.CitationLink).values(links_data)

    do_nothing_stmt = insert_stmt.on_conflict_do_nothing(
        index_elements = ["source_paper_id", "target_paper_id"]
    )

    db.execute(do_nothing_stmt)
    db.commit()