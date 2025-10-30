# apps/api/app/services/gamification_service.py

class GamificationService:
    def award_points_for_purchase(self, user_id: int, order_total: float):
        """Awards loyalty points based on the order total."""
        points_to_award = int(order_total) 
    
        print(f"Awarded {points_to_award} points to user {user_id}.")

    def check_and_award_badges(self, user_id: int):
        """Check user activity and award badges if criteria are met."""

        print(f"Checked for new badges for user {user_id}.")

gamification_service = GamificationService()
