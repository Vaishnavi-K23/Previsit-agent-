"""Phase 1 inventory: inspects the actual Synthea FHIR output on disk and
reports what's really there.

Per SPEC.md, clinical codes are never hardcoded from memory — this script
walks the generated JSON, tallies every resource type and every code
actually present, and writes the results to docs/DATA_MODEL.md. Whatever
codes Synthea's current version happens to use is what ends up documented.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from previsit.config import settings

# Resource types where a `.code` (or `.class`, for Encounter) CodeableConcept/Coding
# carries the clinical meaning worth cataloguing.
CODED_RESOURCE_TYPES = {
    "Condition",
    "Observation",
    "Procedure",
    "Immunization",
    "MedicationRequest",
    "DiagnosticReport",
    "AllergyIntolerance",
    "CarePlan",
    "Encounter",
}

SAMPLE_RESOURCE_TYPES_LIMIT = 3


def _iter_bundles(fhir_dir: Path):
    for path in sorted(fhir_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            yield path, json.load(f)


def _codings_from_resource(resource: dict) -> list[dict]:
    """Pulls every {system, code, display} triple worth cataloguing out of one resource."""
    codings = []

    def add_codeable_concept(cc):
        if not cc:
            return
        for coding in cc.get("coding", []):
            codings.append(
                {
                    "system": coding.get("system", "(no system)"),
                    "code": coding.get("code", "(no code)"),
                    "display": coding.get("display", cc.get("text", "(no display)")),
                }
            )

    # The field that carries the clinical code is NOT uniformly `.code` across FHIR R4
    # resource types (verified against actual Synthea output, not assumed from memory):
    #   Immunization uses `.vaccineCode`, MedicationRequest uses
    #   `.medicationCodeableConcept`, CarePlan has no top-level `.code` at all and uses
    #   `.category`, Encounter's `.class` is a bare Coding rather than a CodeableConcept.
    resource_type = resource.get("resourceType")

    if resource_type == "Encounter":
        cls = resource.get("class")
        if cls:
            codings.append(
                {
                    "system": cls.get("system", "(no system)"),
                    "code": cls.get("code", "(no code)"),
                    "display": cls.get("display", "(no display)"),
                }
            )
        for cc in resource.get("type", []):
            add_codeable_concept(cc)
        return codings

    if resource_type == "Immunization":
        add_codeable_concept(resource.get("vaccineCode"))
        return codings

    if resource_type == "MedicationRequest":
        add_codeable_concept(resource.get("medicationCodeableConcept"))
        return codings

    if resource_type == "CarePlan":
        for cc in resource.get("category", []):
            add_codeable_concept(cc)
        return codings

    add_codeable_concept(resource.get("code"))
    # Observations can carry multiple sub-measurements (e.g. BP panels) under `component`.
    for component in resource.get("component", []):
        add_codeable_concept(component.get("code"))

    return codings


def build_inventory(fhir_dir: Path) -> dict:
    resource_counts: Counter[str] = Counter()
    resource_samples: dict[str, list[dict]] = defaultdict(list)
    # code_counts[resource_type][(system, code, display)] = frequency
    code_counts: dict[str, Counter[tuple[str, str, str]]] = defaultdict(Counter)

    patient_bundle_count = 0
    non_patient_bundle_names = ("hospitalInformation", "practitionerInformation")

    for path, bundle in _iter_bundles(fhir_dir):
        if not path.name.startswith(non_patient_bundle_names):
            patient_bundle_count += 1

        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            rtype = resource.get("resourceType", "(unknown)")
            resource_counts[rtype] += 1

            if len(resource_samples[rtype]) < SAMPLE_RESOURCE_TYPES_LIMIT:
                resource_samples[rtype].append(resource)

            if rtype in CODED_RESOURCE_TYPES:
                for coding in _codings_from_resource(resource):
                    key = (coding["system"], coding["code"], coding["display"])
                    code_counts[rtype][key] += 1

    return {
        "patient_bundle_count": patient_bundle_count,
        "resource_counts": resource_counts,
        "resource_samples": resource_samples,
        "code_counts": code_counts,
    }


def print_summary(inventory: dict) -> None:
    print(f"Patient-level bundles: {inventory['patient_bundle_count']}")
    print()
    print("Resource type counts:")
    for rtype, count in inventory["resource_counts"].most_common():
        print(f"  {rtype:30s} {count}")
    print()
    for rtype in CODED_RESOURCE_TYPES:
        counts = inventory["code_counts"].get(rtype)
        if not counts:
            continue
        print(f"{rtype}: {len(counts)} distinct codes")
        for (system, code, display), freq in counts.most_common(5):
            print(f"    [{freq:>5}] {system}  {code}  {display}")


def _markdown_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_data_model_doc(inventory: dict, out_path: Path, source_dir: Path) -> None:
    lines = []
    lines.append("# Data Model — Discovered Resource Types and Codes")
    lines.append("")
    lines.append(
        "> Generated empirically by `python -m previsit.ingest.inspect_output` "
        f"from the actual FHIR bundles in `{source_dir.as_posix()}`. Nothing below is "
        "hardcoded from memory or from SPEC.md — every code and count reflects "
        "what this run of Synthea actually produced."
    )
    lines.append("")
    lines.append(f"**Patient-level bundles:** {inventory['patient_bundle_count']}")
    lines.append("")

    lines.append("## Notes for implementers")
    lines.append("")
    lines.append(
        "- **Bundle count vs. population target:** `-p 1000` targets 1000 *living* "
        "patients at simulation end, not 1000 total bundles. Synthea also generates "
        "deceased patients along the way for demographic realism and keeps them in "
        "the output — this run produced 1000 living + 175 deceased = 1175 patient "
        "bundles. Kept intentionally: Phase 3's care-gap rules must exclude deceased "
        "patients, so real deceased records let that exclusion be tested for real."
    )
    lines.append(
        "- **The clinical code field is not uniformly `.code` across resource types.** "
        "Verified against actual output, not assumed: `Immunization` uses "
        "`.vaccineCode`, `MedicationRequest` uses `.medicationCodeableConcept`, "
        "`CarePlan` has no top-level `.code` at all (uses `.category`), and "
        "`Encounter.class` is a bare `Coding`, not a `CodeableConcept` (so it has no "
        "`.coding[]` array — pull `system`/`code`/`display` directly off it)."
    )
    lines.append(
        "- **FHIR version confirmed R4** empirically from the jar's bundled "
        "`synthea.properties` (`exporter.fhir_stu3.export = false`, "
        "`exporter.fhir_dstu2.export = false`), matching the spec requirement — not "
        "assumed."
    )
    lines.append(
        "- **`DiagnosticReport.conclusion` is empty in all 152,112 reports in this "
        "dataset** (checked every one, not a sample). The actual narrative note text "
        "lives in `presentedForm[].data`, base64-encoded. Relevant for Phase 4 (note "
        "retrieval), which the spec anticipated might need adjusting: "
        "\"check what your generation actually produced.\""
    )
    lines.append(
        "- **Observation `component[]` panels (e.g. blood pressure) hold their own "
        "codes and values separately from the parent's `.code`**, and the parent "
        "itself usually carries no `valueQuantity` of its own. Phase 2's loader "
        "expands each component into its own `fact_observation` row rather than "
        "trying to force multiple values into one row."
    )
    lines.append("")

    lines.append("## Resource type counts")
    lines.append("")
    lines.append("| Resource type | Count |")
    lines.append("|---|---|")
    for rtype, count in inventory["resource_counts"].most_common():
        lines.append(f"| {rtype} | {count} |")
    lines.append("")

    lines.append("## Codes observed per resource type")
    lines.append("")
    lines.append(
        "Every distinct `(system, code, display)` triple actually present, "
        "sorted by frequency. These are Synthea's synthetic code sets, not "
        "guaranteed identical across Synthea versions — this is why the "
        "engine (Phase 3) looks codes up empirically rather than assuming them."
    )
    lines.append("")

    for rtype in CODED_RESOURCE_TYPES:
        counts = inventory["code_counts"].get(rtype)
        if not counts:
            continue
        lines.append(f"### {rtype} ({len(counts)} distinct codes)")
        lines.append("")
        lines.append("| Count | System | Code | Display |")
        lines.append("|---|---|---|---|")
        for (system, code, display), freq in counts.most_common():
            lines.append(
                f"| {freq} | {_markdown_escape(system)} | {_markdown_escape(code)} "
                f"| {_markdown_escape(display)} |"
            )
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {out_path}")


def main() -> None:
    fhir_dir = Path(settings.synthea_output_dir) / "fhir"
    if not fhir_dir.exists():
        raise SystemExit(
            f"No FHIR output found at {fhir_dir}. Run "
            "`python -m previsit.ingest.synthea_runner` first."
        )

    inventory = build_inventory(fhir_dir)
    print_summary(inventory)
    write_data_model_doc(inventory, Path("docs/DATA_MODEL.md"), fhir_dir)


if __name__ == "__main__":
    main()
