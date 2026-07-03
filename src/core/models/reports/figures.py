"""Typed SVG figure model: geometry primitives rendered by templates."""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field


class _El(BaseModel):
    css_class: str = ""
    data: dict[str, str] = Field(default_factory=dict)
    title: str = ""


class Rect(_El):
    kind: Literal["rect"] = "rect"
    x: float
    y: float
    width: float
    height: float
    rx: float = 0.0
    fill: str = ""
    fill_opacity: float | str | None = None
    stroke: str = ""


class Circle(_El):
    kind: Literal["circle"] = "circle"
    cx: float
    cy: float
    r: float
    fill: str = ""
    fill_opacity: float | str | None = None


class Line(_El):
    kind: Literal["line"] = "line"
    x1: float
    y1: float
    x2: float
    y2: float
    stroke: str = ""
    stroke_width: float = 1.0
    stroke_opacity: float | str | None = None


class Path(_El):
    kind: Literal["path"] = "path"
    d: str
    fill: str = ""
    fill_opacity: float | str | None = None
    stroke: str = ""
    stroke_width: float = 1.0
    stroke_opacity: float | str | None = None


class Text(_El):
    kind: Literal["text"] = "text"
    x: float
    y: float
    content: str
    anchor: Literal["start", "middle", "end"] = "start"
    font_size: float = 12.0
    transform: str = ""


class Group(_El):
    kind: Literal["group"] = "group"
    transform: str = ""
    children: list[SvgElement] = Field(default_factory=list)


SvgElement = Union[Rect, Circle, Line, Path, Text, Group]
Group.model_rebuild()


class SvgDoc(BaseModel):
    width: float
    height: float
    view_box: str = ""
    css_class: str = ""
    style: str = ""
    role: str = ""
    aria_label: str = ""
    elements: list[SvgElement] = Field(default_factory=list)
