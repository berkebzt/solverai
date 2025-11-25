from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager
import uuid
from datetime import datetime
import logging
import os

from config import settings
from database import init_db, close_db, get_db
from models.conversation import Conversation, Message
from services.llm_service import llm_service
from services.rag_service import rag_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting AI Companion API...")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down AI Companion API...")
    await close_db()


app = FastAPI(
    title="AI Companion API",
    version="0.2.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str


class ConversationResponse(BaseModel):
    conversation_id: str
    title: Optional[str]
    messages: List[dict]
    created_at: datetime
    updated_at: datetime


@app.get("/")
async def root():
    return {
        "message": "AI Companion API is running",
        "version": "0.2.0",
        "features": ["LLM Chat", "Persistent Storage", "Streaming"],
        "endpoints": ["/chat", "/conversations", "/health"],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ollama_status = await llm_service.check_ollama_availability()

    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "ollama": "available" if ollama_status else "unavailable",
            "fallback": "openai" if settings.openai_api_key else "none",
        },
    }


@app.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat endpoint with LLM integration

    Supports both streaming and non-streaming responses
    """
    try:
        # Get or create conversation
        conv_id = request.conversation_id or str(uuid.uuid4())

        # Fetch existing conversation or create new one
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                id=conv_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            )
            db.add(conversation)
            await db.flush()

        # Get conversation history
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        history = result.scalars().all()

        # Store user message
        user_message = Message(
            conversation_id=conv_id,
            role="user",
            content=request.message,
        )
        db.add(user_message)
        await db.flush()

        # Format messages for LLM
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]
        messages.append({"role": "user", "content": request.message})

        # Add system message if first message
        if len(messages) == 1:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant. Be concise, friendly, and accurate.",
                },
            )

        # Retrieve context if RAG is enabled
        context = None
        if settings.rag_enabled:
            docs = rag_service.retrieve(request.message)
            if docs:
                context = "\n".join([doc.page_content for doc in docs])
                logger.info(f"Retrieved {len(docs)} documents for context")

        # Generate response
        if request.stream:
            # Return streaming response
            async def generate_stream():
                full_response = ""
                stream_gen = await llm_service.generate_response(messages, stream=True, context=context)
                async for chunk in stream_gen:
                    full_response += chunk
                    yield f"data: {chunk}\n\n"

                # Store complete response in database
                assistant_message = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=full_response,
                )
                db.add(assistant_message)
                await db.commit()

                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
            )
        else:
            # Get complete response
            llm_response = await llm_service.generate_response(messages, stream=False, context=context)

            # Ensure we have a string response
            if not isinstance(llm_response, str):
                raise Exception("Expected string response from LLM")

            # Store assistant response
            assistant_message = Message(
                conversation_id=conv_id,
                role="assistant",
                content=llm_response,
            )
            db.add(assistant_message)
            await db.commit()

            return ChatResponse(
                response=llm_response,
                conversation_id=conv_id,
                timestamp=datetime.now().isoformat(),
            )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
):
    """Upload a document for RAG ingestion"""
    try:
        # Create documents directory if it doesn't exist
        os.makedirs("documents", exist_ok=True)
        
        file_path = f"documents/{file.filename}"
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Ingest file
        chunks = await rag_service.ingest_file(file_path)
        
        return {
            "message": "File uploaded and ingested successfully",
            "filename": file.filename,
            "chunks": chunks
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation with all messages"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return ConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        messages=[
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@app.get("/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all conversations"""
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()

    return {
        "conversations": [
            {
                "conversation_id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv in conversations
        ],
        "limit": limit,
        "offset": offset,
    }


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    return {"message": "Conversation deleted successfully"}
