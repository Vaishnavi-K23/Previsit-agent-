"""LangGraph definition for the pre-visit card agent.

Gather structured data deterministically first, let the LLM decide whether
narrative search adds useful context, then have the LLM compose the card -
every claim it makes still has to pass the citation guardrail
(agent/guardrails.py) before becoming part of the final PreVisitCard. The
LLM never computes a date, a threshold, or a citation on its own; it only
narrates what the deterministic tools already returned.

search_notes is the only tool exposed to the LLM's own tool-calling loop,
and even then patient_id is bound via closure at graph-construction time,
never left for the LLM to supply - it structurally cannot search a
different patient's notes, regardless of what a prompt-injected note might
ask it to do.
"""

from datetime import datetime
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from previsit.agent.guardrails import validate_findings
from previsit.agent.prompts import SYSTEM_PROMPT
from previsit.agent.tools import (
    check_care_gaps,
    find_documentation_gaps,
    get_patient_summary,
    get_recent_encounters,
    search_notes,
)
from previsit.config import settings
from previsit.llm.base import get_chat_model
from previsit.models import DocumentationGap, Encounter, Gap, NoteChunk, PatientSummary, PreVisitCard


class AgentState(TypedDict, total=False):
    patient_id: str
    engine: Engine
    model_name: str
    patient_summary: PatientSummary
    gaps: list[Gap]
    recent_encounters: list[Encounter]
    documentation_gaps: list[DocumentationGap]
    note_chunks: list[NoteChunk]
    raw_findings: list[dict]
    one_line_summary: str
    hallucination_count: int
    schema_violation_count: int
    rejected_findings: list[dict]
    card: PreVisitCard


# The LLM's structured-output target is deliberately looser than the
# Finding model (no min_length on source_resource_ids) - a finding with no
# citation is a real possible LLM output, and it needs to survive being
# parsed so the guardrail can reject and log it as a hallucination, rather
# than the whole structured-output call failing partway with a validation
# error that discards every other finding too.
class _RawFinding(BaseModel):
    category: str
    statement: str
    severity: str
    source_resource_ids: list[str] = []


class _CardDraft(BaseModel):
    one_line_summary: str
    findings: list[_RawFinding]


def gather_structured_data(state: AgentState) -> dict:
    engine = state["engine"]
    patient_id = state["patient_id"]
    return {
        "patient_summary": get_patient_summary(engine, patient_id),
        "gaps": check_care_gaps(engine, patient_id),
        "recent_encounters": get_recent_encounters(engine, patient_id),
        "documentation_gaps": find_documentation_gaps(engine, patient_id),
    }


def _make_search_notes_tool(patient_id: str):
    @tool
    def search_patient_notes(query: str) -> list[dict]:
        """Search this patient's clinical notes for narrative text related
        to the query. Only use this when a structured finding below needs
        supporting context from the notes - not as a first step, and not
        for anything not already implied by the structured findings."""
        chunks = search_notes(patient_id=patient_id, query=query, k=5)
        return [c.model_dump() for c in chunks]

    return search_patient_notes


def _format_structured_context(state: AgentState) -> str:
    summary = state["patient_summary"]
    lines = [
        f"Patient: age {summary.age}, gender {summary.gender}",
        f"Active conditions: {', '.join(summary.active_conditions) or 'none'}",
        f"Active medications: {', '.join(summary.active_medications) or 'none'}",
        f"Latest vitals: {summary.latest_vitals or 'none recorded'}",
        "",
        "Care gaps (already decided deterministically - report these, don't re-derive them):",
    ]
    for gap in state.get("gaps", []):
        lines.append(
            f"  [{gap.severity}] {gap.gap_title}: {gap.detail} "
            f"(source_resource_ids: {gap.source_resource_ids})"
        )
    if not state.get("gaps"):
        lines.append("  none")

    lines.append("")
    lines.append("Documentation gaps (already decided deterministically):")
    for dgap in state.get("documentation_gaps", []):
        lines.append(f"  {dgap.detail} (source_resource_ids: {dgap.source_resource_ids})")
    if not state.get("documentation_gaps"):
        lines.append("  none")

    lines.append("")
    lines.append("Recent encounters:")
    for enc in state.get("recent_encounters", []):
        lines.append(
            f"  {enc.start_datetime} class={enc.encounter_class} {enc.type_display} "
            f"(source_resource_id: {enc.source_resource_id})"
        )
    if not state.get("recent_encounters"):
        lines.append("  none in the last 12 months")

    note_chunks = state.get("note_chunks") or []
    if note_chunks:
        lines.append("")
        lines.append("Relevant note excerpts:")
        for chunk in note_chunks:
            snippet = chunk.text[:300].replace("\n", " ")
            lines.append(f'  "{snippet}" (source_resource_id: {chunk.source_resource_id})')

    return "\n".join(lines)


