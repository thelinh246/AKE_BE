"""User SQLAlchemy ORM model for PostgreSQL."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(128), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class Conservation(Base):
    __tablename__ = "conservation"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    last_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="conservations", lazy="joined")
    details = relationship("ConservationDetail", back_populates="conservation", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"


class ConservationDetail(Base):
    __tablename__ = "conservation_detail"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conservation.id"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # 'user' | 'assistant'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conservation = relationship("Conservation", back_populates="details")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<ConservationDetail(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"
