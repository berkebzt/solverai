from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
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
from models.document import Document
from services.llm_service import llm_service
from services.rag_service import rag_service
from services.document_service import document_service
from services.voice_service import voice_service

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
    document_ids: Optional[List[str]] = None


class SourceDocument(BaseModel):
    document_id: Optional[str]
    chunk_index: Optional[int]
    source_path: Optional[str]
    preview: Optional[str]


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    sources: Optional[List[SourceDocument]] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    title: Optional[str]
    messages: List[dict]
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    status: str
    chunk_count: int
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    ingested_at: Optional[datetime]

    class Config:
        from_attributes = True


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str]
    duration_seconds: Optional[float]


class SpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = None


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
                    "content": """You are SolverAI, a helpful and knowledgeable assistant.

Guidelines for your responses:
- Be clear, accurate, and well-structured
- Use markdown formatting for better readability:
  - Use **bold** for important terms or emphasis
  - Use bullet points or numbered lists for steps or multiple items
  - Use headings (## or ###) for organizing longer responses
  - Use `code` formatting for technical terms, commands, or code
- Keep paragraphs concise and separated
- When providing steps or instructions, number them clearly
- Be friendly but professional in tone
- If you don't know something, say so honestly""",
                },
            )

        # Retrieve context if RAG is enabled
        context = None
        context_sources: List[SourceDocument] = []
        if settings.rag_enabled:
            docs = rag_service.retrieve(
                request.message, document_ids=request.document_ids
            )
            if docs:
                context = "\n".join([doc.page_content for doc in docs])
                context_sources = [
                    SourceDocument(
                        document_id=doc.metadata.get("document_id"),
                        chunk_index=doc.metadata.get("chunk_index"),
                        source_path=doc.metadata.get("source"),
                        preview=doc.page_content[:200],
                    )
                    for doc in docs
                ]
                logger.info(
                    "Retrieved %s documents for context (filtered=%s)",
                    len(docs),
                    bool(request.document_ids),
                )

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
                    meta={"sources": [source.model_dump() for source in context_sources]},
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
                meta={"sources": [source.model_dump() for source in context_sources]},
            )
            db.add(assistant_message)
            await db.commit()

            return ChatResponse(
                response=llm_response,
                conversation_id=conv_id,
                timestamp=datetime.now().isoformat(),
                sources=context_sources or None,
            )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for RAG ingestion"""
    allowed_types = {"application/pdf", "text/plain"}
    ext = os.path.splitext(file.filename.lower())[-1]
    if file.content_type not in allowed_types and ext not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only PDF and TXT are supported.",
        )

    document_id = str(uuid.uuid4())
    stored_filename = document_service.build_stored_filename(document_id, file.filename)
    storage_path = os.path.join(settings.absolute_documents_dir, stored_filename)

    document = Document(
        id=document_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        storage_path=storage_path,
        content_type=file.content_type,
        status="pending",
    )
    db.add(document)
    await db.flush()

    try:
        saved_path, size_bytes = await document_service.save_upload(
            file, stored_filename
        )
        document.storage_path = saved_path
        document.size_bytes = size_bytes
        document.status = "processing"
        await db.commit()

        chunks = await rag_service.ingest_file(saved_path, document.id)
        document.chunk_count = chunks
        document.status = "ready"
        document.ingested_at = datetime.utcnow()
        document.error = None
        await db.commit()
    except Exception as e:
        document.status = "error"
        document.error = str(e)
        await db.commit()
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    await db.refresh(document)
    return document


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


@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded documents"""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return docs


@app.delete("/documents/{document_id}")
async def delete_document_entry(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete document metadata, file, and vector entries"""
    document = await db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    removed_chunks = rag_service.remove_document(document_id)
    document_service.remove_file(document.storage_path)
    await db.delete(document)
    await db.commit()

    return {
        "message": "Document deleted successfully",
        "chunks_removed": removed_chunks,
    }


@app.post("/documents/{document_id}/reingest", response_model=DocumentResponse)
async def reingest_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reprocess an existing document"""
    document = await db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.storage_path):
        raise HTTPException(
            status_code=400, detail="Stored file missing. Re-upload required."
        )

    try:
        document.status = "processing"
        await db.commit()

        rag_service.remove_document(document_id)
        chunks = await rag_service.ingest_file(document.storage_path, document_id)

        document.chunk_count = chunks
        document.status = "ready"
        document.ingested_at = datetime.utcnow()
        document.updated_at = datetime.utcnow()
        document.error = None
        await db.commit()
    except Exception as e:
        document.status = "error"
        document.error = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    await db.refresh(document)
    return document


@app.post("/voice/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """Transcribe audio locally with Whisper"""
    if audio.content_type and not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format")

    tmp_name = f"transcribe_{uuid.uuid4()}.tmp"
    tmp_path = os.path.join(settings.absolute_audio_dir, tmp_name)
    os.makedirs(settings.absolute_audio_dir, exist_ok=True)

    try:
        contents = await audio.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)

        text, detected_language, duration = await voice_service.transcribe(
            tmp_path, language=language
        )
        return TranscriptionResponse(
            text=text,
            language=language or detected_language,
            duration_seconds=duration,
        )
    finally:
        voice_service.cleanup_audio(tmp_path)


@app.post("/voice/speak")
async def synthesize_speech(
    request: SpeechRequest,
    background_tasks: BackgroundTasks,
):
    """Convert text to speech locally"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required for speech")

    audio_path = await voice_service.synthesize(
        request.text.strip(), voice=request.voice
    )

    background_tasks.add_task(voice_service.cleanup_audio, audio_path)

    filename = f"synthesis_{uuid.uuid4()}.wav"
    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename=filename,
    )
