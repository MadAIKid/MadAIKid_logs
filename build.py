#!/usr/bin/env python3
"""把 blog/posts/*.md 与 blog/timeline.md 构建成零依赖静态站点。

用法：
    python3 blog/build.py            # 构建
    python3 blog/build.py --check    # 只校验（不写文件），CI 用

依赖：pandoc（仅用于 Markdown → HTML，MathML 输出，不需要网络与 JS）。
产物：
    blog/index.html      实验日志索引（按时间排序 + 标签筛选）
    blog/timeline.html   完整时间索引
    blog/logs/<slug>.html 每篇日志
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
LOGS = ROOT / "logs"
TIMELINE = ROOT / "timeline.md"
REPO_URL = "https://github.com/MadAIKid/MadAIKid_logs"
SITE_NAME = "MadAIKid · 实验日志"

PANDOC = ["pandoc", "-f",
          "markdown+pipe_tables+tex_math_dollars+task_lists+footnotes+definition_lists",
          "-t", "html5", "--mathml", "--wrap=none"]

STATUS_CLASS = {"完成", "部分完成", "判负", "中止", "进行中"}


# --------------------------------------------------------------------------- #
# Markdown / frontmatter
# --------------------------------------------------------------------------- #

def pandoc(md: str) -> str:
    if not md.strip():
        return ""
    try:
        p = subprocess.run(PANDOC, input=md, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("错误：找不到 pandoc。macOS: brew install pandoc")
    if p.returncode != 0:
        sys.exit(f"pandoc 失败：\n{p.stderr}")
    return p.stdout


def parse_front(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    raw, body = text[3:end], text[end + 4:]
    meta: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip("\"'") for x in val[1:-1].split(",")]
            meta[key] = [i for i in items if i]
        else:
            meta[key] = val.strip("\"'")
    return meta, body.lstrip("\n")


def inline_md(s: str) -> str:
    """极小行内 Markdown 渲染：仅用于时间索引的表格单元格。"""
    s = html.escape(s, quote=False)

    def _code(m):
        return f"<code>{m.group(1)}</code>"

    def _link(m):
        text, url = m.group(1), m.group(2)
        return f'<a href="{url}">{text}</a>'

    s = re.sub(r"`([^`]+)`", _code, s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def strip_md(s: str) -> str:
    """去掉行内 Markdown 标记，用于 meta description / teaser。"""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[*_`]{1,3}", "", s)
    return re.sub(r"\s+", " ", s).strip()


def teaser_from(body: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith(">") and len(line) > 12:
            t = strip_md(line.lstrip("> ").strip())
            t = re.sub(r"^一句话[：:]\s*", "", t)
            if len(t) > 200:
                t = t[:197].rstrip("，,；;、 ") + "…"
            return t
    return ""


def badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{html.escape(text)}</span>'


def status_badge(status: str) -> str:
    cls = f"status-{status}" if status in STATUS_CLASS else "status-中止"
    return badge(status or "未标注", cls)


# --------------------------------------------------------------------------- #
# 页面骨架
# --------------------------------------------------------------------------- #

def page(title: str, desc: str, content: str, depth: int, nav: str,
         built: str) -> str:
    root = "../" * depth
    active = lambda k: ' class="active"' if nav == k else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<meta name="generator" content="blog/build.py">
<link rel="stylesheet" href="{root}assets/style.css">
</head>
<body>
<header class="site-header"><div class="inner">
<a class="brand" href="{root}index.html">MadAIKid<span class="dot">·</span>logs</a>
<nav class="site-nav">
<a href="{root}index.html"{active("index")}>实验日志</a>
<a href="{root}timeline.html"{active("timeline")}>时间索引</a>
<a href="{REPO_URL}">GitHub</a>
</nav>
</div></header>
<main class="wrap">
{content}
</main>
<footer class="site-footer"><div class="inner">
<span>{SITE_NAME}</span>
<span>构建 {built}</span>
<span>源文件即 Markdown，站内无 JS 依赖</span>
</div></footer>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# 单篇日志
# --------------------------------------------------------------------------- #

def spec_item(label: str, value: str, raw_html: str = "") -> str:
    if not value:
        return ""
    val = raw_html or html.escape(value)
    return f'<div class="item"><dt>{label}</dt><dd>{val}</dd></div>'


def build_post(meta: dict, body: str) -> tuple[str, dict]:
    slug = meta.get("slug", "")
    title = meta.get("title", slug)
    subtitle = meta.get("subtitle", "")
    status = meta.get("status", "")
    verdict = meta.get("verdict", "")
    tags = meta.get("tags", []) or []
    if isinstance(tags, str):
        tags = [tags]

    # 去掉正文开头重复的 h1
    body_lines = body.splitlines()
    if body_lines and body_lines[0].startswith("# "):
        body = "\n".join(body_lines[1:]).lstrip("\n")

    d1, d2 = meta.get("date_start", ""), meta.get("date_end", "")
    when = d1 if d1 == d2 or not d2 else f"{d1} → {d2}"
    spec = "".join([
        spec_item("编号", meta.get("id", "")),
        spec_item("日期", when),
        spec_item("状态", status, status_badge(status)),
        spec_item("判定", verdict),
        spec_item("标签", " / ".join(tags)),
        spec_item("硬件", meta.get("hardware", "")),
        spec_item("模型", meta.get("models", "")),
        spec_item("数据", meta.get("datasets", "")),
        spec_item("源文档", " · ".join(meta.get("source_docs", []) or [])),
    ])

    head = f"""<div class="article-head">
