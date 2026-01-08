# apps/api/app/services/ai_checkout_service.py

import random
import logging
import uuid
import json
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.services.payment_orchestrator import PaymentOrchestrator
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason
from app.services.notification_service import NotificationService
from app.models.user import User
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class AICheckoutService:
    """
    💎 DIAMOND CHECKOUT SERVICE (V4.0).

    The Sovereign Financial Orchestrator.
    Handles the transition from 'Intent' to 'Transaction'.

    PILLARS:
    1. 🛡️ Atomic Transactions: DB commits happen only when data is perfect.
    2. ⚡ Direct Redis Uplink: Opens payment modals instantly on the frontend.
    3. 🌐 Universal Payment Routing: Delegates complexity to the Orchestrator.
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: IAsyncCacheClient,
        rabbitmq: RabbitMQService,
        orchestrator: Any, # PaymentOrchestrator injected dynamically
        notification_service: Any = None,
    ):
        self.db = db
        self.cache = cache
        self.rabbitmq = rabbitmq
        self.orchestrator = orchestrator
        self.notification_service = notification_service

    # --- 🔌 1. UI RESPONSE ROUTER (SECURE UPLINK) ---
    async def _send_to_ui(self, user_id: int, payload: dict):
        """
        💎 Direct Uplink to Frontend via Redis Pub/Sub.
        Critical for opening the Payment Modal instantly.
        Includes Universal Serializer for Decimal/Date safety.
        """
        try:
            channel = f"airdeliver:response:{user_id}"

            # Metadata
            payload["meta"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "ai_checkout_v4"
            }

            # 🛡️ Universal Serializer
            def safe_serializer(obj):
                if isinstance(obj, Decimal): return float(obj)
                if hasattr(obj, 'isoformat'): return obj.isoformat()
                return str(obj)

            message = json.dumps(payload, default=safe_serializer)
            await self.cache.publish(channel, message)
        except Exception as e:
            logger.error(f"🔥 UI Delivery Failed in CheckoutService: {e}")

    def _get_cart_key(self, user_id: int) -> str:
        return f"ai_cart:{user_id}"

    # --- 💰 2. MAIN HANDLER: CONFIRM ORDER ---

    async def handle_confirm_order(self, payload: dict):
        """
        Orchestrates the Checkout Flow:
        1. Validate Cart (Redis).
        2. Create Pending Order (DB).
        3. Initialize Payment Gateways (Orchestrator).
        4. Push Payment Intent to UI (Redis).
        """
        user_id = payload.get("user_id")
        if not user_id: return

        # A. Validate Cart
        cart_key = self._get_cart_key(user_id)
        # Using get_json helper from cache client
        cart = await self.cache.get_json(cart_key)

        if not cart or not cart.get("items"):
            await self._send_to_ui(user_id, {"content": "Your cart is empty.", "type": "error"})
            return

        # Safe Float Conversion for DB
        try:
            raw_total = cart.get("total", 0)
            total_amount = float(raw_total)
        except:
            total_amount = 0.0

        delivery_addr = payload.get("address", "Default Saved Address")

        # B. Transaction: Create Pending Order (Atomic)
        new_order = None
        try:
            new_order = Order(
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_price=total_amount,
                delivery_address=delivery_addr,
                created_at=datetime.utcnow()
            )
            self.db.add(new_order)
            await self.db.flush() # Get ID without committing yet

            # Create Items
            order_items_to_create = []
            for item in cart["items"]:
                order_items_to_create.append(OrderItem(
                    order_id=new_order.id,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price_per_unit=float(item["price"])
                ))

            self.db.add_all(order_items_to_create)
            await self.db.commit()
            await self.db.refresh(new_order)

            logger.info(f"📝 Order #{new_order.id} Created (Pending Payment). Total: ${total_amount}")

        except Exception as e:
            await self.db.rollback()
            logger.critical(f"FATAL: DB Transaction Failed: {e}")
            await self._send_to_ui(user_id, {"content": "System error. Could not create order.", "type": "error"})
            return

        # C. Payment Orchestration
        payment_metadata = {
            "order_id": str(new_order.id),
            "user_id": str(user_id),
            "user_email": payload.get("email", ""),
            "idempotency_key": str(uuid.uuid4())
        }

        try:
            # Inform user we are working (Low Latency Feedback)
            await self._send_to_ui(user_id, {"content": "Securing payment channels...", "type": "typing"})

            # Call the injected Orchestrator
            # Note: We pass 'usd' default, but this should come from user config
            payment_options = await self.orchestrator.process_payment(
                amount=total_amount,
                currency="usd",
                region=payload.get("country", "US"),
                metadata=payment_metadata
            )
        except Exception as e:
            logger.error(f"Orchestrator Failed: {e}")
            await self._handle_failed_payment(new_order, "Payment Gateway Unreachable")
            return

        # D. Handle Result
        if payment_options.get("status") == "failure":
            await self._handle_failed_payment(new_order, payment_options.get("error", "Initialization failed"))
        else:
            logger.info(f"💰 Payment Intent Ready for Order {new_order.id}")

            # ✅ Send Payment Intent via Redis (Opens the Modal Instantly)
            # This payload is designed for the Frontend Payment SDK
            await self._send_to_ui(user_id, {
                "type": "payment_intent",
                "content": {
                    "orderId": new_order.id,
                    "total": float(new_order.total_price),
                    "gateways": payment_options.get("available_gateways", []), # Stripe/PayPal keys
                    "client_secret": payment_options.get("client_secret", "") # Critical for Stripe
                }
            })

            # E. Analytics Signal (Fire-and-Forget)
            try:
                await self.rabbitmq.publish(
                    {"user_id": user_id, "order_id": new_order.id, "amount": total_amount},
                    "airdeliver.ai.checkout.initiated"
                )
            except: pass

    # --- 💔 3. FAILURE RECOVERY ---

    async def handle_payment_success(self, payload: dict):
        """
        🚀 MISSION CONTROL: Payment Secured -> Order Processing -> Drone Dispatch.
        Triggers the 'Immersive Logistics Experience' on the frontend.
        """
        user_id = payload.get("user_id")
        order_id = payload.get("order_id")

        try:
            # 1. Lock & Load Order
            order = await self.db.get(Order, order_id)
            if not order: 
                logger.warning(f"Payment Success signal received for non-existent order {order_id}")
                return

            if order.status == OrderStatus.PENDING:
                # Update State
                order.status = OrderStatus.PROCESSING
                order.is_paid = True
                order.paid_at = datetime.utcnow()
                self.db.add(order)
                await self.db.commit()

                # 2. Clear Shopping Cart (Mission Accomplished)
                cart_key = self._get_cart_key(user_id)
                await self.cache.delete(cart_key)

                # 3. 🚁 Generate Flight Telemetry (The Wow Factor)
                flight_data = self._generate_flight_manifest(order.id, order.delivery_address)
                
                # Persist Flight Data to Order Metadata (Optional/Future Proofing)
                # order.metadata = flight_data 
                # await self.db.commit()

                # 4. Notify UI: Phase 1 (Confirmation)
                await self._send_to_ui(user_id, {
                    "content": f"Payment Secured! Order #{order.id} is confirmed. airaero X on his way.",
                    "type": "success_text",
                    "sound": "drone_takeoff" # Frontend hint for audio effect
                })

                # 5. Notify UI: Phase 2 (The Dashboard)
                # Small delay to simulate system boot sequence
                await asyncio.sleep(0.5)
                await self._send_to_ui(user_id, {
                    "content": "Uploading Live Telemetry...",
                    "type": "FLIGHT_MANIFEST",
                    "flight_data": flight_data
                })
                
                # 6. Analytics: Conversion Event
                await self.rabbitmq.publish(
                    {"user_id": user_id, "order_id": order.id, "revenue": float(order.total_price)},
                    "airdeliver.ai.analytics.conversion"
                )

        except Exception as e:
            logger.critical(f"Payment Success Handler Failed: {e}")
            # Even if logic fails, ensure UI gets something
            await self._send_to_ui(user_id, {"content": "Order confirmed! Check your email for details.", "type": "success_text"})

    def _generate_flight_manifest(self, order_id: int, user_address: str) -> dict:
        """
        🛰️ Generates procedural flight data for the UI Dashboard.
        """
        # Simulation Logic
        distance_km = random.uniform(3.5, 15.0) # Realistic drone range
        speed_kph = 120.0 # High-speed drone
        
        # Calculate ETA with "Prep Time" buffer
        flight_time_mins = (distance_km / speed_kph) * 60
        total_eta_mins = int(flight_time_mins + 5) # +5 mins for packing/loading
        
        return {
            "mission_id": f"MSN-{order_id}-{random.randint(1000,9999)}",
            "drone_id": f"AIR-X-{random.randint(100,999)} (Stealth)",
            "distance_km": round(distance_km, 1),
            "cruising_altitude": f"{random.randint(100, 300)}ft",
            "speed_kph": int(speed_kph),
            "estimated_arrival_mins": total_eta_mins,
            "weather_condition": random.choice(["Clear Sky ☀️", "Tailwind 🍃", "Optimal Visibility 👁️"]),
            "battery_status": "100%",
            "status": "PRE-FLIGHT CHECK COMPLETE"
        }

    # --- ❌ 5. FAILURE & CANCELLATION HANDLERS ---

    async def _handle_failed_payment(self, order: Order, reason: str):
        """
        Graceful Failure Handling.
        Prevents user drop-off by suggesting immediate actions.
        """
        try:
            # 1. Update DB Status
            order.status = OrderStatus.FAILED
            self.db.add(order)
            await self.db.commit()
            
            # 2. Smart User Recovery
            await self._send_to_ui(order.user_id, {
                "content": f"Payment Interruption: {reason}. Don't worry, your cart is safe.",
                "type": "confirmation_prompt",
                "options": ["Retry Payment", "Change Method"],
                "reason": "Transaction Recovery"
            })
        except Exception as e:
            logger.error(f"Failed handling failed payment: {e}")

    async def handle_cancel_order(self, payload: dict):
        """
        User-Initiated Cancellation.
        Enforces state checks to prevent cancelling shipped orders.
        """
        user_id = payload.get("user_id")
        order_id = payload.get("order_id")
        
        if not user_id: return
             
        order_cancelled = False
        if order_id:
            order = await self.db.get(Order, order_id)
            if order and order.user_id == user_id:
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.CANCELLED
                    self.db.add(order)
                    await self.db.commit()
                    order_cancelled = True
                    logger.info(f"Order {order_id} cancelled by user.")

                elif order.status in [OrderStatus.PROCESSING, OrderStatus.SHIPPED]:
                     # If order is already flying, we can't discard. Stop here.
                     await self._send_to_ui(user_id, {
                        "content": "Cannot discard: Your order in progress. Contact support for canceling.",
                        "type": "error"
                    })
                     return
             
        try:
            cart_key = self._get_cart_key(user_id)
            await self.cache.delete(cart_key)
        except Exception: pass

        # 3. Update UI (Clear Sidebar Immediately)
        await self._send_to_ui(user_id, {
            "content": {"items": [], "total": 0.0},
            "type": "cart_preview",
            "reason": "Discard Command"
        })
        
        # 4. User Feedback
        msg = f"Order #{order_id} discarded." if order_cancelled else "Your order is canceled."
        await self._send_to_ui(user_id, {
            "content": f"{msg} Cart is cleared.",
            "type": "info" 
        })
    async def _send_error(self, user_id: int, message: str):
        """Utility for quick error dispatch"""
        await self._send_to_ui(user_id, {"content": message, "type": "error"})
