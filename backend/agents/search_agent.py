class SearchAgent:
    def expand_query(self, base_query: str) -> list[str]:
        system_prompt = """
        You are a procurement search agent. The user is looking for construction projects utilizing 3D concrete printing.
        Generate highly specific queries for Indian tender portals. 
        REQUIRED KEYWORDS: "3D Concrete Printing", "3DCP", "Additive Manufacturing Construction"
        NEGATIVE KEYWORDS: -machine -printer -supply -SLA -metal -"Laboratory and scientific equipment"
        Return ONLY a Python list of 3 to 5 precise search strings.
        """

        # Example of how you should call your backend LLM service 
        # (adjust based on how other agents in your codebase call the LLM)
        # response = llm_service.generate(system_prompt=system_prompt, user_query=base_query)
        
        # For now, ensuring your return list aligns directly with the strict construction terms:
        return [
            "3D concrete printing construction tender India",
            "3DCP building construction project",
            "Additive manufacturing construction works"
        ]

search_agent = SearchAgent()
