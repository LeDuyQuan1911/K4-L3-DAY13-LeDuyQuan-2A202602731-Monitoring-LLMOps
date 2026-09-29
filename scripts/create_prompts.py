"""
Script tao prompt day13-chat v1 va v2 tren Langfuse.
Chay: python scripts/create_prompts.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
configure_utf8_stdio()

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from langfuse import get_client

client = get_client()

PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")

# -- Version 1: baseline --
print(f"Creating prompt '{PROMPT_NAME}' version 1...")
try:
    client.create_prompt(
        name=PROMPT_NAME,
        prompt="Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}",
        type="text",
        labels=["baseline", "production"],
    )
    print("  [OK] Version 1 created with labels: baseline, production")
except Exception as e:
    print(f"  [WARN] Version 1: {e}")

# -- Version 2: candidate --
print(f"Creating prompt '{PROMPT_NAME}' version 2...")
try:
    client.create_prompt(
        name=PROMPT_NAME,
        prompt="You are a helpful assistant.\n\nFeature={{feature}}\nContext:\n{{docs}}\n\nUser Question: {{message}}\n\nProvide a concise and accurate answer.",
        type="text",
        labels=["candidate"],
    )
    print("  [OK] Version 2 created with label: candidate")
except Exception as e:
    print(f"  [WARN] Version 2: {e}")

print("\nDone! Check your Langfuse project for prompt versions.")
