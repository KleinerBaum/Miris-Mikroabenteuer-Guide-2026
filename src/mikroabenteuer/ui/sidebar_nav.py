from __future__ import annotations

from mikroabenteuer.constants import Language


def page_label_daily(lang: Language) -> str:
    if lang == "DE":
        return "Mikroabenteuer des Tages / Microadventure of the day"
    return "Microadventure of the day / Mikroabenteuer des Tages"


def page_label_library(lang: Language) -> str:
    if lang == "DE":
        return "Bibliothek / Library"
    return "Library / Bibliothek"
