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
from typing import Dict, Any, Optional
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

    @abstractmethod
    async def get_status(self, payment_id: str) -> str:
        pass


class NoOpGateway(PaymentGateway):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        logger.warning(
            f"Payment provider {self.provider_name} initialized as NoOp. "
            "It is not configured."
        )

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.error(
            f"Payment attempt failed: {self.provider_name} gateway is not configured."
        )
        raise Exception(f"{self.provider_name} payment gateway is not configured.")

    async def get_status(self, payment_id: str) -> str:
        return "not_configured"


class StripeGateway(PaymentGateway):

    def __init__(self, settings: StripeSettings):
        self.settings = settings

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(
            f"Creating Payment Intent via Stripe for region {region} and amount {amount} {currency}."
        )
        try:
            amount_in_cents = int(amount.quantize(Decimal("0.01")) * 100)

            intent_params = {
                "amount": amount_in_cents,
                "currency": currency.lower(),
                "automatic_payment_methods": {"enabled": True},
                "metadata": metadata or {"region": region},
            }

            intent = stripe.PaymentIntent.create(
                **intent_params,
                api_key=self.settings.STRIPE_SECRET_KEY
            )

            logger.info(f"Stripe PaymentIntent {intent.id} created successfully.")
            return {
                "status": "requires_payment_method",
                "provider": "stripe",
                "paymentId": intent.id,
                "clientSecret": intent.client_secret,
            }

        except stripe.error.CardError as e:
            logger.warning(f"Stripe CardError for region {region}: {e}")
            raise
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API Error for region {region}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Stripe payment creation: {e}")
            raise

    async def get_status(self, payment_id: str) -> str:
        try:
            intent = stripe.PaymentIntent.retrieve(
                payment_id,
                api_key=self.settings.STRIPE_SECRET_KEY
            )
            return intent.status
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe status for {payment_id}: {e}")
            return "error"


class PayPalGateway(PaymentGateway):

    TOKEN_CACHE_KEY = "paypal_access_token"

    def __init__(self, settings: PayPalSettings, cache: IAsyncCacheClient):
        self.settings = settings
        self.cache = cache

    async def _get_access_token(self) -> Optional[str]:
        token = await self.cache.get(self.TOKEN_CACHE_KEY)
        if token:
            return token

        auth = base64.b64encode(
            f"{self.settings.PAYPAL_CLIENT_ID}:{self.settings.PAYPAL_CLIENT_SECRET}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.settings.PAYPAL_API_BASE_URL}/v1/oauth2/token",
                    headers=headers,
                    data="grant_type=client_credentials",
                )
                response.raise_for_status()
                data = response.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600) - 300

                await self.cache.set(self.TOKEN_CACHE_KEY, token, ttl=expires_in)
                return token
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get PayPal token: {e.response.text}")
                return None

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        token = await self._get_access_token()
        if not token:
            raise Exception("Could not authenticate with PayPal")

        order_id = metadata.get("order_id", "UNKNOWN")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency.upper(),
                        "value": str(amount.quantize(Decimal("0.01"))),
                    },
                    "reference_id": f"ORDER-{order_id}",
                    "description": f"Airdeliver Order #{order_id}",
                }
            ],
            "application_context": {
                "return_url": f"{metadata.get('return_url_base', 'https://airdeliver.com')}/paypal/success?order_id={order_id}",
                "cancel_url": f"{metadata.get('return_url_base', 'https://airdeliver.com')}/paypal/cancel?order_id={order_id}",
                "brand_name": "Airdeliver",
                "shipping_preference": "NO_SHIPPING",
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.PAYPAL_API_BASE_URL}/v2/checkout/orders",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "requires_payment_method",
                "provider": "paypal",
                "paymentId": data["id"],
                "approval_url": next(
                    link["href"] for link in data["links"] if link["rel"] == "approve"
                ),
            }

    async def get_status(self, payment_id: str) -> str:
        raise NotImplementedError("PayPalGateway.get_status not implemented")


