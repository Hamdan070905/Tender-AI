from fastapi import APIRouter
compliance_router = APIRouter(prefix="/compliance", tags=["Compliance"])

@compliance_router.post("/check")
def check_compliance(tender_id: str, proposal_text: str):
    return {"score": 95, "missing": ["Financial Audit 2023"]}