<div class="crumb"><a href="../index.html">实验日志</a> / {html.escape(slug)}</div>
<h1>{html.escape(title)}</h1>
{f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ''}
<dl class="spec">{spec}</dl>
</div>"""

    return head, {"slug": slug, "title": title, "prose": pandoc(body)}


def build_log_page(post: dict, prev: dict | None, nxt: dict | None,
                   built: str) -> str:
    pn = ""
    if prev or nxt:
        left = (f'<a href="{prev["slug"]}.html"><span class="dir">← 上一篇</span>'
                f'{html.escape(prev["title"])}</a>' if prev else "<span></span>")
        right = (f'<a class="next" href="{nxt["slug"]}.html"><span class="dir">下一篇 →</span>'
                 f'{html.escape(nxt["title"])}</a>' if nxt else "")
        pn = f'<nav class="post-nav">{left}{right}</nav>'

    content = f"""{post["head"]}
<article class="prose">
{post["prose"]}
</article>
{pn}"""
    desc = post["teaser"]
    return page(f'{post["title"]} · {SITE_NAME}', desc, content, 1, "post", built)


# --------------------------------------------------------------------------- #
# 首页
# --------------------------------------------------------------------------- #

def build_index(posts: list[dict], built: str) -> str:
    total = len(posts)
    dates = [p["date_start"] for p in posts if p.get("date_start")]
    span = f"{min(dates)} → {max(dates)}" if dates else "—"
    all_tags = sorted({t for p in posts for t in p["tags"]})
    n_done = sum(1 for p in posts if p.get("status") == "完成")
    n_half = sum(1 for p in posts if p.get("status") == "部分完成")
    n_neg = sum(1 for p in posts if p.get("status") == "判负")

    chips = '<button class="chip" data-tag="*" aria-pressed="true">全部</button>' + "".join(
        f'<button class="chip" data-tag="{html.escape(t)}" aria-pressed="false">{html.escape(t)}</button>'
        for t in all_tags)

    cards = []
    for p in posts:
        d1, d2 = p.get("date_start", ""), p.get("date_end", "")
        if d1 and d2 and d1 != d2:
            when = f'<span>{d1}</span><br><span class="yr">→ {d2}</span>'
        else:
            when = f'<span>{d1}</span>'
        tags_html = "".join(badge(t, "tag") for t in p["tags"])
        cards.append(f"""<article class="card" data-tags="{html.escape(" ".join(p["tags"]))}">
