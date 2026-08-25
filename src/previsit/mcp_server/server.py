"""Phase 7: MCP server exposing the same five deterministic tools the
LangGraph agent (agent/graph.py) calls internally - so they're directly
usable from Claude Code, Cursor, or any other MCP client, not just the
agent's own tool-calling loop. See README.md for client setup.

Every tool here is a thin wrapper around agent/tools.py: same SQL queries,
same Qdrant-filtered vector search, same guarantee that search results
never cross a patient_id boundary. No LLM reasoning happens in this
process - an MCP client's own model does whatever reasoning it wants on
top of these results, same as the agent does with compose_card.
"""

from previsit.agent import tools as _tools
from previsit.ingest.loader import get_engine

try:
    from mcp.server.mcpserver import MCPServer
except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
    raise ImportError("The 'mcp' package is required to run the MCP server: pip install 'mcp[cli]'") from exc

mcp = MCPServer(
    name="previsit-agent",
    instructions=(
        "Deterministic clinical data-retrieval tools over a 100% synthetic (Synthea-generated) "
        "patient population - see docs/SAFETY_AND_PRIVACY.md. Every result traces back to specific "
        "source_resource_ids; care gaps come from fixed SQL rules, never LLM judgment about whether a "
        "screening is due. search_patient_notes is hard-filtered to the given patient_id and cannot "
        "return another patient's data."
    ),
)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


@mcp.tool()
def get_patient_summary(patient_id: str) -> dict:
    """Demographics, active conditions, active medications, and latest vitals for one patient."""
    return _tools.get_patient_summary(_get_engine(), patient_id).model_dump(mode="json")


@mcp.tool()
def check_care_gaps(patient_id: str) -> list[dict]:
    """Deterministic care-gap findings (overdue screenings, uncontrolled labs, etc.) for one
    patient, computed by fixed SQL rules - never an LLM judgment call about what's due."""
    return [g.model_dump(mode="json") for g in _tools.check_care_gaps(_get_engine(), patient_id)]


@mcp.tool()
def get_recent_encounters(patient_id: str, months: int = 12) -> list[dict]:
    """Encounters for one patient in the last N months (default 12), most recent first."""
    return [
        e.model_dump(mode="json") for e in _tools.get_recent_encounters(_get_engine(), patient_id, months=months)
    ]


@mcp.tool()
def find_documentation_gaps(patient_id: str) -> list[dict]:
    """Recurring chief-complaint symptoms with no corresponding coded condition for a diabetic
    patient - framed for human review only, never a coding recommendation."""
    return [g.model_dump(mode="json") for g in _tools.find_documentation_gaps(_get_engine(), patient_id)]


@mcp.tool()
def search_patient_notes(patient_id: str, query: str, k: int = 5) -> list[dict]:
    """Semantic search over one patient's clinical notes, hard-filtered to that patient_id -
    structurally cannot return another patient's data regardless of the query text."""
    return [c.model_dump(mode="json") for c in _tools.search_notes(patient_id=patient_id, query=query, k=k)]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
