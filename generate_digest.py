#!/usr/bin/env python3
"""Daily Communications Strategy Digest Generator.

Uses Claude (Opus 4.7) with built-in web search to compile a structured
intelligence briefing and saves it as JSON (for the web app) and optionally
as Markdown to an Obsidian vault.

Environment variables (set in .env or export before running):
  ANTHROPIC_API_KEY   – required
  NTFY_TOPIC          – ntfy.sh topic slug for push notifications
  DIGEST_APP_URL      – base URL of the served web app (default: http://localhost:8000)
  OBSIDIAN_VAULT_PATH – path to Obsidian vault root (optional)
  DIGEST_TIMEZONE     – timezone label shown in digest (default: EET)
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import httpx

# ── Paths & config ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR   = SCRIPT_DIR / "data" / "issues"
INDEX_FILE = DATA_DIR / "index.json"
LOG_DIR    = SCRIPT_DIR / "logs"

TIMEZONE     = os.getenv("DIGEST_TIMEZONE", "EET")
APP_URL      = os.getenv("DIGEST_APP_URL", "http://localhost:8000")
NTFY_TOPIC   = os.getenv("NTFY_TOPIC", "")
_vault       = os.getenv("OBSIDIAN_VAULT_PATH", "")
OBSIDIAN_DIR = Path(_vault) / "collections" / "digests" if _vault else None

MODEL = "claude-opus-4-7"

# ── JSON schema passed to Claude ──────────────────────────────────────────────
JSON_SCHEMA = """{
  "meta": { "date": "YYYY-MM-DD", "updated_at": "HH:MM", "timezone": "EET" },
  "header": { "uk": "...", "en": "..." },
  "editorial_intro": { "uk": "...", "en": "..." },
  "executive_summary": {
    "uk": ["bullet 1", "bullet 2", "bullet 3"],
    "en": ["bullet 1", "bullet 2", "bullet 3"]
  },
  "top_signals": [
    { "uk": "...", "en": "...", "importance": "critical|watch|monitor", "score": 85 }
  ],
  "briefs": {
    "global": [
      {
        "category": "Politics|Economics|Technology|Cybersecurity|Science|Society",
        "importance": "critical|watch|monitor",
        "score": 80,
        "published_at": "YYYY-MM-DDTHH:MM",
        "headline": { "uk": "...", "en": "..." },
        "summary": { "uk": "...", "en": "..." },
        "why_it_matters": { "uk": "...", "en": "..." },
        "comms_implication": { "uk": "...", "en": "..." },
        "sources": [{ "name": "Source Name", "url": "https://..." }]
      }
    ],
    "ukraine": []
  },
  "pro_block": {
    "lead": { "uk": "...", "en": "..." },
    "items": [
      {
        "title": { "uk": "...", "en": "..." },
        "insight": { "uk": "...", "en": "..." },
        "application": { "uk": "...", "en": "..." },
        "sources": [{ "name": "...", "url": "https://..." }]
      }
    ]
  },
  "comms_metrics": [
    {
      "title": { "uk": "...", "en": "..." },
      "description": { "uk": "...", "en": "..." },
      "formula": "...",
      "tools": [{ "name": "...", "url": "https://..." }]
    }
  ],
  "research_radar": [
    { "title": "...", "why_read": { "uk": "...", "en": "..." }, "url": "https://..." }
  ]
}"""

SYSTEM_PROMPT = """\
You are a senior communications strategist and media intelligence analyst.
Your job is to produce a structured daily briefing for a comms professional.

Rules:
- Search for REAL news from the last 24 hours with actual, working URLs.
- Analyse everything through a strategic communications lens.
- Be specific: real names, numbers, quotes — no vague platitudes.
- Write fluently in BOTH Ukrainian and English.
- Output ONLY valid JSON — no markdown fences, no preamble, no commentary.\
"""

USER_PROMPT = """\
Create the Comms Strategy Digest for {date} (time now: {time} {tz}).

Search and compile the following sections:

1. GLOBAL NEWS — 5–7 top stories from the last 24 h across politics, economics,
   science, AI/technology, cybersecurity, society. Per story: 2-sentence summary,
   why it matters for communicators, one practical comms implication.

2. UKRAINE NEWS — 3–5 most important Ukraine stories (political, military,
   economic, international communications about Ukraine).

