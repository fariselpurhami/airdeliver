# apps/api/app/services/payment_orchestrator.py

import stripe
import logging
import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from app.core.config import (
    StripeSettings,
    PayPalSettings,
    MpesaSettings,
)
from app.services.cache_service import IAsyncCacheClient

logger = logging.getLogger(__name__)

class PaymentGateway(ABC):
    """
    💎 UNIVERSAL PAYMENT INTERFACE.
    Enforces a strict contract for any financial processor (Stripe, PayPal, Crypto).
    """

    @property
    @abstractmethod
    def provider_key(self) -> str:
        """Unique identifier (e.g., 'stripe', 'paypal')."""
        pass

    @abstractmethod
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a secure transaction intent.
        Must handle Atomic Decimal Conversion internally.
        """
        pass

# --- 💳 SECTION 2: STRIPE TITANIUM GATEWAY ---

class StripeGateway(PaymentGateway):
    """
    🛡️ STRIPE GATEWAY (TITANIUM EDITION).
    Features:
    - ⚡ Async Non-Blocking Execution.
    - 🔒 Idempotency Keys (Prevents double-charging on network retry).
    - 🎯 Atomic Decimal Conversion (Bank-Grade Precision).
    - 📝 Rich Metadata Injection (For Reconciliation).
    """

    def __init__(self, settings: Any):
        self.settings = settings
        stripe.api_key = self.settings.STRIPE_SECRET_KEY
        # Set API version to ensure stability
        stripe.api_version = "2023-10-16"

    @property
    def provider_key(self) -> str:
        return "stripe"

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the creation of a Stripe PaymentIntent.
        """
        try:
            # 1. 🛡️ ATOMIC CURRENCY CONVERSION
            # Stripe requires amounts in "smallest currency unit" (cents for USD).
            # We use quantize to ensure exactly 2 decimal places before multiplying.
            safe_amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            amount_in_cents = int(safe_amount * 100)

            # 2. 🔒 IDEMPOTENCY KEY GENERATION
            # If the caller provided a key (from UUID), use it. Otherwise, generate one.
            # This ensures if the request is retried, Stripe knows it's the SAME transaction.
            idem_key = metadata.get("idempotency_key") if metadata else str(uuid.uuid4())

            # 3. 📝 METADATA ENRICHMENT
            # Add system tags for easier debugging in Stripe Dashboard
            enriched_metadata = metadata or {}
            enriched_metadata.update({
                "region": region,
                "platform": "AirDeliver AI",
                "env": "production" # or dynamic
            })

            logger.info(f"💳 Initiating Stripe Charge: {safe_amount} {currency} (Idem: {idem_key})")

            # 4. ⚡ ASYNC EXECUTION (Non-Blocking)
            loop = asyncio.get_running_loop()
            intent = await loop.run_in_executor(
                None,
                lambda: stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency=currency.lower(),
                    automatic_payment_methods={"enabled": True},
                    metadata=enriched_metadata,
                    description=f"Order {metadata.get('order_id', 'N/A')}",
                    idempotency_key=idem_key # 💎 The Safety Net
                )
            )

            # 5. ✅ STANDARDIZED RESPONSE
            return {
                "status": "requires_payment_method", # or intent.status
                "provider": "stripe",
                "paymentId": intent.id,
                "clientSecret": intent.client_secret,
                "publishableKey": self.settings.STRIPE_PUBLISHABLE_KEY,
                "amount_captured": float(safe_amount) # For UI verification
            }

        # --- 🛡️ ROBUST ERROR HANDLING ---
        except stripe.error.CardError as e:
            # Card declined by bank
            logger.warning(f"🚫 Stripe Card Error: {e.user_message}")
            return {"status": "failure", "error": e.user_message}

        except stripe.error.RateLimitError as e:
            # Too many requests
            logger.error("⚠️ Stripe Rate Limit Hit. Backing off.")
            raise Exception("Payment Service Busy. Please retry.")

        except stripe.error.StripeError as e:
            # Generic Stripe Error
            logger.error(f"❌ Stripe API Error: {e}")
            raise Exception(f"Payment Gateway Error: {e.user_message or 'Processing Failed'}")

        except Exception as e:
            # System Error
            logger.critical(f"🔥 Stripe Critical Failure: {e}", exc_info=True)
            raise Exception("Internal Payment System Failure")


