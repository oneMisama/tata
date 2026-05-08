"""
Tata - Payment Service (Stripe Integration)
Subscription tiers: Free / Pro / Enterprise
"""

import stripe
from datetime import datetime, timedelta
from config import settings
from models import SessionLocal, User, Subscription, SubscriptionTier

stripe.api_key = settings.stripe_api_key


class PaymentService:
    """Handle Stripe subscriptions and payment processing."""

    SUBSCRIPTION_TIERS = {
        SubscriptionTier.FREE: {
            "name": "Free",
            "price": 0,
            "messages_per_month": 50,
            "personas": 1,
            "features": ["基础对话", "1 个人格", "文本消息"],
        },
        SubscriptionTier.PRO: {
            "name": "Pro",
            "price": 9.99,
            "messages_per_month": 2000,
            "personas": 5,
            "features": ["无限对话", "5 个人格", "定时消息", "对话导出", "语音消息"],
        },
        SubscriptionTier.ENTERPRISE: {
            "name": "Enterprise",
            "price": 29.99,
            "messages_per_month": 10000,
            "personas": 20,
            "features": ["无限一切", "20 个人格", "API 接入", "私有部署", "优先支持", "自定义模型"],
        },
    }

    @classmethod
    def get_tiers(cls) -> dict:
        return cls.SUBSCRIPTION_TIERS

    @classmethod
    async def create_checkout_session(cls, user_id: int, tier: SubscriptionTier) -> str:
        """Create a Stripe Checkout session URL."""
        if tier == SubscriptionTier.FREE:
            return None

        price_id = (
            settings.pro_price_id if tier == SubscriptionTier.PRO
            else settings.enterprise_price_id
        )

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url="https://tata.app/payment/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://tata.app/payment/cancel",
            metadata={"user_id": str(user_id), "tier": tier.value},
        )
        return session.url

    @classmethod
    async def handle_webhook(cls, payload: bytes, sig_header: str):
        """Process Stripe webhook events."""
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        db = SessionLocal()

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = int(session["metadata"]["user_id"])
            tier = SubscriptionTier(session["metadata"]["tier"])
            customer_id = session["customer"]

            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.subscription_tier = tier
                user.stripe_customer_id = customer_id
                user.messages_remaining = cls.SUBSCRIPTION_TIERS[tier]["messages_per_month"]

                sub = Subscription(
                    user_id=user_id,
                    tier=tier,
                    stripe_subscription_id=session.get("subscription", ""),
                    expires_at=datetime.utcnow() + timedelta(days=30),
                )
                db.add(sub)

        elif event["type"] == "customer.subscription.deleted":
            sub_data = event["data"]["object"]
            sub = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == sub_data["id"]
            ).first()
            if sub:
                sub.is_active = False
                user = db.query(User).filter(User.id == sub.user_id).first()
                if user:
                    user.subscription_tier = SubscriptionTier.FREE
                    user.messages_remaining = cls.SUBSCRIPTION_TIERS[SubscriptionTier.FREE]["messages_per_month"]

        db.commit()
        db.close()

    @classmethod
    def check_quota(cls, user: User) -> bool:
        """Check if user has remaining messages."""
        if user.subscription_tier == SubscriptionTier.ENTERPRISE:
            return True
        return user.messages_remaining > 0

    @classmethod
    def consume_message(cls, user: User):
        """Decrement message quota."""
        if user.subscription_tier != SubscriptionTier.ENTERPRISE:
            user.messages_remaining = max(0, user.messages_remaining - 1)


payment_service = PaymentService()
