# Prepared transactional clear lifecycle

Canonical journal clear now keeps existing pending-order cancellation together
with cart clear and receipt in a caller-owned SQL transaction. Replays return
current cart/revision but never cancel orders created after the original clear.
Rollback restores the cart, pending-order state and absent receipt together.

Real PostgreSQL tests cover rollback, committed replay, newer cart and new pending
order preservation. Full local suite 842 passed, 4 skipped, 20 existing warnings.
This path remains prepared only. No traffic routing, user-stack migration,
deployment or credit/payment cancellation has been performed.
