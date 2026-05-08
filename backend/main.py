"""
Tata - AI Personality Replication Chat Companion
FastAPI Main Application
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from models import (
    init_db, SessionLocal, User, Persona, ChatLog, Conversation,
    Schedule, SubscriptionTier, Gender, MessageRole
)
from services.llm_service import llm_service
from services.payment_service import payment_service

# ── App Setup ─────────────────────────────────────────

app = FastAPI(
    title="Tata API",
    version=settings.app_version,
    description="AI Personality Replication & Chat Companion",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth Setup ────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── Schemas ───────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    display_name: str = ""


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    display_name: str
    subscription_tier: SubscriptionTier
    messages_remaining: int


class PersonaCreate(BaseModel):
    name: str
    description: str = ""
    gender: Gender = Gender.UNSPECIFIED
    age_range: str = ""
    native_language: str = "zh-CN"
    speaking_style: str = ""
    habits: list[str] = []
    custom_prompt: str = ""
    emotion_range: str = "warm,friendly"


class PersonaResponse(BaseModel):
    id: int
    name: str
    description: str
    gender: Gender
    speaking_style: str
    habits: list[str]
    is_active: bool
    total_messages_sent: int


class ChatRequest(BaseModel):
    persona_id: int
    message: str
    provider: str = "openai"


class ScheduleCreate(BaseModel):
    persona_id: int
    cron_expression: str
    prompt_hint: str = ""


# ══════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════

@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=user_data.email,
        username=user_data.username,
        display_name=user_data.display_name,
        hashed_password=pwd_context.hash(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)},
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.model_validate(user)}


@app.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


# ══════════════════════════════════════════════════════
#  PERSONA ROUTES
# ══════════════════════════════════════════════════════

@app.post("/personas", response_model=PersonaResponse)
async def create_persona(
    data: PersonaCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new AI persona."""
    persona = Persona(owner_id=user.id, **data.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@app.get("/personas", response_model=list[PersonaResponse])
async def list_personas(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all personas for the current user."""
    return db.query(Persona).filter(Persona.owner_id == user.id).all()


@app.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific persona."""
    persona = db.query(Persona).filter(
        Persona.id == persona_id, Persona.owner_id == user.id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@app.post("/personas/{persona_id}/chat-logs")
async def upload_chat_logs(
    persona_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload chat logs to train the persona.
    Supports formats:
      - WeChat export (.txt) - format: "2024-01-01 12:00 对方: 消息"
      - JSON array [{"role": "original", "content": "...", "sender": "..."}]
    """
    persona = db.query(Persona).filter(
        Persona.id == persona_id, Persona.owner_id == user.id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    content = await file.read()
    text = content.decode("utf-8")

    logs = []
    if file.filename.endswith(".json"):
        import json
        data = json.loads(text)
        if isinstance(data, list):
            for item in data:
                logs.append(ChatLog(
                    persona_id=persona_id,
                    role=MessageRole.ORIGINAL,
                    sender_name=item.get("sender", ""),
                    content=item.get("content", ""),
                    metadata_=item.get("metadata", {})
                ))
    else:
        # Parse chat export (WeChat-style)
        import re
        pattern = r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+(.+?)[:：]\s*(.+)'
        for match in re.finditer(pattern, text):
            sender = match.group(2).strip()
            msg_content = match.group(3).strip()
            logs.append(ChatLog(
                persona_id=persona_id,
                role=MessageRole.ORIGINAL,
                sender_name=sender,
                content=msg_content,
            ))

    if logs:
        db.add_all(logs)
        db.commit()
        # Index into vector store for RAG
        await llm_service.index_chat_logs(persona_id, logs)
        return {"imported": len(logs)}

    return {"imported": 0, "error": "No valid chat messages found"}


@app.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a persona and all associated data."""
    persona = db.query(Persona).filter(
        Persona.id == persona_id, Persona.owner_id == user.id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    db.delete(persona)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════════
#  CHAT ROUTES
# ══════════════════════════════════════════════════════

@app.post("/chat")
async def chat_with_persona(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the AI persona and get a reply."""
    if not payment_service.check_quota(user):
        raise HTTPException(status_code=402, detail="Message quota exceeded. Upgrade to Pro!")

    persona = db.query(Persona).filter(
        Persona.id == req.persona_id, Persona.owner_id == user.id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Get recent conversation history
    history = db.query(Conversation).filter(
        Conversation.persona_id == persona.id
    ).order_by(Conversation.created_at.desc()).limit(30).all()

    history_msgs = [
        {"role": h.role.value if h.role.value != "ai" else "assistant", "content": h.content}
        for h in reversed(history)
    ]

    # Save user message
    user_msg = Conversation(
        persona_id=persona.id, user_id=user.id,
        role=MessageRole.USER, content=req.message
    )
    db.add(user_msg)

    # Generate response
    response = await llm_service.generate_message(
        persona=persona,
        user_message=req.message,
        conversation_history=history_msgs,
        provider=req.provider,
    )

    # Save AI response
    ai_msg = Conversation(
        persona_id=persona.id, user_id=user.id,
        role=MessageRole.AI, content=response
    )
    db.add(ai_msg)
    persona.total_messages_sent += 1
    payment_service.consume_message(user)
    db.commit()

    return {"reply": response, "remaining": user.messages_remaining}


@app.post("/chat/stream")
async def chat_with_persona_stream(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream chat with persona."""
    if not payment_service.check_quota(user):
        raise HTTPException(status_code=402, detail="Message quota exceeded")

    persona = db.query(Persona).filter(
        Persona.id == req.persona_id, Persona.owner_id == user.id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Save user message
    user_msg = Conversation(
        persona_id=persona.id, user_id=user.id,
        role=MessageRole.USER, content=req.message
    )
    db.add(user_msg)
    db.commit()

    async def stream_response():
        full_response = ""
        async for chunk in llm_service.generate_stream(
            persona=persona, user_message=req.message, provider=req.provider
        ):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # Save after stream completes
        ai_msg = Conversation(
            persona_id=persona.id, user_id=user.id,
            role=MessageRole.AI, content=full_response
        )
        db2 = SessionLocal()
        db2.add(ai_msg)
        persona2 = db2.query(Persona).filter(Persona.id == persona.id).first()
        persona2.total_messages_sent += 1
        db2.commit()
        db2.close()
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@app.get("/chat/{persona_id}/history")
async def get_chat_history(
    persona_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Get conversation history."""
    messages = db.query(Conversation).filter(
        Conversation.persona_id == persona_id
    ).order_by(Conversation.created_at.desc()).limit(limit).all()

    return [
        {"role": m.role.value, "content": m.content, "time": m.created_at.isoformat()}
        for m in reversed(messages)
    ]


# ══════════════════════════════════════════════════════
#  SCHEDULE ROUTES
# ══════════════════════════════════════════════════════

@app.post("/schedules")
async def create_schedule(
    data: ScheduleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a scheduled autonomous message."""
    persona = db.query(Persona).filter(
        Persona.id == data.persona_id, Persona.owner_id == user.id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    schedule = Schedule(**data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return {"id": schedule.id, "cron": schedule.cron_expression}


@app.get("/schedules")
async def list_schedules(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all schedules."""
    return db.query(Schedule).join(Persona).filter(
        Persona.owner_id == user.id
    ).all()


# ══════════════════════════════════════════════════════
#  PAYMENT ROUTES
# ══════════════════════════════════════════════════════

@app.get("/payments/tiers")
async def get_tiers():
    """Get subscription tier info."""
    result = {}
    for tier, info in payment_service.SUBSCRIPTION_TIERS.items():
        result[tier.value] = info
    return result


@app.post("/payments/checkout")
async def create_checkout(
    tier: SubscriptionTier,
    user: User = Depends(get_current_user),
):
    """Create Stripe checkout session."""
    if tier == SubscriptionTier.FREE:
        user.subscription_tier = SubscriptionTier.FREE
        return {"url": None, "message": "Switched to Free tier"}

    url = await payment_service.create_checkout_session(user.id, tier)
    return {"url": url}


@app.post("/payments/webhook")
async def stripe_webhook(request):
    """Stripe webhook handler."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    await payment_service.handle_webhook(payload, sig)
    return {"ok": True}


# ══════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "name": "Tata"}


# ── Startup ───────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    print("🚀 Tata API started!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
