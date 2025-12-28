"""
Database configuration for ViMax with SQLAlchemy
Provides database engine and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database_models import Base
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vimax_seko.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Database session dependency for FastAPI
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_URL}")


def drop_db():
    """
    Drop all tables - use with caution!
    Only for development/testing
    """
    print("WARNING: Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped")


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print("\n✅ Database setup complete!")
    print(f"📁 Database file: {DATABASE_URL}")