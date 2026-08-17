from fastapi import APIRouter
search_router = APIRouter(prefix="/search", tags=["Search"])

@search_router.get("/saved")
def get_saved_searches():
    return [{"id": 1, "query": "3D concrete printing"}]