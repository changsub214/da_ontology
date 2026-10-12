#!/usr/bin/env python3
"""Export second_brain/runbook/runbook.yaml (SSOT) → RUNBOOK.md + docs/data/runbook.json.

One fact in one place: the YAML is the only hand-edited source. This script renders the
human-readable runbook for the second brain and the JSON that docs/viewer.html §08 renders,
and refuses to write either if the runbook is inconsistent with the repository.

Gates (each can fail):
  RB-G1 files      : every stages[].files path exists in the repo
  RB-G2 structure  : every stage has id/title/goal/steps(run)/gates(id, expect, measured.result);
                     gates[].status ∈ {pass, finding} (default pass)
  RB-G3 order      : depends_on only references earlier stage ids; ids unique
  RB-G4 measured   : no gate left with a placeholder result ("… 참조", "TODO", empty)
  RB-G5 adr        : every referenced ADR number has a file in second_brain/decisions/

Usage:
  python3 tools/export_runbook.py            # validate + write
  python3 tools/export_runbook.py --check    # validate only
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "second_brain" / "runbook" / "runbook.yaml"
MD_OUT = ROOT / "second_brain" / "runbook" / "RUNBOOK.md"
JSON_OUT = ROOT / "docs" / "data" / "runbook.json"
DECISIONS = ROOT / "second_brain" / "decisions"
PLACEHOLDER = re.compile(r"(참조\)$|^\(|TODO|TBD)")
# pass    = re-measured and matches `expect`
# finding = re-measured and exposes a defect of the original instance (recorded, not hidden)
GATE_STATUS = {"pass", "finding"}


def adr_files() -> dict[str, str]:
    return {p.name[:4]: p.name for p in sorted(DECISIONS.glob("[0-9][0-9][0-9][0-9]-*.md"))}


def validate(spec: dict) -> list[str]:
    errs: list[str] = []
    adrs = adr_files()
    seen: list[str] = []
    for st in spec.get("stages", []):
        sid = st.get("id", "?")
        for key in ("id", "title", "goal", "steps", "gates"):
            if not st.get(key):
                errs.append(f"RB-G2 {sid}: missing `{key}`")
        for i, step in enumerate(st.get("steps") or []):
            if not step.get("run"):
                errs.append(f"RB-G2 {sid}.steps[{i}]: missing `run`")
        for g in st.get("gates") or []:
            for key in ("id", "expect"):
                if not g.get(key):
                    errs.append(f"RB-G2 {sid}.{g.get('id', '?')}: missing `{key}`")
            if g.get("status", "pass") not in GATE_STATUS:
                errs.append(f"RB-G2 {sid}.{g.get('id', '?')}: status must be one of {sorted(GATE_STATUS)}")
            res = str((g.get("measured") or {}).get("result", "")).strip()
            if not res or PLACEHOLDER.search(res):
                errs.append(f"RB-G4 {sid}.{g.get('id', '?')}: measured.result is a placeholder: {res!r}")
        for f in st.get("files") or []:
            if not ((ROOT / f).exists() or (ROOT / "finance" / f).exists()):
                errs.append(f"RB-G1 {sid}: file not found: {f}")
        for dep in st.get("depends_on") or []:
            if dep not in seen:
                errs.append(f"RB-G3 {sid}: depends_on {dep} is not an earlier stage")
        for a in st.get("adr") or []:
            if str(a) not in adrs:
                errs.append(f"RB-G5 {sid}: ADR {a} has no file in second_brain/decisions/")
        if sid in seen:
            errs.append(f"RB-G3 duplicate stage id {sid}")
        seen.append(sid)
    return errs


def md_link(path: str) -> str:
    return f"[`{path}`](../../{path})"


def render_md(spec: dict) -> str:
    m = spec["meta"]
    adrs = adr_files()
    out: list[str] = []
    w = out.append
    w("---")
    w("type: Runbook")
    w(f"title: \"{m['title']}\"")
    w(f"version: {m['version']}")
    w(f"updated_at: \"{m['updated_at']}\"")
    w("generated: { by: tools/export_runbook.py, from: second_brain/runbook/runbook.yaml }")
    w("---")
    w("")
    w(f"# {m['title']}")
    w("")
    w("> [!IMPORTANT]")
    w("> 이 파일은 [`runbook.yaml`](runbook.yaml) 에서 `python3 tools/export_runbook.py` 로 생성된다. 직접 고치지 말고 YAML 을 고친 뒤 다시 생성한다.")
    w("> 같은 내용이 `docs/viewer.html#sec-runbook` 에 인터랙티브로 렌더된다.")
    w("")
    w(f"- **대상**: {m['audience']}")
    w(f"- **범위**: {m['scope']}")
    w(f"- **범위 밖**: {m['out_of_scope']}")
    w(f"- **실측 시각**: {m['measured_at']}")
    w(f"- **읽는 법**: {m['how_to_read']}")
    w("")

    w("## 1. 단계 지도")
    w("")
    w("| Stage | 제목 | Plane | 선행 | 게이트 | ADR |")
    w("|---|---|---|---|---|---|")
    for st in spec["stages"]:
        gates = " · ".join(g["id"] for g in st["gates"])
        adr = " ".join(f"[{a}](../decisions/{adrs[str(a)]})" for a in st.get("adr") or [])
        w(f"| [{st['id']}](#{st['id'].lower()}) | {st['title']} | {st['plane']} | {', '.join(st.get('depends_on') or []) or '—'} | {gates} | {adr or '—'} |")
    w("")

    w("## 2. 파라미터")
    w("")
    w("| 키 | 원 인스턴스 값 | 바꾸는 방법 | 상수로 박힌 곳 |")
    w("|---|---|---|---|")
    for p in spec["parameters"]:
        hc = ", ".join(f"`{x}`" for x in p.get("hardcoded_in") or []) or "—"
        note = f" — {p['note']}" if p.get("note") else ""
        w(f"| `{p['key']}` | `{p['value']}`{note} | {p.get('override', '—')} | {hc} |")
    w("")

    pre = spec["prerequisites"]
    w("## 3. 사전 준비")
    w("")
    w("| 도구 | 확인 | 비고 |")
    w("|---|---|---|")
    for t in pre["tools"]:
        w(f"| {t['name']} | `{t['check']}` | {t.get('note', '')} |")
    w("")
    w("```bash")
    w("\n".join(pre["auth"]))
    w("```")
    w("")
    w(f"권한: {pre['permissions']}")
    w("")
    for n in pre["env_notes"]:
        w(f"- **{n['id']}** — {n['text']}")
    w("")

    w("## 4. 만들어지는 GCP 리소스")
    w("")
    w("| 종류 | 이름 | Stage |")
    w("|---|---|---|")
    for r in spec["gcp_resources"]:
        w(f"| {r['kind']} | {r['name']} | {r['stage']} |")
    w("")

    w("## 5. 단계별 절차")
    w("")
    for st in spec["stages"]:
        w(f"<a id=\"{st['id'].lower()}\"></a>")
        w("")
        w(f"### {st['id']} · {st['title']}")
        w("")
        w(f"**목표** — {st['goal']}")
        w("")
        meta_bits = [f"Plane `{st['plane']}`", f"선행 {', '.join(st.get('depends_on') or []) or '없음'}"]
        if st.get("adr"):
            meta_bits.append("ADR " + " ".join(f"[{a}](../decisions/{adrs[str(a)]})" for a in st["adr"]))
        w(" · ".join(meta_bits))
        w("")
        if st.get("files"):
            w("관련 파일: " + " · ".join(md_link(f) for f in st["files"]))
            w("")
        for i, step in enumerate(st["steps"], 1):
            w(f"{i}. **{step['name']}**")
            w("")
            w("   ```bash")
            for line in step["run"].rstrip("\n").split("\n"):
                w(f"   {line}")
            w("   ```")
            if step.get("note"):
                w(f"   > {step['note']}")
            w("")
        if st.get("endpoints"):
            w("엔드포인트:")
            for e in st["endpoints"]:
                w(f"- `{e}`")
            w("")
        if st.get("outputs"):
            w("**산출물**")
            for o in st["outputs"]:
                w(f"- {o}")
            w("")
        w("**게이트**")
        w("")
        w("| ID | 상태 | 검사 | 기대값 | 실측 |")
        w("|---|---|---|---|---|")
        for g in st["gates"]:
            ms = g.get("measured") or {}
            badge = "⚠️ finding" if g.get("status") == "finding" else "✅ pass"
            w(f"| {g['id']} | {badge} | {g.get('name', '')} | {g['expect']} | {ms.get('result', '')} *({ms.get('at', '')})* |")
        w("")
        for g in st["gates"]:
            w(f"<details><summary>{g['id']} 실행 명령</summary>")
            w("")
            w("```bash")
            w(g["run"].rstrip("\n"))
            w("```")
            w("</details>")
            w("")
        if st.get("pitfalls"):
            w("**함정**")
            for p in st["pitfalls"]:
                w(f"- {p}")
            w("")

    w("## 6. 이식성 갭 (고객 실습 전에 고칠 것)")
    w("")
    w("| ID | 심각도 | 위치 | 문제 | 해결 |")
    w("|---|---|---|---|---|")
    for g in spec["portability_gaps"]:
        w(f"| {g['id']} | {g['severity']} | {g['where']} | {g['issue']} | {g['fix']} |")
    w("")
    w("## 7. 기록과 실물의 드리프트")
    w("")
    w("| ID | 위치 | 내용 |")
    w("|---|---|---|")
    for d in spec["drifts"]:
        w(f"| {d['id']} | {d['where']} | {d['issue']} |")
    w("")
    w("## 8. 아직 재현할 수 없는 것")
    w("")
    for x in spec["not_yet_reproducible"]:
        w(f"- {x}")
    w("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only")
    args = ap.parse_args()
    spec = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    errs = validate(spec)
    n_st = len(spec.get("stages", []))
    n_g = sum(len(s.get("gates") or []) for s in spec.get("stages", []))
    n_f = sum(len(s.get("files") or []) for s in spec.get("stages", []))
    n_find = sum(1 for s in spec.get("stages", []) for g in s.get("gates") or [] if g.get("status") == "finding")
    for e in errs:
        print("FAIL", e)
    if errs:
        print(f"[export_runbook] RESULT: FAIL ({len(errs)} issue(s)) — nothing written")
        return 1
    print(f"[export_runbook] RB-G1..G5 PASS — stages {n_st} · gates {n_g} (finding {n_find}) · file refs {n_f} · "
          f"portability gaps {len(spec['portability_gaps'])} · drifts {len(spec['drifts'])}")
    if args.check:
        return 0
    MD_OUT.write_text(render_md(spec), encoding="utf-8")
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {**spec, "adr_files": adr_files(),
               "summary": {"stages": n_st, "gates": n_g, "findings": n_find, "file_refs": n_f}}
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[export_runbook] wrote {MD_OUT.relative_to(ROOT)} and {JSON_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
