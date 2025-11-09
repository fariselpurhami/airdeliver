import stripe
import logging
from app.core.config import settings
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal, InvalidOperation
import stripe.error

logger = logging.getLogger(__name__)

class PaymentGateway(ABC):
    
    @abstractmethod
    def create_payment(self, amount: Decimal, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    
        pass

    @abstractmethod
    def get_status(self, payment_id: str) -> str:
    
        pass

class StripeGateway(PaymentGateway):
    
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment(self, amount: Decimal, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"Creating Payment Intent via Stripe for region {region} and amount {amount} {currency}.")
        try:
    
            amount_in_cents = int(amount.quantize(Decimal('0.01')) * 100)
            
            intent_params = {
                "amount": amount_in_cents,
                "currency": currency.lower(),
                "automatic_payment_methods": {"enabled": True},
                "metadata": metadata or {"region": region}
            }
            
            intent = stripe.PaymentIntent.create(**intent_params)
            
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

    def get_status(self, payment_id: str) -> str:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            return intent.status
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe status for {payment_id}: {e}")
            return "error"


class PayPalGateway(PaymentGateway):
    
    def create_payment(self, amount: Decimal, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.warning(f"PayPalGateway is not yet implemented. Bypassing.")
        
        raise NotImplementedError("PayPalGateway not implemented")

    def get_status(self, payment_id: str) -> str:
        raise NotImplementedError("PayPalGateway.get_status not implemented")


class MpesaGateway(PaymentGateway):

    def create_payment(self, amount: Decimal, currency: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.warning(f"MpesaGateway is not yet implemented. Bypassing.")
    
        raise NotImplementedError("MpesaGateway not implemented")

    def get_status(self, payment_id: str) -> str:
        raise NotImplementedError("MpesaGateway.get_status not implemented")

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
    
        try:
            
            decimal_amount = Decimal(str(amount))
        except InvalidOperation:
            logger.error(f"Invalid amount format: {amount}. Must be a valid number.")
            return {"status": "failure", "error": "Invalid amount format."}

        gateways_for_region = self._routing_rules.get(region, self._routing_rules["DEFAULT"])

        for provider_key in gateways_for_region:
            gateway = self._gateways.get(provider_key)
            if gateway:
                try:
                    result = gateway.create_payment(decimal_amount, currency, region, metadata)
                    
                    if result.get("status") in ["success", "requires_payment_method"] and result.get("clientSecret"):
                        logger.info(f"Payment processed successfully by {provider_key}.")
                        return result
                        
                except stripe.error.CardError as e:
                
                    logger.warning(f"Payment failed with CardError from {provider_key}. Stopping retry logic.")
                    return {"status": "failure", "error": str(e), "provider": provider_key, "error_type": "user"}
                    
                except Exception as e:
                    
                    logger.error(f"Gateway {provider_key} failed: {e}. Trying next available gateway.")
                    
        
        logger.error(f"All payment gateways failed for region {region} and amount {amount}.")
        return {"status": "failure", "error": "All payment gateways failed."}

payment_orchestrator = PaymentOrchestrator()
