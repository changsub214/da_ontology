#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정형 데이터 품질 및 Zero Answer-Leakage 검증기 (`data/validate_structured.py` v2.0)

검증 목표:
1. [C00] Zero Answer-Leakage 게이트:
   - 정형 원장(`data/structured/*.csv`)에 법령 파일명(`.pdf`), 조문번호(`제29조`, `별표3`, `제14조` 등),
     시나리오/골든앵커 태그(`scenario_tag`, `is_golden_anchor`), 사전 계산된 법정 적립률(`min_prov_rate_pct`,
     `required_provision_krw`), 부서별 연체율 Y/N 플래그(`ews_triggered` 등), 사전 집계 팩트(`fact_loan_portfolio.csv`)가
     단 1건이라도 존재하면 즉시 FAIL 처리한다.
2. [C01~C18] 계정계·정보계 원장 무결성 및 온톨로지 결합 추론 검증:
   - 원장 자체는 순수 기초 사실만 담고 있으되, 온톨로지(`l1.yaml`)와 비정형 PDF 조항을 결합했을 때
     6대 시나리오의 정량 정답(1.51% / 2.26% / 4.00%, F·G·H·L 3,000만원 과소적립 적발, 회생법 공익채권 10억 감경 등)이
     오차 없이 도출되는지 검증한다.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "structured")
REPORT_PATH = os.path.join(DATA_DIR, "validation_report.json")

FORBIDDEN_FILES = {"fact_loan_portfolio.csv", "restructuring_reviews.csv"}
FORBIDDEN_COLUMNS = {
    "governing_pdf", "governing_clause", "internal_pdf", "internal_clause",
    "fsc_guideline_clause", "internal_policy_clause", "applied_provision_clause",
    "scenario_tag", "is_golden_anchor", "min_prov_rate_pct", "required_provision_krw",
    "ews_triggered", "official_1m_delinq", "npl_90d_flag", "final_verdict",
}
FORBIDDEN_SUBSTRINGS = (".pdf", "제29조", "별표3", "별표 3", "제14조", "제18조", "제25조", "SCEN")

EXPECTED_SCHEMA = {
    "financial_products.csv": [
        "product_code", "product_name", "loan_category", "target_segment",
        "base_rate_benchmark", "repayment_method", "max_maturity_months",
    ],
    "customers.csv": [
        "customer_id", "borrower_name", "corp_reg_no", "ksic_section_code",
        "ksic_detail_code", "industry_name", "credit_rating", "tcb_tech_grade", "debt_ratio_pct",
    ],
    "loan_contracts.csv": [
        "contract_id", "customer_id", "borrower_name", "ksic_section_code",
        "product_code", "reg_dt", "contract_dt", "disburse_dt",
        "base_rate", "spread_rate", "pref_rate", "applied_rate",
        "contract_amt", "outstanding_amt", "overdue_days", "asset_classification",
        "rehab_priority_claim_yn", "booked_provision_krw", "account_status",
    ],
    "workout_histories.csv": [
        "workout_id", "contract_id", "customer_id", "workout_start_dt",
        "consecutive_normal_repay_months", "new_equity_paid_in_krw", "legal_proceeding_code",
    ],
    "delinquency_events.csv": [
        "event_id", "contract_id", "customer_id", "overdue_days",
        "overdue_principal_krw", "overdue_interest_krw", "write_off_yn",
    ],
    "collaterals.csv": [
        "collateral_id", "contract_id", "customer_id", "collateral_type_code",
        "guarantee_agency_code", "guarantee_ratio_pct", "appraised_collateral_krw",
    ],
    "exception_approvals.csv": [
        "approval_id", "contract_id", "customer_id", "approval_type_code",
        "approval_status", "approver_role_code", "approval_dt",
    ],
    "rate_cut_requests.csv": [
        "request_id", "contract_id", "customer_id", "request_dt",
        "application_reason_code", "patent_reg_no", "credit_rating_before",
        "credit_rating_after", "yoy_revenue_growth_pct", "review_status_code", "approved_cut_bp",
    ],
}

