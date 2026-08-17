from fastapi import APIRouter
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])

@analytics_router.get("/dashboard")
def get_dashboard_metrics():
    return {
        "success_rate": "68%",
        "active_bids": 12,
        "win_loss_ratio": "3:1"
    }
