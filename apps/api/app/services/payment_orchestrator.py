# apps/api/app/services/payment_orchestrator.py

import stripe.error
import httpx
import logging
from app.core.config import (
    StripeSettings,
    PayPalSettings,
    MpesaSettings,
    get_stripe_settings,
    get_paypal_settings,
    get_mpesa_settings,
)
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal, InvalidOperation
from app.services.cache_service import IAsyncCacheClient, get_cache_client
import base64
from datetime import datetime
import time
from fastapi import Depends

logger = logging.getLogger(__name__)


class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pass
    
    @property
    @abstractmethod
    def provider_key(self) -> str:
        pass


class StripeGateway(PaymentGateway):
    def __init__(self, settings: StripeSettings):
        self.settings = settings

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
        try:
            amount_in_cents = int(amount.quantize(Decimal("0.01")) * 100)
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency.lower(),
                automatic_payment_methods={"enabled": True},
                metadata=metadata or {"region": region},
                api_key=self.settings.STRIPE_SECRET_KEY
            )
            return {
                "status": "requires_payment_method",
                "provider": "stripe",
                "paymentId": intent.id,
                "clientSecret": intent.client_secret,
            }
        except Exception as e:
            logger.error(f"Stripe creation failed: {e}")
            raise

class PayPalGateway(PaymentGateway):
    def __init__(self, settings: PayPalSettings, cache: IAsyncCacheClient):
        self.settings = settings
        self.cache = cache

    @property
    def provider_key(self) -> str:
        return "paypal"
    
    async def _get_access_token(self) -> Optional[str]:
        pass

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {"status": "requires_payment_method", "provider": "paypal", "approval_url": "..."}

class MpesaGateway(PaymentGateway):
    def __init__(self, settings: MpesaSettings, cache: IAsyncCacheClient):
        self.settings = settings
        self.cache = cache

    @property
    def provider_key(self) -> str:
        return "mpesa"

    async def _get_access_token(self) -> Optional[str]:
        pass
    
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {"status": "pending_confirmation", "provider": "mpesa", "checkoutRequestId": "..."}


class PaymentOrchestrator:

    def __init__(
        self,
        stripe_gateway: PaymentGateway,
        paypal_gateway: PaymentGateway,
        mpesa_gateway: PaymentGateway,
    ):
        self._gateways: Dict[str, PaymentGateway] = {
            "stripe": stripe_gateway,
            "paypal": paypal_gateway,
            "mpesa": mpesa_gateway,
        }
        self._routing_rules = {
            "NA": ["stripe", "paypal"],
            "US": ["stripe", "paypal"],
            "EU": ["stripe", "paypal"],
            "KE": ["mpesa", "stripe"],
            "DEFAULT": ["stripe"],
        }

    async def process_payment(
        self,
        amount: float,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            decimal_amount = Decimal(str(amount))
        except InvalidOperation:
            return {"status": "failure", "error": "Invalid amount format."}

        gateways_for_region = self._routing_rules.get(
            region.upper(), self._routing_rules["DEFAULT"]
        )
        
        available_gateways: List[Dict[str, Any]] = []

        for provider_key in gateways_for_region:
            gateway = self._gateways.get(provider_key)
            if gateway:
                try:
                    result = await gateway.create_payment(
                        decimal_amount, currency, region, metadata
                    )
                    available_gateways.append(result)
                except Exception as e:
                    logger.error(
                        f"Gateway {provider_key} failed to initialize: {e}."
                    )
        
        if not available_gateways:
            return {"status": "failure", "error": "All payment gateways failed."}

        return {"status": "success", "available_gateways": available_gateways}
