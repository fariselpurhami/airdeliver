# apps/api/app/services/feature_flags.py

class FeatureFlags:
    def __init__(self):
        self._flags = {
            "new-checkout-flow": (False, 10),
            "ai-chatbot-enabled": True,
        }

    def is_enabled(self, flag_name: str, user_id: int) -> bool:

        is_global, percentage = self._flags.get(flag_name, (False, 0))

        if is_global:
            return True

        if (user_id % 100) < percentage:
            return True

        return False
