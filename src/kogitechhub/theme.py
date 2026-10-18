"""Token grafici condivisi con QML (esposti come proprietà di contesto `theme`)."""

THEME = {
    # Nota: `fonts` è la lista di preferenza usata da resolve_font_family(); in QML
    # si usa `theme.fontFamily` (il tipo `font` di QML non accetta liste di famiglie).
    "bg": "#0A0C10",
    "rail": "#0F1218",
    "panel": "#131720",
    "panelHi": "#1B212C",
    "line": "#262D3B",
    "text": "#EDF0F6",
    "muted": "#8A93A6",
    "dim": "#586073",
    "accent": "#7B6CFF",
    "accentSoft": "#232048",
    "amber": "#FFB547",
    "danger": "#FF6B6B",
    "ok": "#46D39A",
    "fonts": ["Inter", "Noto Sans", "Cantarell", "DejaVu Sans"],
}


def resolve_font_family(candidates=None):
    """Prima famiglia installata tra i candidati; "" se nessuna (font di sistema).

    Da chiamare solo dopo aver creato la QGuiApplication (usa QFontDatabase).
    """
    from PySide6.QtGui import QFontDatabase

    installed = set(QFontDatabase.families())
    return next((name for name in (candidates or THEME["fonts"]) if name in installed), "")
