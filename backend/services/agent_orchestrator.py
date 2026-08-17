import json
import structlog
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END
from services.llm_service import llm

log = structlog.get_logger()

class ProposalState(TypedDict):
    tender_id: str
    tender_context: str
    draft_proposal: str
    technical_feedback: str
    financial_feedback: str
    iteration: int
    is_approved: bool

async def generate_draft(state: ProposalState) -> ProposalState:
    log.info("agent.generator.run", iteration=state.get("iteration", 0))
    prompt = f"Write a comprehensive construction 3D printing proposal for the following tender. Tender Context:\n{state.get('tender_context', '')}\n\nCurrent Draft (if any to improve):\n{state.get('draft_proposal', '')}\nTechnical Feedback:\n{state.get('technical_feedback', '')}\nFinancial Feedback:\n{state.get('financial_feedback', '')}"
    
    response = await llm.chat([
        {"role": "system", "content": "You are an expert AI bid writer for Kelvin6k, a 3D concrete printing company."},
        {"role": "user", "content": prompt}
    ])
    
    return {"draft_proposal": response, "iteration": state.get("iteration", 0) + 1}

async def technical_auditor(state: ProposalState) -> ProposalState:
    log.info("agent.technical_auditor.run")
    prompt = f"Review this proposal for technical compliance and feasibility for 3D concrete printing. Tender Requirements:\n{state.get('tender_context', '')}\n\nDraft Proposal:\n{state.get('draft_proposal', '')}\n\nOutput ONLY valid JSON with format: {{\"compliant\": bool, \"feedback\": \"string\"}}"
    
    response = await llm.chat([
        {"role": "system", "content": "You are a strict technical compliance auditor for construction projects."},
        {"role": "user", "content": prompt}
    ], fast=True, json_mode=True)
    
    try:
        data = json.loads(response)
        return {"technical_feedback": data.get("feedback", ""), "is_approved": data.get("compliant", False)}
    except Exception:
        return {"technical_feedback": "Failed to parse technical audit.", "is_approved": False}

async def financial_auditor(state: ProposalState) -> ProposalState:
    log.info("agent.financial_auditor.run")
    prompt = f"Review this proposal for financial risks, missing guarantees, and budget compliance. Tender Requirements:\n{state.get('tender_context', '')}\n\nDraft Proposal:\n{state.get('draft_proposal', '')}\n\nOutput ONLY valid JSON with format: {{\"compliant\": bool, \"feedback\": \"string\"}}"
    
    response = await llm.chat([
        {"role": "system", "content": "You are a strict financial and legal auditor for construction projects."},
        {"role": "user", "content": prompt}
    ], fast=True, json_mode=True)
    
    try:
        data = json.loads(response)
        current_approval = state.get("is_approved", True)
        return {"financial_feedback": data.get("feedback", ""), "is_approved": current_approval and data.get("compliant", False)}
    except Exception:
        return {"financial_feedback": "Failed to parse financial audit.", "is_approved": False}

def should_continue(state: ProposalState) -> str:
    if state.get("is_approved", False) or state.get("iteration", 0) >= 3:
        return END
    return "generate_draft"

# Build Graph
graph_builder = StateGraph(ProposalState)
graph_builder.add_node("generate_draft", generate_draft)
graph_builder.add_node("technical_auditor", technical_auditor)
graph_builder.add_node("financial_auditor", financial_auditor)

graph_builder.set_entry_point("generate_draft")
graph_builder.add_edge("generate_draft", "technical_auditor")
graph_builder.add_edge("technical_auditor", "financial_auditor")
graph_builder.add_conditional_edges("financial_auditor", should_continue, {END: END, "generate_draft": "generate_draft"})

proposal_orchestrator = graph_builder.compile()
