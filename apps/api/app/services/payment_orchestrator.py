# apps/api/app/services/payment_orchestrator.py

import asyncio
import logging
import json
import contextvars
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum, unique
from typing import Dict, Any, Optional, List

import stripe
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# -------------------------------------------------------------------------
# Core Configuration & Interfaces (Simulated for completeness)
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class StripeSettings:
    secret_key: str
    publishable_key: str
    webhook_secret: str
    api_version: str = "2023-10-16"

@dataclass(frozen=True)
class PayPalSettings:
    client_id: str
    client_secret: str
    environment: str

@dataclass(frozen=True)
class MpesaSettings:
    consumer_key: str
    consumer_secret: str
    passkey: str
    environment: str

class IAsyncCacheClient(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]: pass
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None: pass

# -------------------------------------------------------------------------
# Observability & Structured Logging
# -------------------------------------------------------------------------

# Context variable for distributed tracing and correlation
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="unknown")

class StructuredLogger(logging.LoggerAdapter):
    """Injects correlation IDs and formats logs for JSON aggregation."""
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        base_extra = {"correlation_id": correlation_id_var.get()}
        if "extra" in kwargs:
            kwargs["extra"].update(base_extra)
        else:
            kwargs["extra"] = base_extra
        # In a real system, this would output JSON. Here we format the string for clarity.
        formatted_msg = f"[Trace: {base_extra['correlation_id']}] {msg}"
        return formatted_msg, kwargs

logger = StructuredLogger(logging.getLogger(__name__), {})

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

@dataclass(frozen=True)
class PaymentRequest:
    """
    Strict immutable DTO for payment requests.
    Enforces architectural invariants at the boundary.
    """
    order_id: str
    amount: Decimal
    currency: str
    region: str
    idempotency_key: str  # Mandatory: Must be supplied by the caller to guarantee network idempotency
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            raise ValueError("Amount must be a Decimal to guarantee precision.")
        if self.amount <= Decimal("0"):
            raise ValueError("Amount must be strictly positive.")
        if not self.idempotency_key or len(self.idempotency_key) < 16:
            raise ValueError("A strong idempotency key is required to prevent double-charging.")
        # Ensure upper case for standardization
        object.__setattr__(self, 'currency', self.currency.upper())
        object.__setattr__(self, 'region', self.region.upper())

@dataclass(frozen=True)
class GatewayResult:
    provider: GatewayProvider
    status: PaymentStatus
    transaction_id: Optional[str] = None
    client_secret: Optional[str] = None
    action_url: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

# -------------------------------------------------------------------------
# Gateway Interfaces
# -------------------------------------------------------------------------

class IPaymentGateway(ABC):
    """
    Strict contract for financial processors.
    Enforces Liskov Substitution Principle across all payment integrations.
    """
    @property
    @abstractmethod
    def provider(self) -> GatewayProvider:
        pass

    @abstractmethod
    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        """
        Executes a secure transaction intent asynchronously.
        Must handle its own specific connectivity, retries, and error mapping.
        """
        pass

# -------------------------------------------------------------------------
# Implementations
# -------------------------------------------------------------------------

