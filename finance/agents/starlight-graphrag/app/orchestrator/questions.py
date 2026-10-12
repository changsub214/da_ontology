"""Module 05 question list — dependency-light (stdlib + PyYAML only).

Split out of `engine.py` so the web tier (`tools/studio_server.py` `/api/agent/questions`, and a
future Cloud Run image) can render the 21-question sidebar without importing ADK, genai, BigQuery
or the tool stack. `engine.py` re-exports these names, so existing callers keep working.

Do not import anything from `app.*` here: the web shim loads this file by path to bypass
`app/__init__.py` (which imports the ADK agent).
"""

from __future__ import annotations

import os
from typing import Any

import yaml

# Packaged copy of `ontology/cq/competency_questions.yaml` (SSOT). Shipped with the agent so the
# Agent Runtime container resolves the same 21 CQs as the workstation; equality with the SSOT is
# asserted by `tests/unit/test_orchestrator.py::test_packaged_cq_yaml_matches_ssot`.
CQ_YAML_PATH = os.environ.get(
    "STARLIGHT_CQ_YAML",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "competency_questions.yaml"),
)

_CQ_CACHE: list[dict[str, Any]] | None = None


def _load_cqs() -> list[dict[str, Any]]:
    global _CQ_CACHE
    if _CQ_CACHE is None:
        with open(CQ_YAML_PATH, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        _CQ_CACHE = doc.get("cqs", [])
    return _CQ_CACHE


QUESTION_TITLES: dict[str, str] = {
    "CQ01": "정상 여신 대손준비금 추가 적립 산정",
    "CQ02": "고정 여신 법정 최소 충당금 및 과부족",
    "CQ03": "기촉법 워크아웃 우선변제자산 충당금 특례",
    "CQ04": "당행 대손충당금 적립률(Coverage Ratio) 비교",
    "CQ05": "리스크관리위원회 기업여신 고정이하 비율",
    "CQ06": "금감원 공시 원화대출 연체율 산정 기준",
    "CQ07": "여신관리팀 조기경보 실질 연체율 비교",
    "CQ08": "채권재조정 여신 요주의 유지 근거 및 감사 요건",
    "CQ09": "30일 초과 연체 기업여신 EOD 처리·유예 판정",
    "CQ10": "보증서 담보 여신 EOD 유예 요건 충족 계좌",
    "CQ11": "상각 특수채권 적법성 및 연체율 모수 포함 여부",
    "CQ12": "특허 취득 사유 금리인하요구 거절 적법성",
    "CQ13": "TCB 운전자금 전결 한도 및 부채비율 위반 점검",
    "CQ14": "2월 13일 체결 기준 대출 평균 금리 및 주력 상품",
    "CQ15": "비교공시용 대출금리 구성(A+B-C) 및 가산금리 규제",
    "CQ16": "정상 여신 충당금 적립률(0.5%·0.85%·1.0%) 구분",
    "CQ17": "회수의문 여신 업권별 충당금 적립률(50% vs 55%)",
    "CQ18": "거액익스포져 한도 규제 적용 및 미구비 스키마 점검",
    "CQ19": "신규 대출 실적 집계 기준일(신청·체결·실행일) 차이",
    "CQ20": "채권재조정 여신 1회 미상환 시 건전성·충당금 영향",
    "Q21_D5": "폐기된 구버전 감독규정 스냅샷 호출 차단 검증",
}


def get_agent_questions() -> list[dict[str, Any]]:
    """Returns the 21 questions for Module 05 left sidebar, numbered strictly 01. through 21."""
    cqs = _load_cqs()
    dept_names = {
        "RISK_MGMT": "리스크관리부",
        "DISCLOSURE": "재무기획부(공시)",
        "CREDIT_MGMT": "여신관리팀",
        "CREDIT_REVIEW": "기업여신심사부",
        "BRANCH": "영업점(RM)",
        "COMPLIANCE": "준법감시부",
    }
    items: list[dict[str, Any]] = []
    for idx, cq in enumerate(cqs, start=1):
        num_str = f"{idx:02d}"
        cq_id = cq["id"]
        ctx_id = cq.get("business_context", {}).get("id", "RISK_MGMT")
        items.append({
            "num": num_str,
            "internal_key": cq_id,
            "title": QUESTION_TITLES.get(cq_id, cq["question"][:24]),
            "dept_id": ctx_id,
            "dept_name": dept_names.get(ctx_id, ctx_id),
            "question": cq["question"].strip(),
            "graph_path": cq.get("graph_path", "").strip(),
        })
    # Item 21: Governance Block (deprecated KC entry without replacement)
    items.append({
        "num": "21",
        "internal_key": "Q21_D5",
        "title": QUESTION_TITLES["Q21_D5"],
        "dept_id": "RISK_MGMT",
        "dept_name": "리스크관리부",
        "question": "과거 폐기된 구버전 감독규정 스냅샷(versions/art_29_allowance_coverage_ratio_v0.2.0)을 기준으로 이번 분기 정상 여신 대손충당금 적립률을 산정해줘.",
        "graph_path": "(:BusinessContext{context_id:'RISK_MGMT'})-[:INVOKES_PROVISION{term_key:'provision-criteria'}]->(:Provision{kc_entry_id:'versions/art_29_allowance_coverage_ratio_v0.2.0', status:'deprecated'})",
    })
    return items
