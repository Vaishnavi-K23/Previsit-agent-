from previsit.ingest.loader import (
    BUNDLE_KEY_BY_TABLE,
    LOAD_ORDER,
    RESET_ORDER,
    TABLE_SPECS,
    TABLES_REQUIRING_DELETE,
    _split_sql_batches,
)


def test_split_sql_batches_on_go_lines():
    sql_text = "CREATE TABLE a (x INT);\nGO\nCREATE TABLE b (y INT);\nGO\n"
    batches = _split_sql_batches(sql_text)
    assert batches == ["CREATE TABLE a (x INT);", "CREATE TABLE b (y INT);"]


def test_split_sql_batches_ignores_go_inside_a_statement():
    # A column or string literally containing "go" shouldn't be mistaken for
    # a batch separator - only a line that is *only* GO counts.
    sql_text = "CREATE TABLE goose (go_count INT);\nGO\n"
    batches = _split_sql_batches(sql_text)
    assert len(batches) == 1
    assert "goose" in batches[0]


def test_every_load_order_table_has_a_spec_and_bundle_key():
    for table in LOAD_ORDER:
        assert table in TABLE_SPECS, f"{table} missing from TABLE_SPECS"
        assert table in BUNDLE_KEY_BY_TABLE, f"{table} missing from BUNDLE_KEY_BY_TABLE"


def test_reset_order_is_exact_reverse_of_load_order():
    # Reset must tear down children before parents; load must build parents
    # before children. If these drift apart, one of the FK constraints breaks.
    assert RESET_ORDER == list(reversed(LOAD_ORDER))


def test_tables_requiring_delete_are_fk_referenced_targets():
    # dim_patient (every fact table) and fact_encounter (fact_observation)
    # are the only two tables anything else points a FOREIGN KEY at.
    assert TABLES_REQUIRING_DELETE == {"dim_patient", "fact_encounter"}
