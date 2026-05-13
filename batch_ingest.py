#!/usr/bin/env python3
"""
batch_ingest.py — Process an entire folder of lecture PDFs in one go.

Finds all PDFs in a folder, auto-matches transcripts by filename, and
runs ingest.py for each one with an optional delay between uploads.

Usage:
  python batch_ingest.py --folder "C:/Lectures/CS-101" --module "CS-101"
  python batch_ingest.py --module "DBM-101"            # uses DEFAULT_SOURCE_FOLDER from config.py
  python batch_ingest.py --folder "C:/Lectures" --module "CS-101" --dry-run
  python batch_ingest.py --folder "C:/Lectures" --module "CS-101" --delay 30

Transcript matching rules (checked in order):
  1. Exact stem match:   Lecture01_Intro.txt  for  Lecture01_Intro.pdf
  2. Number prefix match: Lecture01.txt        for  Lecture01_Intro.pdf
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from config import DEFAULT_SOURCE_FOLDER
except ImportError:
    DEFAULT_SOURCE_FOLDER = ""

PIPELINE_DIR  = Path(__file__).parent
INGEST_SCRIPT = PIPELINE_DIR / "ingest.py"


def find_pdf_transcript_pairs(folder: Path) -> list[dict]:
    """
    Scan a folder for PDFs and pair each with a transcript if one exists.
    Returns a list of dicts with keys 'pdf' (Path) and 'transcript' (Path | None).
    """
    pdfs = sorted(folder.glob("*.pdf"))
    pairs = []

    for pdf in pdfs:
        transcript = None

        # Rule 1: exact stem match  (Lecture01_Intro.txt)
        candidate = pdf.with_suffix(".txt")
        if candidate.exists():
            transcript = candidate
        else:
            # Rule 2: number-prefix match  (Lecture01.txt, VL01.txt, L01.txt)
            nr_match = re.match(r"((?:VL|Lecture|L)\d+)", pdf.stem, re.IGNORECASE)
            if nr_match:
                short = folder / f"{nr_match.group(1)}.txt"
                if short.exists():
                    transcript = short

        pairs.append({"pdf": pdf, "transcript": transcript})

    return pairs


def run_ingest(pdf: Path, module: str, transcript: Path | None) -> tuple[bool, str]:
    """
    Call ingest.py for a single PDF file.
    Returns (success: bool, message: str).
    """
    cmd = [sys.executable, str(INGEST_SCRIPT), "--pdf", str(pdf), "--module", module]
    if transcript:
        cmd += ["--transcript", str(transcript)]

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode == 0:
        return True, "OK"
    return False, f"Exit code {result.returncode}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-process a folder of lecture PDFs through the NotebookLM pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_ingest.py --folder "C:/Lectures/CS-101" --module "CS-101"
  python batch_ingest.py --module "DBM-101"   # uses DEFAULT_SOURCE_FOLDER from config.py
  python batch_ingest.py --folder "C:/Lectures" --module "CS-101" --dry-run
""",
    )
    parser.add_argument(
        "--folder",
        default=DEFAULT_SOURCE_FOLDER or None,
        help="Folder containing PDF files (default: DEFAULT_SOURCE_FOLDER in config.py)",
    )
    parser.add_argument("--module",  required=True, help='Module code, e.g. "CS-101"')
    parser.add_argument("--delay",   type=int, default=15,
                        help="Seconds to wait between PDFs (default: 15)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without actually running")
    args = parser.parse_args()

    if not args.folder:
        print(
            "[ERROR] No folder specified.\n"
            "  Pass --folder or set DEFAULT_SOURCE_FOLDER in config.py.",
            file=sys.stderr,
        )
        sys.exit(1)

    folder = Path(args.folder).resolve()
    if not folder.exists():
        print(f"[ERROR] Folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    if not INGEST_SCRIPT.exists():
        print(f"[ERROR] ingest.py not found at: {INGEST_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    pairs = find_pdf_transcript_pairs(folder)
    if not pairs:
        print(f"[INFO] No PDFs found in: {folder}")
        sys.exit(0)

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  BATCH INGEST — {len(pairs)} PDF(s) found")
    print(f"  Module : {args.module}")
    print(f"  Folder : {folder}")
    if args.dry_run:
        print(f"  Mode   : DRY RUN (nothing will actually be processed)")
    print(sep)

    results = {"ok": 0, "fail": 0}

    for i, pair in enumerate(pairs, 1):
        pdf        = pair["pdf"]
        transcript = pair["transcript"]
        tx_info    = f" + {transcript.name}" if transcript else ""
        print(f"\n[{i}/{len(pairs)}] {pdf.name}{tx_info}")

        if args.dry_run:
            print(f"       → would be processed (dry-run, skipped)")
            continue

        success, msg = run_ingest(pdf, args.module, transcript)

        if success:
            print(f"       ✓ Done")
            results["ok"] += 1
        else:
            print(f"       ✗ Failed: {msg}")
            results["fail"] += 1

        if i < len(pairs):
            print(f"       Waiting {args.delay}s before next PDF...")
            time.sleep(args.delay)

    print(f"\n{sep}")
    if args.dry_run:
        print(f"  DRY RUN complete — {len(pairs)} PDF(s) found, none processed")
    else:
        print(f"  BATCH complete — {results['ok']} succeeded, {results['fail']} failed")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
