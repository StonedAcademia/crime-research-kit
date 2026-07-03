"""Typed report page and SVG figure models."""

from core.models.reports.figures import Circle, Group, Line, Path, Rect, SvgDoc, SvgElement, Text
from core.models.reports.page import Dashboard, MetricBlock, ReportPage, TableBlock

__all__ = [
    "Circle",
    "Dashboard",
    "Group",
    "Line",
    "MetricBlock",
    "Path",
    "Rect",
    "ReportPage",
    "SvgDoc",
    "SvgElement",
    "TableBlock",
    "Text",
]
