#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
okf_lint — OKF v0.2 conformance checker for a knowledge bundle.

Checks, per SPEC.md:
  §3.1  Reserved filenames: index.md (listing), log.md (history)
  §4.1  Every concept document has YAML frontmatter with a required `type`
  §5.2  generated.by / verified[].by follow the actor convention (§7)
  §5.4  status is one of draft | stable | deprecated
  §5.5  stale_after is an absolute YYYY-MM-DD date
  §5.1  every sources[] entry has `resource`; footnote refs resolve to a sources id
  §6.1  bundle-relative (/...) and relative links resolve to a file in the bundle
  §8    index.md carries no frontmatter, except the bundle root which may declare okf_version
  §12   bundle root index.md declares okf_version

Exit 0 when there are no errors. Warnings do not affect exit code.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

# os.walk() yields paths prefixed with whatever root it was handed, while link targets are
# resolved through normpath(). Given a relative root such as ".", the two disagree
# ("./tables/x.md" vs "tables/x.md") and every bundle-relative link is misreported as
# pointing outside the bundle. Normalising to an absolute path keeps both sides comparable.
BUNDLE = os.path.abspath(
    sys.argv[1] if len(sys.argv) > 1
    # finance_ontology vendored copy (2026-09-27, PG-03): from ~/my_second_brain/references/okf_lint.py
    # (sha256 prefix d8f7bc8b5b0d2f19). Only this default changed: the repo's own finance/okf/ bundle.
    else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finance", "okf")
)
RESERVED = {"index.md", "log.md"}
VALID_STATUS = {"draft", "stable", "deprecated"}
ACTOR_RE = re.compile(r"^(human:.+|process:.+|[^/\s]+/[^/\s]+)$")
# OKF SPEC §5.2: every timestamp-valued key is an ISO 8601 datetime with an
# explicit UTC offset (2026-06-30T14:00:00Z). A bare date is no longer valid.
DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

errors: list[str] = []
warns: list[str] = []


def err(p, m):
    errors.append(f"{p}: {m}")


def warn(p, m):
    warns.append(f"{p}: {m}")


def check_at(p, key, v):
    """SPEC §5.2 — a timestamp key must be an ISO 8601 datetime with an offset.

    PyYAML resolves an unquoted `2026-09-17T04:00:00Z` into a `datetime` and a
    bare `2026-09-17` into a `date`, so the raw string never reaches us in
    those cases. A tz-aware datetime is accepted; a date, or a naive datetime,
    is the violation.
    """
    if isinstance(v, _dt.datetime):
        if v.tzinfo is None:
            err(p, f"{key}={v.isoformat()!r} has no UTC offset (SPEC §5.2)")
        return
    if isinstance(v, _dt.date):
        err(p, f"{key}={v.isoformat()!r} is a bare date, not a datetime (SPEC §5.2)")
        return
    if not DATE_RE.match(str(v)):
        err(p, f"{key}={v!r} is not an ISO 8601 datetime with an offset (SPEC §5.2)")


