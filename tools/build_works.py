"""Regenerate design/film/shortform index.html grids from works/*.json.

Replaces content between <!-- WORKS:START --> and <!-- WORKS:END --> markers.
Run standalone: python tools/build_works.py
"""
from __future__ import annotations
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKS = ROOT / "works"
MARK_RE = re.compile(r"(<!-- WORKS:START -->)(.*?)(<!-- WORKS:END -->)", re.DOTALL)


def h(s: str) -> str:
    return escape(s or "", quote=True)


def render_filter_bar(filters: list[str], scope: str | None = None) -> str:
    scope_attr = f' data-scope="{scope}"' if scope else ""
    parts = [f'  <div class="filter-bar"{scope_attr}>']
    parts.append('    <button class="filter-tag active" data-filter="all">全部</button>')
    for f in filters:
        parts.append(
            f'    <button class="filter-tag" data-filter="{h(f)}">{h(f)}</button>'
        )
    parts.append("  </div>")
    return "\n".join(parts)


def render_design(data: dict) -> str:
    out = [render_filter_bar(data["filters"]), '  <div class="brand-grid cols-3">']
    for it in data["items"]:
        tag = it["tag"]
        title = it["title"]
        href = it.get("href")
        cover = it.get("cover")
        el, close = ("a", "a") if href else ("div", "div")
        href_attr = f' href="{h(href)}"' if href else ""
        classes = "brand-card has-img" if cover else "brand-card"
        out.append(f'    <{el}{href_attr} class="{classes}" data-tag="{h(tag)}">')
        if cover:
            out.append(
                f"      <div class=\"brand-card-img\" style=\"background-image:url('{h(cover)}');\"></div>"
            )
        out.append(f'      <span class="bc-tag">{h(tag)}</span>')
        out.append('      <div class="hover-overlay">')
        out.append(f'        <div class="hover-title">{h(title)}</div>')
        out.append("      </div>")
        out.append(f"    </{close}>")
    out.append("  </div>")
    return "\n".join(out)


def render_film(data: dict) -> str:
    out = []
    # Video
    v = data["video"]
    out.append('  <div class="section-label"><span>影片 ／ FILM</span></div>')
    out.append("")
    out.append(render_filter_bar(v["filters"], scope="video"))
    out.append("")
    out.append('  <div class="work-grid" data-scope="video">')
    for it in v["items"]:
        tag = it["tag"]
        label = it.get("tag_label", tag)
        title = it["title"]
        out.append(
            f'    <div class="work-card video" data-tag="{h(tag)}">'
            f'<span class="work-card-tag">{h(label)}</span>'
            f'<div class="work-card-title">{h(title)}</div></div>'
        )
    out.append("  </div>")
    out.append("")
    # Photo
    p = data["photo"]
    out.append('  <div class="section-label"><span>攝影 ／ PHOTOGRAPHY</span></div>')
    out.append("")
    out.append(render_filter_bar(p["filters"], scope="photo"))
    out.append("")
    out.append('  <div class="photo-grid" data-scope="photo">')
    for it in p["items"]:
        tag = it["tag"]
        title = it["title"]
        sub = it.get("sub", "")
        href = it.get("href")
        el, close = ("a", "a") if href else ("div", "div")
        href_attr = f' href="{h(href)}"' if href else ""
        out.append(
            f'    <{el}{href_attr} class="photo-theme work-card" data-tag="{h(tag)}">'
        )
        out.append(f'      <span class="work-card-tag">{h(tag)}</span>')
        out.append(f'      <div class="work-card-title">{h(title)}</div>')
        out.append(f'      <div class="photo-sub">{h(sub)}</div>')
        out.append(f"    </{close}>")
    out.append("  </div>")
    return "\n".join(out)


def render_shorts(data: dict) -> str:
    out = []
    out.append('  <section class="client-wall">')
    out.append('    <div class="client-wall-header">')
    out.append('      <div class="cw-en">LONG-TERM CLIENTS</div>')
    out.append("      <h3>長期合作客戶</h3>")
    out.append("    </div>")
    out.append('    <div class="client-wall-grid">')
    for c in data["clients"]:
        out.append('      <div class="client-card">')
        out.append(f'        <div class="client-name">{h(c["name"])}</div>')
        out.append(f'        <div class="client-industry">{h(c["industry"])}</div>')
        out.append("      </div>")
    out.append("    </div>")
    out.append("  </section>")
    out.append("")
    out.append('  <div class="section-label"><span>所有合作影片 ／ ALL CLIPS</span></div>')
    out.append("")
    out.append(render_filter_bar(data["filters"]))
    out.append("")
    out.append('  <div class="work-grid">')
    for it in data["items"]:
        tag = it["tag"]
        title = it["title"]
        out.append(
            f'    <div class="work-card video" data-tag="{h(tag)}">'
            f'<span class="work-card-tag">{h(tag)}</span>'
            f'<div class="work-card-title">{h(title)}</div></div>'
        )
    out.append("  </div>")
    return "\n".join(out)


PAGES = [
    ("design",   ROOT / "design"   / "index.html", "design.json",   render_design),
    ("film",     ROOT / "film"     / "index.html", "film.json",     render_film),
    ("shorts",   ROOT / "shortform"/ "index.html", "shorts.json",   render_shorts),
]


def build_one(name: str, html_path: Path, json_name: str, renderer) -> None:
    data = json.loads((WORKS / json_name).read_text(encoding="utf-8"))
    body = renderer(data)
    html = html_path.read_text(encoding="utf-8")
    new_block = f"<!-- WORKS:START -->\n{body}\n  <!-- WORKS:END -->"
    if not MARK_RE.search(html):
        raise SystemExit(f"[{name}] no WORKS markers in {html_path}")
    new_html = MARK_RE.sub(lambda _m: new_block, html, count=1)
    if new_html != html:
        html_path.write_text(new_html, encoding="utf-8")
        print(f"[{name}] updated {html_path.relative_to(ROOT)}")
    else:
        print(f"[{name}] no change")


def main() -> None:
    for args in PAGES:
        build_one(*args)


if __name__ == "__main__":
    main()
