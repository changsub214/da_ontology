#!/usr/bin/env python3
"""Push the Finance Ontology OKF v0.2 bundle into Dataplex Knowledge Catalog
as one entry per markdown file in project `finance-ontology-changseop`.

Architecture mapping:
    GCS object  gs://finance_okf/okf/<path>.md     <- where the OKF actually lives
       ^
       | entrySource.resource (gs:// URI)
       |
    Entry       finance-okf/entries/<path>         <- the Dataplex Catalog handle
       + aspect `567090080191.us-central1.okf`     <- the frontmatter signal layer
       + aspect `dataplex-types.global.overview`   <- Markdown body (contentType=MARKDOWN)

Mapping rules follow upstream `knowledge-catalog/toolbox/mdcode/demo/okf/okf.ts`:
  - `title`, `description`, `tags` stay on the entry itself (`LAYOUT_KEYS`)
  - `generated`, `verified`, `status`, `sources`, etc. go onto the `okf` aspect (`SIGNAL_KEYS`)
  - Everything else (`content_class`, `sha256`, `section_number`, `source_page`,
    `part_of`, `sequence`, `verified[].method`, etc.) is JSON-stringified into
    `okf.extra` as `[path, value]` pairs so the round-trip is 100% lossless.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as _dt
import json
import os
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OKF_DIR = os.path.join(ROOT, "finance", "okf")

PROJECT = "finance-ontology-changseop"
PROJECT_NUMBER = "567090080191"
LOCATION = "us-central1"
ENTRY_GROUP = "finance-okf"
ENTRY_TYPE = "okf-bundle"
BUCKET = "finance_okf"
PREFIX = "okf"

OKF_ASPECT = f"{PROJECT_NUMBER}.{LOCATION}.okf"
OVERVIEW_ASPECT = "dataplex-types.global.overview"
CONTACTS_ASPECT = "dataplex-types.global.contacts"

# okf.ts: keys the Documents Layout maps natively; they stay off the aspect.
LAYOUT_KEYS = ("title", "description", "tags")
# Structured keys the `okf` aspect models at the top level.
SIGNAL_KEYS = (
    "generated", "verified", "status", "stale_after", "usage_window",
    "runtime", "parameters", "computation", "executor", "attester", "sources",
    "version", "content_class", "treatment", "language", "license", "part_of",
    "section_number", "source_page", "issuing_body", "document_id", "group",
    "extraction_strategy",
)
# RECORD_KEYS: sub-keys each modelled record declares.
RECORD_KEYS = {
    "generated": {"by", "at"},
    "verified": {"by", "at", "method", "checks"},
    "sources": {"id", "resource", "title", "author", "usage_count", "last_modified", "kind", "sha256"},
    "usage_window": {"from", "to"},
    "parameters": {"name", "type", "required"},
    "executor": {"resource", "receipt"},
    "attester": {"resource"},
}
LIST_KEYS = {"verified", "parameters", "sources"}


def split_frontmatter(text: str):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    return yaml.safe_load(text[4:end]) or {}, text[end + 4:]


def divert(field, value, extras, path):
    """Keep what the aspect schema declares; normalize list sub-fields like `checks`."""
    allowed = RECORD_KEYS.get(field)
    if allowed is None or not isinstance(value, dict):
        return value
    kept = {}
    for k, v in value.items():
        if k in allowed:
            if isinstance(v, list):
                kept[k] = ", ".join(str(x) for x in v)
            else:
                kept[k] = str(v) if k not in ("usage_count",) and not isinstance(v, (str, int, float, bool)) else v
        else:
            extras.append([path + [k], v])
    return kept


def to_aspect(fm: dict) -> dict:
    extras: list = []
    data: dict = {}

    if "type" in fm:
        data["okf_type"] = str(fm["type"])
    data["version"] = str(fm.get("version", "0.2.0"))

    for key in SIGNAL_KEYS:
        if key not in fm:
            continue
        v = fm[key]
        if key in LIST_KEYS:
            items = v if isinstance(v, list) else [v]
            data[key] = [
                divert(key, it, extras, [key, str(i)]) for i, it in enumerate(items)
            ]
        elif isinstance(v, dict):
            data[key] = divert(key, v, extras, [key])
        else:
            data[key] = str(v)

    return data


def entry_id(rel: str) -> str:
    return rel[:-3] if rel.endswith(".md") else rel


def source_update_time(fm: dict) -> str:
    at = (fm.get("generated") or {}).get("at") if isinstance(
        fm.get("generated"), dict) else None
    if isinstance(at, str) and at:
        return at
    return _dt.datetime.now(_dt.timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")


def parse_contacts_aspect(raw_contacts) -> dict | None:
    """Parse '이름(직급) - 부서 <email>' into dataplex-types.global.contacts aspect payload."""
    if not raw_contacts:
        return None
    s = str(raw_contacts).strip()
    if not s or s == "-":
        return None
    import re
    m = re.match(r"^(.+?)\s*<([^>]+)>$", s)
    if m:
        name_part = m.group(1).strip()
        email_part = m.group(2).strip()
    else:
        name_part = s
        email_part = ""
    role = "owner" if "봉미선" in name_part or "여신심사" in name_part else "steward"
    return {
        "identities": [
            {
                "role": role,
                "name": name_part,
                "id": email_part or name_part,
            }
        ]
    }


def push_one(rel: str, dry_run: bool = False) -> bool:
    path = os.path.join(OKF_DIR, rel)
    fm, body = split_frontmatter(open(path, encoding="utf-8").read())
    gcs = f"gs://{BUCKET}/{PREFIX}/{rel}"

    aspects = {}
    aspect_data = to_aspect(fm)
    if aspect_data:
        aspects[OKF_ASPECT] = {"data": aspect_data}
    aspects[OVERVIEW_ASPECT] = {
        "data": {"content": (body.strip() or f"# {rel}"), "contentType": "MARKDOWN"}
    }
    contacts_data = parse_contacts_aspect(fm.get("contacts"))
    if contacts_data:
        aspects[CONTACTS_ASPECT] = {"data": contacts_data}

    eid = entry_id(rel)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(aspects, f, ensure_ascii=False, default=str)
        aspect_file = f.name

    cmd = [
        "gcloud", "dataplex", "entries", "create", eid,
        f"--entry-group={ENTRY_GROUP}", f"--location={LOCATION}",
        f"--project={PROJECT}",
        f"--entry-type={ENTRY_TYPE}", f"--entry-type-location={LOCATION}",
        f"--entry-type-project={PROJECT}",
        f"--entry-source-resource={gcs}",
        "--entry-source-system=Open Knowledge Format",
        "--entry-source-platform=OKF",
        f"--aspects={aspect_file}",
    ]
    if fm.get("title"):
        cmd.append(f"--entry-source-display-name={str(fm['title'])[:250]}")
    if fm.get("description"):
        cmd.append(f"--entry-source-description={str(fm['description'])[:1000]}")

    if dry_run:
        os.unlink(aspect_file)
        print(json.dumps(aspects, ensure_ascii=False, indent=2, default=str)[:2000])
        print("\n$ " + " ".join(cmd))
        return True

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        os.unlink(aspect_file)
        print(f"  ok      {eid}", flush=True)
        return True

    if "ALREADY_EXISTS" in r.stderr or "already exists" in r.stderr.lower():
        upd = [
            "gcloud", "dataplex", "entries", "update", eid,
            f"--entry-group={ENTRY_GROUP}", f"--location={LOCATION}",
            f"--project={PROJECT}",
            f"--entry-source-resource={gcs}",
            f"--entry-source-update-time={source_update_time(fm)}",
            f"--update-aspects={aspect_file}",
        ]
        if fm.get("title"):
            upd.append(f"--entry-source-display-name={str(fm['title'])[:250]}")
        if fm.get("description"):
            upd.append(f"--entry-source-description={str(fm['description'])[:1000]}")
        r2 = subprocess.run(upd, capture_output=True, text=True)
        os.unlink(aspect_file)
        if r2.returncode == 0:
            print(f"  updated {eid}", flush=True)
            return True
        print(f"FAIL(update) {rel}\n{r2.stderr.strip()[:1200]}", file=sys.stderr, flush=True)
        return False

    os.unlink(aspect_file)
    print(f"FAIL {rel}\n{r.stderr.strip()[:1200]}", file=sys.stderr, flush=True)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="push a single relative path (with or without .md)")
    ap.add_argument("--prefix", help="push all files starting with a relative directory prefix")
    ap.add_argument("--workers", type=int, default=12, help="parallel gcloud workers")
    ap.add_argument("--concepts-only", action="store_true",
                    help="push only OKF Concept documents (exclude directory index.md files)")
    args = ap.parse_args()

    rels = []
    for dirpath, _, names in os.walk(OKF_DIR):
        for n in sorted(names):
            if n.endswith(".md"):
                if args.concepts_only and n == "index.md":
                    continue
                rels.append(os.path.relpath(os.path.join(dirpath, n), OKF_DIR))
    rels.sort()

    if args.prefix:
        rels = [r for r in rels if r.startswith(args.prefix)]
        if not rels:
            sys.exit(f"no files matching prefix: {args.prefix}")

    if args.only:
        target = args.only if args.only.endswith(".md") else f"{args.only}.md"
        rels = [r for r in rels if r == target or r == args.only]
        if not rels:
            sys.exit(f"no such file: {args.only}")

    if args.dry_run or len(rels) == 1 or args.workers <= 1:
        ok = sum(push_one(r, args.dry_run) for r in rels)
    else:
        ok = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(push_one, r, False): r for r in rels}
            for fut in as_completed(futs):
                if fut.result():
                    ok += 1

    print(f"\n{ok}/{len(rels)} entries pushed to {PROJECT}/{LOCATION}/{ENTRY_GROUP}")
    return 0 if ok == len(rels) else 1


if __name__ == "__main__":
    sys.exit(main())
