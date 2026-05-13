"""
config.py — Edit this file before running ingest.py.

Steps:
  1. Set VAULT_PATH to the root of your Obsidian vault.
  2. Set DEFAULT_LANGUAGE to "en" or "de".
  3. Optionally change INBOX_FOLDER if your vault uses a different name.
"""

import os

# Absolute path to your Obsidian vault root.
# Windows example:  "C:/Users/yourname/MasterVault"
# macOS example:    "/Users/yourname/MasterVault"
# Linux example:    "/home/yourname/MasterVault"
# Or use a home-relative path:
VAULT_PATH = os.path.expanduser("~/MasterVault")

# Subfolder inside the vault where new notes are saved.
INBOX_FOLDER = "00_INBOX"

# Language for NotebookLM queries.
# "en" → English questions and section headers
# "de" → German questions and section headers
DEFAULT_LANGUAGE = "en"

# Optional: default source folder for batch_ingest.py.
# Leave as "" to always pass --folder explicitly.
DEFAULT_SOURCE_FOLDER = ""
