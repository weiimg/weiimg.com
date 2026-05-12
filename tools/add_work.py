"""Local browser tool for adding portfolio works.

Run:   python tools/add_work.py
Open:  http://localhost:5000

Flow:
  1. Pick category (Design / Film video / Film photo / Shorts client / Shorts item)
  2. Fill in fields, optionally drop images (Design only)
  3. Submit -> renames + saves images, updates works/*.json, rebuilds index.html
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, request, redirect, url_for, flash, render_template_string

ROOT = Path(__file__).resolve().parent.parent
WORKS = ROOT / "works"
DESIGN_DIR = ROOT / "design"

sys.path.insert(0, str(ROOT / "tools"))
import build_works  # noqa: E402

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

app = Flask(__name__)
app.secret_key = "wei-local-tool"

SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slugify(s: str) -> str:
    s = (s or "").strip().lower().replace(" ", "-")
    s = SLUG_RE.sub("", s)
    return s or "untitled"


def load(name: str) -> dict:
    return json.loads((WORKS / name).read_text(encoding="utf-8"))


def save(name: str, data: dict) -> None:
    (WORKS / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def ensure_filter(data: dict, tag: str, key: str = "filters") -> None:
    if tag and tag not in data[key]:
        data[key].append(tag)


def save_image(file_storage, dest: Path, max_w: int = 2000, quality: int = 85) -> None:
    """Save uploaded image. If Pillow available, convert to webp + downscale."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if HAS_PIL:
        img = Image.open(file_storage.stream)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        img.save(dest, "WEBP", quality=quality, method=6)
    else:
        file_storage.save(dest)


def insert(items: list, entry: dict, position: str) -> None:
    if position == "top":
        items.insert(0, entry)
    else:
        items.append(entry)


