from sqlalchemy.orm import Session, joinedload
from app.models import models
from app.schemas import schemas

# --- User CRUD ---

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    #placeholder for hashing
    fake_hashed_password = user.password + "_hashed"

    db_user = models.User(email = user.email, hashed_password = fake_hashed_password)\
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
        title = paper.title,
        abstract = paper.abstract,
        year = paper.year,
        status = status
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper

def link_paper_to_project(db: Session, project_id: int, paper_id: int):
    existing_link = db.query(models.ProjectPaper).filter_by(
        project_id = project_id,
        paper_id = paper_id
    ).first()

    if not existing_link:
        db_link = models.ProjectPaper(project_id = project_id, paper_id = paper_id)
        db.add(db_link)
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
            chunk_text = chunk_data["chunk_text"],
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
        models.Chunk.embedding.l2_distance(query_vector)
    ).limit(limit).all()

    return relevant_chunks