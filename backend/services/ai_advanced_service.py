import json
import structlog
from services.llm_service import llm

log = structlog.get_logger()

# Context for Kelvin6k
KELVIN6K_CONTEXT = """
Company: Kelvin6k
Domain: Construction 3D Printing, Concrete Printing, Additive Manufacturing, Construction Robotics.
Focus: Infrastructure/Public Works projects, Civil Infrastructure, Smart Construction.
Capabilities: Advanced manufacturing equipment, robotics for construction, digital fabrication.
"""

class AIAdvancedService:
    @staticmethod
    async def _ask_llm_json(system_prompt: str, user_prompt: str) -> dict:
        try:
            txt = await llm.chat(
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                fast=True, json_mode=True
            )
            return json.loads(txt)
        except Exception as e:
            log.error("ai_advanced.llm_error", error=str(e))
            return {}

    @staticmethod
    async def calculate_match_score(tender_data: dict, company_profile: dict) -> dict:
        system_prompt = "You are an AI procurement matchmaker. Calculate match scores. Return valid JSON only."
        user_prompt = f"""
Evaluate the match between this tender and the company profile based on the following criteria:
Company Profile, Equipment, Certifications, Experience, Revenue, Previous Projects, Geographic Presence, Bid History.
Return a JSON object with scores out of 100 for each criteria and an overall score.

Tender: {json.dumps(tender_data)}
Company Profile: {json.dumps(company_profile)}

Output JSON format:
{{
  "overall_score": 85.5,
  "company_profile_score": 90.0,
  "equipment_score": 80.0,
  "certifications_score": 100.0,
  "experience_score": 75.0,
  "revenue_score": 85.0,
  "previous_projects_score": 80.0,
  "geographic_presence_score": 95.0,
  "bid_history_score": 70.0,
  "summary": "Short explanation of the score"
}}
"""
        return await AIAdvancedService._ask_llm_json(system_prompt, user_prompt)

    @staticmethod
    async def recommend_bid(tender_data: dict, company_profile: dict) -> dict:
        system_prompt = "You are an AI bidding strategist. Return valid JSON only."
        user_prompt = f"""
Analyze if the company should bid on this tender.

Tender: {json.dumps(tender_data)}
Company Profile: {json.dumps(company_profile)}

Output JSON format:
{{
  "recommendation": "Bid" or "Don't Bid",
  "confidence": 85.5,
  "risk": "High/Medium/Low",
  "estimated_profit": 50000.0,
  "estimated_effort": "High/Medium/Low",
  "reason": "Short explanation"
}}
"""
        return await AIAdvancedService._ask_llm_json(system_prompt, user_prompt)

    @staticmethod
    async def analyze_competitors(tender_data: dict) -> dict:
        system_prompt = "You are an AI competitive intelligence analyst for procurement. Return valid JSON only."
        user_prompt = f"""
Analyze likely competitors and winning strategies for this tender.

Tender: {json.dumps(tender_data)}

Output JSON format:
{{
  "previous_winners": ["Competitor A", "Competitor B"],
  "likely_competitors": ["Competitor C", "Competitor D"],
  "winning_strategy": "Short explanation of how to win",
  "winning_price_estimate": "Estimated winning bid amount or range"
}}
"""
        return await AIAdvancedService._ask_llm_json(system_prompt, user_prompt)

    @staticmethod
    async def estimate_cost(tender_data: dict) -> dict:
        system_prompt = "You are an AI cost estimator for construction and procurement. Return valid JSON only."
        user_prompt = f"""
Estimate the costs involved in fulfilling this tender.

Tender: {json.dumps(tender_data)}

Output JSON format:
{{
  "labour": 15000.0,
  "material": 25000.0,
  "machinery": 10000.0,
  "transportation": 5000.0,
  "contingency": 2000.0,
  "total": 57000.0
}}
"""
        return await AIAdvancedService._ask_llm_json(system_prompt, user_prompt)

    @staticmethod
    async def check_compliance(tender_data: dict, company_profile: dict) -> dict:
        system_prompt = "You are an AI compliance checker for procurement. Return valid JSON only."
        user_prompt = f"""
Check the company profile against the tender requirements to find compliance gaps.

Tender: {json.dumps(tender_data)}
Company Profile: {json.dumps(company_profile)}

Output JSON format:
{{
  "missing_documents": ["Document A", "Document B"],
  "missing_certifications": ["ISO 9001"],
  "eligibility_gaps": ["Revenue too low", "Not in correct state"]
}}
"""
        return await AIAdvancedService._ask_llm_json(system_prompt, user_prompt)

    @staticmethod
    async def score_relevance(tender_data: dict) -> dict:
        system_prompt = "You are the Opportunity Relevance Engine specifically calibrated for Kelvin6k. Return valid JSON only."
        user_prompt = f"""
Evaluate this tender specifically for Kelvin6k's business domain.

{KELVIN6K_CONTEXT}

Tender: {json.dumps(tender_data)}

Calculate the relevance score based on:
- Construction 3D Printing relevance
- Concrete/Additive Manufacturing keywords
- Construction Robotics relevance
- Infrastructure/Public Works projects
- Budget fit
- Geographic location (India/State)
- Technical capability match
- Equipment compatibility
- Organization type
- Tender category

Output JSON format:
{{
  "opportunity_score": 92.5,
  "match_level": "High/Medium/Low",
  "priority_level": "Critical/High/Medium/Low",
  "ai_recommendation": "Strongly consider bidding",
  "why_relevant": "Short explanation of what fits well",
  "why_not_relevant": "Short explanation of what doesn't fit"
}}
"""
        return await AIAdvancedService._ask_llm_json(system_prompt, user_prompt)

ai_advanced = AIAdvancedService()
