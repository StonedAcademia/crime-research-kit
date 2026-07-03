"""Typer commands for public-records planning."""

from __future__ import annotations

import typer

from crime_research_kit._runtime.adapters.interfaces.cli.commands import choice_enum, dispatch, enum_values
from crime_research_kit._runtime.adapters.ops.casework.records.planning import open_records, public_records, transcripts

app = typer.Typer(no_args_is_help=True)

PublicRecordLane = choice_enum("PublicRecordLane", sorted(public_records.PUBLIC_RECORD_LANES))


@app.command("plan-public-records", help="Write a public-record source-lane plan for a subject")
def plan_public_records(
    case_dir: str = typer.Argument(...),
    subject: str = typer.Option(..., "--subject"),
    question: str = typer.Option("", "--question"),
    lane: list[PublicRecordLane] = typer.Option([], "--lane"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        public_records.plan_public_records,
        case_dir=case_dir,
        subject=subject,
        question=question,
        lane=enum_values(lane),
        out=out,
    )


@app.command("index-transcript", help="Index timestamp and speaker-line candidates from a source text transcript")
def index_transcript(
    case_dir: str = typer.Argument(...),
    source_id: str = typer.Argument(...),
    max_segments: int = typer.Option(200, "--max-segments"),
    include_private: bool = typer.Option(False, "--include-private"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        transcripts.index_transcript,
        case_dir=case_dir,
        source_id=source_id,
        max_segments=max_segments,
        include_private=include_private,
        out=out,
    )


@app.command("plan-open-records", help="Write a FOIA/open-records request plan for an agency and subject")
def plan_open_records(
    case_dir: str = typer.Argument(...),
    subject: str = typer.Option(..., "--subject"),
    agency: str = typer.Option(..., "--agency"),
    jurisdiction: str | None = typer.Option(None, "--jurisdiction"),
    law: str | None = typer.Option(None, "--law"),
    date_range: str | None = typer.Option(None, "--date-range"),
    record: list[str] = typer.Option([], "--record"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        open_records.plan_open_records,
        case_dir=case_dir,
        subject=subject,
        agency=agency,
        jurisdiction=jurisdiction,
        law=law,
        date_range=date_range,
        record=record,
        out=out,
    )
