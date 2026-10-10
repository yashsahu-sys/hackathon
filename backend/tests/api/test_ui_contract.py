"""The UI is plain HTML/JS; make sure the JS only touches elements that exist
and only calls API routes that exist, so a rename can't silently break the demo."""
import re
from pathlib import Path

from vani.api.app import create_app

WEB = Path(__file__).resolve().parents[3] / "web"


def test_js_element_ids_exist_in_html():
    html = (WEB / "index.html").read_text()
    js = (WEB / "app.js").read_text()
    ids = set(re.findall(r'id="([\w-]+)"', html))
    used = set(re.findall(r'\$\("([\w-]+)"\)', js))
    used |= {f"view-{v}" for v in ("call", "compare", "evidence")}
    assert used - ids == set(), used - ids


def test_js_api_routes_exist():
    js = (WEB / "app.js").read_text()
    calls = set(re.findall(r'(?:api|post)\(\s*[`"](/[\w-]+)', js))
    routes = {r.path for r in create_app().routes if hasattr(r, "path")}
    prefixes = {"/" + p.split("/")[3] for p in routes if p.startswith("/api/v1/")}
    assert calls and calls <= prefixes, calls - prefixes


def test_static_assets_referenced():
    html = (WEB / "index.html").read_text()
    for asset in ("/static/style.css", "/static/app.js"):
        assert asset in html and (WEB / asset.split("/")[-1]).exists()
