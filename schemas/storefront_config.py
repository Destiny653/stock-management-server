"""Storefront config schemas"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ThemeConfigSchema(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    heading_font: Optional[str] = None
    body_font: Optional[str] = None
    border_radius: Optional[str] = None


class HeroSlideSchema(BaseModel):
    title: Optional[str] = None
    title_fr: Optional[str] = None
    subtitle: Optional[str] = None
    subtitle_fr: Optional[str] = None
    image_url: str
    cta_text: Optional[str] = None
    cta_text_fr: Optional[str] = None
    cta_link: Optional[str] = None


class SocialLinksSchema(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None


class StorefrontConfigCreate(BaseModel):
    slug: str
    store_name: str
    tagline: Optional[str] = None
    tagline_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    favicon_url: Optional[str] = None
    theme: Optional[ThemeConfigSchema] = None
    hero_slides: List[HeroSlideSchema] = []
    payment_phone_mtn: Optional[str] = None
    payment_phone_orange: Optional[str] = None
    currency: str = "CFAF"
    about_text: Optional[str] = None
    about_text_fr: Optional[str] = None
    privacy_policy: Optional[str] = None
    privacy_policy_fr: Optional[str] = None
    terms_conditions: Optional[str] = None
    terms_conditions_fr: Optional[str] = None
    return_policy: Optional[str] = None
    return_policy_fr: Optional[str] = None
    social_links: Optional[SocialLinksSchema] = None
    default_language: str = "fr"
    enable_ratings: bool = True
    enable_cart: bool = True
    show_prices: bool = True
    show_stock: bool = False
    featured_category_ids: List[str] = []
    featured_product_ids: List[str] = []
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class StorefrontConfigUpdate(BaseModel):
    slug: Optional[str] = None
    store_name: Optional[str] = None
    tagline: Optional[str] = None
    tagline_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    favicon_url: Optional[str] = None
    theme: Optional[ThemeConfigSchema] = None
    hero_slides: Optional[List[HeroSlideSchema]] = None
    payment_phone_mtn: Optional[str] = None
    payment_phone_orange: Optional[str] = None
    currency: Optional[str] = None
    about_text: Optional[str] = None
    about_text_fr: Optional[str] = None
    privacy_policy: Optional[str] = None
    privacy_policy_fr: Optional[str] = None
    terms_conditions: Optional[str] = None
    terms_conditions_fr: Optional[str] = None
    return_policy: Optional[str] = None
    return_policy_fr: Optional[str] = None
    social_links: Optional[SocialLinksSchema] = None
    default_language: Optional[str] = None
    enable_ratings: Optional[bool] = None
    enable_cart: Optional[bool] = None
    show_prices: Optional[bool] = None
    show_stock: Optional[bool] = None
    featured_category_ids: Optional[List[str]] = None
    featured_product_ids: Optional[List[str]] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


from beanie import PydanticObjectId

class StorefrontConfigResponse(BaseModel):
    id: PydanticObjectId
    organization_id: str
    slug: str
    store_name: str
    tagline: Optional[str] = None
    tagline_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    favicon_url: Optional[str] = None
    theme: ThemeConfigSchema
    hero_slides: List[HeroSlideSchema] = []
    payment_phone_mtn: Optional[str] = None
    payment_phone_orange: Optional[str] = None
    currency: str = "CFAF"
    about_text: Optional[str] = None
    about_text_fr: Optional[str] = None
    privacy_policy: Optional[str] = None
    privacy_policy_fr: Optional[str] = None
    terms_conditions: Optional[str] = None
    terms_conditions_fr: Optional[str] = None
    return_policy: Optional[str] = None
    return_policy_fr: Optional[str] = None
    social_links: Optional[SocialLinksSchema] = None
    default_language: str = "fr"
    enable_ratings: bool = True
    enable_cart: bool = True
    show_prices: bool = True
    show_stock: bool = False
    featured_category_ids: List[str] = []
    featured_product_ids: List[str] = []
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
