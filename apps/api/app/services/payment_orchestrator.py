import stripe
from app.core.config import settings
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PaymentGateway(ABC):
    @abstractmethod
    def create_payment(self, amount: float, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self, payment_id: str) -> str:
        pass

class StripeGateway(PaymentGateway):
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment(self, amount: float, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print(f"Creating Payment Intent via Stripe for region {region}.")
        try:
            amount_in_cents = int(amount * 100)
            intent_params = {
                "amount": amount_in_cents,
                "currency": currency.lower(),
                "automatic_payment_methods": {"enabled": True},
                "metadata": metadata or {"region": region}
            }
            
            intent = stripe.PaymentIntent.create(**intent_params)
            
            return {
                "status": "requires_payment_method",
                "provider": "stripe",
                "paymentId": intent.id,
                "clientSecret": intent.client_secret,
            }
        except Exception as e:
            print(f"Stripe Error: {e}")
            return {"status": "failure", "error": str(e)}

    def get_status(self, payment_id: str) -> str:
        intent = stripe.PaymentIntent.retrieve(payment_id)
        return intent.status


class PayPalGateway(PaymentGateway):
    def create_payment(self, amount: float, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print(f"Processing ${amount} {currency} via PayPal for region {region}.")
        return {"status": "success", "provider": "paypal", "paymentId": "pi_paypal_456", "clientSecret": "pi_paypal_456_secret"}

    def get_status(self, payment_id: str) -> str:
        return "confirmed"


class MpesaGateway(PaymentGateway):
    def create_payment(self, amount: float, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print(f"Processing ${amount} {currency} via M-Pesa for region {region}.")
        return {"status": "success", "provider": "mpesa", "paymentId": "pi_mpesa_789", "clientSecret": "pi_mpesa_789_secret"}

    def get_status(self, payment_id: str) -> str:
        return "pending_confirmation"

class PaymentOrchestrator:
    def __init__(self):
        self._gateways = {
            "stripe": StripeGateway(),
            "paypal": PayPalGateway(),
            "mpesa": MpesaGateway(),
        }
        self._routing_rules = {
            "NA": ["stripe", "paypal"],
            "US": ["stripe", "paypal"],
            "EU": ["stripe", "paypal"],
            "KE": ["mpesa", "stripe"],
            "DEFAULT": ["stripe", "paypal"],
        }

    def process_payment(self, amount: float, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        gateways_for_region = self._routing_rules.get(region, self._routing_rules["DEFAULT"])

        for provider_key in gateways_for_region:
            gateway = self._gateways.get(provider_key)
            if gateway:
                try:
                    result = gateway.create_payment(amount, currency, region, metadata)
                    if result.get("status") in ["success", "requires_payment_method"] and result.get("clientSecret"):
                        return result
                except Exception as e:
                    print(f"Gateway {provider_key} failed: {e}. Trying next.")

        return {"status": "failure", "error": "All payment gateways failed."}


payment_orchestrator = PaymentOrchestrator()
