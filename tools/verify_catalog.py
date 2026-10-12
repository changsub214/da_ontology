#!/usr/bin/env python3
"""Verify that the Finance Ontology OKF v0.2 bundle is registered in
Dataplex Knowledge Catalog (`finance-ontology-changseop/us-central1/finance-okf`)
and linked to `gs://finance_okf/okf/`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request

PROJECT = "finance-ontology-changseop"
PROJECT_NUMBER = "567090080191"
LOCATION = "us-central1"
ENTRY_GROUP = "finance-okf"
OKF_ASPECT_KEY = f"{PROJECT_NUMBER}.{LOCATION}.okf"
OVERVIEW_ASPECT_KEY = "dataplex-types.global.overview"


def get_token() -> str:
    return subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_all_entries(token: str) -> list[dict]:
    entries = []
    page_token = ""
    base = (
        f"https://dataplex.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{LOCATION}/entryGroups/{ENTRY_GROUP}/entries"
    )
    while True:
        url = f"{base}?pageSize=100" + (f"&pageToken={page_token}" if page_token else "")
        data = api_get(url, token)
        entries.extend(data.get("entries", []))
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    return entries


def fixture_entries() -> set[str]:
    """Intended KC entries outside the builder bundle (Q21 governance fixture)."""
    import pathlib

    import yaml

    p = pathlib.Path(__file__).resolve().parent / "okf_fixtures.yaml"
    return set((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("kc_entries") or [])


def local_bundle_ids() -> set[str]:
    """Entry IDs push_catalog.py would create: every okf/**/*.md, relative path without .md."""
    import pathlib

    okf = pathlib.Path(__file__).resolve().parents[1] / "finance" / "okf"
    return {str(p.relative_to(okf))[:-3] for p in okf.rglob("*.md")}


def main() -> int:
    token = get_token()
    all_entries = list_all_entries(token)
    # Exclude Dataplex's auto-generated EntryGroup self-entry (`<entryGroup>_entry`)
    entries = [
        e for e in all_entries
        if not e["name"].endswith(f"/entries/{ENTRY_GROUP}_entry")
    ]
    fixtures = fixture_entries()
    present_ids = {e["name"].split("/entries/", 1)[1] for e in entries}
    fixture_missing = sorted(fixtures - present_ids)
    bundle_entries = [e for e in entries if e["name"].split("/entries/", 1)[1] not in fixtures]
    print(f"Total OKF entries in {PROJECT}/{LOCATION}/{ENTRY_GROUP}: {len(entries)} (plus 1 system self-entry)")
    print(f"  = bundle {len(bundle_entries)} + fixtures {len(fixtures) - len(fixture_missing)}/{len(fixtures)} "
          f"(tools/okf_fixtures.yaml)")
    for fid in fixture_missing:
        print(f"  FIXTURE MISSING: {fid}")
    entries = bundle_entries

    gs_prefix = "gs://finance_okf/okf/"
    bad_resource = [
        e["name"] for e in entries
        if not e.get("entrySource", {}).get("resource", "").startswith(gs_prefix)
    ]
    print(f"Entries pointing to {gs_prefix}*: {len(entries) - len(bad_resource)}/{len(entries)}")

    samples = [
        "regulations/01_fsc_banking_reg/doc",
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
    ]
    for sid in samples:
        url = (
            f"https://dataplex.googleapis.com/v1/projects/{PROJECT}"
            f"/locations/{LOCATION}/entryGroups/{ENTRY_GROUP}/entries/{sid}?view=ALL"
        )
        full = api_get(url, token)
        aspects = full.get("aspects", {})
        okf_data = aspects.get(OKF_ASPECT_KEY, {}).get("data", {})
        ov_data = (
            aspects.get("655216118709.global.overview")
            or aspects.get(OVERVIEW_ASPECT_KEY)
            or {}
        ).get("data", {})
        extra_list = json.loads(okf_data.get("extra", "[]")) if okf_data.get("extra") else []
        print(f"\n[Sample Entry: {sid}]")
        print(f"  entrySource.resource : {full.get('entrySource', {}).get('resource')}")
        print(f"  entrySource.display  : {full.get('entrySource', {}).get('displayName')}")
        print(f"  okf.okf_type         : {okf_data.get('okf_type')}")
        print(f"  okf.status           : {okf_data.get('status')}")
        print(f"  okf.generated        : {okf_data.get('generated')}")
        print(f"  okf.extra pairs      : {len(extra_list)} lossless pairs (e.g. {extra_list[:3]})")
        print(f"  overview.contentType : {ov_data.get('contentType')} ({len(ov_data.get('content', ''))} chars)")

    ids = {e["name"].split("/entries/", 1)[1] for e in entries}
    expected = local_bundle_ids()
    missing = sorted(expected - ids)
    stale = sorted(ids - expected)
    print(f"Local bundle okf/**/*.md: {len(expected)} · missing in KC {len(missing)} · KC-only (stale) {len(stale)}")
    for eid in missing[:20]:
        print(f"  MISSING: {eid}")
    for eid in stale[:20]:
        print(f"  STALE  : {eid}")

    ok = (len(entries) == len(expected) and not missing and not stale
          and not bad_resource and not fixture_missing)
    print(f"\n{'PASS' if ok else 'FAIL'} — bundle entries {len(entries)}/{len(expected)}, "
          f"missing {len(missing)}, stale {len(stale)}, "
          f"bad resource {len(bad_resource)}, fixtures missing {len(fixture_missing)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
