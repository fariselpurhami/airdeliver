import asyncio
import json
import logging
import random
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Final, Iterable, Sequence

from opensearchpy import AsyncOpenSearch, helpers
from opensearchpy.exceptions import RequestError
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymilvus import DataType, MilvusClient
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential


LOGGER_NAME: Final[str] = "ultra_scale_seeder"
UTC = timezone.utc
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
    return datetime.now(UTC).replace(tzinfo=None)


def quantize_price(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def chunked(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


def json_log(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"ts": datetime.now(UTC).isoformat(), "event": event, **fields}
    logger.log(level, json.dumps(payload, default=str, ensure_ascii=False))


def request_error_text(error: RequestError) -> str:
    parts = [str(error)]
    info = getattr(error, "info", None)
    if info is not None:
        parts.append(str(info))
    return " | ".join(parts).lower()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_dsn: str = Field(..., alias="DATABASE_URI")
    opensearch_host: str = Field(..., alias="OPENSEARCH_HOST")
    opensearch_port: int = Field(9200, alias="OPENSEARCH_PORT")
    opensearch_index: str = Field("airdeliver_products", alias="OPENSEARCH_INDEX")
    opensearch_pass: SecretStr | None = Field(default=None, alias="OPENSEARCH_PASS")
    opensearch_user: str | None = Field(default=None, alias="OPENSEARCH_USER")
    opensearch_use_ssl: bool = Field(True, alias="OPENSEARCH_USE_SSL")
    opensearch_verify_certs: bool = Field(True, alias="OPENSEARCH_VERIFY_CERTS")
    opensearch_bulk_chunk_size: PositiveInt = Field(100, alias="OPENSEARCH_BULK_CHUNK_SIZE")
    opensearch_bulk_max_chunk_bytes: PositiveInt = Field(2_097_152, alias="OPENSEARCH_BULK_MAX_CHUNK_BYTES")
    milvus_uri: str = Field(..., alias="MILVUS_URI")
    milvus_token: SecretStr | None = Field(default=None, alias="MILVUS_TOKEN")
    milvus_collection: str = Field("airdeliver_products", alias="MILVUS_COLLECTION")
    embedding_model: str = Field("Alibaba-NLP/gte-Qwen2-1.5B-instruct", alias="EMBEDDING_MODEL")
    batch_size: PositiveInt = Field(32, alias="BATCH_SIZE")
    target_count: PositiveInt = Field(1000, alias="TARGET_COUNT")
    random_seed: int = Field(20260514, alias="RANDOM_SEED")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    embedding_encode_batch_size: PositiveInt = Field(16, alias="EMBEDDING_ENCODE_BATCH_SIZE")
    postgres_pool_size: PositiveInt = Field(20, alias="POSTGRES_POOL_SIZE")
    postgres_max_overflow: PositiveInt = Field(10, alias="POSTGRES_MAX_OVERFLOW")
    retry_attempts: PositiveInt = Field(5, alias="RETRY_ATTEMPTS")
    retry_min_seconds: PositiveInt = Field(1, alias="RETRY_MIN_SECONDS")
    retry_max_seconds: PositiveInt = Field(16, alias="RETRY_MAX_SECONDS")
    milvus_enabled: bool = Field(True, alias="MILVUS_ENABLED")
    opensearch_enabled: bool = Field(True, alias="OPENSEARCH_ENABLED")
    fail_on_milvus_error: bool = Field(False, alias="FAIL_ON_MILVUS_ERROR")
    fail_on_opensearch_error: bool = Field(True, alias="FAIL_ON_OPENSEARCH_ERROR")

    @field_validator("opensearch_user")
    @classmethod
    def validate_opensearch_auth_pair_user(cls, value: str | None, info: Any) -> str | None:
        password = info.data.get("opensearch_pass")
        if (value is None) ^ (password is None):
            raise ValueError("OPENSEARCH_USER and OPENSEARCH_PASS must be provided together")
        return value

    @field_validator("opensearch_index", "milvus_collection")
    @classmethod
    def validate_resource_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("resource name must not be empty")
        return normalized

    @field_validator("postgres_dsn", "milvus_uri", "embedding_model", "opensearch_host")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    sku: str
    name: str
    description: str
    price: Decimal
    category: str
    inventory: int
    image: str
    rating: float
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    currency: str
    is_active: bool

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        normalized = [tag.strip() for tag in value if tag.strip()]
        if not normalized:
            raise ValueError("tags must not be empty")
        return normalized

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("price must be positive")
        return quantize_price(value)

    @field_validator("inventory")
    @classmethod
    def validate_inventory(cls, value: int) -> int:
        if value < 0:
            raise ValueError("inventory must be non-negative")
        return value

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: float) -> float:
        if value < 0 or value > 5:
            raise ValueError("rating must be between 0 and 5")
        return round(value, 1)


class ProductVector(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: int
    vector: list[float]
    price: float
    rating: float
    category: str

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("vector must not be empty")
        return value


@dataclass(frozen=True)
class CatalogItemTemplate:
    name: str
    base_price: int
    image: str


@dataclass(frozen=True)
class CategorySeedData:
    products: tuple[CatalogItemTemplate, ...]
    specs: tuple[str, ...]
    colors: tuple[str, ...]


CATALOG_DATA: Final[dict[str, CategorySeedData]] = {
    "Smartphones": CategorySeedData(
        products=(
            CatalogItemTemplate("Apple iPhone 15 Pro Max", 1199, "https://images.unsplash.com/photo-1696446701796-da61225697cc"),
            CatalogItemTemplate("Samsung Galaxy S24 Ultra", 1299, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c"),
            CatalogItemTemplate("Google Pixel 8 Pro", 999, "https://images.unsplash.com/photo-1698669930852-25916053f317"),
            CatalogItemTemplate("Sony Xperia 1 V", 1399, "https://images.unsplash.com/photo-1596742517684-29729a656515"),
        ),
        specs=("256GB", "512GB", "1TB", "Titanium Frame", "AI Camera"),
        colors=("Natural Titanium", "Blue Titanium", "Black Titanium", "White Titanium", "Phantom Black", "Cream"),
    ),
    "Laptops": CategorySeedData(
        products=(
            CatalogItemTemplate("MacBook Pro 16 M3 Max", 2499, "https://images.unsplash.com/photo-1517336714731-489689fd1ca4"),
            CatalogItemTemplate("Dell XPS 15 OLED", 1899, "https://images.unsplash.com/photo-1593642632823-8f78536788c6"),
            CatalogItemTemplate("Razer Blade 18 Gaming", 3299, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2"),
            CatalogItemTemplate("Asus ROG Zephyrus G14", 1599, "https://images.unsplash.com/photo-1628122393356-97987820d880"),
        ),
        specs=("16GB RAM", "32GB RAM", "64GB RAM", "1TB SSD", "2TB SSD", "RTX 4090"),
        colors=("Space Grey", "Silver", "Midnight", "Mercury White", "Matte Black"),
    ),
    "Headphones": CategorySeedData(
        products=(
            CatalogItemTemplate("Sony WH-1000XM5", 348, "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb"),
            CatalogItemTemplate("Apple AirPods Max", 549, "https://images.unsplash.com/photo-1613040809024-b4ef7ba99bc3"),
            CatalogItemTemplate("Bose QuietComfort Ultra", 429, "https://images.unsplash.com/photo-1546435770-a3e426bf472b"),
        ),
        specs=("Noise Cancelling", "Lossless Audio", "Spatial Audio", "30-Hour Battery"),
        colors=("Silver", "Space Grey", "Sky Blue", "Pink", "Green", "Black"),
    ),
    "Cameras": CategorySeedData(
        products=(
            CatalogItemTemplate("Sony Alpha a7 IV", 2498, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32"),
            CatalogItemTemplate("Canon EOS R5", 3899, "https://images.unsplash.com/photo-1519183071298-a2962feb14f4"),
            CatalogItemTemplate("Fujifilm X-T5", 1699, "https://images.unsplash.com/photo-1502920917128-1aa500764cbd"),
        ),
        specs=("Body Only", "with 24-70mm Lens", "with 50mm Lens", "8K Video"),
        colors=("Black", "Silver", "Retro Styling"),
    ),
    "Drones": CategorySeedData(
        products=(
            CatalogItemTemplate("DJI Mavic 3 Pro", 2199, "https://images.unsplash.com/photo-1579829366248-204fe8413f31"),
            CatalogItemTemplate("DJI Mini 4 Pro", 759, "https://images.unsplash.com/photo-1473968512647-3e447244af8f"),
        ),
        specs=("Fly More Combo", "RC Controller", "Cine Premium Combo"),
        colors=("Classic Grey", "Light Grey"),
    ),
    "Watches": CategorySeedData(
        products=(
            CatalogItemTemplate("Apple Watch Ultra 2", 799, "https://images.unsplash.com/photo-1546868871-7041f2a55e12"),
            CatalogItemTemplate("Garmin Fenix 7X Pro", 899, "https://images.unsplash.com/photo-1523275335684-37898b6baf30"),
            CatalogItemTemplate("Samsung Galaxy Watch 6", 299, "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1"),
        ),
        specs=("49mm", "45mm", "GPS + Cellular", "GPS Only", "Sapphire Solar"),
        colors=("Titanium", "Midnight", "Starlight", "Graphite"),
    ),
}


class RetryPolicy:
    def __init__(self, attempts: int, min_seconds: int, max_seconds: int) -> None:
        self._attempts = attempts
        self._min_seconds = min_seconds
        self._max_seconds = max_seconds

    async def run(self, operation: Any) -> Any:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._attempts),
            wait=wait_exponential(multiplier=1, min=self._min_seconds, max=self._max_seconds),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                return await operation()
        raise RuntimeError("retry policy exhausted unexpectedly")


class ProductGenerator:
    def __init__(self, random_seed: int) -> None:
        self._rng = random.Random(random_seed)
        self._categories = tuple(CATALOG_DATA.keys())

    def generate_batch(self, start_id: int, batch_size: int, limit: int) -> list[Product]:
        if start_id <= 0:
            raise ValueError("start_id must be positive")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if limit <= 0:
            raise ValueError("limit must be positive")
        if start_id > limit:
            return []

        end_id = min(start_id + batch_size - 1, limit)
        created_at = now_naive_utc()
        products: list[Product] = []

        for product_id in range(start_id, end_id + 1):
            category = self._rng.choice(self._categories)
            category_data = CATALOG_DATA[category]
            template = self._rng.choice(category_data.products)
            spec = self._rng.choice(category_data.specs)
            color = self._rng.choice(category_data.colors)

            full_name = f"{template.name} - {spec} ({color})"
            premium_multiplier = Decimal("1.20") if any(token in spec for token in ("1TB", "Pro", "Max", "RTX 4090", "2TB SSD", "Sapphire Solar", "8K")) else Decimal("1.00")
            noise = Decimal(str(round(self._rng.uniform(0.95, 1.05), 4)))
            final_price = quantize_price(Decimal(template.base_price) * premium_multiplier * noise)

            description = " ".join(
                (
                    f"Experience the pinnacle of {category} technology with the {full_name}.",
                    f"Designed in a {color} finish and equipped with {spec}.",
                    "Built for demanding customers who care about performance, quality, and reliability.",
                    "Official airdeliver global stock.",
                )
            )
            inventory = self._rng.randint(5, 500)
            rating = round(self._rng.uniform(3.5, 5.0), 1)
            sku = f"GLB-{category[:3].upper()}-{product_id:08d}"
            tags = [category, "Premium", color, template.name.split()[0], "Official", spec]

            products.append(
                Product(
                    id=product_id,
                    sku=sku,
                    name=full_name,
                    description=description,
                    price=final_price,
                    category=category,
                    inventory=inventory,
                    image=template.image,
                    rating=rating,
                    tags=tags,
                    created_at=created_at,
                    updated_at=created_at,
                    currency=DEFAULT_CURRENCY,
                    is_active=True,
                )
            )

        return products


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
        )
        self._session_factory = async_sessionmaker(bind=self._engine, class_=AsyncSession, expire_on_commit=False)

    async def initialize_schema(self) -> None:
        async def operation() -> None:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS products (
                            id BIGINT PRIMARY KEY,
                            sku VARCHAR(255) UNIQUE NOT NULL,
                            name VARCHAR(512) NOT NULL,
                            description TEXT NOT NULL,
                            price NUMERIC(12, 2) NOT NULL,
                            category VARCHAR(255) NOT NULL,
                            inventory INTEGER NOT NULL,
                            image VARCHAR(2048) NOT NULL,
                            rating NUMERIC(3, 1) NOT NULL,
                            tags JSONB NOT NULL,
                            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                            currency VARCHAR(3) NOT NULL,
                            is_active BOOLEAN NOT NULL
                        );
                        """
                    )
                )
                await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);"))
                await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku);"))

        await self._retry.run(operation)
        json_log(self._logger, logging.INFO, "postgres_schema_initialized")

    async def get_max_id(self) -> int | None:
        async with self._session_factory() as session:
            result = await session.execute(text("SELECT MAX(id) FROM products"))
            value = result.scalar_one_or_none()
            return int(value) if value is not None else None

    async def insert_batch(self, products: Sequence[Product]) -> int:
        if not products:
            return 0

        async def operation() -> int:
            payload = []
            for product in products:
                item = product.model_dump()
                item["tags"] = json.dumps(item["tags"], ensure_ascii=False)
                payload.append(item)

            statement = text(
                """
                INSERT INTO products (
                    id, sku, name, description, price, category, inventory,
                    image, rating, tags, created_at, updated_at, currency, is_active
                ) VALUES (
                    :id, :sku, :name, :description, :price, :category, :inventory,
                    :image, :rating, CAST(:tags AS JSONB), :created_at, :updated_at, :currency, :is_active
                )
                ON CONFLICT (id) DO NOTHING
                """
            )

            async with self._session_factory() as session:
                result = await session.execute(statement, payload)
                await session.commit()
                return result.rowcount or 0

        inserted = await self._retry.run(operation)
        json_log(self._logger, logging.INFO, "postgres_batch_inserted", requested=len(products), inserted=inserted)
        return inserted

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
        self._dimension = 0

    async def _ensure_client(self) -> MilvusClient:
        if not self._enabled:
            raise RuntimeError("milvus is disabled")
        if self._client is not None:
            return self._client

        async def operation() -> MilvusClient:
            def connect() -> MilvusClient:
                return MilvusClient(uri=self._uri, token=self._token)

            client = await asyncio.to_thread(connect)
            return client

        self._client = await self._retry.run(operation)
        json_log(self._logger, logging.INFO, "milvus_connected", collection=self._collection_name)
        return self._client

    async def initialize_schema(self, dimension: int, drop_existing: bool) -> None:
        if not self._enabled:
            json_log(self._logger, logging.INFO, "milvus_disabled")
            return
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dimension = dimension

        async def operation() -> None:
            client = await self._ensure_client()

            def sync_init() -> None:
                has_collection = client.has_collection(self._collection_name)
                if has_collection and drop_existing:
                    client.drop_collection(self._collection_name)
                    has_collection = False
                if not has_collection:
                    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
                    schema.add_field("id", DataType.INT64, is_primary=True)
                    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self._dimension)
                    schema.add_field("price", DataType.DOUBLE)
                    schema.add_field("rating", DataType.DOUBLE)
                    schema.add_field("category", DataType.VARCHAR, max_length=255)
                    index_params = client.prepare_index_params()
                    index_params.add_index(field_name="vector", metric_type="COSINE", index_type="AUTOINDEX")
                    client.create_collection(collection_name=self._collection_name, schema=schema, index_params=index_params)

            await asyncio.to_thread(sync_init)

        await self._retry.run(operation)
        json_log(self._logger, logging.INFO, "milvus_schema_initialized", dimension=dimension, collection=self._collection_name)

    async def insert_batch(self, vectors: Sequence[ProductVector]) -> None:
        if not self._enabled or not vectors:
            return

        async def operation() -> None:
            client = await self._ensure_client()
            data = [
                {
                    "id": vector.product_id,
                    "vector": vector.vector,
                    "price": vector.price,
                    "rating": vector.rating,
                    "category": vector.category,
                }
                for vector in vectors
            ]
            await asyncio.to_thread(client.insert, collection_name=self._collection_name, data=data)

        await self._retry.run(operation)
        json_log(self._logger, logging.INFO, "milvus_batch_inserted", inserted=len(vectors))

    async def close(self) -> None:
        self._client = None
        json_log(self._logger, logging.INFO, "milvus_closed")


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

        self._client = AsyncOpenSearch(**kwargs)

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
        body = {
            "settings": self._index_settings(True),
            "mappings": self._base_mappings(),
        }
        body["mappings"]["properties"]["vector"] = {
            "type": "knn_vector",
            "dimension": dimension,
            "method": {
                "name": "hnsw",
                "engine": "lucene",
                "space_type": "cosinesimil",
            },
        }
        await self._client.indices.create(index=self._index_name, body=body)
        return "knn_vector"

    async def _create_index_dense_vector(self, dimension: int) -> str:
        body = {
            "settings": self._index_settings(False),
            "mappings": self._base_mappings(),
        }
        body["mappings"]["properties"]["vector"] = {
            "type": "dense_vector",
            "dims": dimension,
        }
        await self._client.indices.create(index=self._index_name, body=body)
        return "dense_vector"

    async def _create_index_source_only(self) -> str:
        body = {
            "settings": self._index_settings(False),
            "mappings": self._base_mappings(),
        }
        body["mappings"]["properties"]["vector_payload"] = {
            "type": "object",
            "enabled": False,
        }
        await self._client.indices.create(index=self._index_name, body=body)
        return "source_only"

    async def initialize_schema(self, dimension: int, drop_existing: bool) -> None:
        if not self._enabled:
            json_log(self._logger, logging.INFO, "opensearch_disabled")
            return
        if dimension <= 0:
            raise ValueError("dimension must be positive")

        async def operation() -> None:
            if drop_existing:
                await self._client.indices.delete(index=self._index_name, ignore=[400, 404])

            exists = await self._client.indices.exists(index=self._index_name)
            if exists:
                mapping = await self._client.indices.get_mapping(index=self._index_name)
                properties = mapping.get(self._index_name, {}).get("mappings", {}).get("properties", {})
                vector_field = properties.get("vector")
                payload_field = properties.get("vector_payload")
                if isinstance(vector_field, dict) and vector_field.get("type") == "knn_vector":
                    self._vector_mode = "knn_vector"
                elif isinstance(vector_field, dict) and vector_field.get("type") == "dense_vector":
                    self._vector_mode = "dense_vector"
                elif isinstance(payload_field, dict):
                    self._vector_mode = "source_only"
                else:
                    self._vector_mode = "source_only"
                json_log(self._logger, logging.INFO, "opensearch_schema_initialized", dimension=dimension, index=self._index_name, vector_mode=self._vector_mode)
                return

            try:
                self._vector_mode = await self._create_index_knn_vector(dimension)
                json_log(self._logger, logging.INFO, "opensearch_schema_initialized", dimension=dimension, index=self._index_name, vector_mode=self._vector_mode)
                return
            except RequestError as error:
                if "no handler for type [knn_vector]" not in request_error_text(error):
                    raise
                json_log(self._logger, logging.WARNING, "opensearch_knn_fallback", message="knn_vector not supported, trying dense_vector")

            try:
                self._vector_mode = await self._create_index_dense_vector(dimension)
                json_log(self._logger, logging.INFO, "opensearch_schema_initialized", dimension=dimension, index=self._index_name, vector_mode=self._vector_mode)
                return
            except RequestError as error:
                if "no handler for type [dense_vector]" not in request_error_text(error):
                    raise
                json_log(self._logger, logging.WARNING, "opensearch_dense_fallback", message="dense_vector not supported, falling back to source-only vector storage")

            self._vector_mode = await self._create_index_source_only()
            json_log(self._logger, logging.INFO, "opensearch_schema_initialized", dimension=dimension, index=self._index_name, vector_mode=self._vector_mode)

        await self._retry.run(operation)

    async def insert_batch(self, products: Sequence[Product], vectors: Sequence[ProductVector]) -> int:
        if not self._enabled or not products:
            return 0
        if len(products) != len(vectors):
            raise ValueError("products and vectors length mismatch")
        if self._vector_mode == "unknown":
            raise RuntimeError("opensearch schema must be initialized before insert")

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
                "tags": product.tags,
                "currency": product.currency,
                "is_active": product.is_active,
            }
            if self._vector_mode in {"knn_vector", "dense_vector"}:
                source["vector"] = vector.vector
            else:
                source["vector_payload"] = {
                    "dimension": len(vector.vector),
                    "values": vector.vector,
                }

            actions.append(
                {
                    "_op_type": "index",
                    "_index": self._index_name,
                    "_id": str(product.id),
                    "_source": source,
                }
            )

        async def operation() -> int:
            success_count, _ = await helpers.async_bulk(
                self._client,
                actions,
                chunk_size=self._bulk_chunk_size,
                max_chunk_bytes=self._bulk_max_chunk_bytes,
                raise_on_error=True,
                refresh=False,
            )
            return int(success_count)

        inserted = await self._retry.run(operation)
        json_log(self._logger, logging.INFO, "opensearch_batch_inserted", inserted=inserted, vector_mode=self._vector_mode)
        return inserted

    async def close(self) -> None:
        await self._client.close()
        json_log(self._logger, logging.INFO, "opensearch_closed")


class EmbeddingService:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self._logger = logger
        self._encode_batch_size = settings.embedding_encode_batch_size
        self._model = SentenceTransformer(settings.embedding_model, device="cpu", trust_remote_code=False)
        self._dimension = int(self._model.get_embedding_dimension())
        if self._dimension <= 0:
            raise ValueError("embedding dimension must be positive")
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
                show_progress_bar=True,
            )
            return [row.astype(float).tolist() for row in embeddings]

        vectors = await asyncio.to_thread(encode)
        if len(vectors) != len(products):
            raise RuntimeError("embedding service returned invalid vector count")
        return vectors

    @staticmethod
    def _compose_text(product: Product) -> str:
        return " ".join(
            (
                product.name,
                product.description,
                product.category,
                product.currency,
                " ".join(product.tags),
            )
        )


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

    async def run(self) -> None:
        await self._postgres.initialize_schema()

        max_id = await self._postgres.get_max_id()
        start_id = (max_id or 0) + 1
        fresh_start = start_id == 1

        await self._initialize_indexes(fresh_start)

        if start_id > self._settings.target_count:
            json_log(
                self._logger,
                logging.INFO,
                "seeding_skipped",
                start_id=start_id,
                target_count=self._settings.target_count,
                reason="target_already_reached",
            )
            return

        current_id = start_id
        total_generated = 0

        while current_id <= self._settings.target_count:
            products = self._generator.generate_batch(current_id, self._settings.batch_size, self._settings.target_count)
            if not products:
                break

            embeddings = await self._embedding.embed_products(products)
            vectors = self._build_product_vectors(products, embeddings)

            postgres_result, milvus_result, opensearch_result = await asyncio.gather(
                self._postgres.insert_batch(products),
                self._run_optional_sink(self._milvus.insert_batch(vectors), "milvus", self._settings.fail_on_milvus_error),
                self._run_optional_sink(self._opensearch.insert_batch(products, vectors), "opensearch", self._settings.fail_on_opensearch_error),
                return_exceptions=False,
            )

            current_id += len(products)
            total_generated += len(products)

            json_log(
                self._logger,
                logging.INFO,
                "seeding_progress",
                batch_size=len(products),
                postgres_inserted=postgres_result,
                milvus_status=milvus_result,
                opensearch_status=opensearch_result,
                next_id=current_id,
                total_generated=total_generated,
                target_count=self._settings.target_count,
            )

        json_log(
            self._logger,
            logging.INFO,
            "seeding_completed",
            total_generated=total_generated,
            final_target=self._settings.target_count,
        )

    async def _initialize_indexes(self, fresh_start: bool) -> None:
        await self._run_optional_sink(
            self._milvus.initialize_schema(self._embedding.dimension, drop_existing=fresh_start),
            "milvus",
            self._settings.fail_on_milvus_error,
        )
        await self._run_optional_sink(
            self._opensearch.initialize_schema(self._embedding.dimension, drop_existing=fresh_start),
            "opensearch",
            self._settings.fail_on_opensearch_error,
        )

    async def _run_optional_sink(self, operation: Any, sink_name: str, fail_hard: bool) -> str:
        try:
            await operation
            return "ok"
        except Exception as exc:
            json_log(
                self._logger,
                logging.ERROR,
                "sink_operation_failed",
                sink=sink_name,
                error=type(exc).__name__,
                message=str(exc),
            )
            if fail_hard:
                raise
            return "degraded"

    @staticmethod
    def _build_product_vectors(products: Sequence[Product], embeddings: Sequence[list[float]]) -> list[ProductVector]:
        if len(products) != len(embeddings):
            raise ValueError("products and embeddings length mismatch")
        vectors: list[ProductVector] = []
        for product, embedding in zip(products, embeddings):
            vectors.append(
                ProductVector(
                    product_id=product.id,
                    vector=embedding,
                    price=float(product.price),
                    rating=product.rating,
                    category=product.category,
                )
            )
        return vectors


class Application:
    def __init__(self, settings: Settings) -> None:
        self._logger = configure_logging(settings.log_level)
        self._retry_policy = RetryPolicy(
            attempts=settings.retry_attempts,
            min_seconds=settings.retry_min_seconds,
            max_seconds=settings.retry_max_seconds,
        )
        self._settings = settings
        self._postgres = PostgresRepository(settings, self._logger, self._retry_policy)
        self._milvus = MilvusRepository(settings, self._logger, self._retry_policy)
        self._opensearch = OpenSearchRepository(settings, self._logger, self._retry_policy)
        self._embedding = EmbeddingService(settings, self._logger)
        self._generator = ProductGenerator(settings.random_seed)
        self._service = SeederService(
            settings=settings,
            logger=self._logger,
            postgres=self._postgres,
            milvus=self._milvus,
            opensearch=self._opensearch,
            embedding=self._embedding,
            generator=self._generator,
        )

    async def run(self) -> None:
        json_log(self._logger, logging.INFO, "application_started", target_count=self._settings.target_count, batch_size=self._settings.batch_size)
        try:
            await self._service.run()
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        close_errors: list[Exception] = []

        for closer in (self._opensearch.close, self._milvus.close, self._postgres.close):
            try:
                await closer()
            except Exception as exc:
                close_errors.append(exc)
                json_log(self._logger, logging.ERROR, "resource_close_failed", error=type(exc).__name__, message=str(exc))

        if close_errors:
            raise RuntimeError("one or more resources failed to close cleanly") from close_errors[0]


async def main() -> None:
    settings = Settings()
    app = Application(settings)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
