"""Windows consoles default to cp1252 and crash on Hindi output; force UTF-8."""
import sys


def utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
