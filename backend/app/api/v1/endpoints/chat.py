from datetime import datetime
from typing import List, Optional

# Import your Supabase client
from app.core.supabase import get_supabase_client
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

from ..dependencies import get_current_user

router = APIRouter()


# Models
class ChatMessageCreate(BaseModel):
    content: str
    role: str = "user"  # 'user' or 'assistant'
    sources: Optional[list] = None
    metadata: Optional[dict] = None


class ChatSessionCreate(BaseModel):
    document_id: str
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: str
    document_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    sources: Optional[list] = None


# Endpoints
@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate, current_user: dict = Depends(get_current_user)
):
    """
    Create a new chat session for a document.
    """
    # Verify document exists
    sb = get_supabase_client()
    doc = (
        sb.table("documents").select("id").eq("id", session_data.document_id).execute()
    )
    if not doc.data or len(doc.data) == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    # Create session
    session = {
        "document_id": session_data.document_id,
        "title": session_data.title
        or f"Chat about {doc.data[0].get('title', 'Document')}",
        "user_id": current_user.get("id"),
    }

    result = supabase.table("chat_sessions").insert(session).execute()

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create chat session")

    return result.data[0]


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    document_id: Optional[str] = None, current_user: dict = Depends(get_current_user)
):
    """
    List chat sessions, optionally filtered by document_id.
    """
    query = supabase.table("chat_sessions").select("*")

    # Optional document filter
    if document_id:
        query = query.eq("document_id", document_id)

    # Order by most recent first
    result = query.order("updated_at", desc=True).execute()

    return result.data if result.data else []


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def create_chat_message(
    session_id: str,
    message: ChatMessageCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Add a message to a chat session.
    """
    sb = get_supabase()

    # Verify session exists and user has access
    session = (
        sb.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", current_user.get("id"))
        .execute()
    )
    if not session.data or len(session.data) == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Create message
    message_data = {
        "session_id": session_id,
        "role": message.role,
        "content": message.content,
        "sources": message.sources or [],
        "metadata": message.metadata or {},
    }

    # Insert in transaction
    try:
        # Add message
        result = sb.table("chat_messages").insert(message_data).execute()

        # Update session updated_at
        sb.table("chat_sessions").update(
            {"updated_at": datetime.utcnow().isoformat()}
        ).eq("id", session_id).execute()

        return result.data[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save message: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get all messages for a chat session.
    """
    sb = get_supabase()

    # Verify session exists and user has access
    session = (
        sb.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", current_user.get("id"))
        .execute()
    )
    if not session.data or len(session.data) == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get messages
    result = (
        sb.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Delete a chat session and all its messages.
    """
    sb = get_supabase()

    # Verify session exists and user has access
    session = (
        sb.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", current_user.get("id"))
        .execute()
    )
    if not session.data or len(session.data) == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Delete messages (cascade would handle this, but being explicit)
    sb.table("chat_messages").delete().eq("session_id", session_id).execute()

    # Delete session
    sb.table("chat_sessions").delete().eq("id", session_id).execute()

    return {"message": "Chat session deleted successfully"}
