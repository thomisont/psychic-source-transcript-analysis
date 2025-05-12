from datetime import datetime
from sqlalchemy import func, DateTime, Text, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

from app.extensions import db

# Define models
class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    # Assuming an external ID is used, e.g., from ElevenLabs
    external_id = db.Column(db.String, unique=True, nullable=False, index=True)
    agent_id = db.Column(db.String, nullable=True, index=True) # Added for multi-agent support
    title = db.Column(db.String, nullable=True) # Or extract from messages?
    # Ensure created_at is timezone aware
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    # Add status column
    status = db.Column(db.String, nullable=True, index=True) # e.g., 'done', 'failed', 'processing'
    # Add cost column
    cost_credits = db.Column(db.Integer, nullable=True) # Matches Supabase int4, nullable
    # +++ Add summary field +++
    summary = db.Column(db.Text, nullable=True) # Stores the conversation summary
    # +++ Add HI Notes field for human feedback +++
    hi_notes = db.Column(db.Text, nullable=True) # Stores human input notes/commentary

    # Relationship to messages
    messages = db.relationship('Message', backref='conversation', lazy='selectin', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Conversation {self.id} ({self.external_id})>'

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True)
    # Assuming speaker role ('user', 'psychic', 'system'?)
    speaker = db.Column(db.String, nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True) # Timestamp of the message itself
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional: Store embeddings directly if pgvector is used early
    # embedding = db.Column(Vector(384)) # Example dimension

    def __repr__(self):
        return f'<Message {self.id} in Conv {self.conversation_id}>'

class Agent(db.Model):
    __tablename__ = 'agents' # Define table name

    id = db.Column(db.String, primary_key=True) # Agent ID from ElevenLabs will be string
    name = db.Column(db.String, nullable=False)
    system_prompt = db.Column(db.Text, nullable=True)
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Example additional fields (can be expanded)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String, nullable=True, default='active') # e.g., active, inactive, maintenance
    avatar_url = db.Column(db.String, nullable=True)

    def __repr__(self):
        return f'<Agent {self.id} ({self.name})>'

# TODO: Add other analysis models (Themes, Sentiments, Questions, Concerns, PositiveInteractions, Embeddings, AnalysisCache) later.