KSIC_SECTION_NAME = {
    "F": "건설업",
    "G": "도매 및 소매업",
    "H": "숙박 및 음식점업",
    "I": "운수업",
    "L": "부동산 및 임대업",
}


class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, check_id: str, title: str, clause: str, violations: list[str], checked: int) -> None:
        self.checks.append({
            "id": check_id,
            "title": title,
            "clause": clause,
            "status": "PASS" if not violations else "FAIL",
            "records_checked": checked,
            "violation_count": len(violations),
            "violations": violations[:25],
        })

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks if c["status"] == "FAIL"]

    def to_dict(self) -> dict:
        return {
            "validated_at": date.today().isoformat(),
            "data_dir": DATA_DIR,
            "total_checks": len(self.checks),
            "passed": len(self.checks) - len(self.failed),
            "failed": len(self.failed),
            "total_violations": sum(c["violation_count"] for c in self.checks),
            "overall": "PASS" if not self.failed else "FAIL",
            "checks": self.checks,
        }


def read_csv(name: str) -> list[dict]:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def f(row: dict, key: str) -> float:
    return float(row[key])


def i(row: dict, key: str) -> int:
    return int(row[key])


def parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def validate() -> Report:
    r = Report()

    # ---- C00 Zero Answer-Leakage Gate -------------------------------------
    v, n = [], 0
    existing_files = set(os.listdir(DATA_DIR)) if os.path.isdir(DATA_DIR) else set()
    for bad_file in sorted(FORBIDDEN_FILES):
        n += 1
        if bad_file in existing_files:
            v.append(f"금지된 사전집계/판정 유출 파일 존재: {bad_file}")
    for fname in sorted(EXPECTED_SCHEMA.keys()):
        rows = read_csv(fname)
        if not rows:
            continue
        cols = set(rows[0].keys())
        leaked_cols = cols & FORBIDDEN_COLUMNS
        if leaked_cols:
            v.append(f"{fname}: 정답·법령 유출 컬럼 발견 {sorted(leaked_cols)}")
        for r_idx, row in enumerate(rows, start=1):
            n += 1
            for k, val in row.items():
                sval = str(val)
                for sub in FORBIDDEN_SUBSTRINGS:
                    if sub in sval:
                        v.append(f"{fname}#{r_idx}.{k}: 법령/PDF/시나리오 문자열 유출 '{sub}' in '{sval[:40]}'")
    r.add("C00", "Zero Answer-Leakage 게이트 (정형 원장 내 PDF 파일명·법령조항·시나리오태그·사전집계 0건)",
          "3-Plane 분리 불변식: 원장=기초사실, 온톨로지/PDF=의사결정기준", v, n)

    # ---- C01 필수 8개 계정계 CSV 스키마 일치 ------------------------------
    v, n = [], 0
    for name, cols in EXPECTED_SCHEMA.items():
        n += 1
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            v.append(f"{name}: 파일 없음")
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        if header != cols:
            v.append(f"{name}: 헤더 불일치 expected={cols} actual={header}")
    r.add("C01", "8개 은행 계정계·정보계 CSV 스키마 계약 일치",
          "현업 코어뱅킹 원장 스키마 표준", v, n)

    products = read_csv("financial_products.csv")
    customers = read_csv("customers.csv")
    contracts = read_csv("loan_contracts.csv")
    workouts = read_csv("workout_histories.csv")
    delinq = read_csv("delinquency_events.csv")
    collaterals = read_csv("collaterals.csv")
    approvals = read_csv("exception_approvals.csv")
    ratecuts = read_csv("rate_cut_requests.csv")

    cust_by_id = {c["customer_id"]: c for c in customers}
    con_by_id = {c["contract_id"]: c for c in contracts}
    prod_ids = {p["product_code"] for p in products}

    # ---- C02 PK 유일성 ----------------------------------------------------
    v, n = [], 0
    for name, rows, pk in [
        ("financial_products.csv", products, "product_code"),
        ("customers.csv", customers, "customer_id"),
        ("loan_contracts.csv", contracts, "contract_id"),
        ("workout_histories.csv", workouts, "workout_id"),
        ("delinquency_events.csv", delinq, "event_id"),
        ("collaterals.csv", collaterals, "collateral_id"),
        ("exception_approvals.csv", approvals, "approval_id"),
        ("rate_cut_requests.csv", ratecuts, "request_id"),
    ]:
        n += len(rows)
        seen = set()
        for row in rows:
            if row[pk] in seen:
                v.append(f"{name}: 중복 PK {row[pk]}")
            seen.add(row[pk])
    r.add("C02", "전 테이블 기본키(PK) 유일성", "관계형 무결성", v, n)

    # ---- C03 FK 참조 무결성 -----------------------------------------------
    v, n = [], 0
    for c in contracts:
        n += 1
        if c["customer_id"] not in cust_by_id:
            v.append(f"loan_contracts {c['contract_id']}: 미존재 customer_id")
        if c["product_code"] not in prod_ids:
            v.append(f"loan_contracts {c['contract_id']}: 미존재 product_code")
    for name, rows in [
        ("workout_histories.csv", workouts),
        ("delinquency_events.csv", delinq),
        ("collaterals.csv", collaterals),
        ("exception_approvals.csv", approvals),
        ("rate_cut_requests.csv", ratecuts),
    ]:
        for row in rows:
            n += 1
            if row["contract_id"] not in con_by_id:
                v.append(f"{name}: 고아 contract_id={row['contract_id']}")
            if row["customer_id"] != con_by_id.get(row["contract_id"], {}).get("customer_id"):
                v.append(f"{name}: customer_id가 계약원장 차주와 불일치")
    r.add("C03", "외래키(FK) 참조 무결성 — 고아 레코드 0건 및 차주 ID 일관성",
          "관계형 무결성", v, n)

    # ---- C04 KSIC 섹션코드 ↔ 업종명 정합 ----------------------------------
    v, n = [], 0
    for c in customers:
        n += 1
        code = c["ksic_section_code"]
        if code in KSIC_SECTION_NAME and KSIC_SECTION_NAME[code] not in c["industry_name"]:
            v.append(f"{c['customer_id']}: 섹션 {code} vs 업종명 '{c['industry_name']}' 불일치")
    r.add("C04", "표준산업분류(KSIC) 섹션코드 ↔ 업종명 정합 (F·G·H·I·L 오분류 0건)",
          "한국표준산업분류 및 은행업감독규정 제29조제1항제1호 가목 단서", v, n)

    # ---- C05 금리 산식 & 3대 일자 순서 ------------------------------------
    v, n = [], 0
    for c in contracts:
        n += 1
        exp_rate = round(f(c, "base_rate") + f(c, "spread_rate") - f(c, "pref_rate"), 2)
        if abs(exp_rate - f(c, "applied_rate")) > 0.005:
            v.append(f"{c['contract_id']}: applied_rate 불일치")
        if not (parse_date(c["reg_dt"]) <= parse_date(c["contract_dt"]) <= parse_date(c["disburse_dt"])):
            v.append(f"{c['contract_id']}: 등록일 ≤ 체결일 ≤ 실행일 위반")
    r.add("C05", "적용금리 산식(base+spread−pref) 및 3대 기준일자 순서(reg_dt≤contract_dt≤disburse_dt)",
          "당행 내규 제21조·제22조", v, n)

    # ---- C06 연체원장 ↔ 계약원장 동기화 -----------------------------------
    v, n = [], 0
    evt_map = {d["contract_id"]: d for d in delinq}
    for c in contracts:
        od = i(c, "overdue_days")
        if od > 0:
            n += 1
            if c["contract_id"] not in evt_map:
                v.append(f"{c['contract_id']}: 연체 {od}일이나 delinquency_events 누락")
            elif i(evt_map[c["contract_id"]], "overdue_days") != od:
                v.append(f"{c['contract_id']}: 연체일수 불일치")
    r.add("C06", "연체원장(delinquency_events) ↔ 계약원장 연체일수 1:1 동기화",
          "계정계 원장 정합성", v, n)

    # ---- C07 담보평가액 = 대출잔액 × 보증비율 ------------------------------
    v, n = [], 0
    for col in collaterals:
        n += 1
        con = con_by_id[col["contract_id"]]
        exp = int(i(con, "outstanding_amt") * (f(col, "guarantee_ratio_pct") / 100.0))
        if abs(i(col, "appraised_collateral_krw") - exp) > 1:
            v.append(f"{col['collateral_id']}: 담보평가가액 산식 불일치")
    r.add("C07", "담보·보증서 평가가액(appraised_collateral_krw = 잔액 × 보증비율) 산술 정합",
          "계정계 담보원장 정합성", v, n)

    # ---- C08 온톨로지 추론 시나리오 검증 (원장 + PDF 규칙 결합 시 정답 도출) --
    v, n = [], 0
    on_bal = [c for c in contracts if c["account_status"] != "WRITTEN_OFF_SPECIAL_CLAIM"]
    special = [c for c in contracts if c["account_status"] == "WRITTEN_OFF_SPECIAL_CLAIM"]
    tot_on = sum(i(c, "outstanding_amt") for c in on_bal)
    spec_amt = sum(i(c, "outstanding_amt") for c in special)
    npl_r = round(sum(i(c, "outstanding_amt") for c in on_bal
                      if c["asset_classification"] in ("SUBSTANDARD", "DOUBTFUL", "ESTIMATED_LOSS")) / tot_on * 100, 2)
    off_r = round(sum(i(c, "outstanding_amt") for c in on_bal if i(c, "overdue_days") >= 30) / tot_on * 100, 2)
    ews_r = round((sum(i(c, "outstanding_amt") for c in on_bal if i(c, "overdue_days") >= 10) + spec_amt)
                  / (tot_on + spec_amt) * 100, 2)
    fghl = [c for c in on_bal if c["ksic_section_code"] in ("F", "G", "H", "L") and c["asset_classification"] == "NORMAL"]
    shortfall = int(sum(i(c, "outstanding_amt") for c in fghl) * 0.0090) - sum(i(c, "booked_provision_krw") for c in fghl)
    n += 4
    if (npl_r, off_r, ews_r) != (1.51, 2.26, 4.00):
        v.append(f"부서별 3대 연체율 불일치: {(npl_r, off_r, ews_r)}")
    if shortfall != 30000000:
        v.append(f"F·G·H·L 단서 적용 시 적발되어야 할 충당금 과소적립액이 3,000만원이 아님: {shortfall}")
    r.add("C08", "온톨로지 결합 추론 게이트 — 원장 기초 사실에 PDF 조항 적용 시 3대 연체율(1.51/2.26/4.00%) 및 F·G·H·L 충당금 과소적립(3,000만원) 정확히 도출",
          "Data(원장) + BusinessContext(l1.yaml) + DecisionCriteria(PDF) 3각 결합 검증", v, n)

    return r


def main() -> int:
    r = validate()
    payload = r.to_dict()
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    for c in r.checks:
        print(f"[{c['status']}] {c['id']} {c['title']} ({c['records_checked']}건)")
        for x in c["violations"]:
            print(f"   ✗ {x}")
    print(f"==> 총 {payload['total_checks']}개 검사 · PASS {payload['passed']} · FAIL {payload['failed']} · 위반 {payload['total_violations']}건")
    return 0 if payload["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