PAGE = """<!doctype html>
<html lang="zh-Hant"><head>
<meta charset="utf-8">
<title>weiimg works — add</title>
<style>
:root { font-family: -apple-system, "Inter", "Noto Sans TC", sans-serif; }
body { max-width: 760px; margin: 40px auto; padding: 0 24px; color:#111; }
h1 { font-size: 22px; letter-spacing: -0.02em; margin-bottom: 4px; }
.sub { color:#888; font-size:13px; margin-bottom:28px; }
.tabs { display:flex; gap:4px; border-bottom:1px solid #ddd; margin-bottom:24px; flex-wrap:wrap;}
.tabs a { padding:10px 14px; font-size:13px; text-decoration:none; color:#666; border-bottom:2px solid transparent; margin-bottom:-1px; }
.tabs a.active { color:#111; border-bottom-color:#111; }
form { display:flex; flex-direction:column; gap:14px; }
label { font-size:12px; color:#666; display:flex; flex-direction:column; gap:4px; }
input[type=text], select, textarea { padding:10px 12px; font-size:14px; border:1px solid #ccc; border-radius:4px; font-family:inherit; }
input[type=file] { font-size:13px; }
button { padding:12px 20px; background:#111; color:#fff; border:0; border-radius:4px; font-size:14px; cursor:pointer; align-self:flex-start; margin-top:8px;}
button:hover { background:#333; }
.row { display:flex; gap:12px; }
.row > * { flex:1; }
.radio-row { flex-direction:row !important; gap:16px; align-items:center; }
.radio-row label { flex-direction:row; gap:4px; font-size:13px; color:#111; }
.flash { background:#e8f5e9; color:#1b5e20; padding:10px 14px; border-radius:4px; font-size:13px; margin-bottom:16px;}
.warn { background:#fff3e0; color:#bf360c; padding:10px 14px; border-radius:4px; font-size:13px; margin-bottom:16px;}
.hint { font-size:11px; color:#999; }
.preview-link { font-size:12px; color:#666; margin-top:8px; }
.preview-link a { color:#111; }
</style></head><body>
<h1>weiimg / 作品新增工具</h1>
<div class="sub">{{ pil_status }}</div>
<div class="tabs">
  {% for t, label in tabs %}
  <a href="{{ url_for('index', cat=t) }}" class="{{ 'active' if cat==t else '' }}">{{ label }}</a>
  {% endfor %}
</div>
{% with msgs = get_flashed_messages(with_categories=true) %}
  {% for cat, m in msgs %}<div class="{{ 'warn' if cat=='warn' else 'flash' }}">{{ m }}</div>{% endfor %}
{% endwith %}

{% if cat == 'design' %}
<form method="post" action="{{ url_for('add_design') }}" enctype="multipart/form-data">
  <label>分類 tag
    <input type="text" name="tag" list="design-tags" required placeholder="例：品牌識別 / 主視覺 / 周邊 / 平面圖文 / 影片">
    <datalist id="design-tags">{% for f in design.filters %}<option value="{{ f }}">{% endfor %}</datalist>
  </label>
  <label>標題 title
    <input type="text" name="title" required placeholder="作品名稱（顯示在 hover 上）">
  </label>
  <label>說明 meta
    <input type="text" name="meta" placeholder="客戶 / 年份 / 一句話">
  </label>
  <label>案例頁 slug（選填，例如 yuntech-xd → 會建立 /design/yuntech-xd/）
    <input type="text" name="slug" placeholder="留空則僅顯示卡片，不連到內頁">
  </label>
  <label>圖片（選填，第一張為封面）
    <input type="file" name="images" multiple accept="image/*">
    <span class="hint">會以 slug 為資料夾儲存到 /design/&lt;slug&gt;/img/，自動轉 webp 壓縮（最大寬 2000px）</span>
  </label>
  <div class="row radio-row">
    <span>位置：</span>
    <label><input type="radio" name="position" value="top" checked> 最前</label>
    <label><input type="radio" name="position" value="bottom"> 最後</label>
  </div>
  <button type="submit">新增</button>
</form>
{% elif cat == 'film-video' %}
<form method="post" action="{{ url_for('add_film_video') }}">
  <label>分類 tag
    <input type="text" name="tag" list="film-v-tags" required placeholder="例：紀錄片 / 劇情短片 / 動畫 / 音樂 MV">
    <datalist id="film-v-tags">{% for f in film.video.filters %}<option value="{{ f }}">{% endfor %}</datalist>
  </label>
  <label>標題 title
    <input type="text" name="title" required>
  </label>
  <label>標籤顯示文字（選填，會覆蓋 tag 顯示，例如：紀錄片 — 季軍）
    <input type="text" name="tag_label">
  </label>
  <div class="row radio-row">
    <span>位置：</span>
    <label><input type="radio" name="position" value="top" checked> 最前</label>
    <label><input type="radio" name="position" value="bottom"> 最後</label>
  </div>
  <button type="submit">新增</button>
</form>
{% elif cat == 'film-photo' %}
<form method="post" action="{{ url_for('add_film_photo') }}">
  <label>分類 tag
    <input type="text" name="tag" list="film-p-tags" required placeholder="例：人像 / 街頭 / 活動紀錄">
    <datalist id="film-p-tags">{% for f in film.photo.filters %}<option value="{{ f }}">{% endfor %}</datalist>
  </label>
  <label>主題 title
    <input type="text" name="title" required>
  </label>
  <label>副標 sub
    <input type="text" name="sub" placeholder="一句話描述">
  </label>
  <label>連結 href（選填）
    <input type="text" name="href" placeholder="例：../events/">
  </label>
  <div class="row radio-row">
    <span>位置：</span>
    <label><input type="radio" name="position" value="top" checked> 最前</label>
    <label><input type="radio" name="position" value="bottom"> 最後</label>
  </div>
  <button type="submit">新增</button>
</form>
{% elif cat == 'shorts-item' %}
<form method="post" action="{{ url_for('add_shorts_item') }}">
  <label>產業 tag
    <input type="text" name="tag" list="shorts-tags" required placeholder="例：餐飲 / 不動產 / 重機">
    <datalist id="shorts-tags">{% for f in shorts.filters %}<option value="{{ f }}">{% endfor %}</datalist>
  </label>
  <label>客戶 title
    <input type="text" name="title" required>
  </label>
  <div class="row radio-row">
    <span>位置：</span>
    <label><input type="radio" name="position" value="top" checked> 最前</label>
    <label><input type="radio" name="position" value="bottom"> 最後</label>
  </div>
  <button type="submit">新增</button>
</form>
{% elif cat == 'shorts-client' %}
<form method="post" action="{{ url_for('add_shorts_client') }}">
  <label>客戶名稱 name
    <input type="text" name="name" required>
  </label>
  <label>產業 industry
    <input type="text" name="industry" required>
  </label>
  <div class="row radio-row">
    <span>位置：</span>
    <label><input type="radio" name="position" value="top" checked> 最前</label>
    <label><input type="radio" name="position" value="bottom"> 最後</label>
  </div>
  <button type="submit">新增</button>
</form>
{% endif %}

<div class="preview-link">
  目前資料：
  <a href="/works/design.json" target="_blank">design.json</a> ·
  <a href="/works/film.json" target="_blank">film.json</a> ·
  <a href="/works/shorts.json" target="_blank">shorts.json</a>
  &nbsp;|&nbsp;
  預覽：<a href="/design/" target="_blank">/design/</a> ·
  <a href="/film/" target="_blank">/film/</a> ·
  <a href="/shortform/" target="_blank">/shortform/</a>
</div>
</body></html>
"""

TABS = [
    ("design", "DESIGN"),
    ("film-video", "FILM · 影片"),
    ("film-photo", "FILM · 攝影"),
    ("shorts-item", "SHORTS · 影片"),
    ("shorts-client", "SHORTS · 長期客戶"),
]


def rebuild() -> None:
    build_works.main()


def _ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_ns(v) for v in obj]
    return obj


@app.route("/")
def index():
    cat = request.args.get("cat", "design")
    return render_template_string(
        PAGE,
        cat=cat,
        tabs=TABS,
        design=_ns(load("design.json")),
        film=_ns(load("film.json")),
        shorts=_ns(load("shorts.json")),
        pil_status=("Pillow 已啟用 · 圖片會轉 webp 並壓縮"
                    if HAS_PIL else "Pillow 未安裝 · 圖片會原檔儲存（pip install Pillow 啟用優化）"),
    )


