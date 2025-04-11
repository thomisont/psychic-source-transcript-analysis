from datetime import datetime
from sqlalchemy.sql import func
from app.extensions import db # Ensure this line imports from extensions

# Comment out or remove the incorrect import if it exists
# from app import db 

class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    # Assuming an external ID is used, e.g., from ElevenLabs
    external_id = db.Column(db.String, unique=True, nullable=False, index=True)
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

# TODO: Add other analysis models (Themes, Sentiments, Questions, Concerns, PositiveInteractions, Embeddings, AnalysisCache) later. 