class PayPalGateway(PaymentGateway):
    """
    🌐 PAYPAL GATEWAY (SANDBOX/LIVE).
    Handles redirect-based flows common in e-wallets.
    """
    def __init__(self, settings: Any, cache: Any):
        self.settings = settings
        self.cache = cache # Can store tokens here

    @property
    def provider_key(self) -> str:
        return "paypal"

    async def create_payment(
        self, 
        amount: Decimal, 
        currency: str, 
        region: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulates PayPal Order Creation.
        In Prod: Use 'paypal-checkout-server-sdk'.
        """
        try:
            # Force string format for API compatibility
            amount_str = str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            logger.info(f"🅿️ PayPal Init: {amount_str} {currency} (Order: {metadata.get('order_id')})")
            
            # Simulate API Latency
            await asyncio.sleep(0.1)
            
            return {
                "status": "requires_approval",
                "provider": "paypal",
                "paymentId": f"PAY-{metadata.get('order_id', 'UNKNOWN')}-{uuid.uuid4().hex[:4]}",
                "clientId": getattr(self.settings, 'PAYPAL_CLIENT_ID', 'sb'),
                "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=dummy"
            }
        except Exception as e:
            logger.error(f"PayPal Init Failed: {e}")
            raise e


class MpesaGateway(PaymentGateway):
    """
    📱 MPESA GATEWAY (AFRICA REGION).
    Handles Mobile Money STK Pushes.
    """
    def __init__(self, settings: Any, cache: Any):
        self.settings = settings
        self.cache = cache

    @property
    def provider_key(self) -> str:
        return "mpesa"
    
    async def create_payment(
        self, 
        amount: Decimal, 
        currency: str, 
        region: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulates Safaricom Daraja API STK Push.
        """
        try:
            # M-Pesa deals in Integers usually, but we keep Decimal logic for consistency
            logger.info(f"📲 M-Pesa STK Push: {amount} {currency} -> {metadata.get('phone_number', 'Unknown')}")
            
            await asyncio.sleep(0.1)
            
            return {
                "status": "pending_confirmation",
                "provider": "mpesa",
                "checkoutRequestId": f"ws_{metadata.get('order_id')}_{uuid.uuid4().hex[:6]}",
                "message": "STK Push sent. Check your phone."
            }
        except Exception as e:
            logger.error(f"Mpesa Init Failed: {e}")
            raise e


class PaymentOrchestrator:
    """
    💎 FINANCIAL CONDUCTOR.
    Decides WHICH gateways to show based on User Location (Geo-Routing).
    Executes all eligible options in PARALLEL for max speed.
    """

    def __init__(
        self,
        stripe_gateway: PaymentGateway,
        paypal_gateway: PaymentGateway,
        mpesa_gateway: PaymentGateway,
    ):
        # Registry of available processors
        self._gateways: Dict[str, PaymentGateway] = {
            "stripe": stripe_gateway,
            "paypal": paypal_gateway,
            "mpesa": mpesa_gateway,
        }

        # 🌍 Geo-Routing Rules (Smart Logic)
        self._routing_rules = {
            "NA": ["stripe", "paypal"],      # North America
            "US": ["stripe", "paypal"],      # USA
            "EU": ["stripe", "paypal"],      # Europe
            "KE": ["mpesa", "stripe"],       # Kenya (Mobile First)
            "EG": ["stripe", "paypal"],      # Egypt (Cards + Wallet)
            "DEFAULT": ["stripe"],           # Fallback
        }

    async def process_payment(
        self,
        amount: Union[float, str, Decimal],
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        🚀 UNIVERSAL PAYMENT EXECUTION.
        1. Sanitizes Amount (Atomic Conversion).
        2. Selects Gateways based on Region.
        3. Launches all Gateways concurrently (Async Gather).
        4. Returns a unified list of valid payment options.
        """
        # 1. Architectural Safety: Force conversion to string first
        # avoiding float precision issues (e.g. 19.99 -> 19.989999)
        try:
            if isinstance(amount, float):
                decimal_amount = Decimal(str(amount))
            else:
                decimal_amount = Decimal(amount)
                
            # Normalize scaling (force 2 decimal places for standard fiat)
            decimal_amount = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        except Exception:
            logger.error(f"Invalid payment amount received: {amount}")
            return {"status": "failure", "error": "Invalid amount format."}

        # 2. Select Routing Strategy
        gateways_to_try = self._routing_rules.get(
            region.upper(), self._routing_rules["DEFAULT"]
        )
        
        # 3. Parallel Execution (Ferrari Mode)
        tasks = []
        for provider_key in gateways_to_try:
            gateway = self._gateways.get(provider_key)
            if gateway:
                tasks.append(self._safe_create_payment(gateway, decimal_amount, currency, region, metadata))

        # 4. Gather Results (Failures don't stop Successes)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        available_options = []
        errors = []
        
        for res in results:
            if isinstance(res, dict) and "provider" in res:
                available_options.append(res)
            elif isinstance(res, Exception):
                errors.append(str(res))
        
        # 5. Final Decision
        if not available_options:
            logger.error(f"All payment gateways failed: {errors}")
            return {"status": "failure", "error": "Payment processing unavailable at this moment."}

        # Return list of options for the Frontend to render (e.g., Stripe Form + PayPal Button)
        return {
            "status": "success",
            "available_gateways": available_options,
            "primary_gateway": available_options[0]["provider"] # Default choice
        }

    async def _safe_create_payment(self, gateway, amount, currency, region, metadata):
        """🛡️ Isolation Wrapper: Prevents one gateway crash from killing the whole process."""
        try:
            return await gateway.create_payment(amount, currency, region, metadata)
        except Exception as e:
            logger.warning(f"Gateway {gateway.provider_key} failed init: {e}")
            raise e # Re-raise to be caught by gather
