import uuid

from sqlalchemy import Column, Integer, String, Date, DateTime, Float, JSON, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base


class PO(Base):
    __tablename__ = "pos"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, index=True, nullable=True)
    date = Column(Date, nullable=True)
    client_name = Column(String, index=True, nullable=True)
    total_value = Column(Float, nullable=True)
    source = Column(String, nullable=True)  # 'gmail' | 'drive' | 'cache'
    file_id = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    parsed_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
