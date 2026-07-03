"""Typer commands for ledger casework and intake."""

from __future__ import annotations

import typer

from crime_research_kit._runtime.adapters.interfaces.cli.commands import choice_enum, dispatch, enum_value
from crime_research_kit._runtime.adapters.ops.casework.records import extractions, validation, workspace
from crime_research_kit._runtime.adapters.ops.casework.records.intake import suggestions, web
from crime_research_kit._runtime.adapters.ops.casework.records.names import command as names_command

app = typer.Typer(no_args_is_help=True)

Grade = choice_enum("Grade", ["A", "B", "C", "D", "X"])
ExtractionTemplate = choice_enum("ExtractionTemplate", sorted(extractions.EXTRACTION_TEMPLATE_FILES))


@app.command("init-case", help="Create a case workspace")
def init_case(
    case_dir: str = typer.Argument(...),
    title: str | None = typer.Option(None, "--title"),
    scope: str | None = typer.Option(None, "--scope"),
    public_interest: str | None = typer.Option(None, "--public-interest"),
) -> None:
    dispatch(workspace.init_case, case_dir=case_dir, title=title, scope=scope, public_interest=public_interest)


@app.command("add-source", help="Register a source manually")
def add_source(
    case_dir: str = typer.Argument(...),
    title: str = typer.Option(..., "--title"),
    url: str | None = typer.Option(None, "--url"),
    source_type: str = typer.Option("news_article", "--source-type"),
    reliability_grade: Grade = typer.Option(Grade("C"), "--reliability-grade"),
    author: str | None = typer.Option(None, "--author"),
    publisher: str | None = typer.Option(None, "--publisher"),
    date_published: str | None = typer.Option(None, "--date-published"),
    archive_url: str | None = typer.Option(None, "--archive-url"),
    notes: str = typer.Option("", "--notes"),
    no_public_export: bool = typer.Option(False, "--no-public-export"),
) -> None:
    dispatch(
        workspace.add_source,
        case_dir=case_dir,
        title=title,
        url=url,
        source_type=source_type,
        reliability_grade=enum_value(reliability_grade),
        author=author,
        publisher=publisher,
        date_published=date_published,
        archive_url=archive_url,
        notes=notes,
        no_public_export=no_public_export,
    )


@app.command("ingest-url", help="Fetch URL, extract text, and register as a source")
def ingest_url(
    case_dir: str = typer.Argument(...),
    url: str = typer.Argument(...),
    title: str | None = typer.Option(None, "--title"),
    source_type: str = typer.Option("news_article", "--source-type"),
    reliability_grade: Grade = typer.Option(Grade("C"), "--reliability-grade"),
    author: str | None = typer.Option(None, "--author"),
    publisher: str | None = typer.Option(None, "--publisher"),
    date_published: str | None = typer.Option(None, "--date-published"),
    archive_url: str | None = typer.Option(None, "--archive-url"),
    notes: str = typer.Option("", "--notes"),
    timeout: int = typer.Option(25, "--timeout"),
    no_public_export: bool = typer.Option(False, "--no-public-export"),
) -> None:
    dispatch(
        web.ingest_url,
        case_dir=case_dir,
        url=url,
        title=title,
        source_type=source_type,
        reliability_grade=enum_value(reliability_grade),
        author=author,
        publisher=publisher,
        date_published=date_published,
        archive_url=archive_url,
        notes=notes,
        timeout=timeout,
        no_public_export=no_public_export,
    )


@app.command("draft-extraction", help="Create a structured extraction JSON packet for a source")
def draft_extraction(
    case_dir: str = typer.Argument(...),
    source_id: str = typer.Argument(...),
    excerpt_chars: int = typer.Option(6000, "--excerpt-chars"),
    template: ExtractionTemplate = typer.Option(ExtractionTemplate("generic"), "--template"),
) -> None:
    dispatch(
        extractions.draft_extraction,
        case_dir=case_dir,
        source_id=source_id,
        excerpt_chars=excerpt_chars,
        template=enum_value(template),
    )


@app.command("ner-suggest", help="Generate crude named-entity/date suggestions from source text")
def ner_suggest(
    case_dir: str = typer.Argument(...),
    source_id: str | None = typer.Option(None, "--source-id"),
    limit: int = typer.Option(80, "--limit"),
) -> None:
    dispatch(suggestions.ner_suggest, case_dir=case_dir, source_id=source_id, limit=limit)


@app.command("link-names", help="Link a list of names to existing events and co-mentions")
def link_names(
    case_dir: str = typer.Argument(...),
    name: list[str] = typer.Option([], "--name"),
    names_file: list[str] = typer.Option([], "--names-file"),
) -> None:
    dispatch(names_command.link_names, case_dir=case_dir, name=name, names_file=names_file)


@app.command("import-extraction", help="Import a filled extraction JSON packet into JSONL records")
def import_extraction(case_dir: str = typer.Argument(...), extraction_json: str = typer.Argument(...)) -> None:
    dispatch(extractions.import_extraction, case_dir=case_dir, extraction_json=extraction_json)


@app.command("validate", help="Validate case records")
def validate(case_dir: str = typer.Argument(...)) -> None:
    dispatch(validation.validate, case_dir=case_dir)
