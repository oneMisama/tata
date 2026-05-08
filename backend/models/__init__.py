"""
Tata - SQLAlchemy Database Models (v2.0)
Now with UserProfile, TargetPerson, TokenUsage tracking.
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
    ORIGINAL = "original"


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
    token_balance = Column(Integer, default=50000)  # Free tier: 50K tokens
    stripe_customer_id = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    personas = relationship("Persona", back_populates="owner", cascade="all, delete-orphan")
    token_usage = relationship("TokenUsage", back_populates="user", cascade="all, delete-orphan")


# ── User Profile ──────────────────────────────────────

class UserProfile(Base):
    """The user's own profile — who they are."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    nickname = Column(String(100), default="")
    gender = Column(SQLEnum(Gender), default=Gender.UNSPECIFIED)
    age = Column(Integer, nullable=True)
    bio = Column(Text, default="")
    personality_tags = Column(JSON, default=list)   # ["内向", "喜欢猫", "程序员"]
    photo_urls = Column(JSON, default=list)          # ["url1", "url2"]
    relationship_to_target = Column(String(100), default="")  # "暗恋", "朋友", "前任"
    wechat_id = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


# ── Persona (Target Person) ───────────────────────────

class Persona(Base):
    """The replicated personality of the target person."""
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    real_name = Column(String(100), default="")         # Real name (optional)
    nickname = Column(String(100), default="")           # Their nickname
    description = Column(Text, default="")
    gender = Column(SQLEnum(Gender), default=Gender.UNSPECIFIED)
    age = Column(Integer, nullable=True)
    age_range = Column(String(20), default="")
    native_language = Column(String(50), default="zh-CN")
    location = Column(String(100), default="")           # City
    occupation = Column(String(100), default="")          # Job
    personality_mbti = Column(String(10), default="")     # MBTI
    speaking_style = Column(Text, default="")
    habits = Column(JSON, default=list)
    hobbies = Column(JSON, default=list)                  # ["打游戏", "看电影"]
    quirks = Column(Text, default="")                     # 小癖好
    custom_prompt = Column(Text, default="")
    emotion_range = Column(String(100), default="warm,friendly")
    relationship_context = Column(Text, default="")       # "我们是大学同学，现在异地"
    photo_urls = Column(JSON, default=list)               # Photo gallery
    avatar_url = Column(String(500), default="")
    voice_id = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
    total_messages_sent = Column(Integer, default=0)
    is_adjustable = Column(Boolean, default=True)          # Can be tweaked anytime
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="personas")
    chat_logs = relationship("ChatLog", back_populates="persona", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="persona", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="persona", cascade="all, delete-orphan")


# ── Chat Log (Training Data) ─────────────────────────

class ChatLog(Base):
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
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    prompt_hint = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    persona = relationship("Persona", back_populates="schedules")


# ── Token Usage Tracking ─────────────────────────────

class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="token_usage")


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
