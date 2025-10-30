# apps/api/app/services/ai_ordering_service.py

import re
from sqlmodel import Session, select
from app.models.product import Product
from app.models.user import User
from app import models
import random

SESSION_CARTS = {}

class AIOrderingService:
    def __init__(self):
        self.conversation_state = {"stage": "IDLE"}

    def _clear_state_and_cart(self, session_id: str = "default_user"):
        self.conversation_state = {"stage": "IDLE"}
        SESSION_CARTS.pop(session_id, None)

    def _get_user_cart(self, session_id: str = "default_user"):
        if session_id not in SESSION_CARTS:
            SESSION_CARTS[session_id] = {"items": [], "total": 0.0}
        return SESSION_CARTS[session_id]
    def _parse_intent(self, message: str) -> dict:
        message_lower = message.lower()
        add_keywords = ['buy', 'add', 'get', 'want', 'need', 'order']
        modify_keywords = ['modify cart']
        view_cart_keywords = ['show my cart', 'view cart']
        confirm_keywords = ['confirm', 'checkout', 'pay', 'proceed', 'confirm order']
        clear_keywords = ["clear cart", "cancel", "cancel order"]
        remove_keywords = ['remove', 'delete']

        if any(keyword in message_lower for keyword in confirm_keywords): return {"intent": "CONFIRM_ORDER"}
        if any(keyword in message_lower for keyword in clear_keywords): return {"intent": "CLEAR_CART"}
        if any(keyword in message_lower for keyword in modify_keywords): return {"intent": "MODIFY_CART"}

        for keyword in remove_keywords:
            if keyword in message_lower:
                parts = message_lower.split(keyword, 1)
                if len(parts) > 1 and parts[1].strip():
                    product_name = parts[1].strip()
                    return {"intent": "REMOVE_FROM_CART", "product_name": product_name}

        for keyword in add_keywords:
            if keyword in message_lower:
                parts = message_lower.split(keyword, 1)
                if len(parts) > 1 and parts[1].strip():
                    payload = parts[1].strip() 
                    quantity = 1
                    quantity_match = re.search(r'(\d+)', payload) 
                    if quantity_match:
                        quantity = int(quantity_match.group(1))
                        payload = re.sub(r'(\d+)', '', payload).strip()

                    articles = ['a ', 'an ', 'some ']
                    for article in articles:
                        if payload.startswith(article):
                            payload = payload[len(article):]

                    product_name = payload.strip()
                    product_name = product_name.rstrip('s')
                    stop_words_at_end = ['to my order', 'from my cart', 'for me', 'please']
                    for phrase in stop_words_at_end:
                        if product_name.endswith(phrase):
                            product_name = product_name[:-len(phrase)].strip()

                    return {"intent": "ADD_TO_CART", "quantity": quantity, "product_name": product_name}

        if any(keyword in message_lower for keyword in view_cart_keywords): return {"intent": "VIEW_CART"}
        return {"intent": "UNKNOWN"}
    def _recalculate_cart_total(self, cart: dict):
        cart['total'] = sum(item['price'] * item['quantity'] for item in cart['items'])

    def _format_product_for_frontend(self, p: Product) -> dict:
        """
        Takes a Product SQLModel object and formats its dictionary
        with the correct image_url path for the frontend.
        """
        product_data = p.model_dump()
        image_filename = product_data.get("image_url")

        if image_filename:
            product_data["image_url"] = image_filename
        else:
            product_data["image_url"] = "default.jpeg"

        product_data["image"] = product_data["image_url"]
        return product_data

    def handle_message(self, db: Session, message: str, user: models.User) -> list[dict]:
        cart = self._get_user_cart()
        current_stage = self.conversation_state.get("stage")

        if current_stage == "AWAITING_CLARIFICATION":
            parsed_data = {"intent": "ADD_TO_CART", "product_name": message}
        elif current_stage == "AWAITING_CONFIRMATION":
            parsed_data = self._parse_intent(message)
            allowed_intents = ["CONFIRM_ORDER", "MODIFY_CART", "CLEAR_CART", "ADD_TO_CART", "REMOVE_FROM_CART"]
            if parsed_data['intent'] not in allowed_intents:
                 return [{"contentType": "text", "content": "Please choose an option by clicking one of the buttons."}]
        else:
            parsed_data = self._parse_intent(message)

        intent = parsed_data.get("intent")
        self.conversation_state["stage"] = "IDLE"

        if intent == "ADD_TO_CART":
            product_name = parsed_data["product_name"]
            products = db.exec(select(Product).where(Product.name.ilike(f"%{product_name}%"))).all()

            if not products:
                return [{"contentType": "text", "content": f"I couldn't find a product matching '{product_name}'. Please try another."}]

            if len(products) > 1:
                self.conversation_state["stage"] = "AWAITING_CLARIFICATION"

                product_list = [self._format_product_for_frontend(p) for p in products]
                return [{"contentType": "text", "content": "I found a few items. Which one did you mean?"}, {"contentType": "product_carousel", "products": product_list}]

            product = products[0]

            formatted_product = self._format_product_for_frontend(product)

            cart['items'].append({
                "product_id": product.id,
                "name": product.name,
                "quantity": 1,
                "price": product.price,
                "image_url": formatted_product["image_url"]
            })
            self._recalculate_cart_total(cart)

            suggestions = db.exec(select(Product).where(Product.id != product.id).limit(2)).all()
            suggestion_list = [self._format_product_for_frontend(p) for p in suggestions]

            self.conversation_state["stage"] = "AWAITING_CONFIRMATION"
            responses = [{"contentType": "text", "content": f"Great choice! I've added {product.name} to your cart."}, {"contentType": "cart_preview", "content": cart}]

            if suggestion_list:
                responses.append({"contentType": "proactive_suggestion", "content": "Customers who bought this also love:", "products": suggestion_list, "reason": "I selected these based on top-seller data and immediate availability."})

            responses.append({"contentType": "confirmation_prompt", "content": "Ready to go, or would you like to add anything else?", "options": ["Confirm Order", "Modify Cart", "Cancel Order"]})
            return responses

        if intent == "REMOVE_FROM_CART":
            product_name_to_remove = parsed_data["product_name"]
            item_to_remove = next((item for item in cart['items'] if product_name_to_remove in item['name'].lower()), None)

            if not item_to_remove:
                return [{"contentType": "text", "content": f"I couldn't find '{product_name_to_remove}' in your cart."}]

            cart['items'].remove(item_to_remove)
            self._recalculate_cart_total(cart)
            self.conversation_state["stage"] = "AWAITING_CONFIRMATION"
            return [{"contentType": "text", "content": f"Okay, I've removed {item_to_remove['name']} from your cart."}, {"contentType": "cart_preview", "content": cart}, {"contentType": "confirmation_prompt", "content": "Your cart is updated. What's next?", "options": ["Confirm Order", "Modify Cart", "Cancel Order"]}]

        if intent == "CONFIRM_ORDER":
            if not cart["items"]: return [{"contentType": "text", "content": "Your cart is empty."}]
            total = cart['total']
            self._clear_state_and_cart()
            empty_cart = self._get_user_cart()
            return [{"contentType": "text", "content": f"Confirmed! Your order for ${total:.2f} is being processed. Thank you!"}, {"contentType": "cart_preview", "content": empty_cart}]

        if intent == "MODIFY_CART":
            self.conversation_state["stage"] = "IDLE"
            return [{"contentType": "text", "content": "Okay, what would you like to change? You can ask me to add or remove another item."}]

        if intent == "CLEAR_CART":
            self._clear_state_and_cart()
            empty_cart = self._get_user_cart()
            return [{"contentType": "text", "content": "No problem, your cart has been cleared."}, {"contentType": "cart_preview", "content": empty_cart}]

        return [{"contentType": "text", "content": "I'm sorry, I didn't quite understand. To start, you can ask me to 'buy' an item."}]

ai_ordering_service = AIOrderingService()
