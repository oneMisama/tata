"""
Tata - SQLAlchemy Database Models
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SQLEnum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum

from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Enums ──────────────────────────────────────────────

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class MessageRole(str, enum.Enum):
    USER = "user"
    AI = "ai"
    ORIGINAL = "original"  # Original chat log import


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


# ── User Model ─────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), default="")
    avatar_url = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    messages_remaining = Column(Integer, default=settings.free_tier_messages)
    stripe_customer_id = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    personas = relationship("Persona", back_populates="owner", cascade="all, delete-orphan")


# ── Persona Model ─────────────────────────────────────

class Persona(Base):
    """The replicated personality of someone."""
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    gender = Column(SQLEnum(Gender), default=Gender.UNSPECIFIED)
    age_range = Column(String(20), default="")  # e.g. "20-25"
    native_language = Column(String(50), default="zh-CN")
    speaking_style = Column(Text, default="")   # Detailed style description
    habits = Column(JSON, default=list)          # ["likes using emoji", "types ... when thinking"]
    custom_prompt = Column(Text, default="")     # Extra system prompt
    emotion_range = Column(String(100), default="warm,friendly")
    avatar_url = Column(String(500), default="")
    voice_id = Column(String(100), default="")   # For TTS integration
    is_active = Column(Boolean, default=True)
    total_messages_sent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="personas")
    chat_logs = relationship("ChatLog", back_populates="persona", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="persona", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="persona", cascade="all, delete-orphan")


# ── Chat Log (Training Data) ─────────────────────────

class ChatLog(Base):
    """Uploaded chat logs for training the persona."""
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    role = Column(SQLEnum(MessageRole), default=MessageRole.ORIGINAL)
    sender_name = Column(String(100), default="")
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON, default=dict)

    persona = relationship("Persona", back_populates="chat_logs")


# ── Conversation ──────────────────────────────────────

class Conversation(Base):
    """Real-time conversation between user and AI persona."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    persona = relationship("Persona", back_populates="conversations")


# ── Scheduled Message ────────────────────────────────

class Schedule(Base):
    """Scheduled autonomous messages from the AI persona."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    cron_expression = Column(String(100), nullable=False)  # e.g. "0 9 * * *"
    prompt_hint = Column(Text, default="")                  # Topic hint
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    persona = relationship("Persona", back_populates="schedules")


# ── Subscription ──────────────────────────────────────

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    stripe_subscription_id = Column(String(255), default="")
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)


# ── Init DB ───────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
