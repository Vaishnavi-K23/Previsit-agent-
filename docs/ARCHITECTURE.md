# Architecture

> This file is a Phase 8 deliverable per SPEC.md and will hold the full
> system architecture (diagram, component responsibilities, data flow)
> once the agent and API layers exist. It's started early to record one
> finding, made while designing Phase 5's `find_documentation_gaps` tool,
> that shapes that tool's design and shouldn't get lost by Phase 8.

## The "History of Present Illness" section is circular for documentation-gap detection

`find_documentation_gaps` is specced (SPEC.md Phase 5) to find conditions
"mentioned in notes but not on the coded problem list." The obvious first
approach - scan each note's free-text body for condition mentions and check
whether they're coded - doesn't work on this dataset, and the reason is
structural, not a data-quality accident.

**Finding:** Synthea's `DocumentReference` notes have a fixed template
(`# Chief Complaint`, `# History of Present Illness`, `# Social History`,
`# Allergies`, `# Medications`, `# Assessment and Plan`, `## Plan`). The
`History of Present Illness` section - the largest block of "narrative"
text in every note, and the section a naive implementation would scan
first - is generated as a **direct prose rendering of the patient's
already-coded condition list**:

> "Patient has a history of gingival disease (disorder), chronic kidney
> disease stage 3 (disorder), medication review due (situation), ..."

Every condition named in this sentence is drawn from `fact_condition` -
verified by construction (Synthea generates the note from the same
in-memory patient state it uses to emit the `Condition` resources) and by
direct inspection of multiple sample notes. Scanning this section for
"conditions mentioned but not coded" is checking the coded list against
itself; it can only ever produce a null result, which would be reported to
a clinician as false reassurance ("nothing found") rather than an honest
absence of the tool doing anything.

Corpus-wide characterization (73,448 notes) backs this up beyond the
sample notes: 94.2% of all note text is lines that appear verbatim in 2+
other notes, and even at a strict bar (a line has to recur in 5,000+
separate notes to count), 36.0% of all text is exact-line boilerplate. The
non-boilerplate remainder is overwhelmingly the HPI's slot-filled condition
list and templated Social History sentences (`"Patient identifies as
heterosexual."`, `"Patient comes from a middle socioeconomic
background."`) - not free clinical prose.

**Decision: `find_documentation_gaps` excludes the HPI section entirely**
and is built around the one part of these notes that *is* independent
information - the `# Chief Complaint` bullet list. Chief-complaint symptom
terms (e.g. "Tingling in Hands and Feet", "Blurred Vision") are drawn from
a fixed ~46-term vocabulary but are not simply restatements of
`fact_condition` - a patient can have a symptom charted repeatedly without
the condition it plausibly indicates ever being coded.

## Two symptom -> condition pairs shipped; a third was cut on evidence

Before building the tool, three candidate symptom -> condition pairs were
checked against the actual data (recurrence = the symptom appears in >= 2
distinct notes for the same patient):

- **Shipped: recurring "Tingling in Hands and Feet" + diabetic (Phase 3
  cohort) + no `368581000119106` (diabetic neuropathy) coded -> 12
  patients.** Checked further: all 12 already carry at least one *other*
  diabetes complication code (most often kidney disorder or
  microalbuminuria; 6 of 12 already have a retinopathy code). This tool is
  not catching totally undocumented diabetics - it's catching one specific
  missing complication code on patients whose charts already document
  other diabetic complications. The output framing reflects this: "no
  corresponding condition coded, please review," never implying the chart
  is otherwise empty.
- **Shipped (documented as a weaker signal): recurring "Blurred Vision" +
  diabetic + no retinopathy code (`1551000119108`, `1501000119109`,
  `97331000119101`) coded -> 3 patients.** Kept alongside the neuropathy
  pair specifically to show the symptom -> gap pattern generalizes beyond
  one hardcoded case, but 3 patients is a small sample - see the README's
  known-limitations section.
- **Cut: >= 2 of {Fatigue, Hunger, Thirst, Frequent Urination} recurring,
  as a signal for possibly-undiagnosed diabetes.** 80 living patients had
  this recurring classic symptom cluster. **78 of those 80 (97.5%) were
  already coded diabetic** under the Phase 3 cohort definition - only 2
  were not. This is a negative result worth keeping on record for a
  different reason than the other two: it's independent corroboration
  that the Phase 3 diabetic cohort broadening (base diagnosis +
  complication codes + insulin) is close to complete. If the cohort
  definition had been too narrow, this symptom cluster would have
  surfaced a meaningfully larger "undiagnosed" population; it didn't.
