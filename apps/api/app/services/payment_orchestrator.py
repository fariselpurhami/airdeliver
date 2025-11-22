# apps/api/app/services/payment_orchestrator.py

import stripe
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal, InvalidOperation
from app.core.config import (
    StripeSettings,
    PayPalSettings,
    MpesaSettings,
)
from app.services.cache_service import IAsyncCacheClient

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
        stripe.api_key = self.settings.STRIPE_SECRET_KEY

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
            
            loop = asyncio.get_running_loop()
            intent = await loop.run_in_executor(
                None,
                lambda: stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency=currency.lower(),
                    automatic_payment_methods={"enabled": True},
                    metadata=metadata or {"region": region},
                )
            )
            
            return {
                "status": "requires_payment_method",
                "provider": "stripe",
                "paymentId": intent.id,
                "clientSecret": intent.client_secret,
                "publishableKey": self.settings.STRIPE_PUBLISHABLE_KEY 
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {e}")
            raise Exception(f"Stripe Gateway Error: {e.user_message or str(e)}")
        except Exception as e:
            logger.critical(f"Stripe System error: {e}")
            raise

class PayPalGateway(PaymentGateway):
    def __init__(self, settings: PayPalSettings, cache: IAsyncCacheClient):
        self.settings = settings
        self.cache = cache

    @property
    def provider_key(self) -> str:
        return "paypal"

    async def create_payment(self, amount: Decimal, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        
        logger.info(f"PayPal: Creating order for {amount} {currency}")
        
        await asyncio.sleep(0.2)
        
        return {
            "status": "requires_approval",
            "provider": "paypal",
            "paymentId": f"PAY-{metadata.get('order_id', 'UNKNOWN')}",
            "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=...",
        }

class MpesaGateway(PaymentGateway):
    def __init__(self, settings: MpesaSettings, cache: IAsyncCacheClient):
        self.settings = settings
        self.cache = cache

    @property
    def provider_key(self) -> str:
        return "mpesa"
    
    async def create_payment(self, amount: Decimal, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

        logger.info(f"M-Pesa: Triggering STK Push to {metadata.get('phone_number')}")
        await asyncio.sleep(0.1)
        
        return {
            "status": "pending_confirmation",
            "provider": "mpesa",
            "checkoutRequestId": f"ws_{metadata.get('order_id')}",
            "message": "STK Push sent to phone."
        }


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

        gateways_to_try = self._routing_rules.get(
            region.upper(), self._routing_rules["DEFAULT"]
        )
        
        available_options: List[Dict[str, Any]] = []
        errors = []
      
        tasks = []
        for provider_key in gateways_to_try:
            gateway = self._gateways.get(provider_key)
            if gateway:
                tasks.append(self._safe_create_payment(gateway, decimal_amount, currency, region, metadata))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, dict) and "provider" in res:
                available_options.append(res)
            elif isinstance(res, Exception):
                errors.append(str(res))
        
        if not available_options:
            logger.error(f"All payment gateways failed: {errors}")
            return {"status": "failure", "error": "Payment processing unavailable at this moment."}

        return {
            "status": "success",
            "available_gateways": available_options,
            "primary_gateway": available_options[0]["provider"]
        }

    async def _safe_create_payment(self, gateway, amount, currency, region, metadata):
        """Safety wrapper to prevent one gateway failure from blocking others"""
        try:
            return await gateway.create_payment(amount, currency, region, metadata)
        except Exception as e:
            logger.warning(f"Gateway {gateway.provider_key} failed init: {e}")
            raise e
