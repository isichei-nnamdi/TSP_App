import os
from sqlalchemy import create_engine
from models import Base  # Assuming models.py has all table classes and Base defined
# from database import DB_PATH  # Reuse DB_PATH from your existing database config

DB_PATH = "fta.db"

def reset_database():
    # Delete the existing database file, if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("✅ Existing database removed.")

    # Recreate the database and tables using SQLAlchemy
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Base.metadata.create_all(engine)

    print("✅ Database reset and all tables reinitialized successfully.")

if __name__ == "__main__":
    reset_database()