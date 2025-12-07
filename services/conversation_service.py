from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Conservation, ConservationDetail


class ConversationService:
    """Service for storing chatbot conversation history."""

    @staticmethod
    def get_conversation(db: Session, conversation_id: int) -> Optional[Conservation]:
        return db.get(Conservation, conversation_id)

    @staticmethod
    def create_conversation(db: Session, user_id: Optional[int], title: Optional[str]) -> Conservation:
        conversation = Conservation(
            user_id=user_id,
            title=title,
            last_update=datetime.utcnow(),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def touch_conversation(db: Session, conversation: Conservation, title: Optional[str] = None) -> Conservation:
        if title and title != conversation.title:
            conversation.title = title
        conversation.last_update = datetime.utcnow()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def add_message(db: Session, conversation_id: int, role: str, message: str) -> ConservationDetail:
        detail = ConservationDetail(
            conversation_id=conversation_id,
            role=role,
            message=message,
        )
        db.add(detail)
        # Do not commit here; caller decides.
        return detail

    @staticmethod
    def add_pair(
        db: Session,
        conversation: Conservation,
        user_message: str,
        assistant_message: str,
    ) -> None:
        ConversationService.add_message(db, conversation.id, "user", user_message)
        ConversationService.add_message(db, conversation.id, "assistant", assistant_message)
        conversation.last_update = datetime.utcnow()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    @staticmethod
    def list_conservations(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 20) -> List[Conservation]:
        stmt = select(Conservation).offset(skip).limit(limit).order_by(Conservation.last_update.desc())
        if user_id is not None:
            stmt = stmt.where(Conservation.user_id == user_id)
        return db.scalars(stmt).all()

    @staticmethod
    def list_details(db: Session, conversation_id: int) -> List[ConservationDetail]:
        stmt = (
            select(ConservationDetail)
            .where(ConservationDetail.conversation_id == conversation_id)
            .order_by(ConservationDetail.created_at.asc())
        )
        return db.scalars(stmt).all()

    @staticmethod
    def delete_conversation(db: Session, conversation_id: int) -> bool:
        convo = db.get(Conservation, conversation_id)
        if not convo:
            return False
        db.delete(convo)
        db.commit()
        return True
