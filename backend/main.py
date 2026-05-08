"""
Tata v2.0 — AI Personality Replication Chat Companion
FastAPI Main Application
Cross-platform: iOS / Android / HarmonyOS
"""

import json, os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from models import (
    init_db, SessionLocal, User, UserProfile, Persona, ChatLog,
    Conversation, Schedule, TokenUsage, SubscriptionTier, Gender, MessageRole
)
from services.llm_service import llm_service
from services.token_service import token_service
from services.ocr_service import ocr_service
from services.payment_service import payment_service

# ── App Setup ─────────────────────────────────────────

app = FastAPI(
    title="Tata API v2.0",
    version="2.0.0",
    description="AI Personality Replication — iOS / Android / HarmonyOS",
    docs_url="/docs",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── Upload Config ─────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Auth ──────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id: raise HTTPException(401, "Invalid token")
    except JWTError: raise HTTPException(401, "Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(401, "User not found")
    return user

# ── Schemas ───────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr; username: str; password: str; display_name: str = ""

class UserResponse(BaseModel):
    id: int; email: str; username: str; token_balance: int; subscription_tier: SubscriptionTier
    class Config: from_attributes = True

class ProfileCreate(BaseModel):
    nickname: str = ""; gender: Gender = Gender.UNSPECIFIED; age: int = None
    bio: str = ""; personality_tags: list[str] = []; relationship_to_target: str = ""

class PersonaCreate(BaseModel):
    name: str; real_name: str = ""; nickname: str = ""; description: str = ""
    gender: Gender = Gender.UNSPECIFIED; age: int = None; location: str = ""
    occupation: str = ""; personality_mbti: str = ""
    speaking_style: str = ""; habits: list[str] = []; hobbies: list[str] = []
    quirks: str = ""; custom_prompt: str = ""; emotion_range: str = "warm,friendly"
    relationship_context: str = ""

class PersonaUpdate(BaseModel):
    """Partial update — anything can be adjusted anytime."""
    name: Optional[str] = None; speaking_style: Optional[str] = None
    habits: Optional[list[str]] = None; hobbies: Optional[list[str]] = None
    custom_prompt: Optional[str] = None; emotion_range: Optional[str] = None
    description: Optional[str] = None; quirks: Optional[str] = None
    relationship_context: Optional[str] = None; is_active: Optional[bool] = None

class ChatRequest(BaseModel):
    persona_id: int; message: str; provider: str = "deepseek"; model: str = ""

class ScheduleCreate(BaseModel):
    persona_id: int; cron_expression: str; prompt_hint: str = ""

# ══════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════

@app.post("/auth/register", response_model=UserResponse)
async def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first(): raise HTTPException(400, "Email exists")
    if db.query(User).filter(User.username == data.username).first(): raise HTTPException(400, "Username taken")
    user = User(email=data.email, username=data.username, display_name=data.display_name,
                hashed_password=pwd_context.hash(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.email == form_data.username) | (User.username == form_data.username)).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = jwt.encode({"sub": user.id, "exp": datetime.utcnow() + timedelta(days=7)},
                       settings.secret_key, algorithm=settings.algorithm)
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.model_validate(user)}

@app.get("/auth/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)): return user

# ══════════════════════════════════════════════════════
#  USER PROFILE
# ══════════════════════════════════════════════════════

@app.post("/profile")
async def create_profile(data: ProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if existing: raise HTTPException(400, "Profile exists — use PUT to update")
    profile = UserProfile(user_id=user.id, **data.model_dump())
    db.add(profile); db.commit(); db.refresh(profile)
    return profile

@app.put("/profile")
async def update_profile(data: ProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id, **data.model_dump())
        db.add(profile)
    else:
        for k, v in data.model_dump().items(): setattr(profile, k, v)
    db.commit(); db.refresh(profile)
    return profile

@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

@app.post("/profile/photo")
async def upload_profile_photo(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload user's own photo."""
    ext = file.filename.split(".")[-1]; filename = f"user_{user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f: f.write(await file.read())
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile:
        photos = profile.photo_urls or []; photos.append(f"/uploads/{filename}")
        profile.photo_urls = photos; db.commit()
    return {"url": f"/uploads/{filename}"}

# ══════════════════════════════════════════════════════
#  PERSONA (Target Person)
# ══════════════════════════════════════════════════════

@app.post("/personas")
async def create_persona(data: PersonaCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = Persona(owner_id=user.id, **data.model_dump())
    db.add(persona); db.commit(); db.refresh(persona)
    return persona

@app.get("/personas")
async def list_personas(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Persona).filter(Persona.owner_id == user.id).all()

@app.get("/personas/{pid}")
async def get_persona(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    return p

@app.put("/personas/{pid}")
async def update_persona(pid: int, data: PersonaUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """🔄 Adjust persona anytime — personality is never locked."""
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    for k, v in data.model_dump(exclude_none=True).items(): setattr(p, k, v)
    db.commit(); db.refresh(p)
    return {"ok": True, "persona": p}

@app.delete("/personas/{pid}")
async def delete_persona(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    db.delete(p); db.commit()
    return {"ok": True}

# ── Persona Photos ────────────────────────────────────

@app.post("/personas/{pid}/photo")
async def upload_persona_photo(pid: int, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload target person's photo."""
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    ext = file.filename.split(".")[-1]; filename = f"persona_{pid}_{int(datetime.utcnow().timestamp())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f: f.write(await file.read())
    photos = p.photo_urls or []; photos.append(f"/uploads/{filename}")
    p.photo_urls = photos; db.commit()
    return {"url": f"/uploads/{filename}"}

# ══════════════════════════════════════════════════════
#  CHAT LOGS (WeChat/WhatsApp/JSON + OCR Screenshot)
# ══════════════════════════════════════════════════════

@app.post("/personas/{pid}/chat-logs/upload")
async def upload_chat_file(pid: int, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload WeChat/WhatsApp export file (.txt or .json)."""
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")

    content = await file.read(); text = content.decode("utf-8")
    logs = []

    if file.filename.endswith(".json"):
        data = json.loads(text)
        if isinstance(data, list):
            logs = [ChatLog(persona_id=pid, role=MessageRole.ORIGINAL, sender_name=i.get("sender",""), content=i.get("content","")) for i in data]
    else:
        messages = ocr_service.parse_text_export(text, "wechat")
        logs = [ChatLog(persona_id=pid, role=MessageRole.ORIGINAL, sender_name=m["sender"], content=m["content"]) for m in messages]

    if logs: db.add_all(logs); db.commit()
    # Index to vector store
    await llm_service.index_chat_logs(pid, logs)
    return {"imported": len(logs), "senders": ocr_service.extract_senders([{"sender": l.sender_name, "content": l.content} for l in logs])}

@app.post("/personas/{pid}/chat-logs/ocr")
async def ocr_chat_screenshot(pid: int, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """📸 Upload WeChat screenshot → OCR → extract chat messages."""
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    image_data = await file.read()
    messages = await ocr_service.ocr_screenshot(image_data, llm_service)
    logs = [ChatLog(persona_id=pid, role=MessageRole.ORIGINAL, sender_name=m["sender"], content=m["content"]) for m in messages]
    if logs: db.add_all(logs); db.commit()
    await llm_service.index_chat_logs(pid, logs)
    return {"imported": len(logs), "messages": messages}

@app.get("/personas/{pid}/chat-logs/analysis")
async def analyze_chat_style(pid: int, target_sender: str = "", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Analyze a person's chat style from uploaded logs."""
    p = db.query(Persona).filter(Persona.id == pid, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    logs = db.query(ChatLog).filter(ChatLog.persona_id == pid).all()
    messages = [{"sender": l.sender_name, "content": l.content, "timestamp": str(l.timestamp)} for l in logs]
    sender = target_sender or p.name
    analysis = ocr_service.generate_style_analysis(messages, sender)
    return {"sender": sender, "total_messages": len([m for m in messages if m["sender"] == sender]), "analysis": analysis}

# ══════════════════════════════════════════════════════
#  CHAT (Token-Gated)
# ══════════════════════════════════════════════════════

@app.post("/chat")
async def chat(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """💬 Chat with persona — server proxies LLM API, checks token quota."""
    p = db.query(Persona).filter(Persona.id == req.persona_id, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")

    model = req.model or token_service.PROVIDERS.get(req.provider, {}).get("default_model", "deepseek-chat")

    # Token quota check
    ok, estimate = token_service.check_quota(user.token_balance, req.message)
    if not ok: raise HTTPException(402, f"Token余额不足！需要约{estimate} tokens，剩余{user.token_balance}")

    # Build context
    history = db.query(Conversation).filter(Conversation.persona_id == p.id).order_by(Conversation.created_at.desc()).limit(30).all()
    history_msgs = [{"role": "assistant" if h.role.value == "ai" else h.role.value, "content": h.content} for h in reversed(history)]

    # Save user msg
    db.add(Conversation(persona_id=p.id, user_id=user.id, role=MessageRole.USER, content=req.message))

    # Generate via LLM gateway
    system_prompt = llm_service.build_system_prompt(p)
    full_messages = [{"role": "system", "content": system_prompt}] + history_msgs + [{"role": "user", "content": req.message}]

    result = await token_service.chat_completion(req.provider, model, full_messages)
    response_text = result["content"]

    db.add(Conversation(persona_id=p.id, user_id=user.id, role=MessageRole.AI, content=response_text))
    p.total_messages_sent += 1
    user.token_balance -= result["usage"]["total_tokens"]
    db.add(TokenUsage(user_id=user.id, provider=req.provider, model=model,
                       input_tokens=result["usage"]["input_tokens"],
                       output_tokens=result["usage"]["output_tokens"],
                       estimated_cost_usd=result["usage"]["estimated_cost_usd"]))
    db.commit()
    return {"reply": response_text, "token_remaining": user.token_balance, "usage": result["usage"]}

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stream chat with persona."""
    p = db.query(Persona).filter(Persona.id == req.persona_id, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    model = req.model or token_service.PROVIDERS.get(req.provider, {}).get("default_model", "deepseek-chat")
    ok, _ = token_service.check_quota(user.token_balance, req.message)
    if not ok: raise HTTPException(402, "Token不足")

    system_prompt = llm_service.build_system_prompt(p)
    full_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": req.message}]

    db.add(Conversation(persona_id=p.id, user_id=user.id, role=MessageRole.USER, content=req.message))
    db.commit()

    async def stream():
        full = ""
        async for chunk in token_service.chat_completion_stream(req.provider, model, full_messages):
            full += chunk; yield f"data: {chunk}\n\n"
        db2 = SessionLocal()
        db2.add(Conversation(persona_id=p.id, user_id=user.id, role=MessageRole.AI, content=full))
        db2.commit(); db2.close()
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/chat/{pid}/history")
async def chat_history(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = 50):
    msgs = db.query(Conversation).filter(Conversation.persona_id == pid).order_by(Conversation.created_at.desc()).limit(limit).all()
    return [{"role": m.role.value, "content": m.content, "time": m.created_at.isoformat()} for m in reversed(msgs)]

# ══════════════════════════════════════════════════════
#  TOKEN & PROVIDER INFO
# ══════════════════════════════════════════════════════

@app.get("/tokens/balance")
async def token_balance(user: User = Depends(get_current_user)):
    return {"balance": user.token_balance, "tier": user.subscription_tier.value}

@app.get("/tokens/providers")
async def list_providers():
    return token_service.get_available_providers()

@app.get("/tokens/usage")
async def token_usage_history(user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = 20):
    return db.query(TokenUsage).filter(TokenUsage.user_id == user.id).order_by(TokenUsage.created_at.desc()).limit(limit).all()

# ══════════════════════════════════════════════════════
#  SCHEDULES
# ══════════════════════════════════════════════════════

@app.post("/schedules")
async def create_schedule(data: ScheduleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Persona).filter(Persona.id == data.persona_id, Persona.owner_id == user.id).first()
    if not p: raise HTTPException(404, "Not found")
    sched = Schedule(**data.model_dump()); db.add(sched); db.commit(); db.refresh(sched)
    return sched

@app.get("/schedules")
async def list_schedules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Schedule).join(Persona).filter(Persona.owner_id == user.id).all()

# ══════════════════════════════════════════════════════
#  PAYMENTS
# ══════════════════════════════════════════════════════

@app.get("/payments/tiers")
async def get_tiers():
    return {t.value: info for t, info in payment_service.SUBSCRIPTION_TIERS.items()}

@app.post("/payments/checkout")
async def create_checkout(tier: SubscriptionTier, user: User = Depends(get_current_user)):
    url = await payment_service.create_checkout_session(user.id, tier) if tier != SubscriptionTier.FREE else None
    return {"url": url}

@app.post("/payments/webhook")
async def stripe_webhook(request):
    payload = await request.body(); sig = request.headers.get("stripe-signature")
    await payment_service.handle_webhook(payload, sig)
    return {"ok": True}

# ══════════════════════════════════════════════════════
#  STATIC FILES
# ══════════════════════════════════════════════════════

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path): return FileResponse(path)
    raise HTTPException(404, "File not found")

# ══════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "providers": len(token_service._clients),
            "name": "Tata", "platforms": ["iOS", "Android", "HarmonyOS"]}

@app.on_event("startup")
async def startup():
    init_db()
    print(f"🚀 Tata v2.0 started — {len(token_service._clients)} LLM providers ready")

if __name__ == "__main__":
    import uvicorn; uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
