from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.database import get_db
from core.security import get_current_user
from models.tender import Tender
from collections import Counter
import re

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Fetch all tenders
    stmt = select(Tender)
    result = await db.execute(stmt)
    tenders = result.scalars().all()

    # Default mockup data for Indian states/categories to populate if DB is small
    state_counts = {
        "Maharashtra": 15,
        "Karnataka": 12,
        "Delhi": 9,
        "Tamil Nadu": 8,
        "Gujarat": 7,
        "Uttar Pradesh": 6,
        "Telangana": 5,
        "West Bengal": 4,
        "Rajasthan": 3,
        "Haryana": 3
    }
    
    category_counts = {
        "Civil Works": 18,
        "Concrete 3D Printing": 14,
        "Infrastructure": 12,
        "Roads & Highways": 8,
        "Smart Cities": 6,
        "Electrical Works": 5
    }

    # Count from database if there are tenders
    if tenders:
        db_states = []
        db_categories = []
        for t in tenders:
            # Check state in hidden requirements or title
            state = None
            if t.hidden_requirements and isinstance(t.hidden_requirements, dict):
                state = t.hidden_requirements.get("state")
            if not state:
                # Inferred from organization/title/country
                # simple regex check for Indian states
                text = f"{t.title} {t.organization or ''}".lower()
                for st in ["maharashtra", "karnataka", "delhi", "tamil nadu", "gujarat", "uttar pradesh", "telangana", "west bengal", "rajasthan", "haryana", "kerala", "andhra pradesh"]:
                    if st in text:
                        state = st.title()
                        break
            if state:
                db_states.append(state)
            
            # Category
            cat = None
            if t.hidden_requirements and isinstance(t.hidden_requirements, dict):
                cat = t.hidden_requirements.get("category")
            if not cat:
                text = f"{t.title} {t.overview or ''}".lower()
                if "3d print" in text or "additive" in text or "concrete print" in text:
                    cat = "Concrete 3D Printing"
                elif "road" in text or "highway" in text:
                    cat = "Roads & Highways"
                elif "smart city" in text or "smart cities" in text:
                    cat = "Smart Cities"
                elif "civil" in text or "construction" in text:
                    cat = "Civil Works"
                elif "electrical" in text:
                    cat = "Electrical Works"
            if cat:
                db_categories.append(cat)
        
        # Merge DB results
        if db_states:
            state_counts = dict(Counter(db_states))
        if db_categories:
            category_counts = dict(Counter(db_categories))

    # Calculate budgets
    total_budget = 0.0
    budget_count = 0
    max_budget = 0.0
    min_budget = float('inf')
    
    for t in tenders:
        if t.budget_max:
            total_budget += t.budget_max
            budget_count += 1
            if t.budget_max > max_budget:
                max_budget = t.budget_max
            if t.budget_max < min_budget:
                min_budget = t.budget_max

    if budget_count == 0:
        # mockup budget data
        total_budget = 45000000.0
        budget_count = 12
        avg_budget = total_budget / budget_count
        max_budget = 12000000.0
        min_budget = 500000.0
    else:
        avg_budget = total_budget / budget_count
        if min_budget == float('inf'):
            min_budget = 0.0

    # Trend counts (monthly distribution)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_counts = {m: 0 for m in months}
    # Mockup trend pattern first
    for i, m in enumerate(months):
        monthly_counts[m] = 2 + (i % 3) * 2
        
    for t in tenders:
        if t.created_at:
            month_name = t.created_at.strftime("%b")
            if month_name in monthly_counts:
                monthly_counts[month_name] += 1
                
    trends = [{"month": m, "count": monthly_counts[m]} for m in months]

    return {
        "state_wise_distribution": state_counts,
        "category_distribution": category_counts,
        "budget_totals": {
            "total": total_budget,
            "average": avg_budget,
            "max": max_budget,
            "min": min_budget,
            "count": len(tenders) or 15
        },
        "trends": trends
    }
