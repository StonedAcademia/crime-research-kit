import json

import pytest

from tests.helpers import KIT_ROOT, load_ledger_cli


def load_tcr():
    return load_ledger_cli()


def subcommand_parsers(tcr):
    return tcr.command_tree.commands


def require_command(tcr, *names):
    choices = subcommand_parsers(tcr)
    for name in names:
        if name in choices:
            return name
    pytest.xfail(f"CLI command not implemented yet: one of {', '.join(names)}")


def command_options(tcr, command):
    return {
        option
        for param in subcommand_parsers(tcr)[command].params
        if getattr(param, "param_type_name", None) == "option"
        for option in [*param.opts, *param.secondary_opts]
    }


def option_choices(tcr, command, option):
    for param in subcommand_parsers(tcr)[command].params:
        if getattr(param, "param_type_name", None) == "option" and option in [*param.opts, *param.secondary_opts]:
            return set(getattr(param.type, "choices", None) or [])
    return set()


def report_text(case_dir, captured, *name_terms):
    chunks = [captured.out, captured.err]
    for path in case_dir.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.lower()
        if all(term in lowered for term in name_terms):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def init_case(tcr, tmp_path, title="Improvement Coverage Case"):
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", title])
    return case_dir


def append_source(
    tcr,
    case_dir,
    source_id,
    *,
    publisher="Demo Daily",
    independence_group=None,
    source_type="news_article",
    filename=None,
    text=None,
    public_export=True,
):
    text_path = None
    if filename:
        path = case_dir / "raw" / "sources" / filename
        path.write_text(text or "", encoding="utf-8")
        text_path = f"raw/sources/{filename}"
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": source_id,
        "title": f"Synthetic source {source_id}",
        "source_type": source_type,
        "author": "Demo Reporter",
        "publisher": publisher,
        "date_published": "1978-04-12",
        "date_accessed": "2026-06-30",
        "url": f"https://example.test/{source_id.lower()}",
        "archive_url": None,
        "raw_path": None,
        "text_path": text_path,
        "reliability_grade": "B",
        "independence_group": independence_group,
        "notes": "Synthetic source for CRK improvement coverage.",
        "public_export": public_export,
    })


def append_claim(tcr, case_dir, claim_id, source_ids, **overrides):
    row = {
        "claim_id": claim_id,
        "claim": f"Synthetic claim {claim_id}",
        "claim_type": "background",
        "status": "single_source",
        "confidence": 0.7,
        "source_ids": source_ids,
        "contradicts": [],
        "supports": [],
        "privacy_review": "clear",
        "public_export": True,
        "notes": "Synthetic claim.",
    }
    row.update(overrides)
    tcr.append_jsonl(tcr.record_path(case_dir, "claims"), row)


def append_entity(tcr, case_dir, entity_id, **overrides):
    row = {
        "entity_id": entity_id,
        "entity_type": "person",
        "name": f"Person {entity_id}",
        "display_name": f"Person {entity_id}",
        "aliases": [],
        "status": "confirmed",
        "role_tags": ["person_mentioned"],
        "privacy_level": "public_figure",
        "living_status": "unknown",
        "source_ids": ["SA"],
        "claim_ids": [],
        "public_export": True,
        "notes": "Synthetic entity.",
    }
    row.update(overrides)
    tcr.append_jsonl(tcr.record_path(case_dir, "entities"), row)


def load_schema(schema_name):
    return json.loads(next((KIT_ROOT / "docs" / "schemas").rglob(schema_name)).read_text(encoding="utf-8"))


def validate_schema(schema_name, row):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(instance=row, schema=load_schema(schema_name))
