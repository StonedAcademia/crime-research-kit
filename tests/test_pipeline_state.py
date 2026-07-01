from case_builder.models.state import CaseBuilderState


def test_state_defaults_new_pipeline_fields():
    state = CaseBuilderState(case_dir="data/cases/x").normalized()

    assert state.source_urls == []
    assert state.source_ids == []
    assert state.packets == []
    assert state.approved_packets == []
    assert state.rejected_packets == []
    assert state.export_approved is False
    assert state.index_enabled is False


def test_thread_id_defaults_to_run_id():
    state = CaseBuilderState(case_dir="data/cases/x").normalized()

    assert state.thread_id == state.run_id


def test_explicit_thread_id_is_kept():
    state = CaseBuilderState(case_dir="data/cases/x", thread_id="thread-7").normalized()

    assert state.thread_id == "thread-7"


def test_round_trip_preserves_pipeline_fields():
    state = CaseBuilderState(
        case_dir="data/cases/x",
        source_urls=["https://example.com/a"],
        approved_packets=["S1_extraction.json"],
        export_approved=True,
        index_enabled=True,
    )

    clone = CaseBuilderState.from_dict(state.to_dict())

    assert clone.source_urls == ["https://example.com/a"]
    assert clone.approved_packets == ["S1_extraction.json"]
    assert clone.export_approved is True
    assert clone.index_enabled is True
