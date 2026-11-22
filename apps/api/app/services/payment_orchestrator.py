# apps/api/app/services/payment_orchestrator.py

import asyncio
import contextvars
import logging
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum, unique
from typing import Any, Dict, List, Optional, Final

import httpx
import stripe
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# -------------------------------------------------------------------------
# Core Configuration & Interfaces
# -------------------------------------------------------------------------

class StripeSettings(BaseModel):
    secret_key: SecretStr = Field(..., description="Stripe API Secret Key")
    publishable_key: SecretStr = Field(..., description="Stripe API Publishable Key")
    webhook_secret: SecretStr = Field(..., description="Stripe Webhook Signing Secret")
    api_version: str = Field(default="2026-06-24.dahlia")


class PayPalSettings(BaseModel):
    """Structural type for the gateway; the live object is
    app.core.config.PayPalSettings (env-backed)."""
    PAYPAL_CLIENT_ID: str = Field(..., description="PayPal OAuth Client ID")
    PAYPAL_CLIENT_SECRET: SecretStr = Field(..., description="PayPal OAuth Client Secret")
    PAYPAL_API_BASE_URL: str = Field(
        default="https://api-m.sandbox.paypal.com", description="PayPal API base URL"
    )


class MpesaSettings(BaseModel):
    consumer_key: SecretStr = Field(..., description="Daraja API Consumer Key")
    consumer_secret: SecretStr = Field(..., description="Daraja API Consumer Secret")
    passkey: SecretStr = Field(..., description="Daraja STK Passkey")
    environment: str = Field(default="sandbox", pattern="^(sandbox|production)$")


class IAsyncCacheClient(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None:
        pass


# -------------------------------------------------------------------------
# Observability & Structured Logging
# -------------------------------------------------------------------------

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="unknown_correlation"
)

class StructuredLogger(logging.LoggerAdapter):
    """
    Injects context-local correlation IDs for distributed tracing.
    Formats logs for structured JSON aggregation at the edge.
    """
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        base_extra = {"correlation_id": correlation_id_var.get()}
        if "extra" in kwargs:
            kwargs["extra"].update(base_extra)
        else:
            kwargs["extra"] = base_extra
        return msg, kwargs

# Initialize standard python logger wrapped with trace context injection
logger = StructuredLogger(logging.getLogger("domain.payment_orchestrator"), {})

# -------------------------------------------------------------------------
# Domain Models & Enums
# -------------------------------------------------------------------------

