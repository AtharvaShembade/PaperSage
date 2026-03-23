from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


engine = create_engine(settings.DATABASE_URL, poolclass=NullPool)

@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    from pgvector.psycopg2 import register_vector
    register_vector(dbapi_connection)

SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)
Base = declarative_base()

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()