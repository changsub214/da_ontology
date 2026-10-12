#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 은행 계정계·정보계 원장 스키마 기반 정형 데이터 생성기 (`data/generate_dummy_data.py` v3.0 — Zero Answer-Leakage)

핵심 설계 원칙 (사용자 피드백 반영):
1. **정형 데이터(`data/structured/*.csv`)에는 오직 은행 계정계·정보계에 실제로 존재하는 '기초 거래 사실(Raw Operational Facts)'만 보관한다.**
   - 상품 테이블(`financial_products.csv`)에 `governing_pdf`, `governing_clause` 같은 법령 파일명/조항을 넣지 않는다.
   - 차주·계약 테이블에 `is_golden_anchor`, `scenario_tag`, `min_prov_rate_pct`(법정 최소적립률), `required_provision_krw`(법정 요적립액) 같은 **정답 유출(Answer Leakage) 컬럼을 일절 두지 않는다.**
   - 사전 집계된 정답 팩트 테이블(`fact_loan_portfolio.csv`)이나 부서별 연체율 Y/N 플래그(`ews_triggered`, `official_1m_delinq`, `npl_90d_flag`)를 원장에 미리 구워두지 않는다.
2. **법정 기준·단서·예외(`0.85% vs 0.90%`, `고정 20% vs 우선변제 10%`, `별표3 6개월 상환 면제`, `부서별 연체율 산식`)는 오직 비정형 PDF(`data/un_data/*.pdf`)와 온톨로지(`ontology/l1.yaml`)에만 존재한다.**
   - 따라서 Text-to-SQL 단독으로는 "법정 최소 충당금 부족액"이나 "부서별 3종 연체율", "특허권 단독 취득 금리인하 거절 근거"를 절대 알 수 없으며, 반드시 온톨로지 그래프를 경유해야만 답할 수 있다.
