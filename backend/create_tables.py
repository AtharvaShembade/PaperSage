import logging
from app.models.database import Base, engine
from app.models import models

logging.basicConfig(level = logging.INFO)

def init_db():
    logging.info("Creating tables...")
    try:
        Base.metadata.create_all(bind = engine)
        logging.info("Tables created successfully")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        return

    # NOTE: pgvector HNSW/IVFFlat indexes are limited to 2000 dims.
    # Gemini embeddings are 3072 dims — no vector index possible with current vector type.
    # Revisit if RAG query latency becomes an issue (option: migrate to halfvec type).

if __name__ == "__main__":
    init_db()