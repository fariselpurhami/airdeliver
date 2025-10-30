# file: apps/api/app/services/experimentation_service.py

class ExperimentationService:
    """A service to manage both feature flags and A/B tests."""
    
    def __init__(self):
        self._flags = {"enable-new-product-card": (True, 100)}
        self._experiments = {
            "checkout-button-color": ["blue", "green"] 
        }

    def is_feature_enabled(self, flag_name: str) -> bool:
        """Simple check for a feature flag."""

        return self._flags.get(flag_name, (False, 0))[0]

    def get_user_variant(self, user_id: int, experiment_name: str) -> str:
        """Assigns a user to a variant for an A/B test."""
        variants = self._experiments.get(experiment_name)

        if not variants:
            return "control" 
        
        bucket = user_id % len(variants)
        return variants[bucket]

experimentation_service = ExperimentationService()
