# Literal budget currency and Arabic decimal identity

ShoppingBrief grounding now requires a complete literal three-letter currency
token, case-insensitively, rather than a substring. USDT/USDA no longer ground USD.
The output currency remains uppercase. Explicit dollar forms retain existing
behavior. Arabic decimal separator is normalized only inside the amount token;
100or50cannot be borrowed from100.50. No currency conversion, locale currency
inference or change to unresolved-budget clarification behavior.

Seventeen tests cover literal source/cap/currency acceptance and actual strict
router output grounding. Existing shopping brief/copy tests remain unchanged.
These test mechanical amount identity, not multilingual budget interpretation.