3. COMMUNICATIONS STRATEGY INTELLIGENCE — 3–5 expert insights/cases:
   - Insights from PR/comms thought leaders (PRWeek, SpinSucks, Edelman, PRSA,
     IABC, Meltwater, Sprout Social blog, noted LinkedIn/X communicators)
   - Crisis or strategic comms case studies from last 48 h
   - Platform algorithm or policy changes relevant to communicators
   - New research data or statistics for the communications field

4. COMMS METRICS — 2–3 important metrics/benchmarks published or updated today.

5. RESEARCH RADAR — 2–3 recommended reads: recent reports, white papers,
   long-form articles worth a communicator's time.

Use this exact JSON schema and output nothing else:
{schema}

meta.date = {date}
meta.updated_at = {time}
meta.timezone = {tz}\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?([\s\S]+?)\n?```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1:
        try:
            return json.loads(text[s : e + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON found in response (first 600 chars):\n{text[:600]}")


# ── Core generation ───────────────────────────────────────────────────────────

def generate_issue(client: anthropic.Anthropic, date_str: str, time_str: str) -> dict:
    print(f"[{_ts()}] Generating digest for {date_str} with {MODEL} + web_search …")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # prompt caching
            }
        ],
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 15,
            }
        ],
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    date=date_str,
                    time=time_str,
                    tz=TIMEZONE,
                    schema=JSON_SCHEMA,
                ),
            }
        ],
    )

    full_text = "".join(b.text for b in response.content if b.type == "text")
    print(f"[{_ts()}] Parsing JSON from response …")
    issue = extract_json(full_text)

    # Guarantee meta is accurate
    issue["meta"] = {"date": date_str, "updated_at": time_str, "timezone": TIMEZONE}
    return issue


# ── Persistence ───────────────────────────────────────────────────────────────

def save_issue(issue: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    date_str = issue["meta"]["date"]
    issue_path = DATA_DIR / f"{date_str}.json"
    issue_path.write_text(json.dumps(issue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{_ts()}] Saved {issue_path.name}")

    index: dict = {"issues": []}
    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text())
        except json.JSONDecodeError:
            pass

    rel = f"data/issues/{date_str}.json"
    if rel not in index["issues"]:
        index["issues"].insert(0, rel)
    index["issues"].sort(reverse=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{_ts()}] Index updated ({len(index['issues'])} issues)")
    return issue_path


def save_to_obsidian(issue: dict) -> Path | None:
    if not OBSIDIAN_DIR:
        return None
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)

    date_str = issue["meta"]["date"]
    md_path = OBSIDIAN_DIR / f"Comms Strategy Digest {date_str}.md"
    lang = "uk"

    def g(obj, *keys, fallback=""):
        """Safely drill into nested dicts."""
        for k in keys:
            if not isinstance(obj, dict):
                return fallback
            obj = obj.get(k, fallback)
        return obj if obj else fallback

    lines: list[str] = [
        f"# {g(issue, 'header', lang, fallback=f'Comms Strategy Digest {date_str}')}",
        f"**Дата:** {date_str}  |  **Оновлено:** {issue['meta']['updated_at']} {issue['meta']['timezone']}",
        "",
        f"> {g(issue, 'editorial_intro', lang)}",
        "",
        "## Executive Summary",
        "",
    ]
    for item in g(issue, "executive_summary", lang, fallback=[]):
        lines.append(f"- {item}")
    lines.append("")

    signals = issue.get("top_signals", [])
    if signals:
        lines += ["## Ключові сигнали", ""]
        for s in signals:
            badge = s.get("importance", "").upper()
            lines.append(f"- **[{badge}]** {s.get(lang, '')}  *(score: {s.get('score', '—')}/100)*")
        lines.append("")

    def _story_block(story: dict) -> list[str]:
        hl = g(story, "headline", lang)
        sm = g(story, "summary", lang)
        wm = g(story, "why_it_matters", lang)
        ci = g(story, "comms_implication", lang)
        src_links = "  |  ".join(f"[{s['name']}]({s['url']})" for s in story.get("sources", []))
        out = [f"### {hl}", f"*{story.get('category','')} · {story.get('score','—')}/100 · {story.get('importance','')}*", "", sm]
        if wm:
            out += ["", f"**Чому важливо:** {wm}"]
        if ci:
            out += ["", f"**Для комунікацій:** {ci}"]
        if src_links:
            out += ["", f"**Джерела:** {src_links}"]
        out.append("")
        return out

    global_stories = issue.get("briefs", {}).get("global", [])
    if global_stories:
        lines += ["## 🌍 Світ", ""]
        for s in global_stories:
            lines += _story_block(s)

    ua_stories = issue.get("briefs", {}).get("ukraine", [])
    if ua_stories:
        lines += ["## 🇺🇦 Україна", ""]
        for s in ua_stories:
            lines += _story_block(s)

    pro = issue.get("pro_block", {})
    if pro:
        lines += ["## 📣 Стратегічні комунікації", ""]
        lead = g(pro, "lead", lang)
        if lead:
            lines += [f"> {lead}", ""]
        for item in pro.get("items", []):
            src_links = "  |  ".join(f"[{s['name']}]({s['url']})" for s in item.get("sources", []))
            lines += [
                f"### {g(item, 'title', lang)}",
                g(item, "insight", lang),
                "",
                f"**Застосування:** {g(item, 'application', lang)}",
            ]
            if src_links:
                lines += ["", f"**Джерела:** {src_links}"]
            lines.append("")

    for metric in issue.get("comms_metrics", []):
        lines += [
            "## 📊 Метрики" if not any("📊" in l for l in lines) else "",
            f"### {g(metric, 'title', lang)}",
            g(metric, "description", lang),
            f"*{metric.get('formula','')}*",
            "  |  ".join(f"[{t['name']}]({t['url']})" for t in metric.get("tools", [])),
            "",
        ]

    research = issue.get("research_radar", [])
    if research:
        lines += ["## 📚 Research Radar", ""]
        for r in research:
            lines += [
                f"### [{r.get('title','')}]({r.get('url','')})",
                g(r, "why_read", lang),
                "",
            ]

    lines += ["---", f"tags: digest comms-strategy {date_str}"]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[{_ts()}] Saved Obsidian note: {md_path}")
    return md_path


# ── Notifications ─────────────────────────────────────────────────────────────

def send_notification(issue: dict, date_str: str) -> None:
    header = issue.get("header", {}).get("uk", f"Дайджест {date_str}")
    url = f"{APP_URL.rstrip('/')}"
    body = f"📰 {header}"

    if NTFY_TOPIC:
        try:
            httpx.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                content=body,
                headers={
                    "Title": f"Comms Strategy Digest {date_str}",
                    "Priority": "high",
                    "Click": url,
                    "Tags": "newspaper,ukraine,briefcase",
                },
                timeout=10,
            )
            print(f"[{_ts()}] ntfy.sh notification sent → topic '{NTFY_TOPIC}'")
        except Exception as exc:
            print(f"[{_ts()}] ntfy.sh error: {exc}")
    else:
        print(f"[{_ts()}] Tip: set NTFY_TOPIC in .env to get push notifications.")

    # Linux / macOS desktop notification as bonus
    try:
        if subprocess.run(["which", "notify-send"], capture_output=True).returncode == 0:
            subprocess.run(["notify-send", f"Comms Digest {date_str}", header, "--urgency=normal"], check=False)
        elif subprocess.run(["which", "osascript"], capture_output=True).returncode == 0:
            subprocess.run(
                ["osascript", "-e", f'display notification "{header}" with title "Comms Strategy Digest {date_str}"'],
                check=False,
            )
    except Exception:
        pass

    print(f"[{_ts()}] Digest ready → {url}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # Load .env if present (simple parser, no dependency needed)
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    issue_path = DATA_DIR / f"{date_str}.json"
    if issue_path.exists() and "--force" not in sys.argv:
        print(f"[{_ts()}] Issue for {date_str} already exists. Pass --force to regenerate.")
        sys.exit(0)

    LOG_DIR.mkdir(exist_ok=True)
    client = anthropic.Anthropic(api_key=api_key)

    try:
        issue = generate_issue(client, date_str, time_str)
        save_issue(issue)
        save_to_obsidian(issue)
        send_notification(issue, date_str)
        print(f"[{_ts()}] ✓ Digest for {date_str} generated successfully.")
    except Exception as exc:
        import traceback
        print(f"[{_ts()}] ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
