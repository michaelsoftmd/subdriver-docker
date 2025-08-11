from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from typing import Generator
import json

from app.core.config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class ResearchSession(Base):
    __tablename__ = "research_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String, unique=True, index=True)
    topic = Column(String, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    data = Column(JSON)
    status = Column(String, default="pending")

class CollectedPost(Base):
    __tablename__ = "collected_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    publication = Column(String, index=True)
    title = Column(String)
    author = Column(String)
    published_date = Column(String)
    collected_at = Column(DateTime, server_default=func.now())
    content = Column(Text)
    data = Column(JSON)

# Database initialization
def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Repository pattern for cleaner data access
class ResearchRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, workflow_id: str, topic: str, data: dict) -> ResearchSession:
        """Create new research session"""
        session = ResearchSession(
            workflow_id=workflow_id,
            topic=topic,
            data=data
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def get_session(self, workflow_id: str) -> ResearchSession:
        """Get research session by ID"""
        return self.db.query(ResearchSession).filter(
            ResearchSession.workflow_id == workflow_id
        ).first()
    
    def update_session(self, workflow_id: str, data: dict, status: str = None):
        """Update research session"""
        session = self.get_session(workflow_id)
        if session:
            session.data = data
            if status:
                session.status = status
            self.db.commit()
        return session
