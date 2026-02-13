from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Use a default in-memory database for testing unless otherwise specified
DATABASE_URL = os.getenv("SQLITE_DB_PATH", "sqlite:///./test_api.db")
if DATABASE_URL.endswith(".db"):
    DATABASE_URL = f"sqlite:///./{DATABASE_URL}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)