<div class="when">{when}</div>
<div class="body">
<h3><a href="logs/{p["slug"]}.html"><span class="id-tag">{html.escape(p.get("id", ""))}</span>{html.escape(p["title"])}</a></h3>
<p class="teaser">{html.escape(p["teaser"])}</p>
<div class="meta-row">{status_badge(p.get("status", ""))}{badge(p.get("verdict", ""), "verdict")}{tags_html}</div>
</div>
</article>""")

    content = f"""<section class="hero">
<h1>实验日志</h1>
<p class="lede">把一条条真实跑过的实验整理成可追溯的日志：<strong>问题 → 设置 → 结果 → 判定 → 边界</strong>。
每篇都标明「可写 / 不可写」——负结果和正结果同等重要。</p>
<div class="stats">
<div class="stat"><div class="num">{total}</div><div class="lbl">篇日志</div></div>
<div class="stat"><div class="num">{len(all_tags)}</div><div class="lbl">个标签</div></div>
<div class="stat"><div class="num" style="font-size:1.15rem">{n_done} · {n_half} · {n_neg}</div><div class="lbl">完成 · 部分完成 · 判负</div></div>
<div class="stat"><div class="num" style="font-size:.95rem">{span}</div><div class="lbl">时间跨度</div></div>
</div>
<div class="filters" id="filters">{chips}</div>
</section>

<section class="card-list" id="cards">
{"".join(cards)}
</section>

<p style="margin-top:2rem;font-size:.85rem;color:var(--fg-mute)">
完整到日的索引见 <a href="timeline.html">时间索引</a>。每篇日志的源 Markdown 在
<a href="https://github.com/MadAIKid/MadAIKid_logs/tree/main/posts">posts/</a>。
</p>

<script>
(function () {{
  var chips = document.querySelectorAll('#filters .chip');
  var cards = document.querySelectorAll('#cards .card');
  chips.forEach(function (c) {{
    c.addEventListener('click', function () {{
      chips.forEach(function (x) {{ x.setAttribute('aria-pressed', 'false'); }});
      c.setAttribute('aria-pressed', 'true');
      var tag = c.dataset.tag;
      cards.forEach(function (card) {{
        var tags = (card.dataset.tags || '').split(' ');
        card.style.display = (tag === '*' || tags.indexOf(tag) >= 0) ? '' : 'none';
      }});
    }});
  }});
}})();
</script>"""

    return page(SITE_NAME, "MadAIKid 的实验日志：问题、设置、结果、判定与边界。", content, 0, "index", built)


# --------------------------------------------------------------------------- #
# 时间索引
# --------------------------------------------------------------------------- #

def parse_timeline(text: str) -> tuple[str, list[list[str]]]:
    """返回 (表前说明的 markdown 文本, 表格行)。表格行已去掉表头与分隔行。"""
    lines = text.splitlines()
    first_row = next((i for i, ln in enumerate(lines) if ln.strip().startswith("|")), None)
    if first_row is None:
        return text, []
    intro = "\n".join(lines[:first_row]).strip()
    intro = re.sub(r"^#\s+.*$", "", intro, count=1, flags=re.M).strip()
    rows, seen_sep = [], False
    for ln in lines[first_row:]:
        ln = ln.strip()
        if not ln.startswith("|"):
            if rows and ln == "":
                continue
            if rows and not ln.startswith("|"):
                break
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            seen_sep = True
            continue
        if not seen_sep:          # 表头行
            continue
        rows.append(cells)
    return intro, rows


def build_timeline(built: str) -> str | None:
    if not TIMELINE.exists():
        print("警告：timeline.md 不存在，跳过时间索引页", file=sys.stderr)
        return None
    intro_md, rows = parse_timeline(TIMELINE.read_text(encoding="utf-8"))
    intro_html = pandoc(intro_md) if intro_md else ""

    body_rows, last_month = [], ""
    for cells in rows:
        cells = (cells + ["", "", "", ""])[:4]
        d, what, result, lines_col = cells
        m = re.match(r"(\d{4})-(\d{2})", d)
        month = f"{m.group(1)} 年 {m.group(2)} 月" if m else d
        if month != last_month:
            body_rows.append(f'<tr class="month-sep"><td colspan="4">{html.escape(month)}</td></tr>')
            last_month = month
        body_rows.append(
            f'<tr><td class="col-date">{inline_md(d)}</td>'
            f'<td class="col-what">{inline_md(what)}</td>'
            f'<td class="col-result">{inline_md(result)}</td>'
            f'<td class="col-line">{inline_md(lines_col)}</td></tr>')

    n = len(rows)
    content = f"""<section class="hero">
