"""Text Cleaning — für SYRION Training Pipeline (lokal, kein externer Service)."""
from __future__ import annotations

import re
import html


def clean_text(text: str) -> str:
    """Bereinigt Text für Training: HTML, Whitespace, Normalisierung."""
    if not text or not isinstance(text, str):
        return ""
    # HTML entitäten
    text = html.unescape(text)
    # HTML Tags entfernen
    text = re.sub(r"<[^>]+>", " ", text)
    # URLs entfernen (für Training nicht nötig, aber Quelle bleibt in Memory)
    text = re.sub(r"https?://\S+", " ", text)
    # Mehrfache Whitespaces
    text = re.sub(r"\s+", " ", text)
    # Trim
    text = text.strip()
    # Zu lange/kurze Texte filtern später im Validator
    return text


def is_valid_for_training(text: str, *, min_len: int = 20, max_len: int = 2000) -> bool:
    """Prüft ob Text für Training geeignet (nicht zu kurz/lang, nicht nur Sonderzeichen)."""
    if not text:
        return False
    if len(text) < min_len or len(text) > max_len:
        return False
    # Mindestens ein Buchstabe
    if not re.search(r"[a-zA-ZäöüÄÖÜß]", text):
        return False
    # Nicht nur Wiederholungen
    if len(set(text.lower().split())) < 3:
        return False
    return True