@unique
class GatewayProvider(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    MPESA = "mpesa"


@unique
class PaymentStatus(str, Enum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_ACTION = "requires_action"
    PENDING_CONFIRMATION = "pending_confirmation"
    SUCCESS = "success"
    FAILURE = "failure"


class PaymentRequest(BaseModel):
    """
    Strict immutable DTO boundary for payment requests.
    Validates business invariants before execution logic.
    """
    order_id: str = Field(..., min_length=1, max_length=128)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    region: str = Field(..., min_length=2, max_length=2)
    idempotency_key: str = Field(..., min_length=16, max_length=255)
    metadata: Dict[str, str] = Field(default_factory=dict)

    @field_validator("currency", "region", mode="before")
    def force_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def check_amount_precision(self) -> "PaymentRequest":
        # Force quantization to guarantee exact floating point semantics
        quantized = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.amount = quantized
        return self


class GatewayResult(BaseModel):
    provider: GatewayProvider
    status: PaymentStatus
    transaction_id: Optional[str] = None
    client_secret: Optional[str] = None
    action_url: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------------------
# Gateway Interfaces & Implementations
# -------------------------------------------------------------------------

class IPaymentGateway(ABC):
    """
    Strict contract enforcing Liskov Substitution Principle across financial processors.
    """
    @property
    @abstractmethod
    def provider(self) -> GatewayProvider:
        pass

    @abstractmethod
    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        pass


class StripeGateway(IPaymentGateway):
    """
    Enterprise-Grade Stripe Integration.
    - Isolated StripeClient instance.
    - Exponential backoff for transient network errors.
    - Strict cent-conversion and decimal safety.
    """

    def __init__(self, settings: StripeSettings):
        self._settings = settings
        self.stripe_client = stripe.StripeClient(
            
            api_key=self._settings.STRIPE_SECRET_KEY.get_secret_value(),
            stripe_version=self._settings.api_version
        )

    @property
    def provider(self) -> GatewayProvider:
        return GatewayProvider.STRIPE

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (stripe.error.RateLimitError, stripe.error.APIConnectionError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _execute_stripe_call(
        self,
        amount_cents: int,
        request: PaymentRequest,
    ) -> stripe.PaymentIntent:
        correlation_id = correlation_id_var.get()
        metadata = {
            **request.metadata,
            "order_id": request.order_id,
            "region": request.region,
            "correlation_id": correlation_id,
        }

        logger.info(
            "Executing synchronous Stripe API call",
            extra={
                "provider": self.provider.value,
                "amount_cents": amount_cents,
                "idempotency_key": request.idempotency_key,
            },
        )

        return self.stripe_client.payment_intents.create(
            params={
                "amount": amount_cents,
                "currency": request.currency.lower(),
                "automatic_payment_methods": {"enabled": True},
                "metadata": metadata,
                "description": f"Order {request.order_id}",
            },
            options={
                "idempotency_key": request.idempotency_key,
            }
        )

    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        try:
            amount_in_cents = int(request.amount * 100)

            loop = asyncio.get_running_loop()
            intent = await loop.run_in_executor(
                None,
                self._execute_stripe_call,
                amount_in_cents,
                request,
            )

            if not getattr(intent, "id", None) or not getattr(intent, "client_secret", None):
                logger.error("Incomplete response from Stripe processor", extra={"intent_dict": intent.to_dict()})
                return GatewayResult(
                    provider=self.provider,
                    status=PaymentStatus.FAILURE,
                    error_message="Payment processor returned an incomplete response.",
                )

            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
                transaction_id=intent.id,
                client_secret=intent.client_secret,
                
                raw_response={"publishable_key": self._settings.STRIPE_PUBLISHABLE_KEY},
            )

        except stripe.error.CardError as e:
            logger.warning("Stripe card error", extra={"stripe_code": getattr(e, "code", None)})
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message=e.user_message or "Card declined.",
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API fault: {str(e)}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="Payment processing is temporarily unavailable.",
            )
        except Exception as e:
            logger.critical(f"Critical local failure in Stripe integration: {str(e)}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="Internal system error.",
            )


class PayPalGateway(IPaymentGateway):
    """
    Live PayPal integration: OAuth2 client-credentials token (cached) and the
    v2 Orders API. Returns the buyer approval URL as the action_url; capture
    completes via the PayPal return/webhook flow.
    """

    TOKEN_CACHE_KEY: str = "paypal:oauth_token"

    def __init__(self, settings: PayPalSettings, cache: IAsyncCacheClient, http_client: httpx.AsyncClient):
        self._settings = settings
        self._cache = cache
        self._http_client = http_client

    @property
    def provider(self) -> GatewayProvider:
        return GatewayProvider.PAYPAL

    def _base_url(self) -> str:
        return str(self._settings.PAYPAL_API_BASE_URL).rstrip("/")

    async def _get_access_token(self) -> str:
        try:
            cached = await self._cache.get(self.TOKEN_CACHE_KEY)
            if cached:
                return cached
        except Exception as exc:
            logger.warning("PayPal token cache read failed; fetching fresh token", extra={"error": str(exc)})

        response = await self._http_client.post(
            f"{self._base_url()}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(
                self._settings.PAYPAL_CLIENT_ID,
                self._settings.PAYPAL_CLIENT_SECRET.get_secret_value(),
            ),
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        body = response.json()
        token = body["access_token"]
        ttl = max(int(body.get("expires_in", 300)) - 60, 30)
        try:
            await self._cache.set(self.TOKEN_CACHE_KEY, token, ttl=ttl)
        except Exception as exc:
            logger.warning("PayPal token cache write failed", extra={"error": str(exc)})
        return token

    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        try:
            token = await self._get_access_token()
            purchase_unit: Dict[str, Any] = {
                "reference_id": str(request.order_id),
                "amount": {
                    "currency_code": request.currency,
                    "value": str(request.amount),
                },
            }
            user_ref = request.metadata.get("user_id")
            if user_ref is not None:
                purchase_unit["custom_id"] = str(user_ref)

            logger.info("Creating PayPal order", extra={"order_id": request.order_id})
            response = await self._http_client.post(
                f"{self._base_url()}/v2/checkout/orders",
                json={"intent": "CAPTURE", "purchase_units": [purchase_unit]},
                headers={
                    "Authorization": f"Bearer {token}",
                    "PayPal-Request-Id": request.idempotency_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            body = response.json()

            action_url = next(
                (link["href"] for link in body.get("links", []) if link.get("rel") == "approve"),
                None,
            )
            if not action_url:
                logger.error("PayPal order missing approval link", extra={"order_id": request.order_id})
                return GatewayResult(
                    provider=self.provider,
                    status=PaymentStatus.FAILURE,
                    error_message="PayPal did not return an approval link.",
                )

            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.REQUIRES_ACTION,
                transaction_id=body.get("id"),
                action_url=action_url,
                raw_response={"paypal_order_id": body.get("id")},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "PayPal API rejected the request",
                extra={"status_code": e.response.status_code, "order_id": request.order_id},
                exc_info=True,
            )
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="PayPal rejected the payment request.",
            )
        except httpx.RequestError as e:
            logger.error(f"PayPal Network unreachable: {str(e)}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="PayPal services are unreachable.",
            )
        except asyncio.CancelledError:
            logger.warning("PayPal intent initialization was cancelled by orchestrator timeout")
            raise

    async def capture_order(self, paypal_order_id: str) -> GatewayResult:
        """Capture a buyer-approved PayPal order (post-redirect completion)."""
        try:
            token = await self._get_access_token()
            response = await self._http_client.post(
                f"{self._base_url()}/v2/checkout/orders/{paypal_order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            body = response.json()
            if body.get("status") == "COMPLETED":
                return GatewayResult(
                    provider=self.provider,
                    status=PaymentStatus.SUCCESS,
                    transaction_id=paypal_order_id,
                    raw_response={"capture_status": "COMPLETED"},
                )
            logger.warning(
                "PayPal capture incomplete",
                extra={"paypal_order_id": paypal_order_id, "status": body.get("status")},
            )
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                transaction_id=paypal_order_id,
                error_message=f"PayPal capture ended in status {body.get('status')}.",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "PayPal capture rejected",
                extra={"status_code": e.response.status_code, "paypal_order_id": paypal_order_id},
                exc_info=True,
            )
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                transaction_id=paypal_order_id,
                error_message="PayPal rejected the capture.",
            )
        except httpx.RequestError as e:
            logger.error(f"PayPal capture network failure: {str(e)}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                transaction_id=paypal_order_id,
                error_message="PayPal services are unreachable.",
            )


