import base64

from previsit.ingest.note_indexer import (
    build_chunk_records,
    chunk_text,
    extract_notes_from_bundle,
)


def test_chunk_text_short_text_is_one_chunk():
    text = "short note under the chunk size"
    chunks = chunk_text(text, chunk_size_words=150, overlap_words=30)
    assert chunks == [text]


def test_chunk_text_empty_string_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_overlap_between_consecutive_chunks():
    # 100 words, chunk_size=60, overlap=20, step=40 -> exactly 2 chunks:
    # [0:60) and [40:100), overlapping on words 40-59.
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size_words=60, overlap_words=20)

    assert len(chunks) == 2
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert len(first_words) == 60
    assert len(second_words) == 60
    assert first_words[-20:] == second_words[:20]  # exact overlap region
    assert second_words[-1] == "word99"  # final chunk reaches the end


def test_chunk_text_exact_multiple_of_step_does_not_duplicate_trailing_chunk():
    # 100 words, chunk_size=100 -> exactly one full chunk, no dangling
    # zero-length or duplicate second chunk.
    words = [f"w{i}" for i in range(100)]
    chunks = chunk_text(" ".join(words), chunk_size_words=100, overlap_words=20)
    assert len(chunks) == 1


def test_extract_notes_decodes_base64_and_uses_subject_reference():
    note_text = "2020-01-01\n# Chief Complaint\nNo complaints."
    encoded = base64.b64encode(note_text.encode("utf-8")).decode("ascii")
    bundle = {
        "entry": [
            {
                "resource": {
                    "resourceType": "DocumentReference",
                    "id": "doc-1",
                    "subject": {"reference": "urn:uuid:pat-1"},
                    "content": [{"attachment": {"contentType": "text/plain", "data": encoded}}],
                }
            },
            # Non-DocumentReference resources must be ignored, not raise.
            {"resource": {"resourceType": "Claim", "id": "claim-1"}},
        ]
    }
    notes = extract_notes_from_bundle(bundle)
    assert len(notes) == 1
    assert notes[0]["patient_id"] == "pat-1"
    assert notes[0]["source_resource_id"] == "doc-1"
    assert notes[0]["text"] == note_text


def test_build_chunk_records_preserves_patient_and_source_id_per_chunk():
    notes = [{"patient_id": "pat-1", "source_resource_id": "doc-1", "text": "one two three"}]
    records = build_chunk_records(notes)
    assert len(records) == 1
    assert records[0]["patient_id"] == "pat-1"
    assert records[0]["source_resource_id"] == "doc-1"
    assert records[0]["chunk_index"] == 0
