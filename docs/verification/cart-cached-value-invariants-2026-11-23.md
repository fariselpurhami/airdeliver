# Validate cached cart values before hydration

CartItemModel now requires positive strict integer product IDs, strict integer quantity1-99, and finite nonnegative Decimal prices. Cart total must be finite/nonnegative. Corrupt cached data fails closed before add/sync can overwrite it or emit a success. Existing valid numeric Decimal/string prices remain supported; UI money still comes from server verification at checkout.

Thirteen regression cases cover NaN/infinity/negative prices or totals, boolean/fractional/string/excess quantities, and invalid IDs. Full disposable PostgreSQL19/Redis suite768 passed,4 skipped,20 existing warnings. This is shape/value validation, not a signed cache, live stock guarantee, currency conversion, or cross-store transaction. Corrupt carts remain preserved for investigation rather than silently replaced with an empty one.
