# # db_session.py
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from models import Base
# db_session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
# import models  # ✅ Ensures all models are registered with Base before creating tables

# Absolute path to the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database", "fta.db")

# Create the database folder if it doesn’t exist
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# SQLAlchemy connection string
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Create engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()
