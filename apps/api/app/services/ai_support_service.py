import re
import random

class AISupportService:
    def _parse_support_intent(self, message: str) -> dict:
        """Simulated NLU for support-related queries."""
        message = message.lower()

        # Intent: Greeting
        if any(keyword in message for keyword in ["hello", "hi", "hey"]):
            return {"intent": "GREETING"}
        
        # Intent: Track Order / ETA
        track_match = re.search(r'(track|where is|eta for) my order\s*#?(\d+)', message)
        if track_match:
            order_id = track_match.group(2)
            return {"intent": "TRACK_ORDER", "order_id": order_id}

        # Intent: Cancel Order
        cancel_match = re.search(r'cancel my order\s*#?(\d+)', message)
        if cancel_match:
            order_id = cancel_match.group(2)
            return {"intent": "CANCEL_ORDER", "order_id": order_id}

        # Intent: Thank you
        if any(keyword in message for keyword in ["thanks", "thank you", "شكراً"]):
            return {"intent": "THANKS"}

        return {"intent": "UNKNOWN"}

    def handle_message(self, message: str) -> list[dict]:
        """Orchestrates a human-like support response."""
        parsed_data = self._parse_support_intent(message)
        intent = parsed_data.get("intent")

        if intent == "GREETING":
            responses = ["Hello! How can I assist you with your order today?", "Hi there! Do you have an order number I can help you with?"]
            return [{"contentType": "text", "content": random.choice(responses)}]

        if intent == "TRACK_ORDER":
            order_id = parsed_data["order_id"]
            # In a real app, you would fetch the order status from the database here.
            # For now, we simulate different statuses.
            statuses = [
                f"Of course! Order #{order_id} is currently in transit and is estimated to arrive in the next 15 minutes.",
                f"I've checked on order #{order_id}. It's currently being prepared at our facility and will be dispatched shortly.",
                f"Good news! Order #{order_id} has been delivered. Please let me know if there's anything else."
            ]
            return [{"contentType": "text", "content": random.choice(statuses)}]

        if intent == "CANCEL_ORDER":
            order_id = parsed_data["order_id"]
            # Simulate checking if the order can be cancelled.
            if random.choice([True, False]):
                return [{"contentType": "text", "content": f"I've successfully initiated the cancellation for order #{order_id}. You will receive a confirmation email shortly."}]
            else:
                return [{"contentType": "text", "content": f"I'm sorry, but it looks like order #{order_id} is already out for delivery and cannot be cancelled at this stage."}]

        if intent == "THANKS":
            responses = ["You're welcome! Is there anything else I can help with?", "My pleasure! Let me know if you need anything else."]
            return [{"contentType": "text", "content": random.choice(responses)}]

        return [{"contentType": "text", "content": "I'm sorry, I can only help with tracking or cancelling existing orders. Please provide your order number (e.g., 'track my order #123')."}]

ai_support_service = AISupportService()

