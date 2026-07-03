"""Typed report page and dashboard models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.models.reports.figures import SvgDoc


class TableBlock(BaseModel):
    columns: list[str]
    rows: list[dict[str, str]]
    limit: int = 25


class ReportPage(BaseModel):
    slug: str
    title: str
    case_title: str
    summary: str = ""
    include_private: bool = False
    generated_at: str = ""
    filters: list[str] = Field(default_factory=list)
    figure: SvgDoc | None = None
    legacy_figure_svg: str = ""
    table: TableBlock | None = None
    notes: list[str] = Field(default_factory=list)


class Dashboard(BaseModel):
    case_title: str
    include_private: bool = False
    generated_at: str = ""
    pages: list[ReportPage] = Field(default_factory=list)