class MpesaGateway(PaymentGateway):

    TOKEN_CACHE_KEY = "mpesa_access_token"

    def __init__(self, settings: MpesaSettings, cache: IAsyncCacheClient):
        self.settings = settings
        self.cache = cache

    async def _get_access_token(self) -> Optional[str]:
        token = await self.cache.get(self.TOKEN_CACHE_KEY)
        if token:
            return token

        auth = base64.b64encode(
            f"{self.settings.MPESA_CONSUMER_KEY}:{self.settings.MPESA_CONSUMER_SECRET}".encode()
        ).decode()
        headers = {"Authorization": f"Basic {auth}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.settings.MPESA_API_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600) - 300

                await self.cache.set(self.TOKEN_CACHE_KEY, token, ttl=expires_in)
                return token
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get Mpesa token: {e.response.text}")
                return None

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        region: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if currency.upper() != "KES":
            raise ValueError("Mpesa only supports KES currency.")

        token = await self._get_access_token()
        if not token:
            raise Exception("Could not authenticate with Mpesa")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_data = (
            f"{self.settings.MPESA_SHORTCODE}{self.settings.MPESA_PASSKEY}{timestamp}"
        )
        password = base64.b64encode(password_data.encode()).decode()

        amount_int = int(amount.quantize(Decimal("0")))
        phone_number = metadata.get("phone_number", "").lstrip("+")
        if not phone_number.startswith("254"):
            phone_number = f"254{phone_number.lstrip('0')}"

        if not phone_number or len(phone_number) != 12:
            raise ValueError(
                "Valid Kenyan phone number (e.g., 2547...) is required for Mpesa."
            )

        payload = {
            "BusinessShortCode": self.settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount_int,
            "PartyA": phone_number,
            "PartyB": self.settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{self.settings.MPESA_CALLBACK_URL}?order_id={metadata.get('order_id', '0')}",
            "AccountReference": f"ORD{metadata.get('order_id', '0')}",
            "TransactionDesc": f"Payment for Airdeliver Order #{metadata.get('order_id', '0')}",
        }

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.MPESA_API_BASE_URL}/mpesa/stkpush/v1/processrequest",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("ResponseCode") == "0":
                return {
                    "status": "pending_confirmation",
                    "provider": "mpesa",
                    "paymentId": data["MerchantRequestID"],
                    "checkoutRequestId": data["CheckoutRequestID"],
                    "message": data["ResponseDescription"],
                }
            else:
                raise Exception(
                    f"Mpesa STK Push failed: {data.get('ResponseDescription')}"
                )

    async def get_status(self, payment_id: str) -> str:
        raise NotImplementedError("MpesaGateway.get_status not implemented")


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
            "DEFAULT": ["stripe", "paypal"],
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
            logger.error(f"Invalid amount format: {amount}. Must be a valid number.")
            return {"status": "failure", "error": "Invalid amount format."}

        gateways_for_region = self._routing_rules.get(
            region.upper(), self._routing_rules["DEFAULT"]
        )

        for provider_key in gateways_for_region:
            gateway = self._gateways.get(provider_key)
            if gateway:
                try:
                    result = await gateway.create_payment(
                        decimal_amount, currency, region, metadata
                    )

                    if result.get("status") in [
                        "success",
                        "requires_payment_method",
                        "pending_confirmation",
                    ] and (
                        result.get("clientSecret")
                        or result.get("approval_url")
                        or result.get("checkoutRequestId")
                    ):
                        logger.info(f"Payment processed successfully by {provider_key}.")
                        return result

                except stripe.error.CardError as e:
                    logger.warning(
                        f"Payment failed with CardError from {provider_key}. Stopping retry logic."
                    )
                    return {
                        "status": "failure",
                        "error": str(e),
                        "provider": provider_key,
                        "error_type": "user",
                    }

                except Exception as e:
                    logger.error(
                        f"Gateway {provider_key} failed: {e}. Trying next available gateway."
                    )

        logger.error(
            f"All payment gateways failed for region {region} and amount {amount}."
        )
        return {"status": "failure", "error": "All payment gateways failed."}


def get_payment_orchestrator(
    cache: IAsyncCacheClient = Depends(get_cache_client),
    stripe_settings: StripeSettings = Depends(get_stripe_settings),
    paypal_settings: PayPalSettings = Depends(get_paypal_settings),
    mpesa_settings: MpesaSettings = Depends(get_mpesa_settings),
) -> PaymentOrchestrator:

    stripe_gateway: PaymentGateway
    try:
        stripe_gateway = StripeGateway(settings=stripe_settings)
    except ValidationError:
        stripe_gateway = NoOpGateway(provider_name="Stripe")

    paypal_gateway: PaymentGateway
    try:
        paypal_gateway = PayPalGateway(settings=paypal_settings, cache=cache)
    except ValidationError:
        paypal_gateway = NoOpGateway(provider_name="PayPal")

    mpesa_gateway: PaymentGateway
    try:
        mpesa_gateway = MpesaGateway(settings=mpesa_settings, cache=cache)
    except ValidationError:
        mpesa_gateway = NoOpGateway(provider_name="Mpesa")

    return PaymentOrchestrator(
        stripe_gateway=stripe_gateway,
        paypal_gateway=paypal_gateway,
        mpesa_gateway=mpesa_gateway,
    )