def maybe_search_notes(state: AgentState) -> dict:
    model = get_chat_model()
    tool_fn = _make_search_notes_tool(state["patient_id"])
    model_with_tool = model.bind_tools([tool_fn])

    context = _format_structured_context(state)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "You are deciding ONLY whether to call a tool right now. Do NOT "
                "write a summary, a card, or any findings text in this turn - "
                "composition happens in a separate step later, after this "
                "decision. Your only valid outputs here are: (a) exactly one "
                "call to search_patient_notes, or (b) no tool call at all.\n\n"
                "Here is the structured data gathered for this patient:\n\n"
                f"{context}\n\n"
                "A documentation gap above is based only on a COUNT of "
                "chief-complaint mentions - it does not include the actual "
                "wording clinicians used. Searching the notes for that symptom "
                "term lets you quote real clinical language, which makes the "
                "finding more concrete for the reviewer. If there is a "
                "documentation gap above, or any other finding whose statement "
                "would be strengthened by a supporting quote, call "
                "search_patient_notes with one focused query built from that "
                "finding's own symptom or condition term. If nothing above "
                "would benefit from a quote, do not call any tool."
            )
        ),
    ]
    response = model_with_tool.invoke(messages)

    note_chunks: list[NoteChunk] = []
    for call in getattr(response, "tool_calls", None) or []:
        if call["name"] == tool_fn.name:
            result = tool_fn.invoke(call["args"])
            note_chunks.extend(NoteChunk(**r) for r in result)

    return {"note_chunks": note_chunks}


def compose_card(state: AgentState) -> dict:
    model = get_chat_model()
    structured_model = model.with_structured_output(_CardDraft)

    context = _format_structured_context(state)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "Using ONLY the data below, compose the pre-visit card. Every "
                "finding must cite at least one source_resource_id that "
                "appears next to the fact it's based on - copy those ids "
                "exactly; never invent one.\n\n"
                f"{context}"
            )
        ),
    ]
    draft: _CardDraft = structured_model.invoke(messages)

    return {
        "raw_findings": [f.model_dump() for f in draft.findings],
        "one_line_summary": draft.one_line_summary,
    }


def apply_guardrail(state: AgentState) -> dict:
    engine = state["engine"]
    patient_id = state["patient_id"]
    result = validate_findings(engine, patient_id, state.get("raw_findings", []))

    card = PreVisitCard(
        patient_id=patient_id,
        one_line_summary=state.get("one_line_summary", ""),
        findings=result.accepted,
        generated_at=datetime.utcnow(),
        model_used=state.get("model_name", "unknown"),
    )
    return {
        "card": card,
        "hallucination_count": result.hallucination_count,
        "schema_violation_count": result.schema_violation_count,
        "rejected_findings": [
            {"raw": r.raw, "reason": r.reason, "category": r.category} for r in result.rejected
        ],
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("gather_structured_data", gather_structured_data)
    graph.add_node("maybe_search_notes", maybe_search_notes)
    graph.add_node("compose_card", compose_card)
    graph.add_node("apply_guardrail", apply_guardrail)

    graph.set_entry_point("gather_structured_data")
    graph.add_edge("gather_structured_data", "maybe_search_notes")
    graph.add_edge("maybe_search_notes", "compose_card")
    graph.add_edge("compose_card", "apply_guardrail")
    graph.add_edge("apply_guardrail", END)

    return graph.compile()


def generate_previsit_card(engine: Engine, patient_id: str) -> PreVisitCard:
    app = build_graph()
    result = app.invoke(
        {
            "patient_id": patient_id,
            "engine": engine,
            "model_name": settings.llm_model,
        }
    )
    return result["card"]