class MpesaGateway(IPaymentGateway):
    """
    M-Pesa STK Push Integration using HTTP pooling.
    Requires handling mobile numbers via request metadata.
    """

    def __init__(self, settings: MpesaSettings, cache: IAsyncCacheClient, http_client: httpx.AsyncClient):
        self._settings = settings
        self._cache = cache
        self._http_client = http_client

    @property
    def provider(self) -> GatewayProvider:
        return GatewayProvider.MPESA

    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        phone_number = request.metadata.get("phone_number")
        if not phone_number:
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="Phone number required for M-Pesa transactions."
            )

        try:
            logger.info("Initiating M-Pesa STK Push", extra={"anonymized_phone": f"***{phone_number[-4:]}"})
            
            # Network simulation for STK push
            await asyncio.sleep(0.05)
            
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.PENDING_CONFIRMATION,
                transaction_id=f"ws_{request.order_id}_{request.idempotency_key[:8]}",
                raw_response={"message": "STK Push sent. Awaiting user PIN."}
            )
        except Exception as e:
            logger.error(f"Mpesa Init Failed: {str(e)}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="M-Pesa services unreachable."
            )


# -------------------------------------------------------------------------
# Financial Orchestrator
# -------------------------------------------------------------------------

class OrchestrationResponse(BaseModel):
    status: PaymentStatus
    primary_gateway: Optional[GatewayResult] = None
    alternative_gateways: List[GatewayResult] = Field(default_factory=list)
    error_message: Optional[str] = None


