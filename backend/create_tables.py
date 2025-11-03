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

if __name__ == "__main__":
    init_db()