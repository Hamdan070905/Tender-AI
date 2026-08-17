from openai import OpenAI
from backend.core.config import settings

class ProposalAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def draft_proposal(self, company_profile: str, tender_requirements: str) -> str:
        prompt = f"""
        Using the company profile: {company_profile}
        Write a professional proposal for these requirements: {tender_requirements}
        Include: Cover Letter, Executive Summary, Methodology.
        """
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content

proposal_agent = ProposalAgent()