"""Database session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config import settings
from models import Base


class Database:
    """Database management class."""
    
    def __init__(self):
        # Configure database engine
        if settings.database_url.startswith("sqlite"):
            # SQLite specific configuration
            self.engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.debug
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                settings.database_url,
                echo=settings.debug
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()


# Global database instance
database = Database()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = database.get_session()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    database.create_tables()