@app.post("/add/design")
def add_design():
    tag = request.form["tag"].strip()
    title = request.form["title"].strip()
    meta = request.form.get("meta", "").strip()
    slug_raw = request.form.get("slug", "").strip()
    position = request.form.get("position", "top")
    slug = slugify(slug_raw) if slug_raw else ""

    files = [f for f in request.files.getlist("images") if f and f.filename]
    cover = None
    if slug and files:
        img_dir = DESIGN_DIR / slug / "img"
        for i, fs in enumerate(files, 1):
            ext = ".webp" if HAS_PIL else Path(fs.filename).suffix.lower() or ".jpg"
            name = f"{slug}-{i:02d}{ext}"
            save_image(fs, img_dir / name)
            if i == 1:
                cover = f"/design/{slug}/img/{name}"
        # Create a stub case page if missing
        case_html = DESIGN_DIR / slug / "index.html"
        if not case_html.exists():
            case_html.write_text(stub_case_page(title, meta, slug), encoding="utf-8")

    entry = {"tag": tag, "title": title}
    if meta:
        entry["meta"] = meta
    if slug:
        entry["href"] = f"/design/{slug}/"
    if cover:
        entry["cover"] = cover

    data = load("design.json")
    ensure_filter(data, tag)
    insert(data["items"], entry, position)
    save("design.json", data)
    rebuild()
    flash(f"已新增 design 作品：{title}" + (f"（{len(files)} 張圖已存至 /design/{slug}/img/）" if files and slug else ""))
    return redirect(url_for("index", cat="design"))


@app.post("/add/film-video")
def add_film_video():
    tag = request.form["tag"].strip()
    title = request.form["title"].strip()
    tag_label = request.form.get("tag_label", "").strip()
    position = request.form.get("position", "top")
    entry = {"tag": tag, "title": title}
    if tag_label:
        entry["tag_label"] = tag_label
    data = load("film.json")
    ensure_filter(data["video"], tag)
    insert(data["video"]["items"], entry, position)
    save("film.json", data)
    rebuild()
    flash(f"已新增 film 影片：{title}")
    return redirect(url_for("index", cat="film-video"))


@app.post("/add/film-photo")
def add_film_photo():
    tag = request.form["tag"].strip()
    title = request.form["title"].strip()
    sub = request.form.get("sub", "").strip()
    href = request.form.get("href", "").strip()
    position = request.form.get("position", "top")
    entry = {"tag": tag, "title": title}
    if sub:
        entry["sub"] = sub
    if href:
        entry["href"] = href
    data = load("film.json")
    ensure_filter(data["photo"], tag)
    insert(data["photo"]["items"], entry, position)
    save("film.json", data)
    rebuild()
    flash(f"已新增 film 攝影：{title}")
    return redirect(url_for("index", cat="film-photo"))


@app.post("/add/shorts-item")
def add_shorts_item():
    tag = request.form["tag"].strip()
    title = request.form["title"].strip()
    position = request.form.get("position", "top")
    data = load("shorts.json")
    ensure_filter(data, tag)
    insert(data["items"], {"tag": tag, "title": title}, position)
    save("shorts.json", data)
    rebuild()
    flash(f"已新增 shorts 作品：{title}")
    return redirect(url_for("index", cat="shorts-item"))


@app.post("/add/shorts-client")
def add_shorts_client():
    name = request.form["name"].strip()
    industry = request.form["industry"].strip()
    position = request.form.get("position", "top")
    data = load("shorts.json")
    insert(data["clients"], {"name": name, "industry": industry}, position)
    save("shorts.json", data)
    rebuild()
    flash(f"已新增 shorts 客戶：{name}")
    return redirect(url_for("index", cat="shorts-client"))


# Serve site files so preview links work
@app.route("/<path:path>")
def static_root(path):
    full = (ROOT / path).resolve()
    if ROOT not in full.parents and full != ROOT:
        return ("Forbidden", 403)
    if full.is_dir():
        full = full / "index.html"
    if not full.exists():
        return ("Not found", 404)
    return (full.read_bytes(), 200, {"Content-Type": _mime(full.suffix)})


def _mime(ext: str) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css",
        ".js": "application/javascript",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".mp4": "video/mp4",
    }.get(ext.lower(), "application/octet-stream")


def stub_case_page(title: str, meta: str, slug: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — WEIIMG</title>
<link rel="stylesheet" href="../../style.css">
</head>
<body class="inner-page">
<main style="max-width:980px;margin:120px auto 80px;padding:0 24px;">
  <div class="page-title-block">
    <div class="en">{slug.upper()}</div>
    <h2>{title}</h2>
  </div>
  <p style="color:#666;margin:24px 0 40px;">{meta}</p>
  <!-- TODO: 補上作品內頁內容 -->
</main>
</body></html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
