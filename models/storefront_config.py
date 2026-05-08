"""StorefrontConfig model – per-organization storefront customization"""
from typing import Annotated, Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel


class ThemeConfig(BaseModel):
    """Visual theme settings injected as CSS custom properties."""
    primary_color: str = "#6366f1"       # indigo-500
    secondary_color: str = "#0ea5e9"     # sky-500
    accent_color: str = "#f59e0b"        # amber-500
    background_color: str = "#ffffff"
    text_color: str = "#111827"
    heading_font: str = "Inter"
    body_font: str = "Inter"
    border_radius: str = "0.75rem"       # rounded-xl default


class HeroSlide(BaseModel):
    """One slide in the homepage hero carousel."""
    title: Optional[str] = None
    title_fr: Optional[str] = None
    subtitle: Optional[str] = None
    subtitle_fr: Optional[str] = None
    image_url: str
    cta_text: Optional[str] = None
    cta_text_fr: Optional[str] = None
    cta_link: Optional[str] = None


class SocialLinks(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None


class StorefrontConfig(Document):
    organization_id: Annotated[str, Indexed(unique=True)]
    slug: Annotated[str, Indexed(unique=True)]

    # Branding
    store_name: str
    tagline: Optional[str] = None
    tagline_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    favicon_url: Optional[str] = None

    # Theme
    theme: ThemeConfig = Field(default_factory=ThemeConfig)

    # Hero carousel (up to 5 slides)
    hero_slides: List[HeroSlide] = Field(default_factory=list)

    # Payment
    payment_phone_mtn: Optional[str] = None
    payment_phone_orange: Optional[str] = None
    currency: str = "CFAF"
    accepted_payment_methods: List[str] = Field(default_factory=list)
    
    # Stripe Connect
    stripe_account_id: Optional[str] = None
    stripe_charges_enabled: bool = False

    # Content (bilingual)
    about_text: Optional[str] = None
    about_text_fr: Optional[str] = None
    privacy_policy: Optional[str] = None
    privacy_policy_fr: Optional[str] = None
    terms_conditions: Optional[str] = None
    terms_conditions_fr: Optional[str] = None
    return_policy: Optional[str] = None
    return_policy_fr: Optional[str] = None

    # Social
    social_links: SocialLinks = Field(default_factory=SocialLinks)

    # i18n
    default_language: str = "fr"

    # Feature flags
    enable_ratings: bool = True
    enable_cart: bool = True
    show_prices: bool = True
    show_stock: bool = False

    # Curated content
    featured_category_ids: List[str] = Field(default_factory=list)
    featured_product_ids: List[str] = Field(default_factory=list)

    # Contact
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "storefront_configs"