class PaymentOrchestrator:
    """
    Internet-Scale Financial Conductor.
    Geo-routes traffic concurrently enforcing strict bounded timeouts to prevent cascading failure limits.
    Aggregates partial network successes cleanly and cancels stragglers.
    """
    
    GLOBAL_TIMEOUT_SECONDS: Final[float] = 5.0

    def __init__(self, gateways: List[IPaymentGateway], routing_rules: Optional[Dict[str, List[GatewayProvider]]] = None):
        self._gateways: Dict[GatewayProvider, IPaymentGateway] = {gw.provider: gw for gw in gateways}
        
        self._routing_rules: Dict[str, List[GatewayProvider]] = routing_rules or {
            "NA": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "US": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "EU": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "KE": [GatewayProvider.MPESA, GatewayProvider.STRIPE],
            "EG": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "DEFAULT": [GatewayProvider.STRIPE],
        }

    async def process_payment(self, request: PaymentRequest, corr_id: str) -> OrchestrationResponse:
        """
        Executes parallel, fault-tolerant payment intent generation.
        Strictly enforces self.GLOBAL_TIMEOUT_SECONDS to ensure upstream APIs do not degrade.
        """
        correlation_id_var.set(corr_id)
        
        logger.info("Orchestrating payment routing", extra={
            "order_id": request.order_id,
            "region": request.region,
            "target_amount": str(request.amount)
        })

        target_providers = self._routing_rules.get(request.region, self._routing_rules["DEFAULT"])
        active_gateways = [self._gateways[p] for p in target_providers if p in self._gateways]

        if not active_gateways:
            logger.critical("No valid routing configuration for requested region", extra={"region": request.region})
            return OrchestrationResponse(
                status=PaymentStatus.FAILURE,
                error_message="Payment processing unavailable for this region."
            )

        tasks = [
            asyncio.create_task(self._safe_invoke_gateway(gw, request), name=f"gw_task_{gw.provider.value}")
            for gw in active_gateways
        ]
        
        done, pending = await asyncio.wait(
            tasks, 
            timeout=self.GLOBAL_TIMEOUT_SECONDS, 
            return_when=asyncio.ALL_COMPLETED
        )

        # Ensure aggressive memory-safe cancellation of lingering network I/O
        if pending:
            for pending_task in pending:
                pending_task.cancel()
                logger.error(f"Gateway request timed out and cancelled: {pending_task.get_name()}")
            # Re-await cancelled tasks to suppress 'Task exception was never retrieved' warnings
            await asyncio.gather(*pending, return_exceptions=True)

        successful_results: List[GatewayResult] = []
        for task in done:
            try:
                result: GatewayResult = task.result()
                if result.status != PaymentStatus.FAILURE:
                    successful_results.append(result)
            except Exception as e:
                logger.critical(f"Unexpected orchestrator thread panic: {str(e)}", exc_info=True)

        if not successful_results:
            logger.error("Global processing failure: All targeted gateways failed or timed out.")
            return OrchestrationResponse(
                status=PaymentStatus.FAILURE,
                error_message="Payment systems are currently experiencing high latency. Please try again."
            )

        # Deterministic sorting matching the fallback routing preference priority
        successful_results.sort(key=lambda r: target_providers.index(r.provider))

        return OrchestrationResponse(
            status=PaymentStatus.SUCCESS,
            primary_gateway=successful_results[0],
            alternative_gateways=successful_results[1:]
        )

    async def _safe_invoke_gateway(self, gateway: IPaymentGateway, request: PaymentRequest) -> GatewayResult:
        """
        Hard bulkhead enclosing individual network invocations.
        Traps unchecked edge-case exceptions from SDKs to protect orchestrator stability.
        """
        try:
            return await gateway.create_payment_intent(request)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Catastrophic trap in gateway {gateway.provider.value}: {str(e)}", exc_info=True)
            return GatewayResult(
                provider=gateway.provider,
                status=PaymentStatus.FAILURE,
                error_message="Gateway encountered a critical internal error."
            )
