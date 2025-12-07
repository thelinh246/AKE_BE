"""Chatbot API routes built from the Streamlit demo logic."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from pydantic import BaseModel, Field

from services.chatbot_service import ChatbotService, ChatbotResult
from services.conversation_service import ConversationService
from services.database import get_db
from services.auth import decode_token
from services.user_service import UserService
from sqlalchemy.orm import Session
from models import ConservationResponse, ConservationDetailResponse
from services.context_service import rewrite_question_with_context

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


class ChatbotRequest(BaseModel):
    message: str = Field(..., description="Câu hỏi từ người dùng")
    conversation_id: Optional[int] = Field(None, description="Tiếp tục cuộc trò chuyện cũ")
    title: Optional[str] = Field(None, description="Tiêu đề cuộc trò chuyện (nếu muốn đặt thủ công)")


class ChatbotResponse(BaseModel):
    analysis: Dict[str, Any]
    results: Optional[List[Dict[str, Any]]] = None
    answer: str
    query_type: Optional[str] = None
    conversation_id: Optional[int] = None


def _get_service(request: Request) -> ChatbotService:
    svc = getattr(request.app.state, "chatbot_service", None)
    if not svc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot service is not initialized. Check Gemini/Neo4j configuration.",
        )
    return svc


@router.post("/message", response_model=ChatbotResponse)
def chat_message(
    payload: ChatbotRequest,
    db: Session = Depends(get_db),
    service: ChatbotService = Depends(_get_service),
    authorization: Optional[str] = Header(None),
) -> ChatbotResponse:
    """
    Trả lời câu hỏi bằng pipeline: detect intent -> Cypher -> format.

    Returns both the friendly answer and the raw analysis/results
    to help client-side UIs render richer experiences.
    """
    user_id = _get_user_id_from_token(db, authorization)

    conversation = _get_or_create_conversation(
        db=db,
        payload=payload,
        user_id=user_id,
    )

    # Lấy history để rewrite câu hỏi cho đầy đủ ngữ cảnh
    history_details = ConversationService.list_details(db, conversation.id) if conversation else []
    history_texts = [
        f"{detail.role}: {detail.message}" for detail in history_details[-10:]
    ]
    rewritten_question, new_title = rewrite_question_with_context(
        conversation.title if conversation else None,
        history_texts,
        payload.message,
    )

    # Cập nhật title nếu có đề xuất mới
    if conversation and new_title and new_title != conversation.title:
        ConversationService.touch_conversation(db, conversation, title=new_title)

    result: ChatbotResult = service.chat(rewritten_question)

    # Lưu lịch sử: user hỏi + bot trả lời
    ConversationService.add_pair(
        db=db,
        conversation=conversation,
        user_message=payload.message,
        assistant_message=result.reply,
    )

    return ChatbotResponse(
        analysis=result.analysis,
        results=result.query_results,
        answer=result.reply,
        query_type=result.query_type,
        conversation_id=conversation.id if conversation else None,
    )


def _get_user_id_from_token(db: Session, authorization: Optional[str]) -> Optional[int]:
    """Parse Bearer token to get user id; returns None if missing/invalid."""
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
    except ValueError:
        return None

    payload = decode_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    if not email:
        return None
    user = UserService.get_user_by_email(db, email)
    return user.id if user else None


def _require_user_id(db: Session, authorization: Optional[str]) -> int:
    """Strict version: require Bearer token and valid user."""
    user_id = _get_user_id_from_token(db, authorization)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def _get_or_create_conversation(db: Session, payload: ChatbotRequest, user_id: Optional[int]):
    title = payload.title or payload.message[:80]

    if payload.conversation_id:
        conversation = ConversationService.get_conversation(db, payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Optional guard: if conversation is linked to a user, enforce ownership
        if conversation.user_id and user_id and conversation.user_id != user_id:
            raise HTTPException(status_code=403, detail="Conversation does not belong to this user")
        ConversationService.touch_conversation(db, conversation, title=title)
        return conversation

    return ConversationService.create_conversation(db, user_id=user_id, title=title)


@router.get("/conservations", response_model=List[ConservationResponse])
def list_conservations(
    db: Session = Depends(get_db),
    authorization: str = Header(...),
    skip: int = 0,
    limit: int = 20,
):
    """Lấy danh sách conservation (bắt buộc Bearer token, lọc theo user)."""
    user_id = _require_user_id(db, authorization)
    conservations = ConversationService.list_conservations(db, user_id=user_id, skip=skip, limit=limit)
    return conservations


@router.get("/conservations/{conversation_id}/details", response_model=List[ConservationDetailResponse])
def get_conservation_details(
    conversation_id: int,
    db: Session = Depends(get_db),
    authorization: str = Header(...),
):
    """Lấy chi tiết tin nhắn của một conservation (bắt buộc Bearer token, kiểm tra sở hữu)."""
    user_id = _require_user_id(db, authorization)
    conversation = ConversationService.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        # Không tiết lộ tồn tại nếu không sở hữu
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationService.list_details(db, conversation_id)
