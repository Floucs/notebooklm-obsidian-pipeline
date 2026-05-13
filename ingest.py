#!/usr/bin/env python3
"""
ingest.py — NotebookLM to Obsidian Pipeline

Processes a single lecture PDF (and optional transcript) through NotebookLM
and writes a structured Markdown note directly into your Obsidian vault.

Usage:
  python ingest.py --pdf "Lecture01_Intro.pdf" --module "CS-101"
  python ingest.py --pdf "VL02.pdf" --module "DBM-101" --transcript "VL02.txt"
  python ingest.py --pdf "Lecture03.pdf" --module "CS-101" --title "Data Models" --lecture-nr 03

Edit config.py before running to set your vault path and preferred language.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Load user configuration from config.py
# ---------------------------------------------------------------------------
try:
    from config import VAULT_PATH, INBOX_FOLDER, DEFAULT_LANGUAGE
except ImportError:
    print(
        "[ERROR] config.py not found.\n"
        "  Copy config.py to this directory and edit VAULT_PATH before running.",
        file=sys.stderr,
    )
    sys.exit(1)

VAULT_INBOX = Path(VAULT_PATH).expanduser() / INBOX_FOLDER

# ---------------------------------------------------------------------------
# NotebookLM query sets — English and German
# Keys must stay consistent: key_points, terms, summary, connections
# ---------------------------------------------------------------------------
QUERIES_EN = [
    ("key_points",  "Extract all key points that are relevant for exams."),
    ("terms",       "List all important terms with their definitions."),
    ("summary",     "Write a summary of this lecture in 5-8 sentences."),
    ("connections", "Which topics from other lectures or modules are referenced here?"),
]

QUERIES_DE = [
    ("key_points",  "Extrahiere alle Kernaussagen die klausurrelevant sind. Antworte auf Deutsch."),
    ("terms",       "Liste alle wichtigen Begriffe mit ihrer Definition auf. Antworte auf Deutsch."),
    ("summary",     "Schreibe eine Zusammenfassung der Vorlesung in 5-8 Sätzen. Antworte auf Deutsch."),
    ("connections", "Welche Themen aus anderen Vorlesungen oder Modulen werden hier referenziert? Antworte auf Deutsch."),
]

QUERIES = QUERIES_DE if DEFAULT_LANGUAGE == "de" else QUERIES_EN

# Section header labels per language
LABELS = {
    "en": {
        "key_points":  "🎯 Key Points (Exam Relevant)",
        "terms":       "📖 Concepts & Definitions",
        "connections": "🔗 Connections",
        "summary":     "📝 Summary",
        "questions":   "❓ Open Questions",
    },
    "de": {
        "key_points":  "🎯 Kernaussagen (Klausurrelevant)",
        "terms":       "📖 Konzepte & Definitionen",
        "connections": "🔗 Verbindungen",
        "summary":     "📝 Zusammenfassung",
        "questions":   "❓ Offene Fragen",
    },
}


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def run(args: list[str]) -> str:
    """Run a CLI command and return stdout. Prints error and exits on failure."""
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed: {' '.join(args)}", file=sys.stderr)
        if result.stderr.strip():
            print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        if result.stdout.strip():
            print(f"  stdout: {result.stdout.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def run_best_effort(args: list[str]) -> None:
    """Run a command and silently ignore any failure (used for async waits)."""
    subprocess.run(args, capture_output=True, text=True, encoding="utf-8")


def delete_notebook(notebook_id: str) -> None:
    """Attempt to delete a partially-created notebook on error cleanup."""
    if notebook_id:
        print(f"[CLEANUP] Deleting notebook {notebook_id}...", file=sys.stderr)
        run_best_effort(["notebooklm", "delete", notebook_id])


# ---------------------------------------------------------------------------
# JSON / output parsers
# ---------------------------------------------------------------------------

def extract_answer(raw: str, *keys: str) -> str:
    """
    Parse JSON from notebooklm ask --json and return the answer text.
    Tries a list of known keys, then falls back to the longest string value.
    If the output is not JSON, returns the raw string directly.
    """
    try:
        data = json.loads(raw)
        for key in keys:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        # Fallback: pick the longest string value in the response object
        candidates = [v for v in data.values() if isinstance(v, str) and len(v) > 20]
        if candidates:
            return max(candidates, key=len).strip()
        return raw
    except (json.JSONDecodeError, AttributeError):
        return raw.strip()


def extract_notebook_id(raw: str) -> str:
    """
    Parse the notebook ID from notebooklm create --json output.
    Handles both flat {"id": "..."} and nested {"notebook": {"id": "..."}} shapes.
    """
    try:
        data = json.loads(raw)
        # Unwrap nested structure if present
        if "notebook" in data and isinstance(data["notebook"], dict):
            data = data["notebook"]
        for key in ("id", "notebook_id", "notebookId", "notebookID"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        # Fallback: first string value with no spaces (looks like an ID)
        candidates = [v for v in data.values() if isinstance(v, str) and " " not in v and len(v) > 4]
        if candidates:
            return candidates[0]
    except (json.JSONDecodeError, AttributeError):
        pass
    return raw  # Return raw string if all parsing fails


# ---------------------------------------------------------------------------
# Filename / title helpers
# ---------------------------------------------------------------------------

def extract_lecture_nr(stem: str) -> str:
    """
    Derive a zero-padded lecture number from a filename stem.
    Matches patterns like VL01, Lecture02, L03. Defaults to "01".
    """
    match = re.search(r"(?:VL|Lecture|L)(\d+)", stem, re.IGNORECASE)
    return match.group(1).zfill(2) if match else "01"


def slugify(text: str) -> str:
    """
    Convert a title string into a safe filename slug.
    Strips special characters, replaces spaces with underscores, caps at 60 chars.
    """
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "_", text.strip())
    return text[:60].strip("_")


# ---------------------------------------------------------------------------
# Note builder
# ---------------------------------------------------------------------------

def build_note(
    *,
    title: str,
    module: str,
    lecture_nr: str,
    notebook_id: str,
    pdf_name: str,
    pdf_abs_path: str,
    transcript_name: str,
    answers: dict[str, str],
) -> str:
    """
    Assemble the full Obsidian Markdown note as a string.
    Includes YAML frontmatter and one section per NotebookLM answer.
    """
    today = date.today().isoformat()
    tag_module = module.lower().replace("-", "")
    # Obsidian Annotator plugin reads annotation-target to open the source PDF
    annotation_target = pdf_abs_path.replace("\\", "/")
    lang = DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in LABELS else "en"
    L = LABELS[lang]

    return f"""---
