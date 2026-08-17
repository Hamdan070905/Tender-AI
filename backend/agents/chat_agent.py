class ChatAgent:
    def answer_tender_question(self, question: str, tender_context: str) -> str:
        # MVP Mock: In full version, this uses RAG over the Qdrant vector DB
        return f"Based on the tender context, here is the answer to: {question}"

chat_agent = ChatAgent()