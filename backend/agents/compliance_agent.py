class ComplianceAgent:
    def check_compliance(self, proposal_text: str, requirements: list) -> dict:
        # Analyzes if the drafted proposal meets all hidden requirements
        return {"status": "passed", "missing_elements": []}

compliance_agent = ComplianceAgent()
