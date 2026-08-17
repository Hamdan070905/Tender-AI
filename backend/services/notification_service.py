class NotificationService:
    def send_email_alert(self, user_email: str, tender_title: str, match_score: float):
        # MVP: Mocking SMTP email dispatch
        print(f"📧 EMAIL SENT TO {user_email}: High match tender found! '{tender_title}' (Score: {match_score})")
        
    def send_in_app_notification(self, user_id: str, message: str):
        # MVP: Mocking WebSocket push
        print(f"🔔 IN-APP ALERT (User {user_id}): {message}")

notification_service = NotificationService()