from groq import Groq
from backend.core.config import settings

class SummarizerAgent:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def summarize(self, text: str) -> str:
        prompt = f"Extract structured keys (Overview, Budget, Eligibility, Deliverables, Risks) from this tender document:\n\n{text[:4000]}"
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Summary generation failed: {str(e)}"

summarizer_agent = SummarizerAgent()