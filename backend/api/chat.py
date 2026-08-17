from fastapi import APIRouter
chat_router = APIRouter(prefix="/chat", tags=["Chat"])

@chat_router.post("/{tender_id}")
def chat_with_tender(tender_id: str, message: str):
    return {"reply": "Yes, this tender requires ISO 9001 certification."}