title: "{title}"
module: "{module}"
lecture_nr: {lecture_nr}
date: {today}
professor: ""
tags:
  - lecture
  - {tag_module}
status: "raw"
source_pdf: "{pdf_name}"
source_transcript: "{transcript_name}"
notebooklm_id: "{notebook_id}"
annotation-target: "{annotation_target}"
---

# {title}

## {L['key_points']}

{answers['key_points']}

## {L['terms']}

{answers['terms']}

## {L['connections']}

{answers['connections']}

## {L['summary']}

{answers['summary']}

## {L['questions']}
- [ ]
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a lecture PDF through NotebookLM and write an Obsidian note.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py --pdf "Lecture01_Intro.pdf" --module "CS-101"
  python ingest.py --pdf "VL02.pdf" --module "DBM-101" --transcript "VL02.txt"
  python ingest.py --pdf "L03.pdf" --module "CS-101" --title "Data Models" --lecture-nr 03
""",
    )
    parser.add_argument("--pdf",        required=True, help="Path to the lecture PDF file")
    parser.add_argument("--module",     required=True, help='Module code, e.g. "CS-101"')
    parser.add_argument("--transcript", help="Path to a transcript TXT file (optional)")
    parser.add_argument("--title",      help="Lecture title (default: derived from filename)")
    parser.add_argument("--lecture-nr", dest="lecture_nr", help="Lecture number override, e.g. 03")
    args = parser.parse_args()

    # --- Validate input files ---
    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    transcript_path = None
    if args.transcript:
        transcript_path = Path(args.transcript).resolve()
        if not transcript_path.exists():
            print(f"[ERROR] Transcript not found: {transcript_path}", file=sys.stderr)
            sys.exit(1)

    # --- Check that notebooklm CLI is installed and reachable ---
    check = subprocess.run(["notebooklm", "--version"], capture_output=True, text=True)
    if check.returncode != 0:
        print(
            "[ERROR] notebooklm CLI not found.\n"
            "  Install:      pip install notebooklm-py[playwright]\n"
            "  Browser:      playwright install chromium\n"
            "  Authenticate: notebooklm login",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Derive title and lecture number from filename if not provided ---
    lecture_nr = args.lecture_nr or extract_lecture_nr(pdf_path.stem)
    if args.title:
        raw_title = args.title
    else:
        raw_title = re.sub(r"^(?:VL|Lecture|L)\d+[\s_\-]+", "", pdf_path.stem, flags=re.IGNORECASE)
        raw_title = raw_title.replace("_", " ").replace("-", " ").strip() or pdf_path.stem

    display_title  = f"Lecture {lecture_nr} - {raw_title}"
    notebook_title = f"{display_title} [{args.module}]"

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  NOTEBOOKLM → OBSIDIAN PIPELINE")
    print(sep)
    print(f"  PDF      : {pdf_path.name}")
    print(f"  Module   : {args.module}")
    print(f"  Title    : {display_title}")
    print(f"  Language : {DEFAULT_LANGUAGE.upper()}")
    if transcript_path:
        print(f"  Transcript: {transcript_path.name}")
    print(f"{sep}\n")

    notebook_id = ""
    note_path: Path | None = None

    try:
        # ===== STEP 1: Create notebook =====
        print("[1/5] Creating notebook in NotebookLM...")
        raw_create = run(["notebooklm", "create", notebook_title, "--json"])
        notebook_id = extract_notebook_id(raw_create)
        print(f"      Notebook ID: {notebook_id}")

        # ===== STEP 2: Upload PDF (and optionally transcript) =====
        print("[2/5] Uploading PDF...")
        raw_add = run(["notebooklm", "source", "add", str(pdf_path), "-n", notebook_id, "--type", "file"])
        source_match = re.search(r"[0-9a-f]{8}-[0-9a-f-]{27,}", raw_add)
        source_id = source_match.group(0) if source_match else ""
        print(f"      Uploaded: {pdf_path.name}")

        if transcript_path:
            print("[2b]  Uploading transcript...")
            run(["notebooklm", "source", "add", str(transcript_path), "-n", notebook_id])
            print(f"      Uploaded: {transcript_path.name}")

        # ===== STEP 3: Wait for indexing =====
        print("[3/5] Waiting for source indexing...")
        if source_id:
            run_best_effort(["notebooklm", "source", "wait", source_id, "-n", notebook_id])
        print("      Indexing complete.")

        # ===== STEP 4: Ask 4 questions =====
        print(f"[4/5] Querying NotebookLM ({len(QUERIES)} questions)...")
        answers: dict[str, str] = {}
        for i, (key, query) in enumerate(QUERIES, 1):
            print(f"      [{i}/{len(QUERIES)}] {query[:58]}...")
            raw_answer = run(["notebooklm", "ask", query, "-n", notebook_id, "--json"])
            answers[key] = extract_answer(raw_answer, "answer", "text", "content", "response")
            print(f"            {len(answers[key])} chars received.")

        # ===== STEP 5: Write Obsidian note =====
        print("[5/5] Writing Obsidian note...")
        note_filename = f"Lecture{lecture_nr}_{slugify(raw_title)}.md"
        note_path = VAULT_INBOX / note_filename
        VAULT_INBOX.mkdir(parents=True, exist_ok=True)

        note_content = build_note(
            title=display_title,
            module=args.module,
            lecture_nr=lecture_nr,
            notebook_id=notebook_id,
            pdf_name=pdf_path.name,
            pdf_abs_path=str(pdf_path),
            transcript_name=transcript_path.name if transcript_path else "",
            answers=answers,
        )
        note_path.write_text(note_content, encoding="utf-8")
        print(f"      Saved: {note_path}")

    except SystemExit:
        # If anything went wrong after the notebook was created, clean it up
        if notebook_id:
            delete_notebook(notebook_id)
        raise

    print(f"""
{sep}
  DONE!
{sep}
  Notebook ID : {notebook_id}
  Note saved  : {note_path}
{sep}
""")


if __name__ == "__main__":
    main()
