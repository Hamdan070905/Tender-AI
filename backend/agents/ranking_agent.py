class RankingAgent:
    def calculate_score(self, keyword_sim: float, embedding_sim: float, 
                        industry_match: float, budget_fit: float, 
                        location_score: float, deadline_score: float) -> float:
        """Applies the TenderAI match scoring formula"""
        score = (
            (keyword_sim * 0.30) +
            (embedding_sim * 0.25) +
            (industry_match * 0.15) +
            (budget_fit * 0.10) +
            (location_score * 0.10) +
            (deadline_score * 0.10)
        )
        return round(score, 2)

ranking_agent = RankingAgent()