"""

from __future__ import annotations

import csv
import json
import os
import random

SEED = 20260921
random.seed(SEED)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "structured")
os.makedirs(OUT_DIR, exist_ok=True)


def write_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> str:
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_products() -> list[dict]:
    """실제 은행 여신상품 마스터 원장 — PDF 파일명이나 법령 조항 컬럼 없음."""
    return [
        {
            "product_code": "PROD_TCB_WORKING",
            "product_name": "별빛 TCB 기술혁신 운전자금",
            "loan_category": "CORPORATE_WORKING_CAPITAL",
            "target_segment": "SME_TECH_CERTIFIED",
            "base_rate_benchmark": "KORIBOR_3M",
            "repayment_method": "BULLET_AT_MATURITY",
            "max_maturity_months": 36,
        },
        {
            "product_code": "PROD_CORP_PRIME_WC",
            "product_name": "별빛 프라임 중견기업 운전자금",
            "loan_category": "CORPORATE_WORKING_CAPITAL",
            "target_segment": "MID_CAP_GENERAL",
            "base_rate_benchmark": "FINANCIAL_BOND_6M",
            "repayment_method": "BULLET_AT_MATURITY",
            "max_maturity_months": 24,
        },
        {
            "product_code": "PROD_RESTRUCTURED_DIP",
            "product_name": "별빛 기업구조조정·회생운전자금",
            "loan_category": "CORPORATE_WORKOUT_DIP",
            "target_segment": "WORKOUT_AND_REHAB_CORP",
            "base_rate_benchmark": "FINANCIAL_BOND_1Y",
            "repayment_method": "EQUAL_PRINCIPAL_INSTALLMENT",
            "max_maturity_months": 60,
        },
        {
            "product_code": "PROD_CONST_REALESTATE",
            "product_name": "별빛 프로젝트·시설기업자금",
            "loan_category": "CORPORATE_FACILITY_LOAN",
            "target_segment": "GENERAL_CORP",
            "base_rate_benchmark": "FINANCIAL_BOND_1Y",
            "repayment_method": "EQUAL_PRINCIPAL_INSTALLMENT",
            "max_maturity_months": 48,
        },
    ]


def generate_all() -> None:
    products = build_products()
    customers: list[dict] = []
    contracts: list[dict] = []
    workout_histories: list[dict] = []

    # =========================================================================
    # 1. 주요 거래처 16개 법인 (시나리오 태그나 골든앵커 플래그 없이 순수 원장 속성만 기록)
    #    ※ 단, 회계 전산 배치(booked_provision_krw)는 업종코드/우선변제 단서를 반영하지 못한
    #      일반 원칙(정상=0.85%, 고정=20.0%)으로 적립해 두어, 온톨로지가 과소·과대적립을 적발하게 함.
    # =========================================================================
    featured_specs = [
        {
            "cust_id": "CUST_0001", "name": "별빛정밀(주)", "corp_reg_no": "110111-2849103",
            "ksic_code": "C", "ksic_detail": "C292", "industry_name": "특수목적용 기계 제조업",
            "credit_rating": "BB+", "tcb_grade": "T3", "debt_ratio_pct": 185.4,
            "contract_id": "LN_2026_0001", "product_code": "PROD_RESTRUCTURED_DIP",
            "reg_dt": "2025-07-03", "contract_dt": "2025-07-10", "disburse_dt": "2025-07-12",
            "base_rate": 3.40, "spread_rate": 2.10, "pref_rate": 0.80, "applied_rate": 4.70,
            "contract_amt": 10000000000, "outstanding_amt": 10000000000,
            "overdue_days": 45, "asset_class": "PRECAUTIONARY",
            "rehab_priority_claim_yn": "Y",
            "booked_provision_krw": 700000000,  # 현재 회계장부상 요주의 7% 설정액
            "account_status": "ACTIVE_RESTRUCTURED",
            "workout": {
                "workout_start_dt": "2025-08-01",
                "consecutive_normal_repay_months": 7,
                "new_equity_paid_in_krw": 5000000000,
                "legal_proceeding_code": "CORP_RESTRUCT_ACT_WORKOUT",
            },
        },
        {
            "cust_id": "CUST_0002", "name": "태성금속공업(주)", "corp_reg_no": "130111-1920384",
            "ksic_code": "C", "ksic_detail": "C259", "industry_name": "기타 금속가공제품 제조업",
            "credit_rating": "CCC", "tcb_grade": "T5", "debt_ratio_pct": 310.0,
            "contract_id": "LN_2026_0002", "product_code": "PROD_RESTRUCTURED_DIP",
            "reg_dt": "2025-05-10", "contract_dt": "2025-05-15", "disburse_dt": "2025-05-16",
            "base_rate": 3.50, "spread_rate": 2.60, "pref_rate": 0.40, "applied_rate": 5.70,
            "contract_amt": 10000000000, "outstanding_amt": 10000000000,
            "overdue_days": 95, "asset_class": "SUBSTANDARD",
            "rehab_priority_claim_yn": "Y",
            # 장부에는 일반 고정 20%(20억)로 설정되어 있으나, 회생법 제180조제2항 우선변제자산(Y)이므로
            # 온톨로지가 제29조1항1호다목 단서를 적용하면 법정 최소적립액은 10%(10억)로 판정됨!
            "booked_provision_krw": 2000000000,
            "account_status": "ACTIVE_OVERDUE",
            "workout": {
                "workout_start_dt": "2025-11-15",
                "consecutive_normal_repay_months": 2,
                "new_equity_paid_in_krw": 0,
                "legal_proceeding_code": "REHAB_ACT_ART180_2_DIP",
            },
        },
        {
            "cust_id": "CUST_0003", "name": "극동철강산업(주)", "corp_reg_no": "180111-3049182",
            "ksic_code": "C", "ksic_detail": "C241", "industry_name": "1차 철강 제조업",
            "credit_rating": "CCC", "tcb_grade": "T6", "debt_ratio_pct": 380.0,
            "contract_id": "LN_2026_0003", "product_code": "PROD_CORP_PRIME_WC",
            "reg_dt": "2025-04-10", "contract_dt": "2025-04-12", "disburse_dt": "2025-04-15",
            "base_rate": 3.50, "spread_rate": 2.90, "pref_rate": 0.00, "applied_rate": 6.40,
            "contract_amt": 10000000000, "outstanding_amt": 10000000000,
            "overdue_days": 95, "asset_class": "SUBSTANDARD",
            "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 2000000000,
            "account_status": "ACTIVE_OVERDUE",
            "workout": {
                "workout_start_dt": "2025-12-01",
                "consecutive_normal_repay_months": 0,
                "new_equity_paid_in_krw": 0,
                "legal_proceeding_code": "NONE",
            },
        },
        # KSIC L / F / G / H 정상여신 4건 — 전산 장부(booked_provision_krw)에는 일반 정상(0.85%)으로만 적립되어 있어,
        # 온톨로지가 감독규정 제29조1항1호가목 단서(F·G·H·L = 0.90%)를 연결해야만 총 3,000만 원 과소적립을 적발함!
        {
            "cust_id": "CUST_0004", "name": "대양피에프개발(주)", "corp_reg_no": "110111-4491021",
            "ksic_code": "L", "ksic_detail": "L681", "industry_name": "부동산 및 임대업",
            "credit_rating": "BBB", "tcb_grade": "T4", "debt_ratio_pct": 210.0,
            "contract_id": "LN_2026_KSIC_L1", "product_code": "PROD_CONST_REALESTATE",
            "reg_dt": "2025-09-01", "contract_dt": "2025-09-05", "disburse_dt": "2025-09-08",
            "base_rate": 3.60, "spread_rate": 2.40, "pref_rate": 0.20, "applied_rate": 5.80,
            "contract_amt": 20000000000, "outstanding_amt": 20000000000,
            "overdue_days": 0, "asset_class": "NORMAL",
            "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 170000000,  # 200억 × 0.85% (전산 일반적립액; 법정 단서 0.90% 적용 시 1.8억 필요)
            "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0005", "name": "삼호종합건설(주)", "corp_reg_no": "110111-5120934",
            "ksic_code": "F", "ksic_detail": "F411", "industry_name": "건설업",
            "credit_rating": "BBB-", "tcb_grade": "T4", "debt_ratio_pct": 225.0,
            "contract_id": "LN_2026_KSIC_F1", "product_code": "PROD_CONST_REALESTATE",
            "reg_dt": "2025-09-10", "contract_dt": "2025-09-15", "disburse_dt": "2025-09-17",
            "base_rate": 3.60, "spread_rate": 2.50, "pref_rate": 0.30, "applied_rate": 5.80,
            "contract_amt": 15000000000, "outstanding_amt": 15000000000,
            "overdue_days": 0, "asset_class": "NORMAL",
            "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 127500000,  # 150억 × 0.85% (법정 단서 0.90% 적용 시 1.35억 필요)
            "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0006", "name": "한일유통상사(주)", "corp_reg_no": "110111-6039481",
            "ksic_code": "G", "ksic_detail": "G464", "industry_name": "도매 및 소매업",
            "credit_rating": "BBB+", "tcb_grade": "T3", "debt_ratio_pct": 165.0,
            "contract_id": "LN_2026_KSIC_G1", "product_code": "PROD_CONST_REALESTATE",
            "reg_dt": "2025-10-01", "contract_dt": "2025-10-05", "disburse_dt": "2025-10-06",
            "base_rate": 3.50, "spread_rate": 2.10, "pref_rate": 0.50, "applied_rate": 5.10,
            "contract_amt": 15000000000, "outstanding_amt": 15000000000,
            "overdue_days": 0, "asset_class": "NORMAL",
            "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 127500000,  # 150억 × 0.85% (법정 단서 0.90% 적용 시 1.35억 필요)
            "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0016", "name": "그랜드하모니호텔(주)", "corp_reg_no": "110111-7712093",
            "ksic_code": "H", "ksic_detail": "H551", "industry_name": "숙박 및 음식점업",
            "credit_rating": "BBB", "tcb_grade": "T4", "debt_ratio_pct": 198.0,
            "contract_id": "LN_2026_KSIC_H1", "product_code": "PROD_CONST_REALESTATE",
            "reg_dt": "2025-10-20", "contract_dt": "2025-10-24", "disburse_dt": "2025-10-27",
            "base_rate": 3.50, "spread_rate": 2.30, "pref_rate": 0.40, "applied_rate": 5.40,
            "contract_amt": 10000000000, "outstanding_amt": 10000000000,
            "overdue_days": 0, "asset_class": "NORMAL",
            "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 85000000,  # 100억 × 0.85% (법정 단서 0.90% 적용 시 0.90억 필요)
            "account_status": "ACTIVE_PERFORMING",
        },
        # 2026-02-13 계약체결일(contract_dt) 8건
        {
            "cust_id": "CUST_0007", "name": "네오바이오텍(주)", "corp_reg_no": "120111-8812031",
            "ksic_code": "C", "ksic_detail": "C271", "industry_name": "의료용 기기 제조업",
            "credit_rating": "BBB+", "tcb_grade": "T3", "debt_ratio_pct": 162.0,
            "contract_id": "LN_2026_0213_01", "product_code": "PROD_TCB_WORKING",
            "reg_dt": "2026-02-09", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-17",
            "base_rate": 3.40, "spread_rate": 2.40, "pref_rate": 1.20, "applied_rate": 4.60,
            "contract_amt": 1000000000, "outstanding_amt": 1000000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 8500000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0008", "name": "에이펙스세미콘(주)", "corp_reg_no": "134111-9012834",
            "ksic_code": "C", "ksic_detail": "C261", "industry_name": "반도체 제조업",
            "credit_rating": "BBB", "tcb_grade": "T3", "debt_ratio_pct": 210.5,
            "contract_id": "LN_2026_0213_02", "product_code": "PROD_TCB_WORKING",
            "reg_dt": "2026-02-10", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-16",
            "base_rate": 3.40, "spread_rate": 2.35, "pref_rate": 1.15, "applied_rate": 4.60,
            "contract_amt": 800000000, "outstanding_amt": 800000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 6800000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0009", "name": "다온로보틱스(주)", "corp_reg_no": "134111-9910234",
            "ksic_code": "C", "ksic_detail": "C292", "industry_name": "산업용 로봇 제조업",
            "credit_rating": "BBB", "tcb_grade": "T4", "debt_ratio_pct": 238.0,
            "contract_id": "LN_2026_0213_03", "product_code": "PROD_TCB_WORKING",
            "reg_dt": "2026-02-11", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-18",
            "base_rate": 3.40, "spread_rate": 2.50, "pref_rate": 1.10, "applied_rate": 4.80,
            "contract_amt": 900000000, "outstanding_amt": 900000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 7650000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0010", "name": "코어옵틱스(주)", "corp_reg_no": "134111-7410923",
            "ksic_code": "C", "ksic_detail": "C273", "industry_name": "광학기기 및 사진장비 제조업",
            "credit_rating": "BBB-", "tcb_grade": "T4", "debt_ratio_pct": 244.0,
            "contract_id": "LN_2026_0213_04", "product_code": "PROD_TCB_WORKING",
            "reg_dt": "2026-02-10", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-19",
            "base_rate": 3.40, "spread_rate": 2.45, "pref_rate": 1.15, "applied_rate": 4.70,
            "contract_amt": 1000000000, "outstanding_amt": 1000000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 8500000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0011", "name": "솔라에너지테크(주)", "corp_reg_no": "160111-3910294",
            "ksic_code": "C", "ksic_detail": "C281", "industry_name": "전동기 및 발전기 제조업",
            "credit_rating": "BBB", "tcb_grade": "T3", "debt_ratio_pct": 195.0,
            "contract_id": "LN_2026_0213_05", "product_code": "PROD_TCB_WORKING",
            "reg_dt": "2026-02-11", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-16",
            "base_rate": 3.40, "spread_rate": 2.50, "pref_rate": 1.20, "applied_rate": 4.70,
            "contract_amt": 800000000, "outstanding_amt": 800000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 6800000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0012", "name": "세진오토모티브(주)", "corp_reg_no": "180111-5519203",
            "ksic_code": "C", "ksic_detail": "C303", "industry_name": "자동차 신품 부품 제조업",
            "credit_rating": "A-", "tcb_grade": "T2", "debt_ratio_pct": 140.0,
            "contract_id": "LN_2026_0213_06", "product_code": "PROD_CORP_PRIME_WC",
            "reg_dt": "2026-02-06", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-16",
            "base_rate": 3.50, "spread_rate": 2.10, "pref_rate": 0.60, "applied_rate": 5.00,
            "contract_amt": 3000000000, "outstanding_amt": 3000000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 25500000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0013", "name": "한일화학소재(주)", "corp_reg_no": "170111-6620192",
            "ksic_code": "C", "ksic_detail": "C204", "industry_name": "기타 화학제품 제조업",
            "credit_rating": "BBB+", "tcb_grade": "T3", "debt_ratio_pct": 158.0,
            "contract_id": "LN_2026_0213_07", "product_code": "PROD_CORP_PRIME_WC",
            "reg_dt": "2026-02-08", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-17",
            "base_rate": 3.50, "spread_rate": 2.20, "pref_rate": 0.60, "applied_rate": 5.10,
            "contract_amt": 3500000000, "outstanding_amt": 3500000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 29750000, "account_status": "ACTIVE_PERFORMING",
        },
        {
            "cust_id": "CUST_0014", "name": "동양물류시스템(주)", "corp_reg_no": "120111-8102938",
            "ksic_code": "C", "ksic_detail": "C291", "industry_name": "물류 자동화설비 제조업",
            "credit_rating": "BBB+", "tcb_grade": "T3", "debt_ratio_pct": 172.0,
            "contract_id": "LN_2026_0213_08", "product_code": "PROD_CORP_PRIME_WC",
            "reg_dt": "2026-02-09", "contract_dt": "2026-02-13", "disburse_dt": "2026-02-18",
            "base_rate": 3.50, "spread_rate": 2.15, "pref_rate": 0.60, "applied_rate": 5.05,
            "contract_amt": 2500000000, "outstanding_amt": 2500000000,
            "overdue_days": 0, "asset_class": "NORMAL", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 21250000, "account_status": "ACTIVE_PERFORMING",
        },
        # 대손상각 특수채권 (85억)
        {
            "cust_id": "CUST_0015", "name": "성진해운물류(주)", "corp_reg_no": "180111-9012931",
            "ksic_code": "I", "ksic_detail": "I501", "industry_name": "운수업",
            "credit_rating": "D", "tcb_grade": "T6", "debt_ratio_pct": 620.0,
            "contract_id": "LN_2025_WRITEOFF_01", "product_code": "PROD_CORP_PRIME_WC",
            "reg_dt": "2024-05-10", "contract_dt": "2024-05-15", "disburse_dt": "2024-05-16",
            "base_rate": 3.70, "spread_rate": 3.80, "pref_rate": 0.00, "applied_rate": 7.50,
            "contract_amt": 8500000000, "outstanding_amt": 8500000000,
            "overdue_days": 210, "asset_class": "ESTIMATED_LOSS", "rehab_priority_claim_yn": "N",
            "booked_provision_krw": 8500000000, "account_status": "WRITTEN_OFF_SPECIAL_CLAIM",
        },
    ]

    for g in featured_specs:
        customers.append({
            "customer_id": g["cust_id"],
            "borrower_name": g["name"],
            "corp_reg_no": g["corp_reg_no"],
            "ksic_section_code": g["ksic_code"],
            "ksic_detail_code": g["ksic_detail"],
            "industry_name": g["industry_name"],
            "credit_rating": g["credit_rating"],
            "tcb_tech_grade": g["tcb_grade"],
            "debt_ratio_pct": g["debt_ratio_pct"],
        })
        contracts.append({
            "contract_id": g["contract_id"],
            "customer_id": g["cust_id"],
            "borrower_name": g["name"],
            "ksic_section_code": g["ksic_code"],
            "product_code": g["product_code"],
            "reg_dt": g["reg_dt"],
            "contract_dt": g["contract_dt"],
            "disburse_dt": g["disburse_dt"],
            "base_rate": g["base_rate"],
            "spread_rate": g["spread_rate"],
            "pref_rate": g["pref_rate"],
            "applied_rate": g["applied_rate"],
            "contract_amt": g["contract_amt"],
            "outstanding_amt": g["outstanding_amt"],
            "overdue_days": g["overdue_days"],
            "asset_classification": g["asset_class"],
            "rehab_priority_claim_yn": g["rehab_priority_claim_yn"],
            "booked_provision_krw": g["booked_provision_krw"],
            "account_status": g["account_status"],
        })
        if "workout" in g:
            w = g["workout"]
            workout_histories.append({
                "workout_id": f"WKO_{g['contract_id']}",
                "contract_id": g["contract_id"],
                "customer_id": g["cust_id"],
                "workout_start_dt": w["workout_start_dt"],
                "consecutive_normal_repay_months": w["consecutive_normal_repay_months"],
                "new_equity_paid_in_krw": w["new_equity_paid_in_krw"],
                "legal_proceeding_code": w["legal_proceeding_code"],
            })

    # =========================================================================
    # 2. 일반 기업여신 포트폴리오 84건 (CUST_0017~0100)
    # =========================================================================
    for idx in range(17, 101):
        cid = f"CUST_{idx:04d}"
        lid = f"LN_2026_{idx:04d}"
        bname = f"별빛제조파트너스_{idx:03d}(주)"
        day = random.randint(1, 28)
        month = random.choice(["2025-11", "2025-12", "2026-01"])
        reg_dt = f"{month}-{max(1, day - 3):02d}"
        con_dt = f"{month}-{day:02d}"
        dis_dt = f"{month}-{min(28, day + 2):02d}"

        base_r = 3.40
        spread_r = round(random.uniform(1.80, 2.60), 2)
        pref_r = round(random.uniform(0.30, 1.10), 2)
        app_r = round(base_r + spread_r - pref_r, 2)

        if idx in (21, 22, 23):
            amt = 5000000000
            overdue = 18
            aclass = "NORMAL"
            status = "ACTIVE_OVERDUE"
        else:
            amt = random.choice([12000000000, 15000000000, 18000000000])
            overdue = 0
            aclass = "NORMAL"
            status = "ACTIVE_PERFORMING"

        customers.append({
            "customer_id": cid,
            "borrower_name": bname,
            "corp_reg_no": f"110111-{1000000 + idx:07d}",
            "ksic_section_code": "C",
            "ksic_detail_code": "C259",
            "industry_name": "일반 제조업",
            "credit_rating": "BBB",
            "tcb_tech_grade": "T3",
            "debt_ratio_pct": round(random.uniform(110.0, 210.0), 1),
        })
        contracts.append({
            "contract_id": lid,
            "customer_id": cid,
            "borrower_name": bname,
            "ksic_section_code": "C",
            "product_code": "PROD_CORP_PRIME_WC",
            "reg_dt": reg_dt,
            "contract_dt": con_dt,
            "disburse_dt": dis_dt,
            "base_rate": base_r,
            "spread_rate": spread_r,
            "pref_rate": pref_r,
            "applied_rate": app_r,
            "contract_amt": amt,
            "outstanding_amt": amt,
            "overdue_days": overdue,
            "asset_classification": aclass,
            "rehab_priority_claim_yn": "N",
            "booked_provision_krw": int(amt * 0.0085),
            "account_status": status,
        })

    # =========================================================================
    # 3. 계정계 파생 원장 (연체원장 / 담보·보증원장 / 예외결재원장 / 금리인하요구 접수원장)
    #    ※ 부서별 연체율 플래그(ews_triggered 등)나 법령 조항 컬럼은 일절 두지 않는다!
    # =========================================================================
    con_by_id = {c["contract_id"]: c for c in contracts}

    # 3-1. 연체 원장 (`delinquency_events.csv`): 연체일수 > 0 계약의 원리금 연체 사실만 기록
    delinquency_events = []
    for c in sorted(contracts, key=lambda x: x["contract_id"]):
        od = c["overdue_days"]
        if od <= 0:
            continue
        written_off = c["account_status"] == "WRITTEN_OFF_SPECIAL_CLAIM"
        ratio = 1.0 if written_off else (0.5 if od >= 90 else (0.3 if od >= 30 else 0.1))
        delinquency_events.append({
            "event_id": f"DEL_{c['contract_id']}",
            "contract_id": c["contract_id"],
            "customer_id": c["customer_id"],
            "overdue_days": od,
            "overdue_principal_krw": int(c["outstanding_amt"] * ratio),
            "overdue_interest_krw": int(c["outstanding_amt"] * (c["applied_rate"] / 100.0) * (od / 365.0)),
            "write_off_yn": "Y" if written_off else "N",
        })

    # 3-2. 담보·보증서 원장 (`collaterals.csv`)
    collateral_specs = [
        ("LN_2026_0001", "CREDIT_GUARANTEE_CERT", "KODIT", 90.0),
        ("LN_2026_0002", "CREDIT_GUARANTEE_CERT", "KODIT", 70.0),
        ("LN_2026_KSIC_L1", "REAL_ESTATE_MORTGAGE", "FIRST_LIEN_TRUST", 60.0),
    ]
    collaterals = []
    for cid, ctype, org, ratio_pct in collateral_specs:
        con = con_by_id[cid]
        collaterals.append({
            "collateral_id": f"COL_{cid}",
            "contract_id": cid,
            "customer_id": con["customer_id"],
            "collateral_type_code": ctype,
            "guarantee_agency_code": org,
            "guarantee_ratio_pct": ratio_pct,
            "appraised_collateral_krw": int(con["outstanding_amt"] * (ratio_pct / 100.0)),
        })

    # 3-3. 기한이익상실(EOD) 유예 결재 원장 (`exception_approvals.csv`) — 조문 인용 없이 결재 코드만 기록
    exception_approvals = [
        {
            "approval_id": "APR_LN_2026_0001",
            "contract_id": "LN_2026_0001",
            "customer_id": "CUST_0001",
            "approval_type_code": "EOD_DEFERRAL_REVIEW",
            "approval_status": "APPROVED",
            "approver_role_code": "HQ_SENIOR_CREDIT_OFFICER",
            "approval_dt": "2026-02-25",
        },
        {
            "approval_id": "APR_LN_2026_0002",
            "contract_id": "LN_2026_0002",
            "customer_id": "CUST_0002",
            "approval_type_code": "EOD_DEFERRAL_REVIEW",
            "approval_status": "REJECTED",
            "approver_role_code": "HQ_SENIOR_CREDIT_OFFICER",
            "approval_dt": "2026-02-25",
        },
        {
            "approval_id": "APR_LN_2026_0003",
            "contract_id": "LN_2026_0003",
            "customer_id": "CUST_0003",
            "approval_type_code": "EOD_DEFERRAL_REVIEW",
            "approval_status": "REJECTED",
            "approver_role_code": "HQ_SENIOR_CREDIT_OFFICER",
            "approval_dt": "2026-02-25",
        },
    ]

    # 3-4. 금리인하요구권 접수·심사 원장 (`rate_cut_requests.csv`) — PDF 파일명·조항 컬럼 완전 제거
    rate_cut_requests = [
        {
            "request_id": "RCR_2026_01",
            "contract_id": "LN_2026_0213_02",
            "customer_id": "CUST_0008",
            "request_dt": "2026-03-10",
            "application_reason_code": "PATENT_ACQUISITION",
            "patent_reg_no": "10-2026-0041920",
            "credit_rating_before": "BBB",
            "credit_rating_after": "BBB",
            "yoy_revenue_growth_pct": 1.2,
            "review_status_code": "REJECTED",
            "approved_cut_bp": 0,
        },
        {
            "request_id": "RCR_2026_02",
            "contract_id": "LN_2026_0213_01",
            "customer_id": "CUST_0007",
            "request_dt": "2026-03-11",
            "application_reason_code": "PATENT_ACQUISITION",
            "patent_reg_no": "10-2026-0038811",
            "credit_rating_before": "BBB",
            "credit_rating_after": "BBB+",
            "yoy_revenue_growth_pct": 35.0,
            "review_status_code": "APPROVED",
            "approved_cut_bp": 35,
        },
    ]

    write_csv("financial_products.csv", list(products[0].keys()), products)
    write_csv("customers.csv", list(customers[0].keys()), customers)
    write_csv("loan_contracts.csv", list(contracts[0].keys()), contracts)
    write_csv("workout_histories.csv", list(workout_histories[0].keys()), workout_histories)
    write_csv("delinquency_events.csv", list(delinquency_events[0].keys()), delinquency_events)
    write_csv("collaterals.csv", list(collaterals[0].keys()), collaterals)
    write_csv("exception_approvals.csv", list(exception_approvals[0].keys()), exception_approvals)
    write_csv("rate_cut_requests.csv", list(rate_cut_requests[0].keys()), rate_cut_requests)

    # =========================================================================
    # 4. 벤치마크 채점용 Ground Truth (`summary_stats.json` — 에이전트에게는 비공개,
    #    원장 기초 사실 + PDF 규정을 온톨로지로 결합했을 때 나와야 하는 정답값)
    # =========================================================================
    on_balance = [c for c in contracts if c["account_status"] != "WRITTEN_OFF_SPECIAL_CLAIM"]
    special_claims = [c for c in contracts if c["account_status"] == "WRITTEN_OFF_SPECIAL_CLAIM"]

    total_on_bal_krw = sum(c["outstanding_amt"] for c in on_balance)
    special_krw = sum(c["outstanding_amt"] for c in special_claims)

    npl_90d_krw = sum(c["outstanding_amt"] for c in on_balance
                      if c["asset_classification"] in ("SUBSTANDARD", "DOUBTFUL", "ESTIMATED_LOSS"))
    npl_90d_ratio = round((npl_90d_krw / total_on_bal_krw) * 100, 2)

    delinq_1m_krw = sum(c["outstanding_amt"] for c in on_balance if c["overdue_days"] >= 30)
    delinq_1m_ratio = round((delinq_1m_krw / total_on_bal_krw) * 100, 2)

    ews_10d_krw = sum(c["outstanding_amt"] for c in on_balance if c["overdue_days"] >= 10)
    ews_ratio = round(((ews_10d_krw + special_krw) / (total_on_bal_krw + special_krw)) * 100, 2)

    ksic_fghl_normal = [c for c in on_balance
                        if c["ksic_section_code"] in ("F", "G", "H", "L")
                        and c["asset_classification"] == "NORMAL"]
    ksic_fghl_exposure = sum(c["outstanding_amt"] for c in ksic_fghl_normal)
    ksic_fghl_booked_085 = sum(c["booked_provision_krw"] for c in ksic_fghl_normal)
    ksic_fghl_statutory_090 = int(ksic_fghl_exposure * 0.0090)

    feb13 = [c for c in contracts if c["contract_dt"] == "2026-02-13"]
    feb13_avg_rate = round(sum(c["applied_rate"] for c in feb13) / len(feb13), 2)

    summary = {
        "generated_at": "2026-09-22",
        "design_mode": "ZERO_ANSWER_LEAKAGE_CORE_BANKING_SCHEMA",
        "csv_table_count": 8,
        "scenario_ground_truth_when_combined_with_ontology": {
            "scen1_contextual_delinquency": {
                "risk_npl_90d_ratio_pct": npl_90d_ratio,
                "fisis_official_1m_ratio_pct": delinq_1m_ratio,
                "credit_ews_substantial_ratio_pct": ews_ratio,
            },
            "scen2_feb13_date_and_rate": {
                "contract_dt_2026_02_13_count": len(feb13),
                "avg_applied_rate_pct": feb13_avg_rate,
                "top_by_count": "별빛 TCB 기술혁신 운전자금 (5건 / 45억원)",
                "top_by_amount": "별빛 프라임 중견기업 운전자금 (3건 / 90억원)",
            },
            "scen3_statutory_exceptions_art29_and_annex3": {
                "byulbit_precision_annex3": "별빛정밀(주): workout_histories 상 7개월 연속상환 + 유상증자 50억 확인 → [별표3] 제3호 라목에 따라 고정이하 분류 제외(요주의 7% = 7억 적법)",
                "taesung_metal_art29_1_c": "태성금속공업(주): 장부상 충당금은 20억(20%)으로 설정되어 있으나, rehab_priority_claim_yn='Y'(회생법 제180조제2항 공익채권) → 제29조1항1호다목 단서에 따라 법정 최소적립액은 10억(10%, 10억 감경 가능)",
                "kukdong_steel_baseline": "극동철강산업(주): rehab_priority_claim_yn='N' → 제29조1항1호다목 본문 원칙대로 20억(20%) 적립 의무",
            },
            "scen4_ksic_industry_provision_caveat": {
                "exposure_krw": ksic_fghl_exposure,
                "booked_in_ledger_085_krw": ksic_fghl_booked_085,
                "statutory_required_090_krw": ksic_fghl_statutory_090,
                "provision_shortfall_detected_by_ontology_krw": ksic_fghl_statutory_090 - ksic_fghl_booked_085,
            },
            "scen5_rate_cut_patent_discretion": {
                "rejected_case": "RCR_2026_01 에이펙스세미콘(주) (특허 취득 단독, 신용등급 BBB→BBB 변동 없음, 매출증가율 1.2% → 당행 내규 제25조제2항에 따라 거절 적법)",
                "approved_case": "RCR_2026_02 네오바이오텍(주) (특허 취득 + 신용등급 BBB→BBB+ 상승 + 매출 35% 증가 → 35bp 인하 승인)",
            },
        },
        "row_counts": {
            "financial_products.csv": len(products),
            "customers.csv": len(customers),
            "loan_contracts.csv": len(contracts),
            "workout_histories.csv": len(workout_histories),
            "delinquency_events.csv": len(delinquency_events),
            "collaterals.csv": len(collaterals),
            "exception_approvals.csv": len(exception_approvals),
            "rate_cut_requests.csv": len(rate_cut_requests),
        },
    }
    with open(os.path.join(OUT_DIR, "summary_stats.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    generate_all()
