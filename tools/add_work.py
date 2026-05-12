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
.section-title { font-size:13px; font-weight:600; color:#111; margin-top:4px; padding-bottom:6px; border-bottom:1px solid #eee; }
.manage-section { margin-bottom:32px; }
.manage-section-title { font-size:13px; font-weight:600; color:#111; padding-bottom:8px; margin-bottom:8px; border-bottom:1px solid #eee; }
.manage-list { list-style:none; padding:0; margin:0; }
.manage-row { display:flex; align-items:center; gap:12px; padding:8px 0; border-bottom:1px solid #f0f0f0; }
.manage-thumb { width:48px; height:48px; background:#e8eaed; background-size:cover; background-position:center; border-radius:3px; flex-shrink:0; }
.manage-thumb.empty { background:#f5f5f5; }
.manage-info { flex:1; min-width:0; }
.manage-title { font-size:13px; color:#111; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.manage-meta { font-size:11px; color:#999; margin-top:2px; }
.manage-actions { display:flex; gap:4px; flex-shrink:0; }
.manage-actions button { padding:6px 10px; background:#fff; color:#111; border:1px solid #ddd; border-radius:3px; font-size:12px; cursor:pointer; margin:0;}
.manage-actions button:hover:not(:disabled) { background:#f5f5f5; }
.manage-actions button:disabled { opacity:0.3; cursor:not-allowed; }
.manage-actions button.danger { color:#c62828; }
.manage-actions button.danger:hover:not(:disabled) { background:#ffebee; }
.cover-btn { padding:6px 10px; background:#fff; color:#111; border:1px solid #ddd; border-radius:3px; font-size:12px; cursor:pointer; display:inline-block; line-height:1; }
.cover-btn:hover { background:#f5f5f5; }
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
<form method="post" action="{{ url_for('add_design') }}" enctype="multipart/form-data" id="design-form">
  <div class="section-title">① 卡片內容（必填）</div>
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

  <div class="section-title" style="margin-top:18px;">② 縮圖與案例頁（選填）</div>
  <div class="hint" style="margin:-6px 0 6px;">想讓卡片有縮圖、能點進詳細頁的話，<b>必須同時</b>填 slug + 上傳圖片。兩個都不填則只是純文字卡片（像現在大多數）。</div>
  <label>slug（網址用，英數小寫和 -，例如 yuntech-xd → /design/yuntech-xd/）
    <input type="text" name="slug" id="slug-field" placeholder="留空 = 不建立案例頁、無縮圖">
  </label>
  <label>圖片（第一張會自動變成封面縮圖）
    <input type="file" name="images" id="img-field" multiple accept="image/*">
    <span class="hint">需搭配 slug。自動轉 webp、壓到最大寬 2000px，存到 /design/&lt;slug&gt;/img/</span>
  </label>

  <div class="row radio-row">
    <span>位置：</span>
    <label><input type="radio" name="position" value="top" checked> 最前</label>
    <label><input type="radio" name="position" value="bottom"> 最後</label>
  </div>
  <button type="submit">新增</button>
</form>
<script>
document.getElementById('design-form').addEventListener('submit', function(e) {
  var slug = document.getElementById('slug-field').value.trim();
  var files = document.getElementById('img-field').files;
  if (files.length > 0 && !slug) {
    e.preventDefault();
    alert('你上傳了圖片但沒填 slug。\n\n請填 slug（英數小寫，例：yongfeng），否則圖片無法儲存。');
    document.getElementById('slug-field').focus();
    return false;
  }
});
</script>
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
{% elif cat == 'manage' %}
<div class="hint" style="margin-bottom:16px;">所有分類的項目列表，可調順序或刪除。刪除後 JSON 立即更新並重生 index.html。</div>
{% for sec_key, sec_label, items in manage_sections %}
  <div class="manage-section">
    <div class="manage-section-title">{{ sec_label }} <span class="hint">({{ items|length }} 項)</span></div>
    {% if items %}
    <ul class="manage-list">
      {% for it in items %}
        <li class="manage-row">
          {% if it.cover %}<div class="manage-thumb" style="background-image:url('{{ it.cover }}')"></div>
          {% else %}<div class="manage-thumb empty"></div>{% endif %}
          <div class="manage-info">
            <div class="manage-title">{{ it.title }}</div>
            <div class="manage-meta">{{ it.meta }}</div>
          </div>
          <div class="manage-actions">
            {% if it.cover %}
            <form method="post" action="{{ url_for('replace_cover') }}" enctype="multipart/form-data" style="display:inline">
              <input type="hidden" name="section" value="{{ sec_key }}">
              <input type="hidden" name="index" value="{{ loop.index0 }}">
              <label class="cover-btn" title="換封面（自動轉 webp 覆蓋舊封面）">📷
                <input type="file" accept="image/*" name="image" onchange="this.form.submit()" style="display:none">
              </label>
            </form>
            {% endif %}
            <form method="post" action="{{ url_for('move_item') }}" style="display:inline">
              <input type="hidden" name="section" value="{{ sec_key }}">
              <input type="hidden" name="index" value="{{ loop.index0 }}">
              <input type="hidden" name="direction" value="up">
              <button type="submit" {{ 'disabled' if loop.first else '' }}>↑</button>
            </form>
            <form method="post" action="{{ url_for('move_item') }}" style="display:inline">
              <input type="hidden" name="section" value="{{ sec_key }}">
              <input type="hidden" name="index" value="{{ loop.index0 }}">
              <input type="hidden" name="direction" value="down">
              <button type="submit" {{ 'disabled' if loop.last else '' }}>↓</button>
            </form>
            <form method="post" action="{{ url_for('delete_item') }}" style="display:inline" onsubmit="return confirm('確定刪除「{{ it.title }}」？JSON 條目會移除，但已存的圖檔/案例頁資料夾不會刪。')">
              <input type="hidden" name="section" value="{{ sec_key }}">
              <input type="hidden" name="index" value="{{ loop.index0 }}">
              <button type="submit" class="danger">✕</button>
            </form>
          </div>
        </li>
      {% endfor %}
    </ul>
    {% else %}
      <div class="hint">（無項目）</div>
    {% endif %}
  </div>
{% endfor %}
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
    ("manage", "MANAGE / 管理"),
]

# (cat_key, label, json_file, json_path_to_list)
SECTIONS = [
    ("design",        "DESIGN",            "design.json", ["items"]),
    ("film-video",    "FILM · 影片",       "film.json",   ["video", "items"]),
    ("film-photo",    "FILM · 攝影",       "film.json",   ["photo", "items"]),
    ("shorts-item",   "SHORTS · 影片",     "shorts.json", ["items"]),
    ("shorts-client", "SHORTS · 長期客戶", "shorts.json", ["clients"]),
]


def _section(key: str):
    for s in SECTIONS:
        if s[0] == key:
            return s
    raise ValueError(key)


def _get_list(data: dict, path: list[str]) -> list:
    cur = data
    for p in path:
        cur = cur[p]
    return cur


def _summary(section_key: str, entry: dict) -> tuple[str, str, str]:
    """Return (cover_url_or_empty, title, meta)"""
    if section_key == "shorts-client":
        return ("", entry.get("name", ""), entry.get("industry", ""))
    cover = entry.get("cover", "")
    title = entry.get("title", "")
    meta = entry.get("meta") or entry.get("sub") or entry.get("tag_label") or entry.get("tag", "")
    return (cover, title, meta)


def rebuild() -> None:
    build_works.main()


def _ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_ns(v) for v in obj]
    return obj


def _build_manage_context() -> list[dict]:
    out = []
    for sec_key, sec_label, json_file, path in SECTIONS:
        data = load(json_file)
        items_raw = _get_list(data, path)
        items = []
        for entry in items_raw:
            cover, title, meta = _summary(sec_key, entry)
            items.append({"cover": cover, "title": title, "meta": meta})
        out.append({"sec_key": sec_key, "sec_label": sec_label, "items": items})
    return out


@app.route("/")
def index():
    cat = request.args.get("cat", "design")
    manage_sections = []
    if cat == "manage":
        manage_sections = [
            (s["sec_key"], s["sec_label"], [_ns(it) for it in s["items"]])
            for s in _build_manage_context()
        ]
    return render_template_string(
        PAGE,
        cat=cat,
        tabs=TABS,
        design=_ns(load("design.json")),
        film=_ns(load("film.json")),
        shorts=_ns(load("shorts.json")),
        manage_sections=manage_sections,
        pil_status=("Pillow 已啟用 · 圖片會轉 webp 並壓縮"
                    if HAS_PIL else "Pillow 未安裝 · 圖片會原檔儲存（pip install Pillow 啟用優化）"),
    )


@app.post("/move")
def move_item():
    section = request.form["section"]
    index = int(request.form["index"])
    direction = request.form["direction"]
    _, _, json_file, path = _section(section)
    data = load(json_file)
    items = _get_list(data, path)
    new = index - 1 if direction == "up" else index + 1
    if 0 <= new < len(items):
        items[index], items[new] = items[new], items[index]
        save(json_file, data)
        rebuild()
        flash(f"已調整順序：{section} #{index} → #{new}")
    return redirect(url_for("index", cat="manage"))


@app.post("/replace-cover")
def replace_cover():
    section = request.form["section"]
    index = int(request.form["index"])
    file = request.files.get("image")
    if not file or not file.filename:
        flash("沒選到檔案", "warn")
        return redirect(url_for("index", cat="manage"))
    _, _, json_file, path = _section(section)
    data = load(json_file)
    items = _get_list(data, path)
    if not (0 <= index < len(items)):
        flash("index 無效", "warn")
        return redirect(url_for("index", cat="manage"))
    entry = items[index]
    cover_url = entry.get("cover")
    if not cover_url:
        flash("此項目沒有 cover 欄位，先用一般新增流程建立", "warn")
        return redirect(url_for("index", cat="manage"))
    # Cover URL like "/design/yfe-branding/img/yfe-branding-01.webp"
    rel = cover_url.lstrip("/")
    dest = (ROOT / rel).resolve()
    # Force .webp output regardless of original extension
    dest = dest.with_suffix(".webp")
    save_image(file, dest)
    new_url = "/" + str(dest.relative_to(ROOT)).replace("\\", "/")
    if new_url != cover_url:
        entry["cover"] = new_url
        save(json_file, data)
    rebuild()
    label = entry.get("title") or entry.get("name") or "(item)"
    flash(f"已更新封面：{label}")
    return redirect(url_for("index", cat="manage"))


@app.post("/delete")
def delete_item():
    section = request.form["section"]
    index = int(request.form["index"])
    _, _, json_file, path = _section(section)
    data = load(json_file)
    items = _get_list(data, path)
    if 0 <= index < len(items):
        removed = items.pop(index)
        save(json_file, data)
        rebuild()
        label = removed.get("title") or removed.get("name") or "(item)"
        flash(f"已刪除：{label}")
    return redirect(url_for("index", cat="manage"))


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
        image_names: list[str] = []
        for i, fs in enumerate(files, 1):
            ext = ".webp" if HAS_PIL else Path(fs.filename).suffix.lower() or ".jpg"
            name = f"{slug}-{i:02d}{ext}"
            save_image(fs, img_dir / name)
            image_names.append(name)
            if i == 1:
                cover = f"/design/{slug}/img/{name}"
        case_html = DESIGN_DIR / slug / "index.html"
        if not case_html.exists():
            case_html.write_text(
                stub_case_page(title, meta, slug, image_names), encoding="utf-8"
            )

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


CASE_NAV = """<nav class="nav">
  <a href="/" class="nav-logo">WEIIMG<span class="reg">*</span><span class="arrow-line"></span></a>
  <div class="nav-items">
    <div class="nav-slide-wrap">
      <div class="nav-slide-inner">
        <div class="nav-row">
          <span class="has-dropdown">WORK</span>
          <a href="/about/">ABOUT</a>
          <a href="/blog/">BLOG</a>
        </div>
        <div class="nav-row">
          <a href="/design/">DESIGN</a>
          <a href="/film/">FILM</a>
          <a href="/shortform/">SHORTS</a>
        </div>
      </div>
    </div>
    <div class="nav-cta-wrap">
      <span class="nav-cta">FIND ME</span>
      <div class="findme-dropdown">
        <a href="mailto:hi@weiimg.com"><span class="fm-icon">✉</span>hi@weiimg.com</a>
        <a href="https://instagram.com/wei_img" target="_blank" rel="noopener noreferrer"><span class="fm-icon">\U0001F4F7</span>Instagram</a>
        <a href="https://threads.net/@wei_img" target="_blank" rel="noopener noreferrer"><span class="fm-icon">\U0001F9F5</span>Threads</a>
      </div>
    </div>
  </div>
</nav>"""

CASE_FOOTER = """<footer class="contact">
  <div class="contact-label">Let's collaborate!</div>
  <div class="contact-email"><a href="mailto:hi@weiimg.com">hi@weiimg.com</a></div>
  <a href="mailto:hi@weiimg.com" class="contact-cta">FIND ME</a>
  <div class="contact-copyright">&copy; 2026 林晉維 — weiimg.com</div>
</footer>"""

CASE_SCRIPT = """<script>
(() => {
  const wrap = document.querySelector('.nav-slide-wrap');
  const trigger = wrap && wrap.querySelector('.has-dropdown');
  if (!wrap || !trigger) return;
  let timer;
  const show = () => { clearTimeout(timer); wrap.classList.add('open'); };
  const hide = () => { timer = setTimeout(() => wrap.classList.remove('open'), 250); };
  trigger.addEventListener('mouseenter', show);
  wrap.addEventListener('mouseleave', hide);
  wrap.querySelectorAll('.nav-row:last-child a').forEach(a => a.addEventListener('mouseenter', show));
})();
const logo = document.querySelector('.nav-logo');
const line = logo && logo.querySelector('.arrow-line');
const navItems = document.querySelector('.nav-items');
if (logo && line && navItems) {
  function setArrowWidth() {
    const lR = logo.getBoundingClientRect(), nR = navItems.getBoundingClientRect();
    line.style.width = Math.max(0, nR.left - lR.right - 12) + 'px';
  }
  logo.addEventListener('mouseenter', () => { setArrowWidth(); logo.classList.remove('arrow-out'); logo.classList.add('arrow-in'); });
  logo.addEventListener('mouseleave', () => { logo.classList.remove('arrow-in'); logo.classList.add('arrow-out'); line.addEventListener('transitionend', () => logo.classList.remove('arrow-out'), { once: true }); });
}
</script>"""


CASE_STYLE = """<style>
  .xd-carousel { position: relative; margin: 32px 0 48px; background: var(--dark-2); overflow: hidden; aspect-ratio: 16 / 9; user-select: none; }
  .xd-carousel-track { display: flex; height: 100%; transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1); will-change: transform; }
  .xd-carousel-track.dragging { transition: none; }
  .xd-carousel-slide { flex: 0 0 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: var(--dark-2); }
  .xd-carousel-slide img { max-width: 100%; max-height: 100%; width: auto; height: auto; object-fit: contain; pointer-events: none; }
  .xd-carousel-btn { position: absolute; top: 50%; transform: translateY(-50%); width: 48px; height: 48px; border: 1px solid var(--border); background: rgba(255,255,255,0.85); color: var(--dark); font-size: 18px; cursor: pointer; z-index: 5; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
  .xd-carousel-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }
  .xd-carousel-btn.prev { left: 16px; }
  .xd-carousel-btn.next { right: 16px; }
  .xd-carousel-counter { position: absolute; bottom: 16px; right: 24px; font-size: 11px; letter-spacing: 0.15em; color: var(--dark); background: rgba(255,255,255,0.85); padding: 6px 12px; z-index: 5; }
  .xd-carousel-dots { position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); display: flex; gap: 6px; z-index: 5; }
  .xd-carousel-dots span { width: 6px; height: 6px; border-radius: 50%; background: rgba(45,45,45,0.3); cursor: pointer; transition: background 0.2s; }
  .xd-carousel-dots span.on { background: var(--dark); }
  .xd-thumbs { display: flex; gap: 8px; margin: 0 0 48px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin; }
  .xd-thumbs::-webkit-scrollbar { height: 6px; }
  .xd-thumbs::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  .xd-thumb { flex: 0 0 88px; height: 60px; background: var(--dark-2); cursor: pointer; overflow: hidden; border: 2px solid transparent; transition: border-color 0.2s, opacity 0.2s; opacity: 0.6; }
  .xd-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .xd-thumb:hover { opacity: 1; }
  .xd-thumb.on { border-color: var(--accent); opacity: 1; }
  .xd-section-title { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gray); margin: 0 0 16px; }
</style>"""

CASE_CAROUSEL_SCRIPT = """<script>
(() => {
  const root = document.getElementById('xdCarousel');
  if (!root) return;
  const track = root.querySelector('.xd-carousel-track');
  const slides = root.querySelectorAll('.xd-carousel-slide');
  const prev = root.querySelector('.prev');
  const next = root.querySelector('.next');
  const cur = root.querySelector('.cur');
  const dotsWrap = root.querySelector('.xd-carousel-dots');
  let idx = 0;
  const total = slides.length;
  for (let i = 0; i < total; i++) {
    const d = document.createElement('span');
    if (i === 0) d.classList.add('on');
    d.addEventListener('click', () => go(i));
    dotsWrap.appendChild(d);
  }
  const dots = dotsWrap.querySelectorAll('span');
  const thumbs = document.querySelectorAll('#xdThumbs .xd-thumb');
  thumbs.forEach((t, i) => t.addEventListener('click', () => go(i)));
  function go(n) {
    idx = (n + total) % total;
    track.style.transform = `translateX(-${idx * 100}%)`;
    if (cur) cur.textContent = idx + 1;
    dots.forEach((d, i) => d.classList.toggle('on', i === idx));
    thumbs.forEach((t, i) => t.classList.toggle('on', i === idx));
    const active = thumbs[idx];
    if (active) active.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
  }
  prev.addEventListener('click', () => go(idx - 1));
  next.addEventListener('click', () => go(idx + 1));
  root.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') go(idx - 1);
    if (e.key === 'ArrowRight') go(idx + 1);
  });
  root.tabIndex = 0;
  let startX = 0, dx = 0, dragging = false;
  const onDown = e => { dragging = true; startX = (e.touches ? e.touches[0].clientX : e.clientX); track.classList.add('dragging'); };
  const onMove = e => {
    if (!dragging) return;
    const x = (e.touches ? e.touches[0].clientX : e.clientX);
    dx = x - startX;
    track.style.transform = `translateX(calc(-${idx * 100}% + ${dx}px))`;
  };
  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    track.classList.remove('dragging');
    const w = root.offsetWidth;
    if (Math.abs(dx) > w * 0.15) go(idx + (dx < 0 ? 1 : -1));
    else go(idx);
    dx = 0;
  };
  root.addEventListener('mousedown', onDown);
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
  root.addEventListener('touchstart', onDown, { passive: true });
  root.addEventListener('touchmove', onMove, { passive: true });
  root.addEventListener('touchend', onUp);
})();
</script>"""


def _build_sidebar_links(current_slug: str) -> str:
    """Scan design/ for case subdirs with index.html; pull display title from design.json."""
    title_by_slug = {}
    try:
        for it in load("design.json").get("items", []):
            href = it.get("href", "")
            if href.startswith("/design/") and href.endswith("/"):
                slug = href.strip("/").split("/")[-1]
                title_by_slug[slug] = it.get("title", slug)
    except Exception:
        pass
    rows = []
    design_dir = ROOT / "design"
    if not design_dir.exists():
        return ""
    for sub in sorted(design_dir.iterdir()):
        if not sub.is_dir() or not (sub / "index.html").exists():
            continue
        slug = sub.name
        title = title_by_slug.get(slug, slug)
        is_current = (slug == current_slug)
        cls = ' class="current"' if is_current else ""
        target = "#" if is_current else f"/design/{slug}/"
        rows.append(f'      <a href="{target}"{cls}>{title}</a>')
    return "\n".join(rows)


def stub_case_page(
    title: str,
    meta: str,
    slug: str,
    image_files: list[str] | None = None,
) -> str:
    images = image_files or []
    slides = "\n          ".join(
        f'<div class="xd-carousel-slide"><img src="img/{fn}" alt="{title} — {i+1}"{" loading=\"lazy\"" if i else ""}></div>'
        for i, fn in enumerate(images)
    ) or '<div class="xd-carousel-slide"><!-- 尚未上傳圖片 --></div>'
    thumbs = "\n        ".join(
        f'<div class="xd-thumb{" on" if i == 0 else ""}"><img src="img/{fn}" alt="" loading="lazy"></div>'
        for i, fn in enumerate(images)
    )
    sidebar = _build_sidebar_links(slug) or '      <a href="#" class="current">本作品</a>'
    total = max(1, len(images))
    return f"""<!DOCTYPE html>
<!-- weiimg-auto-stub -->
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{title} — WEIIMG 設計案例。">
<title>{title} — WEIIMG</title>
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/favicon.png">
<link rel="stylesheet" href="../../style.css?v=5">
{CASE_STYLE}
</head>
<body class="inner-page">

{CASE_NAV}

<main>
  <div class="article-layout">
    <aside class="article-sidebar">
      <h4>設計</h4>
{sidebar}
    </aside>
    <div class="article-main">

      <div class="article-back"><a href="/design/">&larr; 返回設計</a></div>

      <div class="xd-carousel" id="xdCarousel">
        <div class="xd-carousel-track">
          {slides}
        </div>
        <button class="xd-carousel-btn prev" aria-label="上一張">&larr;</button>
        <button class="xd-carousel-btn next" aria-label="下一張">&rarr;</button>
        <div class="xd-carousel-counter"><span class="cur">1</span> / <span class="total">{total}</span></div>
        <div class="xd-carousel-dots"></div>
      </div>

      <div class="xd-thumbs" id="xdThumbs">
        {thumbs}
      </div>

      <div class="article-body-grid">
        <div class="article-meta-col">
          <h1>{title}</h1>
          <div class="meta-row">
            <div class="meta-label">說明</div>
            <div class="meta-value">{meta or "—"}</div>
          </div>
          <!-- TODO: 補上更多 meta-row（類型 / 主辦 / 年份 / 服務項目 等） -->
        </div>
        <div class="article-text-col">
          <div class="xd-section-title">概念 / Concept</div>
          <p><!-- TODO: 概念敘述 --></p>

          <div class="xd-section-title" style="margin-top:48px;">主視覺 / Key Visual</div>
          <p><!-- TODO: 視覺說明 --></p>
        </div>
      </div>

    </div>
  </div>
</main>

{CASE_FOOTER}

{CASE_CAROUSEL_SCRIPT}
{CASE_SCRIPT}
<script src="/nav.js?v=3"></script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
