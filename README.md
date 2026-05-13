# notebooklm-obsidian-pipeline

**Automated pipeline: local PDFs + lecture transcripts → NotebookLM → structured Obsidian notes. Built for dense academic material (Master/PhD level).**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## What This Does

You drop a lecture PDF (and optionally a transcript) into a folder. One command later, a fully structured study note appears in your Obsidian vault — ready for review, cross-linked, and tagged.

NotebookLM reads both the slides and the transcript together, cross-references them, and answers four specific academic questions. The pipeline collects those answers and formats them into a clean Markdown note with proper YAML frontmatter.

```
┌─────────────────────────────────────────────────────┐
│                   YOUR INPUT                        │
│  lecture.pdf  +  transcript.txt (optional)          │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│                  ingest.py                          │
│  1. Creates a new NotebookLM notebook               │
│  2. Uploads PDF (+ transcript) as sources           │
│  3. Waits for indexing to complete                  │
│  4. Asks 4 academic questions via notebooklm CLI    │
│  5. Writes structured Markdown note to vault        │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐   ┌────────────────────────────┐
│   NotebookLM     │   │     Obsidian Vault          │
│  (Google AI)     │   │  00_INBOX/                  │
│                  │   │    Lecture01_Topic.md        │
│  Cross-references│   │      ├─ Key Points           │
│  slides + audio  │   │      ├─ Definitions          │
└──────────────────┘   │      ├─ Connections          │
                        │      └─ Summary              │
                        └────────────────────────────┘
```

**The four questions asked to NotebookLM:**
1. Extract all key points relevant for exams
2. List all important terms with their definitions
3. Write a 5–8 sentence summary
4. Which topics from other lectures are referenced here?

---

## Requirements

