from datetime import datetime
from sqlalchemy.sql import func
# from app.extensions import db # Commented out
from flask import current_app

# Import core SQLAlchemy components directly
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func as sa_func # Add func as sa_func to avoid conflict
from sqlalchemy.orm import relationship

_db = None
try:
    # This will likely only succeed if models.py is imported *during* a request or an app context
    if current_app:
        _db = current_app.extensions['sqlalchemy'].db
        print(f"MODELS.PY: Using db from current_app.extensions['sqlalchemy'].db. Type: {type(_db)}, Initialized: {hasattr(_db, 'Model')}")
except RuntimeError: # Outside app context, e.g. during initial flask run import scan
    print("MODELS.PY: current_app not available (likely initial import scan), falling back to app.extensions.db")
    from app.extensions import db as _db_extensions
    _db = _db_extensions
    print(f"MODELS.PY: Using db from app.extensions. Type: {type(_db)}, Initialized: {hasattr(_db, 'Model')}")


if _db is None:
    # This case should ideally not be reached if app.extensions always provides a db.
    # If it is, it means app.extensions itself failed or db was not defined there.
    print("MODELS.PY: CRITICAL - _db is None after attempting to load. Trying one last import from app.extensions directly.")
    from app.extensions import db as _db_fallback
    _db = _db_fallback
    if _db is None:
        raise RuntimeError("MODELS.PY: Could not obtain a db instance even from direct fallback import!")
    print(f"MODELS.PY: Using db from direct fallback import. Type: {type(_db)}, Initialized: {hasattr(_db, 'Model')}")


class Conversation(_db.Model):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    agent_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)
    status = Column(String, nullable=True, index=True)
    cost_credits = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    hi_notes = Column(Text, nullable=True)

    messages = relationship('Message', backref='conversation', lazy='selectin', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Conversation {self.id} ({self.external_id})>'

class Message(_db.Model):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False, index=True)
    speaker = Column(String, nullable=False, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id} in Conv {self.conversation_id}>'

class Agent(_db.Model):
    __tablename__ = 'agents'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=True, default='active')
    avatar_url = Column(String, nullable=True)

    def __repr__(self):
        return f'<Agent {self.id} ({self.name})>'