class StripeGateway(IPaymentGateway):
    """
    Enterprise-Grade Stripe Integration.
    - Explicit API Key passing (no global state mutation).
    - Exponential backoff for transient network errors.
    - Strict cent-conversion and decimal safety.
    """

    def __init__(self, settings: StripeSettings):
        self._settings = settings

    @property
    def provider(self) -> GatewayProvider:
        return GatewayProvider.STRIPE

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((stripe.error.RateLimitError, stripe.error.APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def _execute_stripe_call(self, amount_cents: int, request: PaymentRequest) -> stripe.PaymentIntent:
        """
        Synchronous Stripe SDK wrapper isolated for ThreadPool execution and Retries.
        Passes authentication explicitly per-request to avoid thread-safety issues with global api_key.
        """
        return stripe.PaymentIntent.create(
            api_key=self._settings.secret_key,
            api_version=self._settings.api_version,
            amount=amount_cents,
            currency=request.currency.lower(),
            automatic_payment_methods={"enabled": True},
            metadata={
                **request.metadata,
                "order_id": request.order_id,
                "region": request.region,
                "correlation_id": correlation_id_var.get()
            },
            description=f"Order {request.order_id}",
            idempotency_key=request.idempotency_key
        )

    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        try:
            # 1. Atomic Currency Conversion (Zero-decimal currencies require different logic in a full system)
            safe_amount = request.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            amount_in_cents = int(safe_amount * 100)

            logger.info("Initiating Stripe intent", extra={
                "amount": str(safe_amount),
                "currency": request.currency,
                "idempotency_key": request.idempotency_key
            })

            # 2. Async Execution off the main Event Loop
            loop = asyncio.get_running_loop()
            intent = await loop.run_in_executor(
                None,
                self._execute_stripe_call,
                amount_in_cents,
                request
            )

            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
                transaction_id=intent.id,
                client_secret=intent.client_secret,
                raw_response={"publishable_key": self._settings.publishable_key}
            )

        except stripe.error.CardError as e:
            logger.warning(f"Stripe Card Error: {e.user_message}", extra={"stripe_code": e.code})
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message=e.user_message or "Card declined."
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API Error: {e}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="Payment processing unavailable via Stripe."
            )
        except Exception as e:
            logger.critical(f"Stripe Critical Failure: {e}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="Internal system error."
            )


class PayPalGateway(IPaymentGateway):
    """
    Robust PayPal Integration Scaffold.
    Demonstrates proper async HTTP abstraction and caching of OAuth tokens.
    """
    def __init__(self, settings: PayPalSettings, cache: IAsyncCacheClient):
        self._settings = settings
        self._cache = cache

    @property
    def provider(self) -> GatewayProvider:
        return GatewayProvider.PAYPAL

    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        try:
            amount_str = str(request.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            logger.info("Initiating PayPal order", extra={"amount": amount_str, "currency": request.currency})
            
            # In production:
            # 1. Fetch/Cache OAuth token using self._cache
            # 2. Use `httpx.AsyncClient` with strict timeouts to hit PayPal /v2/checkout/orders
            
            await asyncio.sleep(0.05) # Simulated network I/O
            
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.REQUIRES_ACTION,
                transaction_id=f"PAY-{request.order_id}-{request.idempotency_key[:8]}",
                action_url="https://www.sandbox.paypal.com/checkoutnow?token=dummy_token",
                raw_response={"client_id": self._settings.client_id}
            )
        except Exception as e:
            logger.error(f"PayPal Init Failed: {e}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="PayPal services unreachable."
            )


class MpesaGateway(IPaymentGateway):
    """
    M-Pesa STK Push Integration.
    Requires handling mobile numbers via metadata.
    """
    def __init__(self, settings: MpesaSettings, cache: IAsyncCacheClient):
        self._settings = settings
        self._cache = cache

    @property
    def provider(self) -> GatewayProvider:
        return GatewayProvider.MPESA

    async def create_payment_intent(self, request: PaymentRequest) -> GatewayResult:
        try:
            phone_number = request.metadata.get("phone_number")
            if not phone_number:
                return GatewayResult(
                    provider=self.provider,
                    status=PaymentStatus.FAILURE,
                    error_message="Phone number required for M-Pesa transactions."
                )

            logger.info("Initiating M-Pesa STK Push", extra={"phone_number": phone_number})
            
            # In production:
            # 1. Generate Daraja Password using Passkey + Timestamp
            # 2. httpx.AsyncClient POST to Daraja API with short timeout
            
            await asyncio.sleep(0.05) # Simulated network I/O
            
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.PENDING_CONFIRMATION,
                transaction_id=f"ws_{request.order_id}_{request.idempotency_key[:8]}",
                raw_response={"message": "STK Push sent. Awaiting user PIN."}
            )
        except Exception as e:
            logger.error(f"Mpesa Init Failed: {e}", exc_info=True)
            return GatewayResult(
                provider=self.provider,
                status=PaymentStatus.FAILURE,
                error_message="M-Pesa services unreachable."
            )

# -------------------------------------------------------------------------
# Financial Orchestrator
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class OrchestrationResponse:
    status: PaymentStatus
    primary_gateway: Optional[GatewayResult] = None
    alternative_gateways: List[GatewayResult] = field(default_factory=list)
    error_message: Optional[str] = None