- **Python 3.10 or higher** — [python.org/downloads](https://www.python.org/downloads/)
- **A Google account** — required to log into NotebookLM
- **Obsidian** (free) — [obsidian.md](https://obsidian.md)
- **Claude Pro or Max** *(optional)* — only needed if you want to use Claude Code to extend or customize the pipeline

---

## Installation — Step by Step

### Step 1 — Install notebooklm-py with browser support

This package drives NotebookLM through a real browser in the background.

**Windows (PowerShell) / macOS / Linux:**
```bash
pip install "notebooklm-py[playwright]"
```

### Step 2 — Install the Chromium browser

Playwright needs a browser to automate. Run this once:

```bash
playwright install chromium
```

### Step 3 — Authenticate with your Google account

```bash
notebooklm login
```

A browser window will open. Log in with your Google account and close it when done. Your session is saved locally.

### Step 4 — Clone this repository

```bash
git clone https://github.com/Floucs/notebooklm-obsidian-pipeline.git
cd notebooklm-obsidian-pipeline
```

### Step 5 — Edit config.py

Open `config.py` in any text editor and set the path to your Obsidian vault:

```python
# Windows
VAULT_PATH = "C:/Users/yourname/MasterVault"

# macOS / Linux
VAULT_PATH = "/Users/yourname/MasterVault"
```

Also set `DEFAULT_LANGUAGE`:
- `"en"` → English questions and note headers
- `"de"` → German questions and note headers

### Step 6 — Create your Obsidian vault folder structure

Open Obsidian, create a new vault (or use an existing one), and create these folders inside it:

```
MasterVault/
├── 00_INBOX/
├── 10_LECTURES/
├── 20_CONCEPTS/
├── 30_EXAMS/
├── 40_RESOURCES/
└── 90_TEMPLATES/
```

### Step 7 — Test the setup

Run a test with any PDF to confirm everything works:

```bash
python ingest.py --pdf "path/to/any_lecture.pdf" --module "TEST-01"
```

**Windows PowerShell note:** If you get an execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

If it works, a `.md` file will appear in your vault's `00_INBOX/` folder.

---

## Obsidian Vault Setup

### Folder structure

| Folder | Purpose |
|--------|---------|
| `00_INBOX` | Raw pipeline output — notes land here first with `status: raw` |
| `10_LECTURES` | Reviewed and cleaned-up lecture notes |
| `20_CONCEPTS` | Atomic concept notes, one idea per file (Zettelkasten style) |
| `30_EXAMS` | Exam preparation: summaries, flashcards, practice questions |
| `40_RESOURCES` | Literature references, external links, PDFs |
| `90_TEMPLATES` | Obsidian Templater templates |

### YAML frontmatter

Every generated note includes this frontmatter:

```yaml
---
title: "Lecture 01 - Introduction to Data Models"
module: "CS-101"
lecture_nr: 01
date: 2026-05-13
professor: ""
tags:
  - lecture
  - cs101
status: "raw"
source_pdf: "Lecture01_DataModels.pdf"
source_transcript: "Lecture01.txt"
notebooklm_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
annotation-target: "C:/Users/yourname/Lectures/Lecture01.pdf"
---
```

**Status workflow:** `raw` → `reviewed` → `done`

The `annotation-target` field is used by the Obsidian Annotator plugin to open the original PDF directly from within the note.

### Copy the templates

Copy the files from `obsidian-templates/` into your vault's `90_TEMPLATES/` folder:

```
obsidian-templates/tpl_lecture_note.md  →  MasterVault/90_TEMPLATES/
obsidian-templates/tpl_concept_note.md  →  MasterVault/90_TEMPLATES/
```

---

## Configuration

All settings live in `config.py`. Edit it once before first use:

```python
# Path to your Obsidian vault
VAULT_PATH = "C:/Users/yourname/MasterVault"

# Subfolder where new notes are saved
INBOX_FOLDER = "00_INBOX"

# Query language: "en" or "de"
DEFAULT_LANGUAGE = "en"

# Optional: default source folder for batch_ingest.py
# Set this so you can run: python batch_ingest.py --module "CS-101"
DEFAULT_SOURCE_FOLDER = "C:/Users/yourname/Lectures/CS-101"
```

---

## Usage

### Single lecture

```bash
python ingest.py --pdf "path/to/Lecture01_Introduction.pdf" --module "CS-101"
```

### With transcript

```bash
python ingest.py --pdf "Lecture01.pdf" --transcript "Lecture01.txt" --module "CS-101"
```

### Custom title or lecture number

```bash
python ingest.py --pdf "lecture.pdf" --module "CS-101" --title "Data Models" --lecture-nr 03
```

### Whole folder at once

```bash
python batch_ingest.py --folder "C:/Lectures/CS-101" --module "CS-101"
```

### Preview without processing (dry run)

```bash
python batch_ingest.py --folder "C:/Lectures" --module "CS-101" --dry-run
```

### Custom delay between uploads

```bash
python batch_ingest.py --folder "C:/Lectures" --module "CS-101" --delay 30
```

**After running,** open Obsidian. The new note appears in `00_INBOX/` with:
- `status: raw` — meaning it was auto-generated and needs a human review
- All four sections filled in by NotebookLM
- A direct link back to the source PDF via `annotation-target`

When you've reviewed it, change `status` to `reviewed`, then `done` when complete.

---

## Recommended Obsidian Plugins

Install these from **Settings → Community Plugins → Browse**:

| Plugin | What it does |
|--------|--------------|
| **Dataview** | Live tables and queries across all your notes — powers the dashboard |
| **Templater** | Advanced templates with dynamic fields (date, title) for manual notes |
| **QuickAdd** | One-keystroke commands to create new notes from templates |
| **Obsidian Git** | Auto-commits and pushes your vault to GitHub every few minutes |
| **Calendar** | Visual calendar in the sidebar; click any day to open a daily note |
| **Kanban** | Visual board for moving notes through `raw → reviewed → done` |
| **Excalidraw** | Draw concept maps and diagrams directly inside Obsidian |
| **Annotator** | Open and annotate the source PDF directly from within the note |

---

## Troubleshooting

### 1. PowerShell execution policy error

**Error:** `cannot be loaded because running scripts is disabled on this system`

**Fix:** Open PowerShell as Administrator and run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 2. Ampersand (&) in folder path causes issues

**Error:** Unexpected token or path not found when your folder name contains `&`

**Fix:** Always wrap paths in double quotes:
```powershell
python ingest.py --pdf "C:\Lectures\Marketing & Strategy\Lecture01.pdf" --module "MKT-101"
```

---

### 3. NotebookLM uploads the path as text instead of a file

**Symptom:** NotebookLM receives the string `"C:\path\file.pdf"` as a text source instead of uploading the actual file.

**Fix:** Always pass the full absolute path and include `--type file`:
```bash
notebooklm source add "C:/Users/yourname/Lectures/Lecture01.pdf" -n NOTEBOOK_ID --type file
```
The `ingest.py` script does this automatically — this only matters if you call `notebooklm` manually.

---

### 4. git not recognized in PowerShell

**Error:** `git : The term 'git' is not recognized`

**Fix:** Install Git for Windows:
```powershell
winget install Git.Git
```
Then close and reopen PowerShell.

---

### 5. notebooklm login session expired

**Symptom:** Authentication error or redirect to Google login during a run.

**Fix:**
```bash
notebooklm login
```
Re-authenticate in the browser window that opens.

---

### 6. Note not appearing in Obsidian

**Check:** Is your `VAULT_PATH` in `config.py` pointing to the correct folder?

```python
# Wrong — this is the pipeline folder, not the vault
VAULT_PATH = "C:/Users/yourname/Documents/notebooklm-obsidian-pipeline"

# Correct — this is the Obsidian vault root
VAULT_PATH = "C:/Users/yourname/MasterVault"
```

---

## Contributing

Found a bug or have an idea? Open an issue or submit a pull request — both are very welcome.

This project started as a personal study tool for dense graduate-level coursework. If you've adapted it for a different use case (law school, medical school, research), sharing your config or query set would be especially useful for others.

---

## License

MIT — free to use, modify, and share.

---

*Built for Master's level academic workflows.*
