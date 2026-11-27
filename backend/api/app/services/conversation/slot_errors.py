"""The error slot and compose rendering raise. Kept in its own module so the compose modules need not import slot_copy."""


class SlotError(ValueError):
    """A slot the cards cannot back, or a fact typed outside a slot."""
