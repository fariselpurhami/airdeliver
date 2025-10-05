import re
from sqlmodel import Session, select
from app.models.product import Product
import random

# A simple in-memory store to simulate a user's session cart.
SESSION_CARTS = {}

class AIOrderingService:
    def _get_user_cart(self, session_id: str = "default_user"):
        """Gets or creates a cart for the current user session."""
        if session_id not in SESSION_CARTS:
            SESSION_CARTS[session_id] = {"items": [], "total": 0.0}
        return SESSION_CARTS[session_id]

    def _parse_intent(self, message: str) -> dict:
        """Simulated NLU with expanded intents."""
        message = message.lower()
        
        # Intent: Greeting
        if any(keyword in message for keyword in ["hello", "hi", "hey", "مرحباً", "أهلاً"]):
            return {"intent": "GREETING"}

        # Intent: Add to cart
        add_match = re.search(r'(buy|add|get|want|i need)\s*(\d*)\s*(.*)', message)
        if add_match:
            quantity = int(add_match.group(2)) if add_match.group(2) else 1
            product_name = add_match.group(3).strip().rstrip('s')
            return {"intent": "ADD_TO_CART", "quantity": quantity, "product_name": product_name}

        # Intent: Remove from cart
        remove_match = re.search(r'(remove|delete)\s*(\d*)\s*(.*)', message)
        if remove_match:
            quantity = int(remove_match.group(2)) if remove_match.group(2) else None # Optional quantity
            product_name = remove_match.group(3).strip().rstrip('s')
            return {"intent": "REMOVE_FROM_CART", "quantity": quantity, "product_name": product_name}

        # Intent: View cart
        if any(keyword in message for keyword in ["show my cart", "what's in the cart", "view cart"]):
            return {"intent": "VIEW_CART"}
            
        # Intent: Confirm order
        if any(keyword in message for keyword in ["confirm order", "checkout", "i'm ready to pay"]):
            return {"intent": "CONFIRM_ORDER"}
        
        # Intent: Clear cart
        if "clear cart" in message or "start over" in message:
            return {"intent": "CLEAR_CART"}

        return {"intent": "UNKNOWN"}

    def _recalculate_cart_total(self, cart: dict):
        cart["total"] = sum(item['price'] * item['quantity'] for item in cart['items'])

    def handle_message(self, db: Session, message: str) -> list[dict]:
        """Orchestrates a more human-like response to a user's message."""
        cart = self._get_user_cart()
        parsed_data = self._parse_intent(message)
        intent = parsed_data.get("intent")

        if intent == "GREETING":
            greetings = ["Hello! What can I get for you today?", "Hi there! How can I help you shop?", "Welcome! Let me know what you're looking for."]
            return [{"contentType": "text", "content": random.choice(greetings)}]

        if intent == "ADD_TO_CART":
            product_name = parsed_data["product_name"]
            # Search for multiple products to handle ambiguity
            products = db.exec(select(Product).where(Product.name.ilike(f"%{product_name}%"))).all()
            
            if not products:
                return [{"contentType": "text", "content": f"I'm sorry, I couldn't find anything matching '{product_name}'. Could you be more specific?"}]
            
            # NEW: Clarification question if multiple products are found
            if len(products) > 1:
                product_names = ", ".join([f"'{p.name}'" for p in products])
                return [{"contentType": "text", "content": f"I found a few items matching that: {product_names}. Which one did you mean?"}]
            
            product = products[0]
            existing_item = next((item for item in cart["items"] if item["product_id"] == product.id), None)
            if existing_item:
                existing_item["quantity"] += parsed_data["quantity"]
            else:
                cart["items"].append({"product_id": product.id, "name": product.name, "quantity": parsed_data["quantity"], "price": product.price})
            
            self._recalculate_cart_total(cart)
            responses = [
                f"Alright, I've added {parsed_data['quantity']} of '{product.name}' to your cart.",
                "Here's how your cart looks now. Ready for anything else?",
                "Got it! Your cart is updated."
            ]
            return [
                {"contentType": "text", "content": random.choice(responses)},
                {"contentType": "cart_preview", "content": cart}
            ]

        if intent == "VIEW_CART":
            if not cart["items"]:
                return [{"contentType": "text", "content": "Your cart is currently empty. What can I help you find?"}]
            return [
                {"contentType": "text", "content": "Of course, here is what's in your cart right now:"},
                {"contentType": "cart_preview", "content": cart}
            ]

        if intent == "CONFIRM_ORDER":
            if not cart["items"]:
                return [{"contentType": "text", "content": "Your cart is empty, so there's nothing to confirm yet. Shall we add some items?"}]
            total = cart['total']
            SESSION_CARTS.pop("default_user", None) # Clear cart
            return [{"contentType": "text", "content": f"Perfect! Your order for ${total:.2f} is confirmed. We're now processing the payment and will schedule your delivery shortly. Thank you for shopping with us!"}]
        
        if intent == "CLEAR_CART":
            SESSION_CARTS.pop("default_user", None)
            return [{"contentType": "text", "content": "No problem, I've cleared your cart. Let's start over! What are you looking for?"}]

        return [{"contentType": "text", "content": "I'm sorry, I didn't quite understand that. You can ask me to 'add an item', 'show my cart', or 'confirm order'."}]

ai_ordering_service = AIOrderingService()
