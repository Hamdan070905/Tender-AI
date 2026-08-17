from backend.connectors.ted_eu import TedEUConnector
from backend.agents.summarizer_agent import summarizer_agent
from backend.services.embedding_service import embedding_service

def run_tender_pipeline(query: str):
    """Simplified MVP LangGraph Orchestrator equivalent"""
    # 1. Search Agent
    connector = TedEUConnector()
    results = connector.search(query, limit=5)
    
    processed_tenders = []
    for res in results:
        # 2. Embedding / Ranking Agent (Mocked Match Score)
        vector = embedding_service.get_embedding(res.get("title", ""))
        match_score = 0.85  # In full version, calculate cosine similarity
        
        # 3. Summarizer Agent
        summary = summarizer_agent.summarize(res.get("title", ""))
        
        processed_tenders.append({
            "id": res.get("noticeId", "unknown"),
            "title": res.get("title", "No Title"),
            "source": connector.source_name,
            "match_score": match_score,
            "summary": summary
        })
        
    return processed_tenders