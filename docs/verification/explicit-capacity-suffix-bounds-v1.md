# Explicit capacity suffix bounds

The shared typed capacity gate now accepts the existing exact minimum/maximum
markers after the typed capacity as well as before it. Arabic and English
source phrases retain their actual comparator, number, SI/IEC family and kind.
Contradictory/doubled bounds, missing evidence, ambiguous variants and unrelated
attributes still fail closed. No synonym model, extraction heuristic or guessed
unit conversion is introduced.

Tests exercise positive and exclusion card gates plus the actual per-target SQL,
reviewed writer, scope rejection and stale-publication cases with both Arabic
marker placements. Controlled extraction outputs are not multilingual model
quality evidence. Broader assignment/interpretation quality remains unverified.
