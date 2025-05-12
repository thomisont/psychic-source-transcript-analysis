
from datetime import datetime
from sqlalchemy.sql import func
from app.extensions import db

class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String, unique=True, nullable=False, index=True)
    agent_id = db.Column(db.String, nullable=True, index=True)
    title = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    status = db.Column(db.String, nullable=True, index=True)
    cost_credits = db.Column(db.Integer, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    hi_notes = db.Column(db.Text, nullable=True)

    messages = db.relationship('Message', backref='conversation', lazy='selectin', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Conversation {self.id} ({self.external_id})>'

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True)
    speaker = db.Column(db.String, nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id} in Conv {self.conversation_id}>'

class Agent(db.Model):
    __tablename__ = 'agents'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    system_prompt = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String, nullable=True, default='active')
    avatar_url = db.Column(db.String, nullable=True)

    def __repr__(self):
        return f'<Agent {self.id} ({self.name})>'
