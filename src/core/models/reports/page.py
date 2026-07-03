"""Typed report page and dashboard models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.models.reports.figures import SvgDoc


class TableBlock(BaseModel):
    columns: list[str]
    rows: list[dict[str, str]]
    limit: int = 25
    title: str = ""


class MetricBlock(BaseModel):
    label: str
    value: str


class ReportPage(BaseModel):
    slug: str
    title: str
    case_title: str
    summary: str = ""
    include_private: bool = False
    generated_at: str = ""
    back_href: str = "analysis_charts.html"
    back_label: str = "Back to chart index"
    filters: list[str] = Field(default_factory=list)
    figure: SvgDoc | None = None
    metrics: list[MetricBlock] = Field(default_factory=list)
    table: TableBlock | None = None
    tables: list[TableBlock] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Dashboard(BaseModel):
    case_title: str
    include_private: bool = False
    generated_at: str = ""
    pages: list[ReportPage] = Field(default_factory=list)
