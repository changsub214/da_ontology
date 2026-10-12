#!/usr/bin/env python3
"""Upload the OKF bundle to GCS (gs://finance_okf/okf) and verify MD5 parity.

Proves 3 things after `gcloud storage rsync -r`:
  1. count   -- every local OKF file (.md + locations.yaml) has a remote object
  2. digest  -- every remote object's MD5 equals the local file's MD5
  3. orphans -- nothing remote under gs://finance_okf/okf/ that is not local
               (except the intended fixtures declared in tools/okf_fixtures.yaml, which
               must exist remotely and are shielded from rsync deletion)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OKF_DIR = os.path.join(ROOT, "finance", "okf")
FIXTURES_FILE = os.path.join(ROOT, "tools", "okf_fixtures.yaml")

PROJECT = "finance-ontology-changseop"
BUCKET = "finance_okf"
PREFIX = "okf"
EXCLUDE_FILES = {"verification.json"}


def fixture_objects() -> list[str]:
    """Intended remote-only objects (Q21 governance fixture) — see tools/okf_fixtures.yaml."""
    import yaml

    with open(FIXTURES_FILE, encoding="utf-8") as f:
        return list((yaml.safe_load(f) or {}).get("gcs_objects") or [])


def local_files():
    """Relative path -> base64 MD5, matching the form GCS reports."""
    out = {}
    for dirpath, _, names in os.walk(OKF_DIR):
        for n in sorted(names):
            if n in EXCLUDE_FILES:
                continue
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, OKF_DIR)
            with open(p, "rb") as f:
                out[rel] = base64.b64encode(hashlib.md5(f.read()).digest()).decode()
    return out


def remote_files():
    """Same shape, read back from GCS."""
    r = subprocess.run(
        [
            "gcloud", "storage", "ls", "-r", "--json",
            f"--project={PROJECT}",
            f"gs://{BUCKET}/{PREFIX}/**",
        ],
        capture_output=True, text=True, check=True,
    )
    out = {}
    for item in json.loads(r.stdout):
        url = item.get("url", "")
        if url.endswith("/"):
            continue
        url = url.split("#", 1)[0]
        meta = item.get("metadata") or {}
        rel = url.replace(f"gs://{BUCKET}/{PREFIX}/", "")
        out[rel] = meta.get("md5Hash")
    return out


def sync():
    # `-x` also shields matching DESTINATION objects from --delete-unmatched-destination-objects
    # (measured 2026-09-27 on a scratch prefix), so the fixtures survive a full sync.
    # One anchored group `^(?:a|b|…)$`, not `^a$|^b$`: measured 2026-09-28 with gcloud 584 (dry-run),
    # `^a$|^b$` and repeated `-x` flags exclude only the LAST pattern on the local side, which uploaded
    # verification.json once (01:36Z). The grouped form excluded every alternative.
    excludes = [r"verification\.json"] + [re.escape(p) for p in fixture_objects()]
    exclude_regex = "^(?:" + "|".join(excludes) + ")$"
    subprocess.run(
        [
            "gcloud", "storage", "rsync", "-r",
            "--delete-unmatched-destination-objects",
            "-x", exclude_regex,
            f"--project={PROJECT}",
            OKF_DIR,
            f"gs://{BUCKET}/{PREFIX}",
        ],
        check=False,
    )


def verify():
    loc, rem = local_files(), remote_files()
    fixtures = set(fixture_objects())
    missing = sorted(set(loc) - set(rem))
    orphan = sorted(set(rem) - set(loc) - fixtures)
    fixture_missing = sorted(fixtures - set(rem))
    corrupt = sorted(
        k for k in set(loc) & set(rem)
        if rem[k] is not None and rem[k] != loc[k]
    )
    nodigest = sorted(k for k in set(loc) & set(rem) if rem[k] is None)

    print(f"local {len(loc)} · remote {len(rem)} (= {len(rem) - len(fixtures & set(rem))} bundle + "
          f"{len(fixtures & set(rem))}/{len(fixtures)} fixtures from tools/okf_fixtures.yaml)")
    for label, items in (
        ("MISSING remotely", missing),
        ("ORPHANED remotely", orphan),
        ("FIXTURE MISSING remotely", fixture_missing),
        ("DIGEST MISMATCH", corrupt),
    ):
        if items:
            print(f"\n{label} ({len(items)}):")
            for i in items[:20]:
                print(f"  {i}")
    if nodigest:
        print(f"\nno MD5 reported ({len(nodigest)}) — cannot verify these")
    return not (missing or orphan or fixture_missing or corrupt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument(
        "--retries", type=int, default=3,
        help="rsync attempts before giving up",
    )
    args = ap.parse_args()

    if args.verify_only:
        ok = verify()
        print("\nPASS — every local OKF file is present in gs://finance_okf/okf/ with a matching MD5 digest"
              if ok else "\nFAIL — see the lists above")
        return 0 if ok else 1

    for attempt in range(1, args.retries + 1):
        print(f"--- rsync attempt {attempt} ---")
        sync()
        if verify():
            print("\nPASS — every local OKF file is present in gs://finance_okf/okf/ with a matching MD5 digest")
            return 0
        print(f"\nincomplete after attempt {attempt}")
    print(f"\nFAIL — still incomplete after {args.retries} attempts")
    return 1


if __name__ == "__main__":
    sys.exit(main())