<h1>时间索引</h1>
<p class="lede">按时间正序列出每一次会话/实验的关键节点与结论，共 <strong>{n}</strong> 条。
点「实验线」进入对应日志。</p>
</section>
<div class="prose" style="max-width:none">{intro_html}</div>
<table class="timeline-table">
<thead><tr><th>日期</th><th>事件</th><th>结果 / 结论</th><th>实验线</th></tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
<p style="margin-top:2rem;font-size:.85rem;color:var(--fg-mute)">
母本：<a href="https://github.com/MadAIKid/MadAIKid_logs/blob/main/timeline.md">timeline.md</a>。
</p>"""
    return page(f"时间索引 · {SITE_NAME}", "按时间排序的全部实验节点与结论。", content, 0, "timeline", built)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def load_posts() -> list[dict]:
    posts = []
    for f in sorted(POSTS.glob("*.md")):
        meta, body = parse_front(f.read_text(encoding="utf-8"))
        slug = meta.get("slug") or f.stem
        meta.setdefault("slug", slug)
        meta.setdefault("title", f.stem)
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        head, rendered = build_post(meta, body)
        posts.append({
            **meta, "tags": tags, "head": head, "prose": rendered["prose"],
            "teaser": teaser_from(body), "file": f.name,
        })
    posts.sort(key=lambda p: (p.get("date_start", "9999"), p["slug"]))
    return posts


def main() -> None:
    check = "--check" in sys.argv
    built = datetime.now().strftime("%Y-%m-%d %H:%M")
    posts = load_posts()

    if not posts:
        sys.exit("错误：posts/ 为空")

    # 一致性校验
    errs = []
    seen = set()
    required = ["id", "slug", "title", "date_start", "status", "verdict", "tags"]
    for p in posts:
        for k in required:
            if not p.get(k):
                errs.append(f'{p["file"]}: 缺 frontmatter 字段 `{k}`')
        if p["slug"] in seen:
            errs.append(f'{p["file"]}: slug 重复 {p["slug"]}')
        seen.add(p["slug"])
        if p.get("status") not in STATUS_CLASS:
            errs.append(f'{p["file"]}: status "{p.get("status")}" 不在 {sorted(STATUS_CLASS)}')
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.get("date_start", "")):
            errs.append(f'{p["file"]}: date_start 格式应为 YYYY-MM-DD')
        if p["slug"] != p["file"][:-3]:
            errs.append(f'{p["file"]}: slug ({p["slug"]}) 与文件名不一致')
    if errs:
        print("\n".join("✗ " + e for e in errs), file=sys.stderr)
        sys.exit(f"校验失败（{len(errs)} 处）")
    print(f"✓ {len(posts)} 篇日志通过校验")

    LOGS.mkdir(exist_ok=True)
    written = []
    for i, p in enumerate(posts):
        prev = posts[i - 1] if i > 0 else None
        nxt = posts[i + 1] if i + 1 < len(posts) else None
        out = LOGS / f'{p["slug"]}.html'
        written.append(out)
        if not check:
            out.write_text(build_log_page(p, prev, nxt, built), encoding="utf-8")

    idx = build_index(posts, built)
    written.append(ROOT / "index.html")
    if not check:
        (ROOT / "index.html").write_text(idx, encoding="utf-8")

    tl = build_timeline(built)
    if tl:
        written.append(ROOT / "timeline.html")
        if not check:
            (ROOT / "timeline.html").write_text(tl, encoding="utf-8")

    if check:
        print("✓ 校验完成（--check 未写文件）")
    else:
        print(f"✓ 生成 {len(written)} 个 HTML 文件")
        for p in posts:
            print(f'   logs/{p["slug"]}.html  ({p.get("date_start")}  {p.get("status")})')


if __name__ == "__main__":
    main()
