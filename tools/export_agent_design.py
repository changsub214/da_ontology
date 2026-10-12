#!/usr/bin/env python3
"""Export agents/design/*.yaml → docs/data/*.json so docs/viewer.html renders the design SSOT (no hand-typed values).

Usage:
  uv run --no-project --with pyyaml python tools/export_agent_design.py [--src DIR] [--dry-run]

Gates (fail loudly, write nothing on failure):
  - required top-level keys per design (meta.id)
  - `measured` (v0.3.2+) or legacy `measured_2026_09_27`: per-label sums == totals, 11 node / 15 edge labels
  - `diagrams` (ADR 0015): every figure has id · kind · title · caption; mermaid figures have mermaid text;
    every figure source exists (directories end in `/`); figure ids are unique across designs; every figure
    referenced by `diagrams.intro_tabs` exists. The full live / token gate is tools/export_intro_arch.py.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "finance" / "agents" / "design"
DST = ROOT / "docs" / "data"

# Required top-level keys per design (meta.id). The RAG design has its own schema (no graph surfaces/topology).
REQUIRED_KEYS = {
    "graphrag_agent": ("meta", "surfaces", "topology", "tools", "callbacks", "gates", "open_decisions"),
    "rag_agent": ("meta", "resources", "agent", "tools", "gates"),
}
FIGURE_KINDS = {"mermaid", "l1_schema", "trap_paths"}


def check_diagrams(name: str, spec: dict, seen: dict[str, str]) -> list[str]:
    errs = []
    dg = spec.get("diagrams")
    if not dg:
        return errs
    for fig in dg.get("figures") or []:
        fid = fig.get("id")
        where = f"{name} figure {fid}"
        if not fid:
            errs.append(f"{name}: figure without id")
            continue
        if fid in seen:
            errs.append(f"{where}: duplicate id (also in {seen[fid]})")
        seen[fid] = name
        for key in ("kind", "title", "caption"):
            if not str(fig.get(key) or "").strip():
                errs.append(f"{where}: missing `{key}`")
        if fig.get("kind") not in FIGURE_KINDS:
            errs.append(f"{where}: unknown kind `{fig.get('kind')}`")
        if fig.get("kind") == "mermaid" and not str(fig.get("mermaid") or "").strip():
            errs.append(f"{where}: kind mermaid without mermaid text")
        if fig.get("kind") == "trap_paths" and not fig.get("panels"):
            errs.append(f"{where}: trap_paths without panels")
        for s in fig.get("sources") or []:
            p = ROOT / s
            if not (p.is_dir() if s.endswith("/") else p.is_file()):
                p = ROOT / "finance" / s
            if not (p.is_dir() if s.endswith("/") else p.is_file()):
                errs.append(f"{where}: source `{s}` does not exist")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC), help="design YAML directory (negative controls)")
    ap.add_argument("--dry-run", action="store_true", help="validate only, write nothing")
    args = ap.parse_args()
    src = pathlib.Path(args.src)

    specs = []
    for f in sorted(src.glob("*.yaml")):
        spec = yaml.safe_load(f.read_text(encoding="utf-8"))
        # Minimal structural gate: fail loudly rather than render a broken design.
        design_id = (spec.get("meta") or {}).get("id")
        if design_id not in REQUIRED_KEYS:
            print(f"FAIL {f.name}: unknown meta.id `{design_id}` (expected one of {sorted(REQUIRED_KEYS)})")
            return 1
        for key in REQUIRED_KEYS[design_id]:
            if key not in spec:
                print(f"FAIL {f.name}: missing top-level key `{key}`")
                return 1
        m = spec.get("measured") or spec.get("measured_2026_09_27") or {}
        if m:
            if sum(m["nodes"].values()) != m["totals"]["nodes"] or sum(m["edges"].values()) != m["totals"]["edges"]:
                print(f"FAIL {f.name}: measured totals do not equal the sum of per-label counts")
                return 1
            if len(m["nodes"]) != 11 or len(m["edges"]) != 15:
                print(f"FAIL {f.name}: expected 11 node labels / 15 edge labels, got {len(m['nodes'])}/{len(m['edges'])}")
                return 1
        specs.append((f, spec))

    seen: dict[str, str] = {}
    errs: list[str] = []
    for f, spec in specs:
        errs += check_diagrams(f.name, spec, seen)
    for f, spec in specs:
        for tab in (spec.get("diagrams") or {}).get("intro_tabs") or []:
            refs = list(tab.get("figures") or []) + [o.get("figure") for o in (tab.get("toggle") or {}).get("options") or []]
            errs += [f"{f.name} tab {tab.get('id')}: figure {r} not defined" for r in refs if r not in seen]
    if errs:
        for e in errs:
            print(f"FAIL {e}")
        return 1

    n = 0
    for f, spec in specs:
        spec["_source"] = str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else f.name
        out = DST / (f.stem + ".json")
        if args.dry_run:
            print(f"OK {f.name} (dry-run, figures {len((spec.get('diagrams') or {}).get('figures') or [])})")
        else:
            DST.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(spec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            print(f"OK {f.relative_to(ROOT)} -> {out.relative_to(ROOT)}")
        n += 1
    print(f"exported {n} design file(s)" + (" (dry-run)" if args.dry_run else "") + f" · figures {len(seen)}")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
