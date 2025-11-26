from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    Integer,
    JSON,
)
from datetime import datetime
import uuid
from .base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    storage_path = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    status = Column(String, default="pending")  # pending, processing, ready, error
    chunk_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ingested_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, file={self.original_filename}, status={self.status})>"

