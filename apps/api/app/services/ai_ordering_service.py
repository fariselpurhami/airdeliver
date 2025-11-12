# file: api/app/services/ai_ordering_service.py
import re
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus
from app.models.ai_cart import AIOrderingCartItem
from app import models, schemas
from app.services.ai_commerce_engine import ai_commerce_engine
from app.services.payment_orchestrator import payment_orchestrator
from sqlalchemy import cast, String, desc, func
from typing import List, Tuple, Dict, Any
import random


class AIOrderingService:
    def __init__(self):
        self.conversation_state = {"stage": "IDLE"}

    async def _clear_state_and_cart(self, db: AsyncSession, user_id: int):
        self.conversation_state = {"stage": "IDLE"}
        items_to_delete = (
            await db.exec(
                select(AIOrderingCartItem).where(AIOrderingCartItem.user_id == user_id)
            )
        ).all()
        for item in items_to_delete:
            await db.delete(item)
        await db.commit()

    async def _get_user_cart(self, db: AsyncSession, user_id: int) -> dict:
        cart_items_db = (
            await db.exec(
                select(AIOrderingCartItem, Product)
                .join(Product, AIOrderingCartItem.product_id == Product.id)
                .where(AIOrderingCartItem.user_id == user_id)
            )
        ).all()

        cart = {"items": [], "total": 0.0, "categories": set()}
        total = 0.0

        for cart_item, product in cart_items_db:
            item_total = product.price * cart_item.quantity
            cart["items"].append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "quantity": cart_item.quantity,
                    "price": product.price,
                    "image_url": self._format_product_for_frontend(product).get(
                        "image_url"
                    ),
                }
            )
            if product.category:
                cart["categories"].add(product.category.lower())
            total += item_total

        cart["total"] = total
        return cart

    def _format_product_for_frontend(self, p: Product) -> dict:
        product_data = p.model_dump()
        image_filename = product_data.get("image_url")
        if image_filename:
            product_data["image_url"] = image_filename
        else:
            product_data["image_url"] = "default.jpeg"
        product_data["image"] = product_data["image_url"]

        if "rating" not in product_data or product_data["rating"] is None:
            product_data["rating"] = round(random.uniform(4.5, 5.0), 1)
        if "reviews" not in product_data or product_data["reviews"] is None:
            product_data["reviews"] = random.randint(500, 2000)

        return product_data

    def _parse_intent(self, message: str) -> dict:
        if message == "__INTERNAL_GET_INITIAL_SUGGESTIONS__":
            return {"intent": "INTERNAL_GET_INITIAL_SUGGESTIONS"}

        if message.startswith("__INTERNAL_ADD_BY_ID__"):
            try:
                product_id = int(message.split(":")[-1])
                return {"intent": "INTERNAL_ADD_BY_ID", "product_id": product_id}
            except (ValueError, IndexError):
                return {"intent": "UNKNOWN"}
        if message.startswith("__INTERNAL_REMOVE_BY_ID__"):
            try:
                product_id = int(message.split(":")[-1])
                return {"intent": "INTERNAL_REMOVE_BY_ID", "product_id": product_id}
            except (ValueError, IndexError):
                return {"intent": "UNKNOWN"}

        if message.startswith("__INTERNAL_GET_SUGGESTIONS__"):
            try:
                product_id = int(message.split(":")[-1])
                return {"intent": "INTERNAL_GET_SUGGESTIONS", "product_id": product_id}
            except (ValueError, IndexError):
                return {"intent": "UNKNOWN"}

        message_lower = message.lower()
        confirm_keywords = ["confirm", "checkout", "pay", "proceed", "confirm order"]
        clear_keywords = ["clear cart", "cancel", "cancel order"]
        remove_keywords = ["remove", "delete"]

        if any(keyword in message_lower for keyword in confirm_keywords):
            return {"intent": "CONFIRM_ORDER"}
        if any(keyword in message_lower for keyword in clear_keywords):
            return {"intent": "CLEAR_CART"}

        for keyword in remove_keywords:
            if keyword in message_lower:
                parts = message_lower.split(keyword, 1)
                product_name = parts[1].strip() if len(parts) > 1 else ""
                return {"intent": "REMOVE_FROM_CART", "product_name": product_name}

        return {"intent": "ADD_TO_CART", "product_name": message}

    async def _get_initial_suggestions(self, db: AsyncSession) -> List[dict]:
        top_products = (
            await db.exec(select(Product).order_by(func.random()).limit(5))
        ).all()

        if not top_products:
            return [
                {"contentType": "text", "content": "Welcome! What are you looking for today?"}
            ]

        formatted_products = [
            self._format_product_for_frontend(p) for p in top_products
        ]

        return [
            {
                "contentType": "proactive_suggestion",
                "content": "Here are some popular items to get you started:",
                "products": formatted_products,
                "reason": "Popular items this week",
            }
        ]

    async def _find_proactive_suggestions(
        self, db: AsyncSession, added_product: Product
    ) -> List[Product]:
        suggestions_list: List[Product] = []
        excluded_ids = {added_product.id}

        search_tags = [
            tag
            for tag in (added_product.tags or [])
            if tag
            in [
                "gift",
                "premium",
                "sport",
                "formal",
                "electronics",
                "clothing",
                "accessories",
            ]
        ]

        if search_tags:
            tag_criteria = [
                cast(Product.tags, String).ilike(f"%{tag}%") for tag in search_tags
            ]
            tag_suggestions = (
                await db.exec(
                    select(Product)
                    .where(Product.id.notin_(excluded_ids), or_(*tag_criteria))
                    .limit(3)
                )
            ).all()

            for p in tag_suggestions:
                if p.id not in excluded_ids:
                    suggestions_list.append(p)
                    excluded_ids.add(p.id)

        if len(suggestions_list) >= 3:
            return suggestions_list[:3]

        needed_count = 3 - len(suggestions_list)
        if added_product.category:
            category_suggestions = (
                await db.exec(
                    select(Product)
                    .where(
                        Product.id.notin_(excluded_ids),
                        Product.category == added_product.category,
                    )
                    .limit(needed_count)
                )
            ).all()

            for p in category_suggestions:
                if p.id not in excluded_ids:
                    suggestions_list.append(p)
                    excluded_ids.add(p.id)

        if len(suggestions_list) >= 3:
            return suggestions_list[:3]

        needed_count = 3 - len(suggestions_list)

        fallback_suggestions = (
            await db.exec(
                select(Product)
                .where(Product.id.notin_(excluded_ids))
                .order_by(desc(Product.rating))
                .limit(needed_count)
            )
        ).all()

        for p in fallback_suggestions:
            if p.id not in excluded_ids:
                suggestions_list.append(p)
                excluded_ids.add(p.id)

        return suggestions_list[:3]

    async def _add_product_by_id_silent(
        self, db: AsyncSession, user_id: int, product_id: int, quantity_to_add: int = 1
    ) -> List[dict]:
        product = await db.get(Product, product_id)
        if not product:
            return [
                {"contentType": "error", "content": f"Item (ID: {product_id}) not found."}
            ]

        existing_item = (
            await db.exec(
                select(AIOrderingCartItem).where(
                    AIOrderingCartItem.user_id == user_id,
                    AIOrderingCartItem.product_id == product.id,
                )
            )
        ).first()

        if existing_item:
            existing_item.quantity += quantity_to_add
            db.add(existing_item)
        else:
            new_cart_item = AIOrderingCartItem(
                user_id=user_id, product_id=product.id, quantity=quantity_to_add
            )
            db.add(new_cart_item)

        await db.commit()
        cart = await self._get_user_cart(db, user_id)

        return [
            {"contentType": "cart_preview", "content": cart},
            {
                "contentType": "confirmation_prompt",
                "content": "Anything else?",
                "options": ["Confirm Order", "Clear Cart"],
            },
        ]

    async def _remove_product_by_id_silent(
        self, db: AsyncSession, user_id: int, product_id: int
    ) -> List[dict]:
        item_db = (
            await db.exec(
                select(AIOrderingCartItem).where(
                    AIOrderingCartItem.user_id == user_id,
                    AIOrderingCartItem.product_id == product_id,
                )
            )
        ).first()

        if not item_db:
            cart = await self._get_user_cart(db, user_id)
            return [{"contentType": "cart_preview", "content": cart}]

        product_name = "Item"
        product = await db.get(Product, product_id)
        if product:
            product_name = product.name

        await db.delete(item_db)
        await db.commit()

        cart = await self._get_user_cart(db, user_id)

        responses = [
            {"contentType": "success_text", "content": f"Removed {product_name} from cart."},
            {"contentType": "cart_preview", "content": cart},
        ]

        if cart["items"]:
            responses.append(
                {
                    "contentType": "confirmation_prompt",
                    "content": "Cart updated.",
                    "options": ["Confirm Order", "Clear Cart"],
                }
            )
        else:
            responses.append({"contentType": "text", "content": "Your cart is now empty."})

        return responses

    async def _get_contextual_ai_note(
        self, db: AsyncSession, product: Product, cart: dict
    ) -> str:
        if (
            hasattr(product, "delivery_eta")
            and product.delivery_eta
            and "10 Min" in product.delivery_eta
        ):
            return f"This item is eligible for our 10-minute priority delivery!"

        cart_categories = cart.get("categories", set())
        if (
            product.category
            and product.category.lower() == "sport"
            and "sport" in cart_categories
        ):
            sport_items_count = 0
            for item in cart["items"]:
                item_prod = await db.get(Product, item["product_id"])
                if item_prod and item_prod.category.lower() == "sport":
                    sport_items_count += 1

            if sport_items_count == 1:
                return "That's your 2nd sport item! Add one more for a 15% bundle discount."
            if sport_items_count > 1:
                return f"Another sport item added! You've unlocked the 15% bundle discount."

        if product.tags and "premium" in product.tags:
            return "A premium choice! These accessories would be a perfect match."

        if product.tags and "gift" in product.tags:
            return "Great gift idea! We can add gift wrapping at checkout."

        return "Based on your latest addition."

    async def _get_suggestions_for_product(
        self, db: AsyncSession, product_id: int, user_id: int
    ) -> List[dict]:
        product = await db.get(Product, product_id)
        if not product:
            return []

        suggestions = await self._find_proactive_suggestions(db, product)

        cart = await self._get_user_cart(db, user_id)

        ai_note = await self._get_contextual_ai_note(db, product, cart)

        if suggestions:
            suggestion_list = [
                self._format_product_for_frontend(p) for p in suggestions
            ]

            return [
                {
                    "contentType": "proactive_suggestion",
                    "content": "You might also like these:",
                    "products": suggestion_list,
                    "reason": ai_note,
                }
            ]
        return []

    async def _add_product_to_cart_by_name(
        self, db: AsyncSession, user_id: int, product_name_query: str
    ) -> List[dict]:
        products, entities = await ai_commerce_engine.find_products_from_message(
            db, product_name_query
        )

        quantity = entities.get("quantity", 1)

        if not products:
            return [
                {
                    "contentType": "text",
                    "content": f"I couldn't find a product matching '{product_name_query}'. Please try another.",
                }
            ]

        if len(products) > 1:
            self.conversation_state["stage"] = "AWAITING_CLARIFICATION"
            product_list = [self._format_product_for_frontend(p) for p in products]
            ai_note = f"Found {len(products)} items. For example, '{products[0].name}' matches your request."
            return [
                {
                    "contentType": "text",
                    "content": "I found a few items. Which one did you mean?",
                    "ai_notes": ai_note,
                },
                {"contentType": "product_carousel", "products": product_list},
            ]

        product = products[0]

        cart_responses = await self._add_product_by_id_silent(
            db, user_id, product.id, quantity_to_add=quantity
        )

        suggestion_responses = await self._get_suggestions_for_product(
            db, product.id, user_id
        )

        cart = await self._get_user_cart(db, user_id)
        ai_note = await self._get_contextual_ai_note(db, product, cart)

        add_message = f"Great choice! I've added {product.name} to your cart."
        if quantity > 1:
            add_message = (
                f"Great choice! I've added {quantity} units of {product.name} to your cart."
            )

        responses = [
            {"contentType": "text", "content": add_message, "ai_notes": ai_note},
            *cart_responses,
            *suggestion_responses,
        ]
        return responses

    async def handle_message(
        self, db: AsyncSession, message: str, user: models.User
    ) -> list[dict]:
        current_stage = self.conversation_state.get("stage")

        if current_stage == "AWAITING_CLARIFICATION":
            parsed_data = self._parse_intent(message)
            if parsed_data["intent"] == "ADD_TO_CART":
                self.conversation_state["stage"] = "IDLE"
                return await self._add_product_to_cart_by_name(
                    db, user.id, parsed_data["product_name"]
                )
            self.conversation_state["stage"] = "IDLE"
        elif current_stage == "AWAITING_CONFIRMATION":
            parsed_data = self._parse_intent(message)
        else:
            parsed_data = self._parse_intent(message)

        intent = parsed_data.get("intent")

        if intent == "INTERNAL_GET_INITIAL_SUGGESTIONS":
            await self._clear_state_and_cart(db, user.id)
            return await self._get_initial_suggestions(db)

        if intent == "INTERNAL_ADD_BY_ID":
            return await self._add_product_by_id_silent(
                db, user.id, parsed_data["product_id"], quantity_to_add=1
            )

        if intent == "INTERNAL_REMOVE_BY_ID":
            return await self._remove_product_by_id_silent(
                db, user.id, parsed_data["product_id"]
            )

        if intent == "INTERNAL_GET_SUGGESTIONS":
            return await self._get_suggestions_for_product(
                db, parsed_data["product_id"], user.id
            )

        if intent == "ADD_TO_CART":
            product_name_query = parsed_data["product_name"]
            return await self._add_product_to_cart_by_name(db, user.id, product_name_query)

        if intent == "REMOVE_FROM_CART":
            product_name_to_remove = parsed_data["product_name"]
            cart = await self._get_user_cart(db, user.id)

            item_to_remove_from_cart = next(
                (
                    item
                    for item in cart["items"]
                    if product_name_to_remove in item["name"].lower()
                ),
                None,
            )

            if not item_to_remove_from_cart:
                return [
                    {
                        "contentType": "text",
                        "content": f"I couldn't find '{product_name_to_remove}' in your cart.",
                    }
                ]

            item_db = (
                await db.exec(
                    select(AIOrderingCartItem).where(
                        AIOrderingCartItem.user_id == user.id,
                        AIOrderingCartItem.product_id
                        == item_to_remove_from_cart["product_id"],
                    )
                )
            ).first()

            if item_db:
                await db.delete(item_db)
                await db.commit()

            cart = await self._get_user_cart(db, user.id)
            self.conversation_state["stage"] = "AWAITING_CONFIRMATION"
            return [
                {
                    "contentType": "text",
                    "content": f"Okay, I've removed {item_to_remove_from_cart['name']} from your cart.",
                },
                {"contentType": "cart_preview", "content": cart},
                {
                    "contentType": "confirmation_prompt",
                    "content": "Your cart is updated. What's next?",
                    "options": ["Confirm Order", "Clear Cart"],
                },
            ]

        if intent == "CONFIRM_ORDER":
            cart = await self._get_user_cart(db, user.id)
            if not cart["items"]:
                return [{"contentType": "text", "content": "Your cart is empty."}]

            total = cart["total"]

            delivery_addr = user.address or f"Default Address for {user.email}"
            if user.city and user.country:
                delivery_addr = f"{user.address}, {user.city}, {user.country}"

            new_order = Order(
                user_id=user.id,
                status=OrderStatus.PENDING,
                total_price=total,
                delivery_address=delivery_addr,
            )
            db.add(new_order)
            
            # --- (هنا التعديل) ---
            order_items_to_create = []
            for item in cart["items"]:
                order_items_to_create.append(
                    OrderItem(
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        price_per_unit=item["price"],
                        order=new_order 
                    )
                )
            
            db.add_all(order_items_to_create)
            await db.commit()

            # (!!! الإضافة الجديدة أهيه !!!)
            # 3. اعمل Refresh لكل الأوبجكتس اللي هتحتاجها
            await db.refresh(new_order) 
            await db.refresh(user) 
            # --- (نهاية التعديل) ---

            payment_metadata = {
                "order_id": str(new_order.id), 
                "user_id": str(user.id),       
                "user_email": user.email,     
            }

            payment_info = payment_orchestrator.process_payment(
                amount=total, currency="usd", region="US", metadata=payment_metadata
            )

            if "error" in payment_info or not payment_info.get("clientSecret"):
                new_order.status = OrderStatus.FAILED
                db.add(new_order)
                await db.commit()
                return [
                    {
                        "contentType": "text",
                        "content": f"I couldn't create a payment for this order. Error: {payment_info.get('error', 'Payment gateway failed')}",
                    }
                ]

            return [
                {"contentType": "cart_preview", "content": cart},
                {
                    "contentType": "payment_intent",
                    "content": {
                        "clientSecret": payment_info.get("clientSecret"),
                        "orderId": new_order.id,
                        "total": total,
                    },
                },
            ]

        if intent == "CLEAR_CART":
            await self._clear_state_and_cart(db, user.id)
            empty_cart = await self._get_user_cart(db, user.id)
            return [
                {"contentType": "text", "content": "No problem, your cart has been cleared."},
                {"contentType": "cart_preview", "content": empty_cart},
            ]

        return [
            {
                "contentType": "text",
                "content": "I'm sorry, I didn't quite understand. To start, you can ask me to 'buy' an item.",
            }
        ]

    async def cancel_order_by_id(
        self, db: AsyncSession, order_id: int, user_id: int
    ) -> Order | None:
        """
        Cancels a PENDING order.
        """
        order = await db.get(Order, order_id)
        if not order or order.user_id != user_id:
            
            return None

        if order.status != OrderStatus.PENDING:
            raise ValueError("Order is not pending and cannot be cancelled.")

        order.status = OrderStatus.CANCELLED
        db.add(order)
        await db.commit()
        await db.refresh(order)

        return order

ai_ordering_service = AIOrderingService()
