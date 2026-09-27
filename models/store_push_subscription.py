"""Web Push subscriptions for installed storefront PWAs."""
from typing import Annotated, Optional
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class StorePushSubscription(Document):
    organization_id: Annotated[str, Indexed()]
    store_slug: Annotated[str, Indexed()]
    endpoint: Annotated[str, Indexed(unique=True)]
    keys: PushSubscriptionKeys
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "store_push_subscriptions"
