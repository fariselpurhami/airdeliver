# Recommendation query stays data

filter_and_recommend no longer interpolates the customer query into system-role policy. It sends customer_query and candidate products in one valid bounded user JSON envelope, using the existing14000-character structured context budget rather than blind5000-character JSON slicing. Ranking/fallback/candidate-ID grounding unchanged.

Structural test verifies customer/catalog markers only enter user data, not policy. Existing grounding tests pass. Full local migrated PostgreSQL19/Redis suite802 passed,4 skipped,20 existing warnings. No provider calls. Role separation is not proof that a learned model always resists malicious content or obeys constraints.
