from case_builder.pipeline.graph.review.gates import export_review_gate_node, packet_review_gate_node


def test_packet_gate_waits_without_approvals():
    gate = packet_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x", "packets": ["S1_extraction.json"]})

    assert update["status"] == "waiting_for_human_review"
    assert update["review_required"] is True


def test_packet_gate_passes_with_prior_approvals():
    gate = packet_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x", "approved_packets": ["S1_extraction.json"]})

    assert update["status"] == "packets_approved"
    assert update["review_required"] is False


def test_export_gate_waits_without_approval():
    gate = export_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x"})

    assert update["status"] == "waiting_for_human_review"
    assert update["review_required"] is True


def test_export_gate_passes_when_approved():
    gate = export_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x", "export_approved": True})

    assert update["status"] == "export_approved"
    assert update["review_required"] is False