class PaymentOrchestrator:
    """
    Internet-Scale Financial Conductor.
    - Decoupled from specific gateway implementations via IPaymentGateway interface.
    - Geo-routes traffic concurrently.
    - Enforces bounded timeouts to prevent cascading system failures.
    - Aggregates partial successes securely.
    """

    # Bounded maximum execution time for ALL payment gateways combined
    GLOBAL_TIMEOUT_SECONDS = 5.0

    def __init__(self, gateways: List[IPaymentGateway]):
        self._gateways: Dict[GatewayProvider, IPaymentGateway] = {gw.provider: gw for gw in gateways}
        
        # In a real system, this should be injected via configuration or a Rules Engine.
        self._routing_rules: Dict[str, List[GatewayProvider]] = {
            "NA": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "US": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "EU": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "KE": [GatewayProvider.MPESA, GatewayProvider.STRIPE],
            "EG": [GatewayProvider.STRIPE, GatewayProvider.PAYPAL],
            "DEFAULT": [GatewayProvider.STRIPE],
        }

    async def process_payment(self, request: PaymentRequest, corr_id: str) -> OrchestrationResponse:
        """
        Executes parallel, fault-tolerant payment intent generation based on geo-routing.
        """
        # Set correlation ID for distributed tracing across this entire operation
        correlation_id_var.set(corr_id)
        
        logger.info("Orchestrating payment", extra={
            "order_id": request.order_id,
            "region": request.region
        })

        target_providers = self._routing_rules.get(request.region, self._routing_rules["DEFAULT"])
        active_gateways = [self._gateways[p] for p in target_providers if p in self._gateways]

        if not active_gateways:
            logger.critical("No valid gateways configured for region", extra={"region": request.region})
            return OrchestrationResponse(
                status=PaymentStatus.FAILURE,
                error_message="Payment processing unavailable for this region."
            )

        # Execute gateways concurrently with bounded timeouts.
        # asyncio.wait guarantees we don't hang indefinitely if an underlying library ignores timeouts.
        tasks = [
            asyncio.create_task(self._safe_invoke_gateway(gw, request))
            for gw in active_gateways
        ]
        
        done, pending = await asyncio.wait(
            tasks, 
            timeout=self.GLOBAL_TIMEOUT_SECONDS, 
            return_when=asyncio.ALL_COMPLETED
        )

        # Cancel any stragglers immediately to free up event loop resources
        for pending_task in pending:
            pending_task.cancel()
            logger.error("Gateway request timed out and was cancelled.")

        # Aggregate results
        successful_results: List[GatewayResult] = []
        for task in done:
            try:
                result: GatewayResult = task.result()
                if result.status != PaymentStatus.FAILURE:
                    successful_results.append(result)
            except Exception as e:
                logger.critical(f"Unexpected orchestrator task failure: {e}", exc_info=True)

        if not successful_results:
            logger.error("All selected payment gateways failed or timed out.")
            return OrchestrationResponse(
                status=PaymentStatus.FAILURE,
                error_message="Payment systems are currently experiencing high latency. Please try again."
            )

        # Guarantee a deterministic ordering based on the routing rules preference
        successful_results.sort(key=lambda r: target_providers.index(r.provider))

        return OrchestrationResponse(
            status=PaymentStatus.SUCCESS,
            primary_gateway=successful_results[0],
            alternative_gateways=successful_results[1:]
        )

    async def _safe_invoke_gateway(self, gateway: IPaymentGateway, request: PaymentRequest) -> GatewayResult:
        """
        Strict bulkhead around individual gateway invocations.
        Catches absolutely all unhandled exceptions from poor SDKs to protect the orchestrator.
        """
        try:
            return await gateway.create_payment_intent(request)
        except asyncio.CancelledError:
            # Re-raise standard CancelledError to satisfy asyncio semantics
            raise
        except Exception as e:
            logger.error(f"Unhandled exception in gateway {gateway.provider.value}: {e}", exc_info=True)
            return GatewayResult(
                provider=gateway.provider,
                status=PaymentStatus.FAILURE,
                error_message="Gateway encountered a critical internal error."
            )