def split_frontmatter(text):
    """Return (frontmatter_dict_or_None, body)."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    raw = text[4:end]
    body = text[end + 4:]
    return yaml.safe_load(raw) or {}, body


def check_actor(rel, field, value):
    if not isinstance(value, str) or not ACTOR_RE.match(value):
        err(rel, f"{field}={value!r} does not follow the actor convention "
                 f"(<producer>/<version>, human:<id>, or process:<id>)")


def check_links(rel, body, md_files):
    for text, target in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", body):
        if target.startswith(("http://", "https://", "mailto:", "file://", "#")):
            continue
        target = target.split("#")[0]
        if not target:
            continue
        if target.startswith("/"):
            resolved = os.path.normpath(os.path.join(BUNDLE, target.lstrip("/")))
        else:
            resolved = os.path.normpath(os.path.join(BUNDLE, os.path.dirname(rel), target))
        if not os.path.exists(resolved):
            err(rel, f"broken link -> {target}")
        elif resolved not in md_files and resolved.endswith(".md"):
            err(rel, f"link target outside bundle -> {target}")


_FENCE = re.compile(r"^```.*?^```", re.M | re.S)
_INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(text: str) -> str:
    """Prose only: fenced blocks and inline spans removed.

    Markdown constructs do not apply inside code, and pretending otherwise
    produces false errors on exactly the documents that quote code. ADR 0028
    quotes two regexes containing a negated character class, which the
    footnote pattern read as a reference `[^)]` and demanded a sources[].id
    for. Blanking rather than deleting keeps line counts intact for any
    future check that reports positions.
    """
    text = _FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _INLINE_CODE.sub(" ", text)


def check_footnotes(rel, body, fm):
    source_ids = {s.get("id") for s in (fm.get("sources") or []) if isinstance(s, dict)}
    prose = strip_code(body)
    refs = set(re.findall(r"\[\^([^\]]+)\](?!:)", prose))
    defs = set(re.findall(r"^\[\^([^\]]+)\]:", prose, re.M))
    for r in refs:
        if r not in source_ids:
            err(rel, f"footnote [^{r}] has no matching sources[].id")
    for d in defs - refs:
        warn(rel, f"footnote definition [^{d}] is never referenced in the body")


def main():
    if not os.path.isdir(BUNDLE):
        sys.exit(f"not a directory: {BUNDLE}")

    md_files = set()
    dirs_seen = set()
    for root, _d, files in os.walk(BUNDLE):
        dirs_seen.add(root)
        for f in files:
            if f.endswith(".md"):
                md_files.add(os.path.join(root, f))

    concepts = 0

    # Every directory must offer progressive disclosure via index.md (§8).
    for d in sorted(dirs_seen):
        if not os.path.exists(os.path.join(d, "index.md")):
            err(os.path.relpath(d, BUNDLE) or ".", "directory has no index.md (SPEC §8)")

    # Bundle root must declare okf_version (§12).
    root_index = os.path.join(BUNDLE, "index.md")
    if os.path.exists(root_index):
        with open(root_index, encoding="utf-8") as fh:
            fm, _ = split_frontmatter(fh.read())
        if not fm or "okf_version" not in fm:
            err("index.md", "bundle root index.md does not declare okf_version (SPEC §12)")

    for path in sorted(md_files):
        rel = os.path.relpath(path, BUNDLE)
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        fm, body = split_frontmatter(text)

        if name == "index.md":
            if fm is not None and rel != "index.md":
                err(rel, "index.md must not carry frontmatter (SPEC §8)")
            if fm is not None and rel == "index.md" and set(fm) - {"okf_version"}:
                err(rel, "root index.md frontmatter may only contain okf_version (SPEC §8)")
            check_links(rel, body, md_files)
            continue

        if name == "log.md":
            check_links(rel, body, md_files)
            continue

        # Concept document.
        concepts += 1
        if fm is None:
            err(rel, "concept document has no YAML frontmatter (SPEC §4.1)")
            continue
        if "type" not in fm:
            err(rel, "missing required frontmatter key `type` (SPEC §4.1)")
        for k in ("title", "description"):
            if k not in fm:
                warn(rel, f"recommended frontmatter key `{k}` is absent")

        if "status" in fm and fm["status"] not in VALID_STATUS:
            err(rel, f"status={fm['status']!r} not in {sorted(VALID_STATUS)} (SPEC §5.4)")
        if "stale_after" in fm:
            check_at(rel, "stale_after", fm["stale_after"])

        uw = fm.get("usage_window")
        if isinstance(uw, dict):
            for k in ("from", "to"):
                if k in uw:
                    check_at(rel, f"usage_window.{k}", uw[k])

        gen = fm.get("generated")
        if isinstance(gen, dict):
            if "by" not in gen:
                err(rel, "generated is present but has no `by` (SPEC §5.2)")
            else:
                check_actor(rel, "generated.by", gen["by"])
            if "at" in gen:
                check_at(rel, "generated.at", gen["at"])

        ver = fm.get("verified")
        if ver is not None:
            entries = ver if isinstance(ver, list) else [ver]
            for v in entries:
                if not isinstance(v, dict) or "by" not in v:
                    err(rel, "verified entry must be a mapping with `by` (SPEC §5.2)")
                else:
                    check_actor(rel, "verified[].by", v["by"])
                    if "at" in v:
                        check_at(rel, "verified[].at", v["at"])

        for s in (fm.get("sources") or []):
            if not isinstance(s, dict) or "resource" not in s:
                err(rel, "sources[] entry missing required `resource` (SPEC §5.1)")
            elif "last_modified" in s:
                check_at(rel, "sources[].last_modified", s["last_modified"])

        check_links(rel, body, md_files)
        check_footnotes(rel, body, fm)

    print("=" * 72)
    print(f"OKF v0.2 conformance — {BUNDLE}")
    print("=" * 72)
    print(f"concept documents : {concepts}")
    print(f"directories       : {len(dirs_seen)}")
    print(f"errors            : {len(errors)}")
    print(f"warnings          : {len(warns)}")
    if errors:
        print("\nERRORS")
        for e in errors:
            print(f"  [ERR ] {e}")
    if warns:
        print("\nWARNINGS")
        for w in warns:
            print(f"  [WARN] {w}")
    print("=" * 72)
    print("RESULT:", "PASS" if not errors else "FAIL")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
