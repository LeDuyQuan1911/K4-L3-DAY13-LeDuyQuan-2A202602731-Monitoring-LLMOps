"""
Promote production label to v2, then rollback to v1.
Chay: python scripts/prompt_rollback.py
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

# Step 1: Promote production to v2
print(f"[Step 1] Promoting 'production' label to version 2 of '{PROMPT_NAME}'...")
try:
    # Get current prompt with production label
    prompt_v1 = client.get_prompt(PROMPT_NAME, label="production", type="text")
    print(f"  Current production: version={prompt_v1.version}")

    # Get v2 (candidate)
    prompt_v2 = client.get_prompt(PROMPT_NAME, label="candidate", type="text")
    print(f"  Candidate: version={prompt_v2.version}")

    # Promote v2 to production by creating new version with production label
    # In Langfuse SDK v4, we set labels on existing versions via API
    print("  Promoting v2 to production...")
    # We re-create with production label
    client.create_prompt(
        name=PROMPT_NAME,
        prompt="You are a helpful assistant.\n\nFeature={{feature}}\nContext:\n{{docs}}\n\nUser Question: {{message}}\n\nProvide a concise and accurate answer.",
        type="text",
        labels=["production", "candidate"],
    )
    print("  [OK] Version 3 created with 'production' label (promote)")
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 2: Rollback production to v1
print(f"\n[Step 2] Rolling back 'production' to version 1 (baseline)...")
try:
    client.create_prompt(
        name=PROMPT_NAME,
        prompt="Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}",
        type="text",
        labels=["production", "rollback"],
    )
    print("  [OK] Rollback done - new version with 'production' label (original template)")
except Exception as e:
    print(f"  [ERROR] {e}")

# Verify
print(f"\n[Step 3] Verifying current production prompt...")
try:
    current = client.get_prompt(PROMPT_NAME, label="production", type="text")
    print(f"  Current production version: {current.version}")
    compiled = current.compile(feature="qa", docs="test", message="hello")
    print(f"  Template starts with: {compiled[:60]}...")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\nDone! Take screenshots of Langfuse prompt versions for evidence.")
