"""Extraction packet operations with a gated canonical import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..casefile import CasefileError, ensure_case, log_action
from .policy import PolicyError, ensure_staged_write, lint_guilt_labels
from .result import OpResult, local_op
from .runner import CrkRunner

IMPORT_REFUSAL = (
    "import_extraction writes canonical records and requires confirm=True "
    "after a human has reviewed the extraction packet."
)


def draft_extraction(runner: CrkRunner, case_dir: str, source_id: str, *, template: str = "generic") -> OpResult:
    return runner.run("draft_extraction", ["draft-extraction", case_dir, source_id, "--template", template])


def import_extraction(runner: CrkRunner, case_dir: str, packet_path: str, *, confirm: bool = False) -> OpResult:
    if confirm is not True:
        return OpResult(name="import_extraction", ok=False, errors=[IMPORT_REFUSAL])
    return runner.run("import_extraction", ["import-extraction", case_dir, packet_path])


def list_packets(case_dir: str) -> OpResult:
    def _list(case_dir: str) -> dict[str, Any]:
        staging = ensure_case(case_dir) / "staging" / "extractions"
        names = sorted(path.name for path in staging.glob("*.json")) if staging.exists() else []
        return {"packets": names}

    return local_op("list_packets", _list, case_dir)


def read_packet(case_dir: str, packet_name: str) -> OpResult:
    try:
        path = _packet_path(ensure_case(case_dir), packet_name)
    except (CasefileError, PolicyError) as exc:
        return OpResult(name="read_packet", ok=False, errors=[str(exc)])
    if not path.exists():
        return OpResult(name="read_packet", ok=False, errors=[f"Packet not found: {packet_name}"])
    return OpResult(name="read_packet", data={"packet": json.loads(path.read_text(encoding="utf-8")), "path": str(path)})


def save_packet(case_dir: str, packet_name: str, packet: dict[str, Any]) -> OpResult:
    try:
        case = ensure_case(case_dir)
        target = _packet_path(case, packet_name)
        ensure_staged_write(case, target)
    except (CasefileError, PolicyError) as exc:
        return OpResult(name="save_packet", ok=False, errors=[str(exc)])
    problems = lint_guilt_labels(packet)
    if problems:
        return OpResult(name="save_packet", ok=False, errors=problems)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log_action(case, "save_extraction_packet", {"packet": target.name})
    return OpResult(name="save_packet", data={"path": str(target)})


def _packet_path(case: Path, packet_name: str) -> Path:
    packet = Path(packet_name)
    if packet.is_absolute() or not packet.parts or packet.name != packet_name:
        raise PolicyError(f"Extraction packet must be a filename under staging/extractions: {packet_name}")
    return case / "staging" / "extractions" / packet.name
