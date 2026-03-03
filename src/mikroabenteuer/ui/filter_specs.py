from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Sequence

import streamlit as st

Language = Literal["DE", "EN"]
WidgetType = Literal[
    "text_input",
    "date_input",
    "time_input",
    "select_slider",
    "slider",
    "selectbox",
    "number_input",
    "multiselect",
]
ModeType = Literal["sidebar", "events"]

Container = Any
OptionsFactory = Callable[[Language], Sequence[Any]]
FormatFunc = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class FilterFieldSpec:
    id: str
    widget_type: WidgetType
    label_de: str
    label_en: str
    visible_in_modes: set[ModeType] = field(
        default_factory=lambda: {"sidebar", "events"}
    )
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    options: Optional[Sequence[Any]] = None
    options_factory: Optional[OptionsFactory] = None
    max_selections: Optional[int] = None
    max_chars: Optional[int] = None
    help_de: Optional[str] = None
    help_en: Optional[str] = None
    key_suffix: Optional[str] = None


def build_core_filter_specs(
    *,
    duration_options: Sequence[int],
    effort_options: Sequence[str],
    goal_options: Sequence[str],
    constraint_options: Sequence[str],
    material_options: Sequence[str],
    theme_options_factory: OptionsFactory,
) -> tuple[FilterFieldSpec, ...]:
    return (
        FilterFieldSpec(
            id="plz",
            widget_type="text_input",
            label_de="PLZ",
            label_en="Postal code",
            max_chars=5,
            help_de="5-stellige deutsche PLZ (z. B. 40215).",
            help_en="5-digit German postal code (e.g. 40215).",
        ),
        FilterFieldSpec(
            id="date",
            widget_type="date_input",
            label_de="Datum",
            label_en="Date",
        ),
        FilterFieldSpec(
            id="start_time",
            widget_type="time_input",
            label_de="Startzeit",
            label_en="Start time",
        ),
        FilterFieldSpec(
            id="available_minutes",
            widget_type="select_slider",
            label_de="Verfügbare Zeit (Minuten)",
            label_en="Available time (minutes)",
            options=duration_options,
        ),
        FilterFieldSpec(
            id="radius_km",
            widget_type="slider",
            label_de="Radius (km)",
            label_en="Radius (km)",
            min_value=0.5,
            max_value=50.0,
            step=0.5,
        ),
        FilterFieldSpec(
            id="effort",
            widget_type="selectbox",
            label_de="Aufwand",
            label_en="Effort",
            options=effort_options,
        ),
        FilterFieldSpec(
            id="budget_eur_max",
            widget_type="number_input",
            label_de="Budget (max €)",
            label_en="Budget (max €)",
            min_value=0.0,
            max_value=250.0,
            step=1.0,
        ),
        FilterFieldSpec(
            id="topics",
            widget_type="multiselect",
            label_de="Themen",
            label_en="Topics",
            options_factory=theme_options_factory,
        ),
        FilterFieldSpec(
            id="goals",
            widget_type="multiselect",
            label_de="Ziele",
            label_en="Goals",
            options=goal_options,
            max_selections=2,
        ),
        FilterFieldSpec(
            id="constraints",
            widget_type="multiselect",
            label_de="Rahmenbedingungen",
            label_en="Constraints",
            options=constraint_options,
        ),
        FilterFieldSpec(
            id="available_materials",
            widget_type="multiselect",
            label_de="Haushaltsmaterialien (verfügbar)",
            label_en="Available household materials",
            options=material_options,
        ),
    )


def render_filter_fields(
    specs: Sequence[FilterFieldSpec],
    namespace: str,
    mode: ModeType,
    lang: Language,
    *,
    on_change_handler: Optional[Callable[..., None]] = None,
    on_change_kwargs: Optional[dict[str, Any]] = None,
    container: Optional[Container] = None,
    formatters: Optional[dict[str, FormatFunc]] = None,
) -> dict[str, Any]:
    target = container or st
    values: dict[str, Any] = {}
    field_formatters = formatters or {}

    for spec in specs:
        if mode not in spec.visible_in_modes:
            continue

        key_suffix = spec.key_suffix or spec.id
        key = f"{namespace}_{key_suffix}"
        label = spec.label_de if lang == "DE" else spec.label_en
        help_text = spec.help_de if lang == "DE" else spec.help_en
        options = spec.options_factory(lang) if spec.options_factory else spec.options
        formatter = field_formatters.get(spec.id)

        widget_kwargs: dict[str, Any] = {"key": key}
        if help_text:
            widget_kwargs["help"] = help_text
        if on_change_handler is not None:
            widget_kwargs["on_change"] = on_change_handler
            widget_kwargs["kwargs"] = on_change_kwargs or {}

        if spec.widget_type == "text_input":
            if spec.max_chars is not None:
                widget_kwargs["max_chars"] = spec.max_chars
            value = target.text_input(label, **widget_kwargs)
        elif spec.widget_type == "date_input":
            value = target.date_input(label, **widget_kwargs)
        elif spec.widget_type == "time_input":
            value = target.time_input(label, **widget_kwargs)
        elif spec.widget_type == "select_slider":
            if options is None:
                raise ValueError(
                    f"Field '{spec.id}' requires options for select_slider"
                )
            value = target.select_slider(label, options=options, **widget_kwargs)
        elif spec.widget_type == "slider":
            value = target.slider(
                label,
                min_value=spec.min_value,
                max_value=spec.max_value,
                step=spec.step,
                **widget_kwargs,
            )
        elif spec.widget_type == "selectbox":
            if options is None:
                raise ValueError(f"Field '{spec.id}' requires options for selectbox")
            if formatter is not None:
                widget_kwargs["format_func"] = formatter
            value = target.selectbox(label, options=options, **widget_kwargs)
        elif spec.widget_type == "number_input":
            value = target.number_input(
                label,
                min_value=spec.min_value,
                max_value=spec.max_value,
                step=spec.step,
                **widget_kwargs,
            )
        elif spec.widget_type == "multiselect":
            if options is None:
                raise ValueError(f"Field '{spec.id}' requires options for multiselect")
            widget_kwargs.pop("help", None)
            if formatter is not None:
                widget_kwargs["format_func"] = formatter
            if spec.max_selections is not None:
                widget_kwargs["max_selections"] = spec.max_selections
            value = target.multiselect(
                label, options=options, help=help_text, **widget_kwargs
            )
        else:
            raise ValueError(f"Unsupported widget type '{spec.widget_type}'")

        values[spec.id] = value

    return values
