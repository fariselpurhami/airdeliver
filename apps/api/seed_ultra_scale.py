import asyncio
import json
import logging
import hashlib
import math
import os
import re
import random
import signal
import ssl
import sys
from collections.abc import AsyncGenerator, Iterable, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final, Protocol, runtime_checkable

from opensearchpy import AsyncOpenSearch, helpers
from opensearchpy.exceptions import RequestError
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, PositiveInt, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymilvus import DataType, MilvusClient
from sqlalchemy import text, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.product import Product as DatabaseProduct
from app.core.catalog_contract import PRODUCT_TEXT_MODEL_NAME, PRODUCT_TEXT_MODEL_DIMENSION, PRODUCT_TEXT_COLLECTION, DEFAULT_PRODUCT_TEXT_MODEL_REVISION, PRODUCT_SEARCH_INDEX
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

LOGGER_NAME: Final[str] = "ultra_scale_seeder"
UTC: Final[timezone] = timezone.utc
DEFAULT_CURRENCY: Final[str] = "USD"
JSON_LOG_FORMAT: Final[str] = "%(message)s"


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(JSON_LOG_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def now_naive_utc() -> datetime:
    return datetime.now(UTC)  # Compatibility name; never strip timezone information.


def quantize_price(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def chunked(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def json_log(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"ts": datetime.now(UTC).isoformat(), "event": event, **fields}
    logger.log(level, json.dumps(payload, default=str, ensure_ascii=False))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore', hide_input_in_errors=True)
    postgres_dsn: str = Field(..., alias='DATABASE_URI', repr=False)
    app_env: str = Field('development', alias='APP_ENV')
    allow_production: bool = Field(False, alias='SEED_ALLOW_PRODUCTION')
    opensearch_host: str = Field('opensearch', alias='OPENSEARCH_HOST')
    opensearch_port: int = Field(9200, alias='OPENSEARCH_PORT')
    opensearch_index: str = Field(PRODUCT_SEARCH_INDEX, alias='OPENSEARCH_INDEX')
    opensearch_pass: SecretStr | None = Field(None, alias='OPENSEARCH_PASS')
    opensearch_user: str | None = Field(None, alias='OPENSEARCH_USER')
    opensearch_use_ssl: bool = Field(True, alias='OPENSEARCH_USE_SSL')
    opensearch_verify_certs: bool = Field(True, alias='OPENSEARCH_VERIFY_CERTS')
    opensearch_bulk_chunk_size: PositiveInt = Field(64, alias='OPENSEARCH_BULK_CHUNK_SIZE')
    opensearch_bulk_max_chunk_bytes: PositiveInt = Field(2_097_152, alias='OPENSEARCH_BULK_MAX_CHUNK_BYTES')
    milvus_uri: str = Field('http://milvus:19530', alias='MILVUS_URI')
    milvus_token: SecretStr | None = Field(None, alias='MILVUS_TOKEN')
    milvus_collection: str = Field(PRODUCT_TEXT_COLLECTION, alias='MILVUS_COLLECTION')
    embedding_model: str = Field(PRODUCT_TEXT_MODEL_NAME, alias='EMBEDDING_MODEL')
    api_embedding_revision: str | None = Field(None, alias='PRODUCT_TEXT_MODEL_REVISION')
    embedding_revision: str | None = Field(None, alias='SEED_EMBEDDING_REVISION')
    embedding_dimension: PositiveInt = Field(PRODUCT_TEXT_MODEL_DIMENSION, alias='SEED_EMBEDDING_DIMENSION')
    embedding_local_files_only: bool = Field(False, alias='SEED_EMBEDDING_LOCAL_FILES_ONLY')
    embedding_max_seq_length: int = Field(256, ge=32, le=8192, alias='SEED_EMBEDDING_MAX_SEQ_LENGTH')
    embedding_threads: int = Field(2, ge=1, le=16, alias='SEED_EMBEDDING_THREADS')
    embedding_encode_batch_size: int = Field(1, ge=1, le=32, alias='EMBEDDING_ENCODE_BATCH_SIZE')
    batch_size: int = Field(16, ge=1, le=256, validation_alias=AliasChoices('SEED_BATCH_SIZE','BATCH_SIZE'))
    target_count: int = Field(1000, ge=1, le=10_000_000, validation_alias=AliasChoices('SEED_TARGET_COUNT','TARGET_COUNT'))
    random_seed: int = Field(20260514, validation_alias=AliasChoices('SEED_RANDOM_SEED','RANDOM_SEED'))
    log_level: str = Field('INFO', alias='LOG_LEVEL')
    postgres_pool_size: int = Field(2, ge=1, le=8, alias='POSTGRES_POOL_SIZE')
    postgres_max_overflow: int = Field(0, ge=0, le=8, alias='POSTGRES_MAX_OVERFLOW')
    retry_attempts: PositiveInt = Field(3, alias='RETRY_ATTEMPTS')
    retry_min_seconds: PositiveInt = Field(1, alias='RETRY_MIN_SECONDS')
    retry_max_seconds: PositiveInt = Field(8, alias='RETRY_MAX_SECONDS')
    milvus_enabled: bool = Field(True, alias='MILVUS_ENABLED')
    opensearch_enabled: bool = Field(True, alias='OPENSEARCH_ENABLED')
    fail_on_milvus_error: bool = Field(True, alias='FAIL_ON_MILVUS_ERROR')
    fail_on_opensearch_error: bool = Field(True, alias='FAIL_ON_OPENSEARCH_ERROR')

    @field_validator('embedding_revision','api_embedding_revision', mode='before')
    @classmethod
    def revision_or_none(cls, value):
        if not value:
            return None
        if not re.fullmatch(r'[a-fA-F0-9]{40}',value):
            raise ValueError('Pin the embedding revision to a 40-character commit SHA')
        return value

    @field_validator('postgres_dsn')
    @classmethod
    def async_postgres_only(cls, value):
        if not value.startswith('postgresql+asyncpg://'):
            raise ValueError('DATABASE_URI must use postgresql+asyncpg')
        return value

    @model_validator(mode='after')
    def validate_configuration(self):
        if self.opensearch_enabled and bool(self.opensearch_user) != bool(self.opensearch_pass and self.opensearch_pass.get_secret_value()):
            raise ValueError('OPENSEARCH_USER and OPENSEARCH_PASS must be provided together')
        if self.app_env.lower() in {'production','prod'} and not self.allow_production:
            raise ValueError('Demo seeding is disabled in production without SEED_ALLOW_PRODUCTION=true')
        if self.embedding_revision is None:
            self.embedding_revision=self.api_embedding_revision or (DEFAULT_PRODUCT_TEXT_MODEL_REVISION if self.embedding_model==PRODUCT_TEXT_MODEL_NAME else None)
        if self.milvus_enabled and self.milvus_collection==PRODUCT_TEXT_COLLECTION:
            if self.embedding_model!=PRODUCT_TEXT_MODEL_NAME or self.embedding_dimension!=PRODUCT_TEXT_MODEL_DIMENSION:
                raise ValueError(f'The API product collection requires its selected model and {PRODUCT_TEXT_MODEL_DIMENSION} dimensions; use a separate collection for experiments')
            if self.embedding_revision!=(self.api_embedding_revision or DEFAULT_PRODUCT_TEXT_MODEL_REVISION):
                raise ValueError('The API collection requires the same model revision as PRODUCT_TEXT_MODEL_REVISION')
        from app.core.catalog_contract import SPACES
        for space in SPACES.values():
            if space.key!='gte-v1' and (self.milvus_collection==space.collection or self.opensearch_index==space.search_index):
                if (self.embedding_model,self.embedding_dimension,self.embedding_revision)!=(space.model,space.dimension,space.revision):
                    raise ValueError('Model identity/revision does not match versioned index namespace')
        if self.retry_max_seconds < self.retry_min_seconds:
            raise ValueError('Retry maximum must be at least the minimum')
        return self

    @field_validator('opensearch_index','milvus_collection','embedding_model','milvus_uri','opensearch_host')
    @classmethod
    def non_empty(cls,value):
        if not value.strip():
            raise ValueError('Resource names and endpoints must not be empty')
        return value.strip()


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    sku: str = Field(max_length=128)
    name: str = Field(max_length=255)
    description: str
    price: Decimal
    category: str = Field(max_length=128)
    inventory: int
    image: str
    rating: float
    attributes: dict[str, str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    currency: str
    is_active: bool

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isascii() or not normalized.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code")
        return normalized

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        if not (normalized := [tag.strip() for tag in value if tag.strip()]):
            raise ValueError("Tags must not be empty")
        return normalized

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("Price must be positive")
        return quantize_price(value)

    @field_validator("inventory")
    @classmethod
    def validate_inventory(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Inventory must be non-negative")
        return value

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: float) -> float:
        if not (0.0 <= value <= 5.0):
            raise ValueError("Rating must be between 0 and 5")
        return round(value, 1)


class ProductVector(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: int
    vector: list[float]
    price: float
    rating: float
    category: str
    attributes: dict[str, str]

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, value: list[float]) -> list[float]:
        if not value or not all(math.isfinite(x) for x in value) or sum(x*x for x in value) == 0:
            raise ValueError("Vector must be finite, non-empty and nonzero")
        return value


@dataclass(frozen=True)
class CatalogItemTemplate:
    name: str
    base_price: int
    image: str
    specs: tuple[str, ...]
    colors: tuple[str, ...]


@dataclass(frozen=True)
class CategorySeedData:
    products: tuple[CatalogItemTemplate, ...]


CATALOG_DATA: Final[dict[str, CategorySeedData]] = {
    "Electronics": CategorySeedData(
        products=(
            CatalogItemTemplate("Apple iPhone 17 Pro Max", 1299, "https://images.unsplash.com/photo-1605236453806-6ff36852167e?auto=format&fit=crop&w=800&q=80", ("256GB / 12GB RAM", "512GB / 12GB RAM", "1TB / 12GB RAM", "2TB / 16GB RAM"), ("Desert Titanium", "Natural Titanium", "Black Titanium", "White Titanium")),
            CatalogItemTemplate("Apple iPhone 16 Pro", 999, "https://images.unsplash.com/photo-1616348436168-de43ad0db179?auto=format&fit=crop&w=800&q=80", ("128GB / 8GB RAM", "256GB / 8GB RAM", "512GB / 8GB RAM", "1TB / 8GB RAM"), ("Natural Titanium", "Blue Titanium", "White Titanium", "Black Titanium")),
            CatalogItemTemplate("Samsung Galaxy S26 Ultra", 1399, "https://images.unsplash.com/photo-1610945265064-3234eb351684?auto=format&fit=crop&w=800&q=80", ("256GB / 12GB RAM", "512GB / 16GB RAM", "1TB / 16GB RAM"), ("Titanium Gray", "Titanium Black", "Titanium Violet", "Titanium Yellow")),
            CatalogItemTemplate("Samsung Galaxy S25", 799, "https://images.unsplash.com/photo-1585060544812-6b45742d762f?auto=format&fit=crop&w=800&q=80", ("128GB / 8GB RAM", "256GB / 8GB RAM"), ("Onyx Black", "Marble Gray", "Cobalt Violet", "Amber Yellow")),
            CatalogItemTemplate("Apple MacBook Pro 16 M4 Max", 3499, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80", ("1TB SSD / 36GB RAM", "2TB SSD / 48GB RAM", "4TB SSD / 128GB RAM"), ("Space Black", "Silver")),
            CatalogItemTemplate("Sony WH-1000XM6 Headphones", 399, "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=800&q=80", ("Active Noise Cancelling / 40h Battery", "Spatial Audio / Multi-point"), ("Black", "Platinum Silver", "Midnight Blue")),
        )
    ),
    "Mens_Clothing": CategorySeedData(
        products=(
            CatalogItemTemplate("Hugo Boss Tailored Wool Suit", 895, "https://images.unsplash.com/photo-1593032465175-481ac7f401a0?auto=format&fit=crop&w=800&q=80", ("Size 38R", "Size 40R", "Size 42L", "Size 44L"), ("Charcoal Grey", "Navy Blue", "Black")),
            CatalogItemTemplate("Ralph Lauren Oxford Cloth Shirt", 125, "https://images.unsplash.com/photo-1596755095609-ed3736d8d32a?auto=format&fit=crop&w=800&q=80", ("Size S", "Size M", "Size L", "Size XL", "Size XXL"), ("Optic White", "Light Blue", "Pink", "Navy")),
            CatalogItemTemplate("Nike Tech Fleece Full-Zip", 145, "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=800&q=80", ("Size S", "Size M", "Size L", "Size XL"), ("Dark Heather Grey", "Black", "Midnight Navy", "Olive")),
            CatalogItemTemplate("Diesel D-Strukt Slim Jeans", 195, "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=800&q=80", ("Size 30x30", "Size 32x32", "Size 34x32", "Size 36x34"), ("Vintage Wash", "Dark Indigo", "Pitch Black")),
            CatalogItemTemplate("Tom Ford Tuxedo Jacket", 3490, "https://images.unsplash.com/photo-1507679622115-37cb455f3299?auto=format&fit=crop&w=800&q=80", ("Size 38R", "Size 40R", "Size 42R", "Size 44R"), ("Jet Black", "Midnight Blue")),
            CatalogItemTemplate("Patagonia Better Sweater", 149, "https://images.unsplash.com/photo-1611312449408-fcece27cdbb1?auto=format&fit=crop&w=800&q=80", ("Size S", "Size M", "Size L", "Size XL"), ("Stonewash", "Nickel", "Black")),
        )
    ),
    "Womens_Clothing": CategorySeedData(
        products=(
            CatalogItemTemplate("Zara Pure Silk Midi Dress", 119, "https://images.unsplash.com/photo-1566206091558-7f218b69d731?auto=format&fit=crop&w=800&q=80", ("Size XS", "Size S", "Size M", "Size L"), ("Emerald Green", "Champagne", "Black", "Burgundy")),
            CatalogItemTemplate("Mango Tailored Wool-Blend Coat", 229, "https://images.unsplash.com/photo-1539533285-d6d0db907fa0?auto=format&fit=crop&w=800&q=80", ("Size XS", "Size S", "Size M", "Size L", "Size XL"), ("Camel", "Navy", "Charcoal", "Cream")),
            CatalogItemTemplate("Massimo Dutti Cashmere Knit", 169, "https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=800&q=80", ("Size XS", "Size S", "Size M", "Size L"), ("Oatmeal", "Soft Grey", "Navy", "Dusty Pink")),
            CatalogItemTemplate("Levi's 501 Original Fit Jeans", 108, "https://images.unsplash.com/photo-1542272201-b1b795ea0fa6?auto=format&fit=crop&w=800&q=80", ("Size 24", "Size 26", "Size 28", "Size 30", "Size 32"), ("Classic Indigo", "Light Wash", "Black", "Bleached")),
            CatalogItemTemplate("Lululemon Align High-Rise Pant", 98, "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?auto=format&fit=crop&w=800&q=80", ("Size 0", "Size 2", "Size 4", "Size 6", "Size 8", "Size 10"), ("Black", "True Navy", "Dark Olive", "Espresso")),
            CatalogItemTemplate("Burberry Kensington Trench Coat", 2490, "https://images.unsplash.com/photo-1559582798-678dfc71ce5e?auto=format&fit=crop&w=800&q=80", ("Size UK 4", "Size UK 6", "Size UK 8", "Size UK 10", "Size UK 12"), ("Honey", "Midnight", "Coal Blue")),
        )
    ),
    "Watches": CategorySeedData(
        products=(
            CatalogItemTemplate("Rolex Submariner Date 126610LN", 10250, "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=800&q=80", ("Automatic / 41mm Case / 300m Water Res.", "Automatic / 41mm Case / Date"), ("Oystersteel / Black Dial", "Oystersteel / Green Bezel (Kermit)")),
            CatalogItemTemplate("Omega Speedmaster Moonwatch", 7000, "https://images.unsplash.com/photo-1622434641406-a15661bbd85e?auto=format&fit=crop&w=800&q=80", ("Manual-winding / 42mm Case / Chronograph", "Co-Axial Master Chronometer"), ("Stainless Steel / Black Dial", "Hesalite Crystal / Steel")),
            CatalogItemTemplate("Patek Philippe Nautilus 5811", 69700, "https://images.unsplash.com/photo-1548171915-e7afaca07970?auto=format&fit=crop&w=800&q=80", ("Automatic / 41mm Case / Caliber 26-330", "White Gold / Open Caseback"), ("Sunburst Blue Dial",)),
            CatalogItemTemplate("Audemars Piguet Royal Oak", 27000, "https://images.unsplash.com/photo-1587836374828-cb4387df3c7c?auto=format&fit=crop&w=800&q=80", ("Automatic / 41mm Case / 50m Water Res.", "Self-winding / Calibre 4302"), ("Stainless Steel / Blue Dial", "Stainless Steel / Silver Dial", "Stainless Steel / Black Dial")),
            CatalogItemTemplate("Tissot PRX Powermatic 80", 725, "https://images.unsplash.com/photo-1509048191080-d2984bad6ae5?auto=format&fit=crop&w=800&q=80", ("Automatic / 40mm Case / 80h Power Reserve", "Automatic / 35mm Case"), ("Ice Blue", "Deep Blue", "Emerald Green", "Black")),
            CatalogItemTemplate("Casio G-Shock Mudmaster GWG-2000", 800, "https://images.unsplash.com/photo-1508685002936-397c76899478?auto=format&fit=crop&w=800&q=80", ("Solar Quartz / 54mm Case / Carbon Core", "Multi-Band 6 / Altimeter"), ("Tactical Black", "Military Green", "Sand")),
        )
    ),
    "Makeup": CategorySeedData(
        products=(
            CatalogItemTemplate("Dior Backstage Face & Body Foundation", 43, "https://images.unsplash.com/photo-1599305090598-fe179d501227?auto=format&fit=crop&w=800&q=80", ("Matte Finish / 50ml", "Luminous Matte / Waterproof"), ("0N Neutral", "1W Warm", "2N Neutral", "3W Warm", "4C Cool")),
            CatalogItemTemplate("Charlotte Tilbury Matte Revolution", 35, "https://images.unsplash.com/photo-1586495777357-1909a34bc6af?auto=format&fit=crop&w=800&q=80", ("Matte Finish / Hydrating Formula", "Long-lasting / Orchid Extract"), ("Pillow Talk Original", "Pillow Talk Medium", "Walk of No Shame", "Red Carpet Red")),
            CatalogItemTemplate("Huda Beauty Empowered Eyeshadow Palette", 67, "https://images.unsplash.com/photo-1596462502278-27bf8403348d?auto=format&fit=crop&w=800&q=80", ("High Pigment / 18 Shades", "Matte, Metallic, Gel-Liner Hybrids"), ("Empowered (Gold/Copper/Neutrals)",)),
            CatalogItemTemplate("Fenty Beauty Gloss Bomb", 21, "https://images.unsplash.com/photo-1625014618427-fbc980b974f5?auto=format&fit=crop&w=800&q=80", ("High-Shine Finish / Non-sticky", "Shea Butter Enriched"), ("Fenty Glow", "Diamond Milk", "Fu$$y", "Hot Chocolit")),
            CatalogItemTemplate("Rare Beauty Soft Pinch Liquid Blush", 23, "https://images.unsplash.com/photo-1629198688000-71f23e745b6e?auto=format&fit=crop&w=800&q=80", ("Radiant Finish / Highly Pigmented", "Matte Finish / Blendable"), ("Joy (Peach)", "Happy (Pink)", "Hope (Nude Mauve)", "Grace (Matte Rose)")),
            CatalogItemTemplate("MAC Pro Longwear Concealer", 30, "https://images.unsplash.com/photo-1580870059296-1c322b22ce87?auto=format&fit=crop&w=800&q=80", ("Full Coverage / 15-Hour Wear", "Matte Finish / Non-creasing"), ("NC15", "NC20", "NW20", "NC30", "NW35")),
        )
    ),
    "Accessories": CategorySeedData(
        products=(
            CatalogItemTemplate("Ray-Ban Aviator Classic", 163, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=800&q=80", ("Polarized Lenses / 58mm", "Non-Polarized / 55mm", "G-15 Lenses / 62mm"), ("Gold/Green", "Black/Black", "Silver/Blue", "Gunmetal/Brown")),
            CatalogItemTemplate("Gucci GG Marmont Leather Belt", 480, "https://images.unsplash.com/photo-1624222230623-690226af7298?auto=format&fit=crop&w=800&q=80", ("Genuine Leather / 4cm Width", "Genuine Leather / 3cm Width"), ("Black Leather / Antiqued Gold", "Dusty Pink / Gold", "White / Silver")),
            CatalogItemTemplate("Louis Vuitton Neverfull MM", 2030, "https://images.unsplash.com/photo-1584916201218-f4242ceb4809?auto=format&fit=crop&w=800&q=80", ("Coated Canvas / Leather Trim", "Removable Zippered Pouch"), ("Monogram Canvas", "Damier Ebene", "Damier Azur")),
            CatalogItemTemplate("Montblanc Meisterstück Classique Pen", 640, "https://images.unsplash.com/photo-1583485088034-607b3dd33ce0?auto=format&fit=crop&w=800&q=80", ("Rollerball / Precious Resin", "Ballpoint / Gold-coated Clip", "Fountain Pen / 14K Nib"), ("Deep Black / Gold", "Deep Black / Platinum")),
            CatalogItemTemplate("Hermès Silk Tie", 260, "https://images.unsplash.com/photo-1574634534894-89d7576c8259?auto=format&fit=crop&w=800&q=80", ("100% Silk / 8cm Width", "Hand-stitched / 7cm Width"), ("Navy/Red Pattern", "Burgundy/Grey", "Light Blue/Gold")),
            CatalogItemTemplate("Cartier LOVE Bracelet", 7350, "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?auto=format&fit=crop&w=800&q=80", ("18K Solid Gold / 6.1mm Width", "Includes Screwdriver / Size 16-21"), ("Yellow Gold", "Rose Gold", "White Gold")),
        )
    ),
    "Mens_Shoes": CategorySeedData(
        products=(
            CatalogItemTemplate("Nike Air Jordan 1 Retro High OG", 180, "https://images.unsplash.com/photo-1595950653106-6eb8aca16900?auto=format&fit=crop&w=800&q=80", ("Size 8 US", "Size 9 US", "Size 10 US", "Size 11 US", "Size 12 US", "Size 13 US"), ("Chicago (Red/White/Black)", "Bred (Black/Red)", "Royal Blue", "Shadow")),
            CatalogItemTemplate("Adidas Yeezy Boost 350 V2", 230, "https://images.unsplash.com/photo-1617606002806-381cff4c28f6?auto=format&fit=crop&w=800&q=80", ("Size 8 US", "Size 9 US", "Size 10 US", "Size 11 US", "Size 12 US"), ("Zebra", "Bone", "Onyx", "Beluga Reflective")),
            CatalogItemTemplate("Cole Haan ZeroGrand Oxford", 200, "https://images.unsplash.com/photo-1614252369475-531eba835eb1?auto=format&fit=crop&w=800&q=80", ("Size 8 US", "Size 9 US", "Size 10 US", "Size 11 US", "Size 12 US", "Medium Width", "Wide Width"), ("British Tan", "Black Leather", "Ironstone Suede")),
            CatalogItemTemplate("Timberland 6-Inch Premium Boot", 198, "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?auto=format&fit=crop&w=800&q=80", ("Size 8 US", "Size 9 US", "Size 10 US", "Size 11 US", "Size 12 US", "Waterproof Leather"), ("Wheat Nubuck", "Black Nubuck", "Rust")),
            CatalogItemTemplate("Nike Dunk Low Retro", 115, "https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=800&q=80", ("Size 8 US", "Size 9 US", "Size 10 US", "Size 11 US", "Size 12 US"), ("Panda (Black/White)", "University Red", "Coast Blue")),
            CatalogItemTemplate("Adidas Samba OG", 100, "https://images.unsplash.com/photo-1514989940723-e8e51635b782?auto=format&fit=crop&w=800&q=80", ("Size 8 US", "Size 9 US", "Size 10 US", "Size 11 US", "Size 12 US", "Gum Sole"), ("White/Black", "Black/White", "Cloud White/Green")),
        )
    ),
    "Womens_Shoes": CategorySeedData(
        products=(
            CatalogItemTemplate("Christian Louboutin So Kate Pumps", 795, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=800&q=80", ("Size 36 EU", "Size 37 EU", "Size 38 EU", "Size 39 EU", "Size 40 EU", "120mm Stiletto Heel"), ("Nude Patent Leather", "Black Patent Leather", "Red Suede")),
            CatalogItemTemplate("Jimmy Choo Romy 85", 750, "https://images.unsplash.com/photo-1562183241-b937e95585b6?auto=format&fit=crop&w=800&q=80", ("Size 36 EU", "Size 37 EU", "Size 38 EU", "Size 39 EU", "Size 40 EU", "85mm Heel"), ("Platinum Glitter", "Black Suede", "Navy Leather")),
            CatalogItemTemplate("Nike Air Force 1 Shadow", 130, "https://images.unsplash.com/photo-1515347619152-44a30dbf229c?auto=format&fit=crop&w=800&q=80", ("Size 5 US", "Size 6 US", "Size 7 US", "Size 8 US", "Size 9 US", "Double Swoosh Design"), ("Triple White", "Pastel Multi", "Sail/Pink")),
            CatalogItemTemplate("Veja Campo Sneakers", 175, "https://images.unsplash.com/photo-1595341888016-a392ef81b7de?auto=format&fit=crop&w=800&q=80", ("Size 36 EU", "Size 37 EU", "Size 38 EU", "Size 39 EU", "Size 40 EU", "Chrome-free Leather"), ("White/Matcha", "White/Black", "White/Natural")),
            CatalogItemTemplate("Manolo Blahnik Hangisi 105", 1225, "https://images.unsplash.com/photo-1551489186-ccb95a1ea6a3?auto=format&fit=crop&w=800&q=80", ("Size 36 EU", "Size 37 EU", "Size 38 EU", "Size 39 EU", "Size 40 EU", "105mm Heel / Crystal Buckle"), ("Royal Blue Satin", "Emerald Green Satin", "Black Satin")),
            CatalogItemTemplate("UGG Classic Ultra Mini", 150, "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?auto=format&fit=crop&w=800&q=80", ("Size 5 US", "Size 6 US", "Size 7 US", "Size 8 US", "Size 9 US", "Sheepskin Lining"), ("Chestnut", "Antelope", "Black", "Burnt Cedar")),
        )
    ),
    "Perfumes": CategorySeedData(
        products=(
            CatalogItemTemplate("Tom Ford Oud Wood Eau de Parfum", 295, "https://images.unsplash.com/photo-1592945403429-234e4a7a8f33?auto=format&fit=crop&w=800&q=80", ("50ml / Eau de Parfum", "100ml / Eau de Parfum", "250ml / Decanter"), ("Smoky Amber Base",)),
            CatalogItemTemplate("Creed Aventus", 495, "https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=800&q=80", ("50ml / Eau de Parfum", "100ml / Eau de Parfum"), ("Pineapple / Birch Notes",)),
            CatalogItemTemplate("Maison Francis Kurkdjian Baccarat Rouge 540", 325, "https://images.unsplash.com/photo-1616949755610-8c9bac08f9f8?auto=format&fit=crop&w=800&q=80", ("70ml / Eau de Parfum", "200ml / Eau de Parfum", "70ml / Extrait de Parfum"), ("Saffron / Cedarwood", "Signature Red (Extrait)")),
            CatalogItemTemplate("Chanel Bleu de Chanel", 155, "https://images.unsplash.com/photo-1595425970377-c9703c48ea2d?auto=format&fit=crop&w=800&q=80", ("50ml / Eau de Parfum", "100ml / Eau de Parfum", "150ml / Parfum"), ("Woody Aromatic",)),
            CatalogItemTemplate("Yves Saint Laurent Libre", 165, "https://images.unsplash.com/photo-1588405748880-12d1d2a59f75?auto=format&fit=crop&w=800&q=80", ("50ml / Eau de Parfum", "90ml / Eau de Parfum", "90ml / Intense"), ("Lavender / Orange Blossom",)),
            CatalogItemTemplate("Le Labo Santal 33", 320, "https://images.unsplash.com/photo-1615525997678-ce8a7c29bc15?auto=format&fit=crop&w=800&q=80", ("50ml / Eau de Parfum", "100ml / Eau de Parfum"), ("Sandalwood / Cardamom",)),
        )
    ),
    "Skincare": CategorySeedData(
        products=(
            CatalogItemTemplate("Estée Lauder Advanced Night Repair", 125, "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=800&q=80", ("30ml / Anti-Aging Serum", "50ml / Anti-Aging Serum", "115ml / Anti-Aging Serum"), ("Oil-Free Formula",)),
            CatalogItemTemplate("La Mer Crème de la Mer", 380, "https://images.unsplash.com/photo-1611077544346-630b77c5fb04?auto=format&fit=crop&w=800&q=80", ("30ml / Moisturizing Cream", "60ml / Moisturizing Cream", "100ml / Moisturizing Cream"), ("Miracle Broth Infused",)),
            CatalogItemTemplate("Paula's Choice 2% BHA Liquid Exfoliant", 35, "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=800&q=80", ("30ml / Travel Size", "118ml / Standard Size"), ("Salicylic Acid / Unscented",)),
            CatalogItemTemplate("Kiehl's Ultra Facial Cream", 39, "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?auto=format&fit=crop&w=800&q=80", ("50ml / 24-Hour Hydration", "125ml / 24-Hour Hydration"), ("Squalane Enriched / Fragrance-Free",)),
            CatalogItemTemplate("CeraVe Hydrating Facial Cleanser", 17, "https://images.unsplash.com/photo-1556228720-192a6af6e8ce?auto=format&fit=crop&w=800&q=80", ("236ml / Pump Bottle", "473ml / Pump Bottle"), ("Hyaluronic Acid / Ceramides",)),
            CatalogItemTemplate("The Ordinary Niacinamide 10% + Zinc 1%", 11, "https://images.unsplash.com/photo-1617897903246-719242758050?auto=format&fit=crop&w=800&q=80", ("30ml / Dropper Bottle", "60ml / Dropper Bottle"), ("Water-Based Serum",)),
        )
    ),
}


class RetryPolicy:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self._attempts = settings.retry_attempts
        self._min_seconds = settings.retry_min_seconds
        self._max_seconds = settings.retry_max_seconds
        self._logger = logger

    async def run(self, operation: Any, operation_name: str) -> Any:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._attempts),
            wait=wait_exponential(multiplier=1, min=self._min_seconds, max=self._max_seconds),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    json_log(
                        self._logger,
                        logging.WARNING,
                        "retrying_operation",
                        operation=operation_name,
                        attempt=attempt.retry_state.attempt_number,
                    )
                return await operation()
        raise RuntimeError(f"Retry policy exhausted for {operation_name}")


class ProductGenerator:
    def __init__(self, random_seed: int) -> None:
        self._random_seed = random_seed
        self._namespace = hashlib.sha256(str(random_seed).encode()).hexdigest()[:16]
        self._categories = tuple(CATALOG_DATA.keys())
        self._attr_mapping = {
            "Electronics": "Configuration",
            "Womens_Clothing": "Size",
            "Mens_Clothing": "Size",
            "Makeup": "Finish/Shade",
            "Accessories": "Material/Size",
            "Mens_Shoes": "Size",
            "Womens_Shoes": "Size",
            "Perfumes": "Volume",
            "Skincare": "Size/Type",
            "Watches": "Movement/Case"
        }

    def generate_batch(self, start_id: int, batch_size: int, limit: int) -> list[Product]:
        if start_id <= 0 or batch_size <= 0 or limit <= 0:
            raise ValueError("start_id, batch_size, and limit must be strictly positive")
        if start_id > limit:
            return []

        end_id = min(start_id + batch_size - 1, limit)
        created_at = datetime(2026, 1, 1, tzinfo=UTC)  # Explicit, deterministic demo timestamp.
        products: list[Product] = []

        for product_id in range(start_id, end_id + 1):
            rng = random.Random(f"{self._random_seed}:{product_id}")
            category = rng.choice(self._categories)
            category_data = CATALOG_DATA[category]
            
            # Entity-level attribute resolution to prevent hallucinations
            template = rng.choice(category_data.products)
            spec = rng.choice(template.specs)
            color = rng.choice(template.colors)

            attr_key = self._attr_mapping.get(category, "Specification")
            attributes = {"Color/Variant": color, attr_key: spec}

            premium_tokens = {"1TB", "2TB", "4TB", "Max", "Pro", "18K", "Diamond", "Extrait"}
            premium_multiplier = Decimal("1.25") if any(token in spec or token in template.name for token in premium_tokens) else Decimal("1.00")
            noise = Decimal(str(round(rng.uniform(0.98, 1.02), 4)))
            final_price = quantize_price(Decimal(template.base_price) * premium_multiplier * noise)

            description = (
                f"Demo catalog item: {template.name}. Sample variant: {color}; {spec}. "
                "Price, stock, rating and specifications are synthetic test data, not a merchant offer. "
                "The image is illustrative, not verified product photography."
            )
            sku = f"ADL-DEMO-v1-{self._namespace}-{product_id:08d}"
            attributes.update({'_seed_dataset':'airdeliver-demo-v1', '_seed_ordinal':str(product_id), '_seed_random':str(self._random_seed)})
            tags = [category.replace('_',' '), 'Demo', template.name.split()[0]]

            products.append(
                Product(
                    id=product_id,
                    sku=sku,
                    name=template.name,
                    description=description,
                    price=final_price,
                    category=category,
                    inventory=rng.randint(5, 500),
                    image=template.image,
                    rating=round(rng.uniform(4.0, 5.0), 1),
                    attributes=attributes,
                    tags=tags,
                    created_at=created_at,
                    updated_at=created_at,
                    currency=DEFAULT_CURRENCY,
                    is_active=True,
                )
            )

        return products


@runtime_checkable
class VectorSink(Protocol):
    async def initialize_schema(self, dimension: int, drop_existing: bool) -> None: ...
    async def insert_batch(self, products: Sequence[Product], vectors: Sequence[ProductVector]) -> int: ...


class PostgresRepository:
    def __init__(self, settings: Settings, logger: logging.Logger, retry_policy: RetryPolicy) -> None:
        self._logger = logger
        self._retry = retry_policy
        self._engine: AsyncEngine = create_async_engine(
            settings.postgres_dsn,
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
            pool_pre_ping=True,
            future=True,
            hide_parameters=True,
        )
        self._session_factory = async_sessionmaker(bind=self._engine, class_=AsyncSession, expire_on_commit=False)

    async def initialize_schema(self) -> None:
        # Migrations own the schema. Seeding must not create a parallel catalog.
        async with self._engine.connect() as connection:
            migrated = (await connection.execute(text("SELECT to_regclass('alembic_version')"))).scalar_one()
            columns = (await connection.execute(text("SELECT column_name,data_type,column_default FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='products'"))).mappings().all()
            by_name = {row['column_name']:row for row in columns}
            if not migrated or set(Product.model_fields)-set(by_name):
                raise RuntimeError('Run alembic upgrade head before seeding; the migrated products schema is required')
            if any(by_name[name]['data_type']!='timestamp with time zone' for name in ('created_at','updated_at')):
                raise RuntimeError('Run the catalog timestamp migration before seeding; do not guess historical timezone')
            if not by_name['id']['column_default']:
                raise RuntimeError('The migrated products.id database-generated sequence is required')
        json_log(self._logger,logging.INFO,'postgres_schema_verified')

    async def get_max_id(self) -> int | None:
        async def operation() -> int | None:
            async with self._session_factory() as session:
                result = await session.execute(text("SELECT MAX(id) FROM products"))
                value = result.scalar_one_or_none()
                return int(value) if value is not None else None
        
        return await self._retry.run(operation, "postgres_get_max_id")

    async def insert_batch(self, products: Sequence[Product]) -> int:
        _, inserted = await self.persist_batch(products)
        return inserted

    async def persist_batch(self, products: Sequence[Product]) -> tuple[list[Product], int]:
        if not products:
            return [], 0
        skus = [item.sku for item in products]
        if len(skus)!=len(set(skus)):
            raise ValueError('Duplicate SKUs within one batch')
        payload = [item.model_dump(exclude={'id'}) for item in products]
        table = DatabaseProduct.__table__
        async def operation():
            async with self._session_factory() as session:
                statement = pg_insert(table).values(payload).on_conflict_do_nothing(index_elements=['sku']).returning(table.c.id)
                inserted = len((await session.execute(statement)).scalars().all())
                rows = (await session.execute(select(table).where(table.c.sku.in_(skus)))).mappings().all()
                actual = {row['sku']:Product.model_validate(dict(row)) for row in rows}
                if len(actual)!=len(skus):
                    raise RuntimeError('The database did not return every requested catalog SKU')
                await session.commit()
                return [actual[sku] for sku in skus], inserted
        actual, inserted = await self._retry.run(operation,'postgres_persist_batch')
        json_log(self._logger,logging.INFO,'postgres_batch_persisted',requested=len(products),inserted=inserted,existing=len(products)-inserted)
        return actual, inserted

    async def close(self) -> None:
        await self._engine.dispose()
        json_log(self._logger, logging.INFO, "postgres_closed")


class MilvusRepository:
    def __init__(self, settings: Settings, logger: logging.Logger, retry_policy: RetryPolicy) -> None:
        self._logger = logger
        self._retry = retry_policy
        self._enabled = settings.milvus_enabled
        self._uri = settings.milvus_uri
        self._token = settings.milvus_token.get_secret_value() if settings.milvus_token else None
        self._client: MilvusClient | None = None
        self._collection_name = settings.milvus_collection
        self._model_name = settings.embedding_model
        self._model_revision = settings.embedding_revision
        self._dimension = 0

    async def _ensure_client(self) -> MilvusClient:
        if not self._enabled:
            raise RuntimeError("Milvus is disabled")
        if self._client is not None:
            return self._client

        async def operation() -> MilvusClient:
            def connect() -> MilvusClient:
                return MilvusClient(uri=self._uri, token=self._token)
            return await asyncio.to_thread(connect)

        self._client = await self._retry.run(operation, "milvus_connect")
        json_log(self._logger, logging.INFO, "milvus_connected", collection=self._collection_name)
        return self._client

    async def initialize_schema(self, dimension: int, drop_existing: bool) -> None:
        if not self._enabled:
            json_log(self._logger, logging.INFO, "milvus_disabled")
            return
        if dimension <= 0:
            raise ValueError("Dimension must be strictly positive")
        self._dimension = dimension

        async def operation() -> None:
            client = await self._ensure_client()

            def sync_init() -> None:
                has_collection = client.has_collection(self._collection_name)
                if drop_existing:
                    raise ValueError('Destructive collection resets are disabled; choose a new collection explicitly')
                if has_collection:
                    description = client.describe_collection(self._collection_name)
                    fields = {f['name']:f for f in description.get('fields',[])}
                    if int(fields.get('vector',{}).get('params',{}).get('dim',0))!=dimension:
                        raise ValueError('Existing Milvus collection dimension differs from the embedding model; no collection was dropped')
                    required={'id','vector','price','rating','category'}
                    if not required.issubset(fields):
                        raise ValueError(f'Existing Milvus collection {self._collection_name} is not an API product schema; missing fields={sorted(required-set(fields))}; present fields={sorted(fields)}. No data changed. Run python -m scripts.inspect_product_collection for read-only diagnosis; do not reset or drop the collection.')
                    if description.get('auto_id',False) or not fields['id'].get('is_primary',False):
                        raise ValueError('Milvus must preserve database-assigned primary IDs')
                    if int(fields['id'].get('type',0))!=int(DataType.INT64) or int(fields['vector'].get('type',0))!=int(DataType.FLOAT_VECTOR):
                        raise ValueError('Milvus primary ID and vector field types differ from the API contract')
                    metrics=[]
                    for name in client.list_indexes(self._collection_name):
                        definition=client.describe_index(self._collection_name,name)
                        if definition.get('field_name')=='vector':
                            metrics.append(definition.get('metric_type','').upper())
                    if metrics!=['COSINE']:
                        raise ValueError('Milvus product vectors need the COSINE index used by API search')
                    if 'attributes' not in fields and not description.get('enable_dynamic_field',False):
                        raise ValueError('Milvus needs an attributes field or dynamic fields for product metadata')
                if not has_collection:
                    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
                    schema.add_field("id", DataType.INT64, is_primary=True)
                    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self._dimension)
                    schema.add_field("price", DataType.FLOAT)
                    schema.add_field("rating", DataType.FLOAT)
                    schema.add_field("category", DataType.VARCHAR, max_length=128)
                    schema.add_field("attributes", DataType.JSON)
                    index_params = client.prepare_index_params()
                    index_params.add_index(field_name="vector", metric_type="COSINE", index_type="AUTOINDEX")
                    client.create_collection(collection_name=self._collection_name, schema=schema, index_params=index_params)

            await asyncio.to_thread(sync_init)

        await self._retry.run(operation, "milvus_initialize_schema")
        json_log(self._logger, logging.INFO, "milvus_schema_initialized", dimension=dimension, collection=self._collection_name)

    async def insert_batch(self, products: Sequence[Product], vectors: Sequence[ProductVector]) -> int:
        if not self._enabled:
            return 0
        if len(products)!=len(vectors) or any(product.id!=vector.product_id for product,vector in zip(products,vectors)):
            raise ValueError('Product/vector identity mismatch')
        if any(len(vector.vector)!=self._dimension for vector in vectors) and self._dimension:
            raise ValueError('Milvus vector dimension mismatch')
        if not vectors:
            return 0

        async def operation() -> int:
            client = await self._ensure_client()
            data = [
                {
                    "id": vector.product_id,
                    "vector": vector.vector,
                    "price": vector.price,
                    "rating": vector.rating,
                    "category": vector.category,
                    "attributes": {**vector.attributes, '_embedding_model':self._model_name, '_embedding_revision':self._model_revision or 'unpinned'},
                }
                for vector in vectors
            ]
            result = await asyncio.to_thread(client.upsert, collection_name=self._collection_name, data=data)
            if int(result.get('upsert_count',-1))!=len(vectors):
                raise RuntimeError('Milvus did not confirm every requested upsert')
            return len(vectors)

        inserted = await self._retry.run(operation, "milvus_insert_batch")
        json_log(self._logger, logging.INFO, "milvus_batch_inserted", inserted=inserted)
        return inserted

    async def close(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None
        json_log(self._logger,logging.INFO,'milvus_closed')


class OpenSearchRepository:
    def __init__(self, settings: Settings, logger: logging.Logger, retry_policy: RetryPolicy) -> None:
        self._logger = logger
        self._retry = retry_policy
        self._enabled = settings.opensearch_enabled
        self._index_name = settings.opensearch_index
        self._bulk_chunk_size = settings.opensearch_bulk_chunk_size
        self._bulk_max_chunk_bytes = settings.opensearch_bulk_max_chunk_bytes
        self._vector_mode = "unknown"

        auth = None
        if settings.opensearch_user and settings.opensearch_pass:
            auth = (settings.opensearch_user, settings.opensearch_pass.get_secret_value())

        kwargs: dict[str, Any] = {
            "hosts": [{"host": settings.opensearch_host, "port": settings.opensearch_port}],
            "http_auth": auth,
            "timeout": 60,
            "max_retries": 3,
            "retry_on_timeout": True,
        }

        if settings.opensearch_use_ssl:
            ssl_context = ssl.create_default_context()
            if not settings.opensearch_verify_certs:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            kwargs["use_ssl"] = True
            kwargs["ssl_context"] = ssl_context
        else:
            kwargs["use_ssl"] = False

        self._client = AsyncOpenSearch(**kwargs) if self._enabled else None

    def _base_mappings(self) -> dict[str, Any]:
        return {
            "properties": {
                "id": {"type": "long"},
                "sku": {"type": "keyword"},
                "name": {"type": "text"},
                "description": {"type": "text"},
                "price": {"type": "double"},
                "category": {"type": "keyword"},
                "inventory": {"type": "integer"},
                "image": {"type": "keyword"},
                "rating": {"type": "double"},
                "attributes": {"type": "object"},
                "tags": {"type": "keyword"},
                "currency": {"type": "keyword"},
                "is_active": {"type": "boolean"},
            }
        }

    def _index_settings(self, knn_enabled: bool) -> dict[str, Any]:
        settings: dict[str, Any] = {
            "index.number_of_shards": 1,
            "index.number_of_replicas": 1,
            "index.refresh_interval": "30s",
        }
        if knn_enabled:
            settings["index.knn"] = True
        return settings

    async def _create_index_knn_vector(self, dimension: int) -> str:
        body = {"settings": self._index_settings(True), "mappings": self._base_mappings()}
        body["mappings"]["properties"]["vector"] = {
            "type": "knn_vector",
            "dimension": dimension,
            "method": {"name": "hnsw", "engine": "lucene", "space_type": "cosinesimil"},
        }
        await self._client.indices.create(index=self._index_name, body=body)
        return "knn_vector"

    async def _create_index_dense_vector(self, dimension: int) -> str:
        body = {"settings": self._index_settings(False), "mappings": self._base_mappings()}
        body["mappings"]["properties"]["vector"] = {"type": "dense_vector", "dims": dimension}
        await self._client.indices.create(index=self._index_name, body=body)
        return "dense_vector"

    async def _create_index_source_only(self) -> str:
        body = {"settings": self._index_settings(False), "mappings": self._base_mappings()}
        body["mappings"]["properties"]["vector_payload"] = {"type": "object", "enabled": False}
        await self._client.indices.create(index=self._index_name, body=body)
        return "source_only"

    async def initialize_schema(self, dimension: int, drop_existing: bool) -> None:
        if not self._enabled:
            json_log(self._logger, logging.INFO, "opensearch_disabled")
            return
        if dimension <= 0:
            raise ValueError("Dimension must be positive")

        async def operation() -> None:
            if drop_existing:
                raise ValueError("Destructive index resets are disabled; choose a new index explicitly")

            exists = await self._client.indices.exists(index=self._index_name)
            if exists:
                mapping = await self._client.indices.get_mapping(index=self._index_name)
                properties = mapping.get(self._index_name, {}).get("mappings", {}).get("properties", {})
                vector_field = properties.get("vector")
                
                if isinstance(vector_field, dict) and vector_field.get("type") == "knn_vector":
                    self._vector_mode = "knn_vector"
                elif isinstance(vector_field, dict) and vector_field.get("type") == "dense_vector":
                    self._vector_mode = "dense_vector"
                else:
                    self._vector_mode = "source_only"
                if vector_field and int(vector_field.get('dimension',vector_field.get('dims',0)))!=dimension:
                    raise ValueError('Existing OpenSearch vector dimension differs from the embedding model; no index was dropped')
                return

            try:
                self._vector_mode = await self._create_index_knn_vector(dimension)
                return
            except RequestError as error:
                if "no handler for type [knn_vector]" not in str(error).lower():
                    raise
                json_log(self._logger, logging.WARNING, "opensearch_knn_fallback", message="knn_vector not supported, trying dense_vector")

            try:
                self._vector_mode = await self._create_index_dense_vector(dimension)
                return
            except RequestError as error:
                if "no handler for type [dense_vector]" not in str(error).lower():
                    raise
                json_log(self._logger, logging.WARNING, "opensearch_dense_fallback", message="dense_vector not supported, fallback to source-only")

            self._vector_mode = await self._create_index_source_only()

        await self._retry.run(operation, "opensearch_initialize_schema")
        json_log(self._logger, logging.INFO, "opensearch_schema_initialized", dimension=dimension, index=self._index_name, vector_mode=self._vector_mode)

    async def insert_batch(self, products: Sequence[Product], vectors: Sequence[ProductVector]) -> int:
        if not self._enabled or not products:
            return 0
        if len(products) != len(vectors) or any(product.id!=vector.product_id for product,vector in zip(products,vectors)):
            raise ValueError("Products and vectors length or identity mismatch")
        if self._vector_mode == "unknown":
            raise RuntimeError("OpenSearch schema must be initialized before insert")

        actions = []
        for product, vector in zip(products, vectors):
            source: dict[str, Any] = {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "category": product.category,
                "inventory": product.inventory,
                "image": product.image,
                "rating": product.rating,
                "attributes": product.attributes,
                "tags": product.tags,
                "currency": product.currency,
                "is_active": product.is_active,
            }
            if self._vector_mode in {"knn_vector", "dense_vector"}:
                source["vector"] = vector.vector
            else:
                source["vector_payload"] = {"dimension": len(vector.vector), "values": vector.vector}

            actions.append({"_op_type": "index", "_index": self._index_name, "_id": str(product.id), "_source": source})

        async def operation() -> int:
            success_count, _ = await helpers.async_bulk(
                self._client,
                actions,
                chunk_size=self._bulk_chunk_size,
                max_chunk_bytes=self._bulk_max_chunk_bytes,
                raise_on_error=True,
                refresh=False,
            )
            if int(success_count)!=len(products):
                raise RuntimeError('OpenSearch did not confirm every requested product')
            return int(success_count)

        inserted = await self._retry.run(operation, "opensearch_insert_batch")
        json_log(self._logger, logging.INFO, "opensearch_batch_inserted", inserted=inserted, vector_mode=self._vector_mode)
        return inserted

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
        json_log(self._logger, logging.INFO, "opensearch_closed")


class EmbeddingService:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self._logger = logger
        self._encode_batch_size = settings.embedding_encode_batch_size
        self._candidate = next((key.split('-')[0] for key,space in __import__('app.core.catalog_contract',fromlist=['SPACES']).SPACES.items() if key!='gte-v1' and settings.embedding_model==space.model),None)
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(settings.embedding_threads)
        options={'local_files_only':True,'model_kwargs':{'dtype':torch.float32}} if settings.embedding_local_files_only else {}
        model_path=settings.embedding_model
        if self._candidate:
            from scripts.owner_embedding_benchmark import resolve,validate_files,definitions
            path,revision=resolve(self._candidate);validate_files(path,definitions()[self._candidate]);model_path=str(path)
        self._model = SentenceTransformer(model_path, revision=settings.embedding_revision, device='cpu', trust_remote_code=False, **options)
        self._model.max_seq_length = settings.embedding_max_seq_length
        self._dimension = int(self._model.get_embedding_dimension())
        if self._dimension!=settings.embedding_dimension:
            raise ValueError('Embedding model dimension does not match SEED_EMBEDDING_DIMENSION')
        self._model.eval()
        if self._dimension <= 0:
            raise ValueError("Embedding dimension must be positive")
        json_log(self._logger, logging.INFO, "embedding_model_loaded", model=settings.embedding_model, dimension=self._dimension)

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_products(self, products: Sequence[Product]) -> list[list[float]]:
        if not products:
            return []

        texts = [self._compose_text(product) for product in products]

        def encode() -> list[list[float]]:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=self._encode_batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
                **({"prompt":""} if self._candidate else {}),
            )
            return [row.astype(float).tolist() for row in embeddings]

        vectors = await asyncio.to_thread(encode)
        if len(vectors) != len(products) or any(len(v)!=self._dimension or not all(math.isfinite(x) for x in v) or sum(x*x for x in v)==0 for v in vectors):
            raise RuntimeError("Embedding service returned invalid vector count")
        return vectors

    @staticmethod
    def _compose_text(product: Product) -> str:
        attr_text = " ".join(f"{k}: {v}" for k, v in product.attributes.items() if not k.startswith("_seed_"))
        return f"{product.name} {attr_text} {product.description} {product.category} {product.currency} {' '.join(product.tags)}"


class SeederService:
    def __init__(
        self,
        settings: Settings,
        logger: logging.Logger,
        postgres: PostgresRepository,
        milvus: MilvusRepository,
        opensearch: OpenSearchRepository,
        embedding: EmbeddingService,
        generator: ProductGenerator,
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._postgres = postgres
        self._milvus = milvus
        self._opensearch = opensearch
        self._embedding = embedding
        self._generator = generator
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False

    async def run(self) -> dict:
        await self._postgres.initialize_schema()
        use_vectors = self._settings.milvus_enabled or self._settings.opensearch_enabled
        self._initialization_degraded = False
        if use_vectors:
            await self._initialize_indexes(False)
        inserted = generated = 0
        degraded = self._initialization_degraded
        # Stable SKUs, not MAX(id), identify this demo dataset. Replaying every SKU
        # repairs indexes after a prior interruption without replacing catalog rows.
        for current_id in range(1,self._settings.target_count+1,self._settings.batch_size):
            if not self._is_running:
                raise asyncio.CancelledError('Demo seeding interrupted; rerun to reconcile indexes')
            candidates = self._generator.generate_batch(current_id,self._settings.batch_size,self._settings.target_count)
            products, new_rows = await self._postgres.persist_batch(candidates)
            inserted += new_rows
            vectors=[]
            if use_vectors:
                embeddings=await self._embedding.embed_products(products)
                vectors=self._build_product_vectors(products,embeddings)
            statuses={}
            for name,sink,enabled,fail_hard in (
                ('milvus',self._milvus,self._settings.milvus_enabled,self._settings.fail_on_milvus_error),
                ('opensearch',self._opensearch,self._settings.opensearch_enabled,self._settings.fail_on_opensearch_error)):
                statuses[name]=await self._run_optional_sink(sink.insert_batch(products,vectors),name,fail_hard) if enabled else 'disabled'
                if statuses[name]=='degraded':
                    degraded=True
            generated += len(products)
            json_log(self._logger,logging.INFO,'seeding_progress',processed=generated,inserted=inserted,target=self._settings.target_count,**statuses)
        summary={'status':'degraded' if degraded else 'completed','processed':generated,'inserted':inserted,'target':self._settings.target_count,
                 'milvus':'enabled' if self._settings.milvus_enabled else 'disabled','opensearch':'enabled' if self._settings.opensearch_enabled else 'disabled'}
        json_log(self._logger,logging.INFO if not degraded else logging.ERROR,'seeding_completed' if not degraded else 'seeding_incomplete',**summary)
        if degraded:
            raise RuntimeError('One or more configured indexes failed; rerun to reconcile persisted products')
        return summary

    async def _initialize_indexes(self, fresh_start: bool) -> None:
        if self._settings.milvus_enabled:
            status = await self._run_optional_sink(
                self._milvus.initialize_schema(self._embedding.dimension, drop_existing=False),
                "milvus", self._settings.fail_on_milvus_error,
            )
            self._initialization_degraded |= status=='degraded'
        if self._settings.opensearch_enabled:
            status = await self._run_optional_sink(
                self._opensearch.initialize_schema(self._embedding.dimension, drop_existing=False),
                "opensearch", self._settings.fail_on_opensearch_error,
            )
            self._initialization_degraded |= status=='degraded'

    async def _run_optional_sink(self, operation: Any, sink_name: str, fail_hard: bool) -> str | int:
        try:
            return await operation
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            json_log(self._logger, logging.ERROR, "sink_operation_failed", sink=sink_name, error=type(exc).__name__)
            if fail_hard:
                raise
            return "degraded"

    @staticmethod
    def _build_product_vectors(products: Sequence[Product], embeddings: Sequence[list[float]]) -> list[ProductVector]:
        if len(products)!=len(embeddings):
            raise ValueError("Products and embeddings length mismatch")
        if len({len(v) for v in embeddings})>1:
            raise ValueError("Mixed embedding dimensions")
        return [
            ProductVector(
                product_id=product.id,
                vector=embedding,
                price=float(product.price),
                rating=product.rating,
                category=product.category,
                attributes=product.attributes,
            )
            for product, embedding in zip(products, embeddings)
        ]


@asynccontextmanager
async def application_context(settings: Settings) -> AsyncGenerator[SeederService, None]:
    logger = configure_logging(settings.log_level)
    retry_policy = RetryPolicy(settings, logger)
    
    postgres = PostgresRepository(settings, logger, retry_policy)
    milvus = MilvusRepository(settings, logger, retry_policy)
    opensearch = OpenSearchRepository(settings, logger, retry_policy)
    
    async with AsyncExitStack() as stack:
        stack.push_async_callback(postgres.close)
        stack.push_async_callback(milvus.close)
        stack.push_async_callback(opensearch.close)

        await postgres.initialize_schema()
        embedding = EmbeddingService(settings, logger) if (settings.milvus_enabled or settings.opensearch_enabled) else None
        generator = ProductGenerator(settings.random_seed)
        
        service = SeederService(
            settings=settings,
            logger=logger,
            postgres=postgres,
            milvus=milvus,
            opensearch=opensearch,
            embedding=embedding,
            generator=generator,
        )
        
        yield service


async def main() -> None:
    settings = Settings()
    loop = asyncio.get_running_loop()
    
    async with application_context(settings) as service:
        def shutdown_handler(sig: signal.Signals) -> None:
            logging.getLogger(LOGGER_NAME).info(f"Received exit signal {sig.name}...")
            service.stop()

        for sig_name in {"SIGINT", "SIGTERM"}:
            if hasattr(signal, sig_name):
                loop.add_signal_handler(getattr(signal, sig_name), shutdown_handler, getattr(signal, sig_name))

        await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
