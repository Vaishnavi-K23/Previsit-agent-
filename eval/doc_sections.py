"""Shared helpers so eval/run_eval.py (agent-level, LLM-dependent metrics)
and eval/run_deterministic_eval.py (SQL-engine-vs-ground-truth, no LLM) can
each regenerate their own section of docs/EVAL_RESULTS.md without
clobbering the other's. The two are independent by design: the
deterministic check costs nothing and can be re-run any time against the
full population; the agent-level check is rate-limited and accumulates
across multiple days via --resume. Neither script can assume the other has
run first, or run in this session, so each preserves what it doesn't own.
"""

DETERMINISTIC_START = "<!-- DETERMINISTIC_SECTION:START -->"
DETERMINISTIC_END = "<!-- DETERMINISTIC_SECTION:END -->"

AGENT_START = "<!-- AGENT_SECTION:START -->"
AGENT_END = "<!-- AGENT_SECTION:END -->"

MUTATION_START = "<!-- MUTATION_SECTION:START -->"
MUTATION_END = "<!-- MUTATION_SECTION:END -->"


def extract_section(doc_text: str, start_marker: str, end_marker: str) -> str | None:
    start = doc_text.find(start_marker)
    end = doc_text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        return None
    return doc_text[start : end + len(end_marker)]


def upsert_section(doc_text: str, section_text: str, start_marker: str, end_marker: str) -> str:
    """Replaces the marked section if present, else appends it after the
    title line (the first line of the file)."""
    start = doc_text.find(start_marker)
    end = doc_text.find(end_marker)
    if start != -1 and end != -1 and end > start:
        return doc_text[:start] + section_text + doc_text[end + len(end_marker) :]
    lines = doc_text.split("\n", 1)
    title = lines[0] if lines else "# Eval Results"
    rest = lines[1] if len(lines) > 1 else ""
    return f"{title}\n\n{section_text}\n{rest}"
