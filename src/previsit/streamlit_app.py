"""Phase 7: Streamlit demo UI. Patient picker, rendered pre-visit card,
every citation expandable to show the exact underlying database record.

The expandable citation is the whole point of this screen: it's the one
place a reviewer can verify, for any specific claim on the card, that the
record it cites actually exists and says what the card says it says -
nothing here is invented, and this is where you'd catch it if it were.

Run: `streamlit run src/previsit/streamlit_app.py`
"""

from datetime import date, datetime

import streamlit as st
from sqlalchemy import text
from sqlalchemy.engine import Engine

from previsit.agent.graph import generate_previsit_card
from previsit.agent.guardrails import CITABLE_TABLES
from previsit.config import settings

st.set_page_config(page_title="Pre-Visit Clinical Intelligence Agent", layout="wide")


@st.cache_resource
def _engine() -> Engine:
    from previsit.ingest.loader import get_engine

    return get_engine()


def _jsonable(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _lookup_citation(engine: Engine, source_resource_id: str) -> tuple[str, dict] | None:
    """Every citation on a card came from CITABLE_TABLES in the first
    place (guardrails.py already verified this before the finding was
    accepted) - this just re-fetches the row to display it, it isn't a
    second validation pass."""
    with engine.connect() as conn:
        for table in CITABLE_TABLES:
            row = conn.execute(
                text(f"SELECT * FROM {table} WHERE source_resource_id = :sid"),
                {"sid": source_resource_id},
            ).mappings().fetchone()
            if row is not None:
                return table, {k: _jsonable(v) for k, v in dict(row).items()}
    return None


engine = _engine()

st.title("Pre-Visit Clinical Intelligence Agent")
st.caption(
    "100% synthetic Synthea-generated patients - no real clinical data. See "
    "docs/SAFETY_AND_PRIVACY.md. Model pinned to "
    f"`{settings.llm_model}` (provider `{settings.llm_provider}`)."
)

with engine.connect() as conn:
    patients = conn.execute(
        text(
            "SELECT patient_id, birth_date, gender, city, state FROM dim_patient "
            "WHERE deceased_flag = 0 ORDER BY patient_id"
        )
    ).mappings().all()

if not patients:
    st.error("No patients found in dim_patient - has the ingest pipeline run? See README.md Quickstart.")
    st.stop()

options = {
    f"{p['patient_id']}  —  {p['gender'] or '?'}, {p['city'] or '?'}, {p['state'] or '?'} "
    f"(b. {p['birth_date'].isoformat() if p['birth_date'] else '?'})": p["patient_id"]
    for p in patients
}
label = st.selectbox("Patient", list(options.keys()))
patient_id = options[label]

if "cards" not in st.session_state:
    st.session_state.cards = {}

generate = st.button("Generate / refresh card", type="primary")

if generate:
    with st.spinner(f"Generating card for {patient_id} (live LLM call, pinned model - may take 10-80s)..."):
        try:
            st.session_state.cards[patient_id] = generate_previsit_card(engine, patient_id)
        except Exception as exc:  # noqa: BLE001 - surface the real error to the demo user, don't crash the app
            st.error(f"Card generation failed: {type(exc).__name__}: {exc}")

card = st.session_state.cards.get(patient_id)

if card is None:
    st.info("Click **Generate / refresh card** to produce a pre-visit card for this patient.")
else:
    st.subheader(card.one_line_summary or "(no summary)")
    st.caption(f"Generated {card.generated_at.isoformat()}Z by `{card.model_used}`")

    if not card.findings:
        st.success("No findings - nothing flagged for this patient.")

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    severity_badge = {"high": "🔴 high", "medium": "🟠 medium", "low": "🟢 low"}
    for finding in sorted(card.findings, key=lambda f: severity_rank.get(f.severity, 3)):
        with st.container(border=True):
            st.markdown(
                f"**{finding.category.replace('_', ' ').title()}** · {severity_badge.get(finding.severity, finding.severity)}"
            )
            st.write(finding.statement)
            for sid in finding.source_resource_ids:
                with st.expander(f"Citation: `{sid}`"):
                    found = _lookup_citation(engine, sid)
                    if found is None:
                        st.error(
                            "No underlying record found for this id - this should never happen, since the "
                            "citation guardrail already verified it before this finding was accepted. Please "
                            "report this as a bug."
                        )
                    else:
                        table, row = found
                        st.caption(f"From `{table}`")
                        st.json(row)
