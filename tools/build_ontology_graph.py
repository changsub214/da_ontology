#!/usr/bin/env python3
"""Build Starlight Bank L1 Knowledge Graph (`starlight_bank_ontology.finance_graph`),
create Dataplex Business Glossary (`starlight-finance-glossary`), and attach the
Class Anchor Custom Aspect (`ontology-class-anchors`) to the BigQuery Property Graph
Entry in Dataplex Knowledge Catalog.

Key Architectural Invariants (ADR 0005):
  1. 11 Node Classes (LDM 8 + CTX 1 + LEX 2) & 14 Edge Types.
  2. Single Source of Governance (KC Only):
     - `lex_provisions` and `v_node_provision` hold only immutable `provision_slot_id` and `kc_entry_id`.
     - Document lifecycle (`status: verified | deprecated`) and replacement chains (`superseded_by`)
       live exclusively in Dataplex Knowledge Catalog (`okf` Aspect).
  3. Zero Ground-Truth Leakage (`G04_no_leakage`) & Real-Time Views:
     - `v_edge_governed_by_criteria` and `v_edge_evaluated_under_provision` are pure SQL Views
       over live Spanner federated tables (`ont_loan_contracts`, `ont_rate_cut_requests`) and
       `workout_histories`, connecting jurisdictional scope without pre-baking answers.
  4. Dataplex Business Glossary (`starlight-finance-glossary`) & `term_key`:
     - 7 canonical financial terms registered in Dataplex Glossary and mapped 1:1 to
       `INVOKES_PROVISION.term_key` and `ont_entity_aliases`.
  5. Intuitive 1-line Korean descriptions (`OPTIONS(description=...)`) on all tables, views,
     columns, and KC Aspect definitions, generated from `ontology/l1.yaml` (SSOT).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from google.cloud import bigquery
import yaml

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OKF_DIR = os.path.join(ROOT, "finance", "okf")
VERIFICATION_JSON = os.path.join(OKF_DIR, "verification.json")
L1_YAML = os.path.join(ROOT, "finance", "ontology", "l1.yaml")
GRAPH_SQL_PATH = os.path.join(ROOT, "finance", "sql", "bigquery_finance_graph.sql")

PROJECT = "finance-ontology-changseop"
PROJECT_NUMBER = "567090080191"
LOCATION = "us-central1"
SRC_DS = "starlight_bank"
ONT_DS = "starlight_bank_ontology"
GRAPH_NAME = "finance_graph"
BUCKET = "finance_okf"

GLOSSARY_ID = "starlight-finance-glossary"
ANCHOR_ASPECT_ID = "ontology-class-anchors"


def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT, location=LOCATION)


def get_gcloud_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True, timeout=10
    ).strip()


def dataplex_request(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
    ignore_status: tuple[int, ...] = (),
) -> tuple[int, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        if e.code in ignore_status:
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw}
        raise RuntimeError(f"HTTP {e.code} on {method} {url}: {raw[:600]}") from e


def wait_lro(op_name: str, token: str, timeout_sec: int = 45) -> dict:
    url = f"https://dataplex.googleapis.com/v1/{op_name}"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        _, data = dataplex_request("GET", url, token)
        if data.get("done"):
            if "error" in data:
                raise RuntimeError(f"LRO Error on {op_name}: {data['error']}")
            return data.get("response", data)
        time.sleep(1.5)
    raise TimeoutError(f"Timed out waiting for LRO {op_name}")


def run_sql(client: bigquery.Client, sql: str, label: str = "") -> None:
    if label:
        print(f"[BQ] Executing {label}...", flush=True)
    job = client.query(sql)
    job.result()


def load_table_rows(
    client: bigquery.Client,
    table_id: str,
    schema: list[bigquery.SchemaField],
    rows: list[dict],
    table_desc: str,
) -> None:
    full_id = f"{PROJECT}.{ONT_DS}.{table_id}"
    tbl = bigquery.Table(full_id, schema=schema)
    tbl.description = table_desc
    client.delete_table(full_id, not_found_ok=True)
    tbl = client.create_table(tbl)
    job_cfg = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_json(rows, full_id, job_config=job_cfg)
    job.result()
    tbl = client.get_table(full_id)
    tbl.description = table_desc
    tbl.schema = schema
    client.update_table(tbl, ["description", "schema"])
    print(f"[BQ] Loaded {len(rows)} rows into {ONT_DS}.{table_id}", flush=True)


def build_lex_and_ctx_data(client: bigquery.Client, l1_cfg: dict) -> None:
    with open(VERIFICATION_JSON, "r", encoding="utf-8") as f:
        ver = json.load(f)

    # Remove deprecated static bridge tables (replaced by pure real-time SQL views)
    for old_tbl in ("edge_governed_by_criteria", "edge_evaluated_under_provision"):
        client.delete_table(f"{PROJECT}.{ONT_DS}.{old_tbl}", not_found_ok=True)
        print(f"[BQ] Dropped static table if existed: {ONT_DS}.{old_tbl}", flush=True)

    # 1. BusinessContext (6 rows)
    ctx_schema = [
        bigquery.SchemaField("context_id", "STRING", mode="REQUIRED", description="부서·업무목적 맥락 고유 식별자 (PK, 예: RISK_MGMT, DISCLOSURE, CREDIT_MGMT)"),
        bigquery.SchemaField("dept_name", "STRING", mode="NULLABLE", description="업무를 주관하는 은행 내 부서명 (예: 리스크관리부, 재무기획부, 여신관리팀)"),
        bigquery.SchemaField("purpose_summary", "STRING", mode="NULLABLE", description="해당 부서의 핵심 의사결정 및 보고 목적 한 줄 요약"),
        bigquery.SchemaField("primary_metric_scope", "STRING", mode="NULLABLE", description="해당 맥락에서 주로 산출·점검하는 핵심 지표 및 심사 범위"),
    ]
    ctx_rows = [
        {
            "context_id": "RISK_MGMT",
            "dept_name": "리스크관리부",
            "purpose_summary": "자산건전성 5단계 분류, 대손충당금·대손준비금 최소적립 점검 및 리스크관리위원회 고정이하여신비율 보고",
            "primary_metric_scope": "고정이하여신비율(NPL Ratio 1.51%), 대손충당금 적립률(Coverage Ratio 78.6%), 경기민감업종(F·G·H·L) 0.90% 단서 적립",
        },
        {
            "context_id": "DISCLOSURE",
            "dept_name": "재무기획부(대외공시)",
            "purpose_summary": "금융감독원 및 은행연합회 제출용 공식 원화대출 연체율 산출 및 대외공시",
            "primary_metric_scope": "공시용 원화대출 연체율(2.26% = 1개월/30일 이상 원리금 연체 기준, 대손상각 특수채권 제외)",
        },
        {
            "context_id": "CREDIT_MGMT",
            "dept_name": "여신관리팀",
            "purpose_summary": "부실징후 차주 조기경보(EWS) 실질관리 연체율 산출 및 기한이익상실(EOD) 통지·유예 사후관리",
            "primary_metric_scope": "EWS 실질연체율(4.00% = 10일 이상 연체 + 대손상각 특수채권 분자·분모 모두 포함), 30일 초과 연체 EOD 유예 요건 점검",
        },
        {
            "context_id": "CREDIT_REVIEW",
            "dept_name": "기업여신심사부",
            "purpose_summary": "채권재조정(워크아웃·회생) 여신의 건전성 재분류 특례 심사 및 보증서 담보 적격성 판정",
            "primary_metric_scope": "별표3 제3호 라목(6개월 연속상환·유상증자·판단근거 문서화) 및 내규 제18조(신보 85% 이상 보증서) 요건 심사",
        },
        {
            "context_id": "BRANCH",
            "dept_name": "영업점(RM)",
            "purpose_summary": "기업여신 신규 실행 실적 집계, 대출금리 산정 및 차주 금리인하요구권 응대·통보",
            "primary_metric_scope": "체결일(contract_dt) 기준 신규 대출 실적, 최종 적용금리(applied_rate), 단독 특허 취득 시 금리인하 제외 및 사유 통보",
        },
        {
            "context_id": "COMPLIANCE",
            "dept_name": "준법감시부",
            "purpose_summary": "내규 전결 한도(TCB 우대금리·부채비율) 준수 점검, A+B+C 분리공시 적정성 및 거액익스포져 신설 규제 영향도 감리",
            "primary_metric_scope": "TCB 우대금리 상한(1.20%p)·부채비율 상한(250%), 금리 A+B+C 분리공시 의무, 거액익스포져(기본자본 25%) 데이터 구비 여부",
        },
    ]
    load_table_rows(
        client,
        "ctx_business_contexts",
        ctx_schema,
        ctx_rows,
        "[Node: BusinessContext] 부서 및 업무목적 맥락 테이블 — 동일 금융 용어의 적용 규정·컬럼 분기 기준점 (6건)",
    )

    # 2. SourceDocument (10 rows)
    doc_authority_map = {
        "DOC_01_FSC_BANK_REG": ("01", "binding", "COMMERCIAL_BANK", "금융위원회"),
        "DOC_02_LAW_ANNEX3": ("02", "binding", "COMMERCIAL_BANK", "금융위원회·법제처"),
        "DOC_03_FSC_IMPACT": ("03", "advisory", "COMMERCIAL_BANK", "금융위원회"),
        "DOC_04_FSC_EXPOSURE_NOTICE": ("04", "advisory", "COMMERCIAL_BANK", "금융위원회"),
        "DOC_05_FSC_KFB_RATE": ("05", "advisory", "COMMERCIAL_BANK", "금융위원회·금융감독원·은행연합회"),
        "DOC_06_FSC_7TH_TF": ("06", "advisory", "COMMERCIAL_BANK", "금융위원회·금융감독원"),
        "DOC_07_NARS_RATE": ("07", "advisory", "COMMERCIAL_BANK", "국회입법조사처(NARS)"),
        "DOC_08_KIF_PROVISION": ("08", "advisory", "COMMERCIAL_BANK", "한국금융연구원(KIF)"),
        "DOC_09_DISTRACTOR_SAVINGS_BANK": ("09", "distractor", "SAVINGS_BANK", "금융위원회(상호저축은행)"),
        "DOC_10_SYNTHETIC_BYULBIT_POLICY": ("10", "internal", "COMMERCIAL_BANK", "별빛은행(내규)"),
    }
    doc_schema = [
        bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED", description="원본 법령·내규 문서 고유 식별자 (PK, DOC_01 ~ DOC_10)"),
        bigquery.SchemaField("doc_code", "STRING", mode="NULLABLE", description="문서 번호 코드 (01 ~ 10)"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE", description="법령·감독규정·브리프·내규 문서의 공식 명칭"),
        bigquery.SchemaField("authority_level", "STRING", mode="NULLABLE", description="법적 구속력 구분 (binding 법규 / internal 당행내규 / advisory 가이드·자문 / distractor 타업권교란)"),
        bigquery.SchemaField("applicable_sector", "STRING", mode="NULLABLE", description="규정 적용 대상 금융업권 (COMMERCIAL_BANK 시중은행 vs SAVINGS_BANK 상호저축은행)"),
        bigquery.SchemaField("issuing_body", "STRING", mode="NULLABLE", description="문서 제정·발행 기관명 (금융위원회, 은행연합회, 별빛은행 등)"),
        bigquery.SchemaField("kc_entry_id", "STRING", mode="NULLABLE", description="Dataplex Knowledge Catalog에 등록된 문서 루트 Entry ID"),
        bigquery.SchemaField("gcs_uri", "STRING", mode="NULLABLE", description="GCS에 저장된 OKF 문서 루트 마크다운 파일 경로 (ObjectRef)"),
    ]
    doc_rows = []
    for d in ver["documents"]:
        did = d["doc_id"]
        code, auth, sector, issuer = doc_authority_map.get(did, ("00", "advisory", "COMMERCIAL_BANK", "금융위원회"))
        rel_no_ext = d["concept_id"]
        doc_rows.append({
            "doc_id": did,
            "doc_code": code,
            "title": d["title"],
            "authority_level": auth,
            "applicable_sector": sector,
            "issuing_body": issuer,
            "kc_entry_id": rel_no_ext,
            "gcs_uri": f"gs://{BUCKET}/okf/{rel_no_ext}.md",
        })
    load_table_rows(
        client,
        "lex_source_documents",
        doc_schema,
        doc_rows,
        "[Node: SourceDocument] 법령·감독규정·내규·타업권 문서 루트 테이블 (10건, Knowledge Catalog 1:1 매핑)",
    )

    # 3. Provision (174 rows) — Single Source of Governance: NO lifecycle_hint or superseded_by_id in BigQuery!
    special_meta = {
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026": (
            "BASE_CRITERIA",
            "ont_loan_contracts.outstanding_amt,customers.customer_id",
            "tier1_capital,counterparty_group_id",
        ),
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027": (
            "BASE_CRITERIA",
            "ont_loan_contracts.asset_classification,ont_loan_contracts.account_status,ont_delinquency_events.write_off_yn",
            "",
        ),
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029": (
            "BASE_CRITERIA",
            "ont_loan_contracts.asset_classification,ont_loan_contracts.outstanding_amt,ont_loan_contracts.booked_provision_krw,ont_loan_contracts.rehab_priority_claim_yn,customers.ksic_section_code,financial_products.loan_category",
            "",
        ),
        "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_normal_precautionary": (
            "DEFINITION",
            "ont_loan_contracts.asset_classification,ont_loan_contracts.overdue_days",
            "",
        ),
        "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_substandard_doubtful_loss": (
            "DEFINITION",
            "ont_loan_contracts.asset_classification,ont_loan_contracts.overdue_days",
            "",
        ),
        "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption": (
            "EXCEPTION_PROVISO",
            "workout_histories.consecutive_normal_repay_months,workout_histories.new_equity_paid_in_krw,ont_exception_approvals.approval_status,ont_exception_approvals.approval_dt",
            "",
        ),
        "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_06_07_workout_special_rules": (
            "EXCEPTION_PROVISO",
            "workout_histories.legal_proceeding_code,ont_loan_contracts.rehab_priority_claim_yn,ont_delinquency_events.overdue_days",
            "",
        ),
        "regulations/03_fsc_reg_impact_analysis/sec02_article_comparison_and_annex/impact_04_annex3_4_general_rules": (
            "ADVISORY_METRIC",
            "ont_loan_contracts.outstanding_amt",
            "tier1_capital",
        ),
        "regulations/03_fsc_reg_impact_analysis/sec02_article_comparison_and_annex/impact_05_annex3_4_counterparty_group": (
            "ADVISORY_METRIC",
            "customers.customer_id",
            "counterparty_group_id,affiliate_control_relation",
        ),
        "regulations/04_fsc_large_exposure_notice/sec01_background_and_tier1_limit/notice_01_background": (
            "ADVISORY_METRIC",
            "ont_loan_contracts.outstanding_amt",
            "tier1_capital,counterparty_group_id",
        ),
        "regulations/05_fsc_kfb_loan_rate_reform/ch01_background_and_statement/rate_reform_sec_2_1_a_statement": (
            "DEFINITION",
            "ont_loan_contracts.base_rate,ont_loan_contracts.spread_rate,ont_loan_contracts.pref_rate,ont_loan_contracts.applied_rate",
            "",
        ),
        "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion": (
            "EXCEPTION_PROVISO",
            "ont_rate_cut_requests.application_reason_code,ont_rate_cut_requests.review_status_code",
            "",
        ),
        "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_c_abc_separation": (
            "BASE_CRITERIA",
            "ont_loan_contracts.base_rate,ont_loan_contracts.spread_rate,ont_loan_contracts.pref_rate,ont_loan_contracts.applied_rate",
            "",
        ),
        "research_briefs/07_nars_rate_policy_issues/sec01_rate_components_and_dsr/nars_02_dsr_and_delinquency_trend": (
            "DISTRACTOR_RULE",
            "financial_products.loan_category",
            "",
        ),
        "research_briefs/08_kif_loan_loss_provision/sec01_coverage_ratio_and_implications/kif_01_cr_definition_and_domestic": (
            "ADVISORY_METRIC",
            "ont_loan_contracts.booked_provision_krw,ont_loan_contracts.outstanding_amt,ont_loan_contracts.asset_classification,ont_loan_contracts.account_status",
            "",
        ),
        "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_01_overview": (
            "DISTRACTOR_RULE",
            "ont_loan_contracts.asset_classification",
            "",
        ),
        "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge": (
            "DISTRACTOR_RULE",
            "ont_loan_contracts.asset_classification,ont_loan_contracts.booked_provision_krw",
            "",
        ),
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency": (
            "INTERNAL_RULE",
            "ont_loan_contracts.outstanding_amt,ont_loan_contracts.asset_classification,ont_loan_contracts.account_status,ont_delinquency_events.overdue_days,ont_delinquency_events.overdue_principal_krw,ont_delinquency_events.write_off_yn",
            "",
        ),
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule": (
            "INTERNAL_RULE",
            "ont_loan_contracts.overdue_days,ont_loan_contracts.account_status",
            "",
        ),
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver": (
            "EXCEPTION_PROVISO",
            "ont_loan_contracts.rehab_priority_claim_yn,workout_histories.consecutive_normal_repay_months,workout_histories.new_equity_paid_in_krw,ont_collaterals.collateral_type_code,ont_collaterals.guarantee_agency_code,ont_collaterals.guarantee_ratio_pct,ont_exception_approvals.approval_status",
            "",
        ),
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates": (
            "INTERNAL_RULE",
            "ont_loan_contracts.contract_dt,ont_loan_contracts.reg_dt,ont_loan_contracts.disburse_dt,ont_loan_contracts.contract_amt",
            "",
        ),
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc": (
            "INTERNAL_RULE",
            "ont_loan_contracts.base_rate,ont_loan_contracts.spread_rate,ont_loan_contracts.pref_rate,ont_loan_contracts.applied_rate,financial_products.base_rate_benchmark",
            "",
        ),
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion": (
            "INTERNAL_RULE",
            "ont_loan_contracts.product_code,ont_loan_contracts.pref_rate,customers.debt_ratio_pct,ont_rate_cut_requests.application_reason_code,ont_rate_cut_requests.credit_rating_before,ont_rate_cut_requests.credit_rating_after,ont_rate_cut_requests.review_status_code",
            "",
        ),
    }

    prov_schema = [
        bigquery.SchemaField("provision_slot_id", "STRING", mode="REQUIRED", description="버전이 바뀌어도 유지되는 불변 조문 슬롯 식별자 (PK, canonical_id)"),
        bigquery.SchemaField("doc_id", "STRING", mode="NULLABLE", description="소속 원본 문서 식별자 (FK -> SourceDocument.doc_id)"),
        bigquery.SchemaField("kc_entry_id", "STRING", mode="NULLABLE", description="Dataplex Knowledge Catalog에서 실시간 유효성(status) 및 대체문서(superseded_by)를 조회할 기준 Entry ID"),
        bigquery.SchemaField("article_no", "STRING", mode="NULLABLE", description="조문 번호 또는 별표 항목명 (예: 제29조, 별표3 제3호 라목, 내규 제25조)"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE", description="조문·별표 항목의 제목"),
        bigquery.SchemaField("provision_role", "STRING", mode="NULLABLE", description="조문의 기능적 역할 (BASE_CRITERIA 본칙 / EXCEPTION_PROVISO 단서·특례 / INTERNAL_RULE 당행내규 / DISTRACTOR_RULE 교란조문)"),
        bigquery.SchemaField("target_columns", "STRING", mode="NULLABLE", description="조문 적용 시 조회해야 하는 정형 원장 테이블.컬럼 목록 (콤마 구분)"),
        bigquery.SchemaField("missing_schema_columns", "STRING", mode="NULLABLE", description="규정상 필요하나 현재 DW에 존재하지 않는 데이터 공백 컬럼 (예: tier1_capital)"),
        bigquery.SchemaField("gcs_uri", "STRING", mode="NULLABLE", description="GCS에 저장된 조문 마크다운 원문 URI (ObjectRef)"),
    ]
    prov_rows = []
    for p in ver["provisions"]:
        cid = p["concept_id"]
        did = p["doc_id"]
        default_role = (
            "INTERNAL_RULE" if did == "DOC_10_SYNTHETIC_BYULBIT_POLICY"
            else "DISTRACTOR_RULE" if did == "DOC_09_DISTRACTOR_SAVINGS_BANK"
            else "ADVISORY_METRIC" if did in ("DOC_03_FSC_IMPACT", "DOC_04_FSC_EXPOSURE_NOTICE", "DOC_05_FSC_KFB_RATE", "DOC_06_FSC_7TH_TF", "DOC_07_NARS_RATE", "DOC_08_KIF_PROVISION")
            else "BASE_CRITERIA"
        )
        role, t_cols, m_cols = special_meta.get(cid, (default_role, "", ""))
        prov_rows.append({
            "provision_slot_id": cid,
            "doc_id": did,
            "kc_entry_id": cid,
            "article_no": p["section_number"],
            "title": p["title"],
            "provision_role": role,
            "target_columns": t_cols,
            "missing_schema_columns": m_cols,
            "gcs_uri": f"gs://{BUCKET}/okf/{cid}.md",
        })
    load_table_rows(
        client,
        "lex_provisions",
        prov_schema,
        prov_rows,
        "[Node: Provision] 법령·감독규정·내규 조문 및 별표 조항 테이블 (174건 전체, 불변 슬롯 ID 및 KC Entry 참조 보유 — 유효성·대체 체인은 KC에서만 관리)",
    )

    # 4. Build INVOKES_PROVISION Bridge Table (with Dataplex Business Glossary `term_key` & `glossary_term_uri`)
    invokes_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED", description="부서맥락-용어-조문 호출 엣지 고유 식별자 (PK)"),
        bigquery.SchemaField("context_id", "STRING", mode="REQUIRED", description="호출 주체 부서·업무목적 맥락 식별자 (Source FK -> BusinessContext.context_id)"),
        bigquery.SchemaField("term_key", "STRING", mode="REQUIRED", description="Dataplex Business Glossary 표준 금융 용어 식별자 (예: delinquency-rate, provision-criteria, loan-rate)"),
        bigquery.SchemaField("glossary_term_uri", "STRING", mode="NULLABLE", description="Dataplex Knowledge Catalog Business Glossary 용어 리소스 경로"),
        bigquery.SchemaField("provision_slot_id", "STRING", mode="REQUIRED", description="호출 대상 법령·내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("invocation_reason", "STRING", mode="NULLABLE", description="해당 부서 맥락과 금융 용어 조합에서 이 조문을 호출하는 비즈니스 이유 한 줄 설명"),
    ]
    invokes_tuples = [
        ("RISK_MGMT", "delinquency-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency", "리스크관리위원회 보고용 고정이하여신비율(NPL Ratio 1.51%) 정의 및 산식 적용"),
        ("RISK_MGMT", "delinquency-rate", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027", "리스크관리부 자산건전성 5단계 분류(정상~추정손실) 및 고정이하 분류 기준 적용"),
        ("RISK_MGMT", "provision-criteria", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029", "리스크관리부 대손충당금·대손준비금 최소적립비율(0.85%/0.90%/7%/20%/10%) 산출"),
        ("RISK_MGMT", "provision-criteria", "research_briefs/08_kif_loan_loss_provision/sec01_coverage_ratio_and_implications/kif_01_cr_definition_and_domestic", "대손충당금 적립률(Coverage Ratio = 총충당금 ÷ 고정이하여신) 산출 및 국내 은행그룹 비교"),
        ("RISK_MGMT", "restructured-exemption", "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption", "채권재조정 여신 요주의 유지(고정이하 제외) 특례의 대손충당금 민감도 분석"),
        ("DISCLOSURE", "delinquency-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency", "금융감독원 대외공시용 원화대출 연체율(1개월 이상 연체, 상각 특수채권 제외 2.26%) 산출"),
        ("DISCLOSURE", "delinquency-rate", "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_06_07_workout_special_rules", "공시용 연체기간 기산일(약정기일 다음날) 기준 확인"),
        ("CREDIT_MGMT", "delinquency-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency", "여신관리팀 조기경보(EWS) 실질관리 연체율(10일 이상 연체 + 상각 특수채권 분자·분모 포함 4.00%) 산출"),
        ("CREDIT_MGMT", "eod-deferral", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule", "원리금 연체 30일(1월) 초과 시 기한이익상실(EOD) 예정 통지 원칙 적용"),
        ("CREDIT_MGMT", "eod-deferral", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver", "채권재조정·신보 85% 이상 보증서 및 우선변제자산 충족 시 본부심사역 승인하 EOD 유예 특례 적용"),
        ("CREDIT_REVIEW", "restructured-exemption", "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption", "기업여신심사부 채권재조정 여신 고정이하 분류 제외 특례(6개월 상환·증자·문서화) 적격성 심사"),
        ("CREDIT_REVIEW", "eod-deferral", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver", "기업여신심사부 신용보증기금(KODIT) 85% 이상 보증서 담보 적격성 및 EOD 유예 심사"),
        ("BRANCH", "loan-rate", "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion", "영업점 금리인하요구권 응대 시 특허 취득 사유의 은행 선택적 적용 재량 및 거절 사유 통보 의무 확인"),
        ("BRANCH", "loan-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion", "영업점 단독 특허 취득 시 필수 금리인하 제외 기준 및 TCB 우대금리 전결 한도 확인"),
        ("BRANCH", "loan-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc", "영업점 대출금리 산식(applied_rate = base_rate + spread_rate - pref_rate) 적용"),
        ("BRANCH", "base-date", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates", "영업점 신규 대출 실적 및 특정일자 대출 조회 시 체결일(contract_dt) 필수 기준 적용"),
        ("COMPLIANCE", "large-exposure", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026", "준법감시부 거액익스포져 한도(기본자본의 25% 이내) 신설 규제 준수 및 데이터 구비 여부 점검"),
        ("COMPLIANCE", "delinquency-rate", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027", "준법감시부 추정손실 부실자산 조기 대손상각(제27조④) 적정성 감사"),
        ("COMPLIANCE", "delinquency-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency", "준법감시부 대손상각 특수채권의 공시 연체율(제외) vs EWS 연체율(포함) 분리 처리 점검"),
        ("COMPLIANCE", "loan-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc", "준법감시부 은행연합회 비교공시 시 기준(A)·가산(B)·가감조정(C) 분리공시 및 착시 공시 금지 점검"),
        ("COMPLIANCE", "loan-rate", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion", "준법감시부 TCB 기술혁신 운전자금 우대금리(1.20%p) 및 부채비율(250%) 내규 한도 위반 여부 감사"),
    ]
    invokes_rows = [
        {
            "edge_id": f"INV_{i+1:03d}",
            "context_id": c,
            "term_key": tkey,
            "glossary_term_uri": f"projects/{PROJECT}/locations/{LOCATION}/glossaries/{GLOSSARY_ID}/terms/{tkey}",
            "provision_slot_id": p,
            "invocation_reason": r,
        }
        for i, (c, tkey, p, r) in enumerate(invokes_tuples)
    ]
    load_table_rows(
        client,
        "edge_invokes_provision",
        invokes_schema,
        invokes_rows,
        "[Edge: INVOKES_PROVISION] 부서·업무목적 맥락(BusinessContext)과 Dataplex Glossary 용어(term_key) 조합별 호출 조문(Provision) 브리지 테이블",
    )

    # 5. LEX Self-Edges: HAS_EXCEPTION_PROVISO, DELEGATES_TO_INTERNAL, CONFLICTS_BY_SECTOR
    exc_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED", description="본칙-단서/특례 조문 연결 엣지 고유 식별자 (PK)"),
        bigquery.SchemaField("base_slot_id", "STRING", mode="REQUIRED", description="원칙(본칙) 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("proviso_slot_id", "STRING", mode="REQUIRED", description="단서·예외·특례 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("exception_condition", "STRING", mode="NULLABLE", description="본칙에서 단서·특례로 분기되는 예외 성립 요건 한 줄 요약"),
    ]
    exc_rows = [
        {
            "edge_id": "EXC_001",
            "base_slot_id": "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
            "proviso_slot_id": "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
            "exception_condition": "채권재조정 여신 중 6개월 이상 연속 정상상환 또는 유상증자 발생 및 판단근거 문서화 시 고정이하 분류 제외(요주의 가능)",
        },
        {
            "edge_id": "EXC_002",
            "base_slot_id": "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
            "proviso_slot_id": "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_06_07_workout_special_rules",
            "exception_condition": "기촉법 제18조② 및 회생법 제180조②에 따른 우선변제자산은 고정 10%·회수의문 25%·추정손실 50%로 적립비율 감경 (단, 요주의 7%는 감경 없음)",
        },
        {
            "edge_id": "EXC_003",
            "base_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule",
            "proviso_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
            "exception_condition": "연체 30일 초과 시에도 (6개월 정상상환 OR 유상증자 OR 신보 85% 이상 보증서) AND 우선변제자산 요건 충족 + 본부심사역 승인 시 EOD 유예",
        },
        {
            "edge_id": "EXC_004",
            "base_slot_id": "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026",
            "proviso_slot_id": "regulations/03_fsc_reg_impact_analysis/sec02_article_comparison_and_annex/impact_07_annex3_4_item54_exceptions",
            "exception_condition": "거액익스포져 기본자본 25% 한도(D-SIB 20%) 적용 시 별표3의4 제54호 한도초과 예외 사유 및 정책금융 특례",
        },
    ]
    load_table_rows(
        client,
        "edge_has_exception_proviso",
        exc_schema,
        exc_rows,
        "[Edge: HAS_EXCEPTION_PROVISO] 원칙(본칙) 조문에서 단서·예외·특례 조문으로 분기하는 법령 내부 엣지 테이블",
    )

    del_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED", description="상위법령-당행내규 위임 엣지 고유 식별자 (PK)"),
        bigquery.SchemaField("external_slot_id", "STRING", mode="REQUIRED", description="상위 감독규정·모범규준 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("internal_slot_id", "STRING", mode="REQUIRED", description="위임받아 구체화한 별빛은행 내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("delegation_scope", "STRING", mode="NULLABLE", description="상위 규정이 당행 내규에 위임하거나 구체화한 세부 운영 기준 설명"),
    ]
    del_rows = [
        {
            "edge_id": "DEL_001",
            "external_slot_id": "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
            "internal_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
            "delegation_scope": "감독규정 건전성 분류 및 연체 기준을 리스크위 보고용(고정이하)·공시용(30일 이상, 상각 제외)·EWS용(10일 이상, 상각 포함) 3종 지표로 세분화",
        },
        {
            "edge_id": "DEL_002",
            "external_slot_id": "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
            "internal_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
            "delegation_scope": "별표3 라목 채권재조정 특례 및 보증부 여신 평가를 당행 EOD 유예 요건(신보 85% 이상 보증서 + 본부심사역 결재)으로 구체화",
        },
        {
            "edge_id": "DEL_003",
            "external_slot_id": "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion",
            "internal_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion",
            "delegation_scope": "모범규준 Ⅱ-1-나 ④항의 '특허 취득 은행 선택적 적용 재량'을 행사하여 당행 내규 제25조②에서 단독 특허를 필수 인하 사유에서 제외",
        },
        {
            "edge_id": "DEL_004",
            "external_slot_id": "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_c_abc_separation",
            "internal_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc",
            "delegation_scope": "대출금리 비교공시 개선방안의 기준(A)·가산(B)·가감조정(C) 분리공시 원칙을 당행 전산 산식 및 착시공시 금지 내규로 명문화",
        },
    ]
    load_table_rows(
        client,
        "edge_delegates_to_internal",
        del_schema,
        del_rows,
        "[Edge: DELEGATES_TO_INTERNAL] 상위 법령·모범규준에서 별빛은행 자체 내규 조문으로 세부 기준을 위임·구체화하는 엣지 테이블",
    )

    conf_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED", description="업권·여신유형 충돌 대조 엣지 고유 식별자 (PK)"),
        bigquery.SchemaField("bank_slot_id", "STRING", mode="REQUIRED", description="시중은행 기업여신 정식 적용 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("distractor_slot_id", "STRING", mode="REQUIRED", description="혼입 차단 대상 타업권(저축은행)·타세그먼트 교란 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
        bigquery.SchemaField("conflict_warning", "STRING", mode="NULLABLE", description="두 조문을 혼동하면 안 되는 업권·세그먼트 차이 경고 설명"),
    ]
    conf_rows = [
        {
            "edge_id": "CONF_001",
            "bank_slot_id": "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
            "distractor_slot_id": "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge",
            "conflict_warning": "시중은행 기업여신 충당금(정상 0.85%/0.90%, 회수의문 50%)에 상호저축은행업감독규정 제38조(정상 0.5%, 회수의문 75%/55%, 다중채무자 가중)를 혼입 적용 금지",
        },
        {
            "edge_id": "CONF_002",
            "bank_slot_id": "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
            "distractor_slot_id": "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_02_overdue_criteria",
            "conflict_warning": "시중은행 건전성 분류 기준에 상호저축은행 전용 건전성 분류 및 연체 기준(79개 저축은행 대상)을 혼입 적용 금지",
        },
        {
            "edge_id": "CONF_003",
            "bank_slot_id": "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
            "distractor_slot_id": "research_briefs/07_nars_rate_policy_issues/sec01_rate_components_and_dsr/nars_02_dsr_and_delinquency_trend",
            "conflict_warning": "별빛은행 기업여신 공시 연체율(2.26%) 산출 시 국회입법조사처 브리프에 인용된 거시 가계대출 연체율(0.24%) 수치를 혼입 인용 금지",
        },
    ]
    load_table_rows(
        client,
        "edge_conflicts_by_sector",
        conf_schema,
        conf_rows,
        "[Edge: CONFLICTS_BY_SECTOR] 시중은행 기업여신 규정과 상호저축은행(타업권)·가계여신 규정 간의 오적용 방지 대조 엣지 테이블",
    )

    # 6. Build Entity Alias Table (`ont_entity_aliases`) with Live Data Alignment & Glossary Term Mapping
    alias_schema = [
        bigquery.SchemaField("alias_id", "STRING", mode="REQUIRED", description="별칭 매핑 고유 번호 (PK)"),
        bigquery.SchemaField("alias_term", "STRING", mode="REQUIRED", description="사용자 질문에 등장하는 자연어 약칭·별칭·동의어 (최장일치 Longest-Match-First 매칭 대상)"),
        bigquery.SchemaField("target_class", "STRING", mode="REQUIRED", description="매핑 대상 그래프 노드 또는 엣지 클래스명 (예: Customer, FinancialProduct, BusinessContext, GlossaryTerm, Provision)"),
        bigquery.SchemaField("match_bind_key", "STRING", mode="REQUIRED", description="GQL MATCH 절 내부에 바인딩할 프로퍼티 키 이름 (예: customer_id, product_code, context_id, term_key)"),
        bigquery.SchemaField("canonical_id", "STRING", mode="REQUIRED", description="정규화된 실제 PK 또는 코드 값 (예: CUST_0008, PROD_CORP_PRIME_WC, RISK_MGMT, delinquency-rate)"),
        bigquery.SchemaField("canonical_display", "STRING", mode="NULLABLE", description="정규화된 엔티티의 공식 표시 명칭 (예: 에이펙스세미콘(주))"),
        bigquery.SchemaField("gql_match_snippet", "STRING", mode="NULLABLE", description="에이전트가 GQL MATCH 절에 즉시 삽입할 수 있는 완성형 노드·엣지 패턴 스니펫"),
    ]
    alias_rows = []
    seen_pairs: set[tuple[str, str]] = set()
    a_idx = 1

    def add_alias(term: str, cls: str, key: str, cid: str, disp: str, snippet: str):
        nonlocal a_idx
        t = term.strip()
        if not t or (t, cls) in seen_pairs:
            return
        seen_pairs.add((t, cls))
        alias_rows.append({
            "alias_id": f"ALS_{a_idx:04d}",
            "alias_term": t,
            "target_class": cls,
            "match_bind_key": key,
            "canonical_id": cid,
            "canonical_display": disp,
            "gql_match_snippet": snippet,
        })
        a_idx += 1

    # 6a. Customer aliases (100 live customers + explicit colloquial short names)
    cust_list = list(client.query(f"SELECT customer_id, borrower_name FROM `{PROJECT}.{SRC_DS}.customers` ORDER BY customer_id").result())
    for c in cust_list:
        cid = c["customer_id"]
        bname = c["borrower_name"]
        short_name = re.sub(r"\(주\)|주식회사|\s+", "", bname).strip()
        add_alias(bname, "Customer", "customer_id", cid, bname, f"(c:Customer {{customer_id: '{cid}'}})")
        add_alias(short_name, "Customer", "customer_id", cid, bname, f"(c:Customer {{customer_id: '{cid}'}})")

    explicit_cust_aliases = [
        ("별빛정밀", "CUST_0001", "별빛정밀(주)"),
        ("태성금속", "CUST_0002", "태성금속공업(주)"),
        ("태성금속공업", "CUST_0002", "태성금속공업(주)"),
        ("극동철강", "CUST_0003", "극동철강산업(주)"),
        ("극동철강산업", "CUST_0003", "극동철강산업(주)"),
        ("한울바이오텍", "CUST_0004", "한울바이오텍(주)"),
        ("삼호종합건설", "CUST_0005", "삼호종합건설(주)"),
        ("삼호건설", "CUST_0005", "삼호종합건설(주)"),
        ("대양해운물류", "CUST_0006", "대양해운물류(주)"),
        ("대양해운", "CUST_0006", "대양해운물류(주)"),
        ("코어 로보틱스", "CUST_0007", "코어로보틱스(주)"),
        ("에이펙스세미콘", "CUST_0008", "에이펙스세미콘(주)"),
        ("에이펙스 반도체", "CUST_0008", "에이펙스세미콘(주)"),
    ]
    for term, cid, disp in explicit_cust_aliases:
        add_alias(term, "Customer", "customer_id", cid, disp, f"(c:Customer {{customer_id: '{cid}'}})")

    # 6b. FinancialProduct aliases (exact live product codes from starlight_bank.financial_products)
    prod_aliases = [
        ("별빛 TCB 기술혁신 운전자금", "PROD_TCB_WORKING", "별빛 TCB 기술혁신 운전자금"),
        ("TCB 기술혁신 운전자금", "PROD_TCB_WORKING", "별빛 TCB 기술혁신 운전자금"),
        ("TCB 운전자금", "PROD_TCB_WORKING", "별빛 TCB 기술혁신 운전자금"),
        ("TCB 대출", "PROD_TCB_WORKING", "별빛 TCB 기술혁신 운전자금"),
        ("별빛 프라임 중견기업 운전자금", "PROD_CORP_PRIME_WC", "별빛 프라임 중견기업 운전자금"),
        ("프라임 중견기업 운전자금", "PROD_CORP_PRIME_WC", "별빛 프라임 중견기업 운전자금"),
        ("중견기업 운전자금", "PROD_CORP_PRIME_WC", "별빛 프라임 중견기업 운전자금"),
        ("별빛 프로젝트·시설기업자금", "PROD_CONST_REALESTATE", "별빛 프로젝트·시설기업자금"),
        ("프로젝트 시설기업자금", "PROD_CONST_REALESTATE", "별빛 프로젝트·시설기업자금"),
        ("프로젝트 시설자금", "PROD_CONST_REALESTATE", "별빛 프로젝트·시설기업자금"),
        ("별빛 기업구조조정·회생운전자금", "PROD_RESTRUCTURED_DIP", "별빛 기업구조조정·회생운전자금"),
        ("기업구조조정 회생운전자금", "PROD_RESTRUCTURED_DIP", "별빛 기업구조조정·회생운전자금"),
        ("구조조정 회생운전자금", "PROD_RESTRUCTURED_DIP", "별빛 기업구조조정·회생운전자금"),
    ]
    for term, pcode, pname in prod_aliases:
        add_alias(term, "FinancialProduct", "product_code", pcode, pname, f"(p:FinancialProduct {{product_code: '{pcode}'}})")

    # 6c. BusinessContext aliases
    ctx_aliases = [
        ("리스크관리위원회", "RISK_MGMT", "리스크관리부"),
        ("리스크관리부", "RISK_MGMT", "리스크관리부"),
        ("금융감독원 공시", "DISCLOSURE", "재무기획부(대외공시)"),
        ("금감원 공시", "DISCLOSURE", "재무기획부(대외공시)"),
        ("대외공시", "DISCLOSURE", "재무기획부(대외공시)"),
        ("재무기획부", "DISCLOSURE", "재무기획부(대외공시)"),
        ("여신관리팀", "CREDIT_MGMT", "여신관리팀"),
        ("조기경보", "CREDIT_MGMT", "여신관리팀"),
        ("EWS", "CREDIT_MGMT", "여신관리팀"),
        ("기업여신심사부", "CREDIT_REVIEW", "기업여신심사부"),
        ("여신심사부", "CREDIT_REVIEW", "기업여신심사부"),
        ("영업점", "BRANCH", "영업점(RM)"),
        ("준법감시부", "COMPLIANCE", "준법감시부"),
        ("준법감시", "COMPLIANCE", "준법감시부"),
    ]
    for term, ctx_id, disp in ctx_aliases:
        add_alias(term, "BusinessContext", "context_id", ctx_id, disp, f"(ctx:BusinessContext {{context_id: '{ctx_id}'}})")

    # 6d. Dataplex Business Glossary Terms (`term_key` for INVOKES_PROVISION edge binding)
    for gterm in l1_cfg.get("glossary_terms", []):
        tkey = gterm["term_key"]
        disp = gterm["display_name"]
        for syn in gterm.get("synonyms", []):
            add_alias(
                syn,
                "GlossaryTerm",
                "term_key",
                tkey,
                disp,
                f"-[inv:INVOKES_PROVISION {{term_key: '{tkey}'}}]->(pr:Provision)",
            )

    # 6e. Provision shorthand aliases
    prov_aliases = [
        ("감독규정 제26조", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026", "은행업감독규정 제26조(경영지도비율·거액익스포져)"),
        ("제26조", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026", "은행업감독규정 제26조(경영지도비율·거액익스포져)"),
        ("감독규정 제27조", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027", "은행업감독규정 제27조(자산건전성분류 등)"),
        ("제27조", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027", "은행업감독규정 제27조(자산건전성분류 등)"),
        ("감독규정 제29조", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029", "은행업감독규정 제29조(대손충당금등 적립기준)"),
        ("제29조", "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029", "은행업감독규정 제29조(대손충당금등 적립기준)"),
        ("별표3 제3호 라목", "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption", "별표3 제3호 라목(채권재조정여신 고정이하 분류 제외 특례)"),
        ("별표3 라목", "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption", "별표3 제3호 라목(채권재조정여신 고정이하 분류 제외 특례)"),
        ("내규 제14조", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency", "별빛은행 내규 제14조(부서별 연체율·EWS 산정 기준)"),
        ("내규 제16조", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule", "별빛은행 내규 제16조(30일 초과 연체 EOD 통지 원칙)"),
        ("내규 제18조", "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver", "별빛은행 내규 제18조(채권재조정·신보 85% 보증서 EOD 유예 특례)"),
        ("내규 제21조", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates", "별빛은행 내규 제21조(등록일·체결일·실행일 3대 기준일자)"),
        ("내규 제22조", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc", "별빛은행 내규 제22조(금리 산출식 및 A+B+C 분리공시)"),
        ("내규 제25조", "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion", "별빛은행 내규 제25조(TCB 우대금리 1.20%p 상한 및 단독 특허 금리인하 제외)"),
        ("저축은행 감독규정 제38조", "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge", "상호저축은행업감독규정 제38조(타업권 교란 조문)"),
        ("저축은행 제38조", "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge", "상호저축은행업감독규정 제38조(타업권 교란 조문)"),
    ]
    for term, pslot, disp in prov_aliases:
        add_alias(term, "Provision", "provision_slot_id", pslot, disp, f"(pr:Provision {{provision_slot_id: '{pslot}'}})")

    # 6f. Direct PK & Domain aliases for all remaining classes (F3: all 11 classes key-bound)
    for d in doc_rows:
        add_alias(d["doc_id"], "SourceDocument", "doc_id", d["doc_id"], d["title"], f"(doc:SourceDocument {{doc_id: '{d['doc_id']}'}})")
        add_alias(d["title"], "SourceDocument", "doc_id", d["doc_id"], d["title"], f"(doc:SourceDocument {{doc_id: '{d['doc_id']}'}})")

    for r in client.query(f"SELECT contract_id, borrower_name FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` ORDER BY contract_id").result():
        cid = r["contract_id"]
        add_alias(cid, "LoanContract", "contract_id", cid, f"{cid} ({r['borrower_name']})", f"(l:LoanContract {{contract_id: '{cid}'}})")

    for r in client.query(f"SELECT workout_id, contract_id, legal_proceeding_code FROM `{PROJECT}.{SRC_DS}.workout_histories` ORDER BY workout_id").result():
        wid = r["workout_id"]
        add_alias(wid, "WorkoutHistory", "workout_id", wid, f"{wid} ({r['legal_proceeding_code']})", f"(w:WorkoutHistory {{workout_id: '{wid}'}})")
    add_alias("기촉법 워크아웃", "WorkoutHistory", "legal_proceeding_code", "CORP_RESTRUCT_ACT_WORKOUT", "기업구조조정촉진법 워크아웃", "(w:WorkoutHistory {legal_proceeding_code: 'CORP_RESTRUCT_ACT_WORKOUT'})")
    add_alias("회생법 제180조", "WorkoutHistory", "legal_proceeding_code", "REHAB_ACT_ART180_2_DIP", "채무자회생법 제180조제2항 공익채권", "(w:WorkoutHistory {legal_proceeding_code: 'REHAB_ACT_ART180_2_DIP'})")

    for r in client.query(f"SELECT collateral_id, collateral_type_code, guarantee_agency_code FROM `{PROJECT}.{SRC_DS}.ont_collaterals` ORDER BY collateral_id").result():
        col_id = r["collateral_id"]
        add_alias(col_id, "Collateral", "collateral_id", col_id, f"{col_id} ({r['collateral_type_code']})", f"(col:Collateral {{collateral_id: '{col_id}'}})")
    add_alias("신용보증기금", "Collateral", "guarantee_agency_code", "KODIT", "신용보증기금(KODIT)", "(col:Collateral {guarantee_agency_code: 'KODIT'})")
    add_alias("신보", "Collateral", "guarantee_agency_code", "KODIT", "신용보증기금(KODIT)", "(col:Collateral {guarantee_agency_code: 'KODIT'})")

    for r in client.query(f"SELECT event_id, contract_id, overdue_days, write_off_yn FROM `{PROJECT}.{SRC_DS}.ont_delinquency_events` ORDER BY event_id").result():
        eid = r["event_id"]
        add_alias(eid, "DelinquencyEvent", "event_id", eid, f"{eid} ({r['overdue_days']}d)", f"(del:DelinquencyEvent {{event_id: '{eid}'}})")
    add_alias("대손상각 특수채권", "DelinquencyEvent", "write_off_yn", "Y", "회계상 대손상각 특수채권(write_off_yn='Y')", "(del:DelinquencyEvent {write_off_yn: 'Y'})")

    for r in client.query(f"SELECT request_id, application_reason_code, review_status_code FROM `{PROJECT}.{SRC_DS}.ont_rate_cut_requests` ORDER BY request_id").result():
        rid = r["request_id"]
        add_alias(rid, "RateCutRequest", "request_id", rid, f"{rid} ({r['application_reason_code']})", f"(rc:RateCutRequest {{request_id: '{rid}'}})")
    add_alias("단독 특허 취득", "RateCutRequest", "application_reason_code", "PATENT_ACQUISITION_STANDALONE", "특허권 단독 취득 금리인하 신청", "(rc:RateCutRequest {application_reason_code: 'PATENT_ACQUISITION_STANDALONE'})")

    for r in client.query(f"SELECT approval_id, approval_type_code, approval_status FROM `{PROJECT}.{SRC_DS}.ont_exception_approvals` ORDER BY approval_id").result():
        aid = r["approval_id"]
        add_alias(aid, "ExceptionApproval", "approval_id", aid, f"{aid} ({r['approval_status']})", f"(ea:ExceptionApproval {{approval_id: '{aid}'}})")
    add_alias("본부 여신심사역 승인", "ExceptionApproval", "approver_role_code", "HQ_SENIOR_CREDIT_OFFICER", "본부 여신심사역 예외승인(HQ_SENIOR_CREDIT_OFFICER)", "(ea:ExceptionApproval {approver_role_code: 'HQ_SENIOR_CREDIT_OFFICER'})")

    load_table_rows(
        client,
        "ont_entity_aliases",
        alias_schema,
        alias_rows,
        "[Alias Table] 자연어 질문의 기업명·상품명·부서·KC Glossary 용어·전 클래스 PK를 최장일치(Longest-Match-First)로 정규화하여 GQL MATCH 절에 바인딩하는 매핑 테이블",
    )


def build_views_and_property_graph(client: bigquery.Client) -> None:
    sql_statements = f"""
-- ============================================================================
-- 1. 11 NODE VIEWS IN `starlight_bank_ontology` (모든 뷰·컬럼 직관적 한 줄 설명 포함)
-- ============================================================================

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_business_context` (
  context_id OPTIONS(description="부서·업무목적 맥락 고유 식별자 (PK, 예: RISK_MGMT, DISCLOSURE, CREDIT_MGMT)"),
  dept_name OPTIONS(description="업무를 주관하는 은행 내 부서명 (예: 리스크관리부, 재무기획부, 여신관리팀)"),
  purpose_summary OPTIONS(description="해당 부서의 핵심 의사결정 및 보고 목적 한 줄 요약"),
  primary_metric_scope OPTIONS(description="해당 맥락에서 주로 산출·점검하는 핵심 지표 및 심사 범위")
)
OPTIONS(
  description="[Node: BusinessContext] 동일 금융 용어(연체율·금리·실적) 호출 시 부서와 업무목적에 따라 적용 조문과 물리 컬럼을 분기하는 맥락 노드"
)
AS
SELECT context_id, dept_name, purpose_summary, primary_metric_scope
FROM `{PROJECT}.{ONT_DS}.ctx_business_contexts`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_source_document` (
  doc_id OPTIONS(description="원본 법령·내규 문서 고유 식별자 (PK, DOC_01 ~ DOC_10)"),
  doc_code OPTIONS(description="문서 번호 코드 (01 ~ 10)"),
  title OPTIONS(description="법령·감독규정·브리프·내규 문서의 공식 명칭"),
  authority_level OPTIONS(description="법적 구속력 구분 (binding 법규 / internal 당행내규 / advisory 가이드·자문 / distractor 타업권교란)"),
  applicable_sector OPTIONS(description="규정 적용 대상 금융업권 (COMMERCIAL_BANK 시중은행 vs SAVINGS_BANK 상호저축은행)"),
  issuing_body OPTIONS(description="문서 제정·발행 기관명 (금융위원회, 은행연합회, 별빛은행 등)"),
  kc_entry_id OPTIONS(description="Dataplex Knowledge Catalog에 등록된 문서 루트 Entry ID"),
  gcs_uri OPTIONS(description="GCS에 저장된 OKF 문서 루트 마크다운 파일 경로"),
  gcs_obj_ref OPTIONS(description="BigQuery Cloud Resource Connection(us-central1.okf-gcs-conn) 기반 네이티브 ObjectRef 구조체 (OBJ.FETCH_METADATA / OBJ.GET_ACCESS_URL 호출용)")
)
OPTIONS(
  description="[Node: SourceDocument] 은행업감독규정·모범규준·당행내규·타업권 규정 등 10종 원본 문서의 법적 구속력과 적용 업권 및 네이티브 ObjectRef(gcs_obj_ref)를 정의하는 루트 노드"
)
AS
SELECT
  doc_id, doc_code, title, authority_level, applicable_sector, issuing_body, kc_entry_id, gcs_uri,
  OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
FROM `{PROJECT}.{ONT_DS}.lex_source_documents`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_provision` (
  provision_slot_id OPTIONS(description="버전이 바뀌어도 유지되는 불변 조문 슬롯 식별자 (PK, canonical_id)"),
  doc_id OPTIONS(description="소속 원본 문서 식별자 (FK -> SourceDocument.doc_id)"),
  kc_entry_id OPTIONS(description="Dataplex Knowledge Catalog에서 실시간 유효성(status) 및 대체문서(superseded_by)를 조회할 기준 Entry ID"),
  article_no OPTIONS(description="조문 번호 또는 별표 항목명 (예: 제29조, 별표3 제3호 라목, 내규 제25조)"),
  title OPTIONS(description="조문·별표 항목의 제목"),
  provision_role OPTIONS(description="조문의 기능적 역할 (BASE_CRITERIA 본칙 / EXCEPTION_PROVISO 단서·특례 / INTERNAL_RULE 당행내규 / DISTRACTOR_RULE 교란조문)"),
  target_columns OPTIONS(description="조문 적용 시 조회해야 하는 정형 원장 테이블.컬럼 목록 (콤마 구분)"),
  missing_schema_columns OPTIONS(description="규정상 필요하나 현재 DW에 존재하지 않는 데이터 공백 컬럼 (예: tier1_capital)"),
  gcs_uri OPTIONS(description="GCS에 저장된 조문 마크다운 원문 URI"),
  gcs_obj_ref OPTIONS(description="BigQuery Cloud Resource Connection(us-central1.okf-gcs-conn) 기반 네이티브 ObjectRef 구조체 (OBJ.FETCH_METADATA / OBJ.GET_ACCESS_URL 호출용)")
)
OPTIONS(
  description="[Node: Provision] 174개 개별 조문·별표·단서 조항 노드로, 불변 슬롯 ID·KC Entry 참조·참조 물리 컬럼 및 네이티브 ObjectRef(gcs_obj_ref)를 보유함"
)
AS
SELECT
  provision_slot_id, doc_id, kc_entry_id, article_no, title,
  provision_role, target_columns, missing_schema_columns, gcs_uri,
  OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
FROM `{PROJECT}.{ONT_DS}.lex_provisions`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_loan_contract` (
  contract_id OPTIONS(description="여신계약 고유 번호 (PK, 예: LN_2026_0001)"),
  customer_id OPTIONS(description="차주 고객 고유 번호 (FK -> Customer.customer_id)"),
  product_code OPTIONS(description="가입 여신상품 코드 (FK -> FinancialProduct.product_code)"),
  borrower_name OPTIONS(description="차주 법인명"),
  ksic_section_code OPTIONS(description="한국표준산업분류 대분류 코드 (F 건설, G 도소매, H 숙박음식, L 부동산업 등)"),
  reg_dt OPTIONS(description="여신 심사 전산 최초 등록일 (실적 기준일 아님)"),
  contract_dt OPTIONS(description="여신거래약정 체결일 (내규 제21조상 신규 영업실적 및 특정일자 조회 필수 기준일)"),
  disburse_dt OPTIONS(description="실제 대출금 자금 실행일 (자금부 집행 기준일)"),
  base_rate OPTIONS(description="기준금리 A (연 %, 코픽스·CD·금융채 연동)"),
  spread_rate OPTIONS(description="가산금리 B (연 %, 신용·업무원가·목표이익률 합산)"),
  pref_rate OPTIONS(description="가감조정 우대금리 C (연 %p, 차감 항목이며 TCB 전결 상한은 1.20%p)"),
  applied_rate OPTIONS(description="최종 적용금리 (연 %, base_rate + spread_rate - pref_rate)"),
  contract_amt OPTIONS(description="최초 여신 약정 금액 (원)"),
  outstanding_amt OPTIONS(description="현재 여신 대출 잔액 (원)"),
  overdue_days OPTIONS(description="현재 원리금 연체 일수 (일)"),
  asset_classification OPTIONS(description="자산건전성 5단계 분류 (NORMAL, PRECAUTIONARY, SUBSTANDARD, DOUBTFUL, ESTIMATED_LOSS)"),
  rehab_priority_claim_yn OPTIONS(description="회생법·기촉법상 은행 우선변제권 인정 자산 여부 (Y/N)"),
  booked_provision_krw OPTIONS(description="현재 장부에 적립된 대손충당금 금액 (원)"),
  account_status OPTIONS(description="계좌 원장 상태 (ACTIVE 정상운용 vs WRITTEN_OFF_SPECIAL_CLAIM 대손상각 특수채권)")
)
OPTIONS(
  description="[Node: LoanContract] Spanner에서 실시간 연합 조회되는 기업여신 계약 원장이자 7개 정형 엔티티와 규정이 만나는 단일 중심 허브 노드"
)
AS
SELECT
  contract_id, customer_id, product_code, borrower_name, ksic_section_code,
  reg_dt, contract_dt, disburse_dt,
  base_rate, spread_rate, pref_rate, applied_rate,
  contract_amt, outstanding_amt, overdue_days,
  asset_classification, rehab_priority_claim_yn, booked_provision_krw, account_status
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_customer` (
  customer_id OPTIONS(description="기업 차주 고유 식별자 (PK, CUST_0001 ~ CUST_0100)"),
  borrower_name OPTIONS(description="차주 공식 법인명 (예: 별빛정밀(주), 에이펙스세미콘(주))"),
  corp_reg_no OPTIONS(description="법인등록번호"),
  ksic_section_code OPTIONS(description="한국표준산업분류 대분류 알파벳 코드 (감독규정 제29조 단서 F·G·H·L 판정 기준)"),
  ksic_detail_code OPTIONS(description="한국표준산업분류 세세분류 5자리 코드"),
  industry_name OPTIONS(description="영위 업종 한글 명칭"),
  credit_rating OPTIONS(description="당행 내부 기업신용등급 (예: AAA, A+, BBB+, BBB, BB-)"),
  tcb_tech_grade OPTIONS(description="기술신용평가기관(TCB) 기술등급 (예: T2, T3, T4, NONE)"),
  debt_ratio_pct OPTIONS(description="차주 최근 결산 부채비율 (%, 내규 제25조 신속심사 상한 250.0% 판정 기준)")
)
OPTIONS(
  description="[Node: Customer] 기업 차주의 산업분류(KSIC)·신용등급·기술등급·부채비율을 관리하는 BigQuery 마스터 노드"
)
AS
SELECT
  customer_id, borrower_name, corp_reg_no, ksic_section_code, ksic_detail_code,
  industry_name, credit_rating, tcb_tech_grade, debt_ratio_pct
FROM `{PROJECT}.{SRC_DS}.customers`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_financial_product` (
  product_code OPTIONS(description="여신 금융상품 고유 코드 (PK, PROD_TCB_WORKING, PROD_CORP_PRIME_WC, PROD_CONST_REALESTATE, PROD_RESTRUCTURED_DIP)"),
  product_name OPTIONS(description="여신 금융상품 한글 명칭"),
  loan_category OPTIONS(description="여신 대분류 코드 (CORPORATE_* 기업여신 여부 확인 및 가계여신 규정 배제 기준)"),
  target_segment OPTIONS(description="주요 가입 대상 기업 세그먼트"),
  base_rate_benchmark OPTIONS(description="연동 기준금리 지표 (KORIBOR_3M, BANK_DEBENTURE_1Y, COFIX_NEW)"),
  repayment_method OPTIONS(description="원리금 상환 방식"),
  max_maturity_months OPTIONS(description="최대 대출 만기 개월 수")
)
OPTIONS(
  description="[Node: FinancialProduct] 대출 상품의 여신유형(기업여신 여부)·타깃 세그먼트·기준금리 벤치마크를 정의하는 상품 마스터 노드"
)
AS
SELECT
  product_code, product_name, loan_category, target_segment,
  base_rate_benchmark, repayment_method, max_maturity_months
FROM `{PROJECT}.{SRC_DS}.financial_products`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_workout_history` (
  workout_id OPTIONS(description="워크아웃·채권재조정 이력 고유 번호 (PK)"),
  contract_id OPTIONS(description="대상 여신계약 번호 (FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="대상 차주 고객 번호 (FK -> Customer.customer_id)"),
  workout_start_dt OPTIONS(description="채권재조정·워크아웃 개시일자"),
  consecutive_normal_repay_months OPTIONS(description="채권재조정 후 연속 정상 원리금 상환 개월 수 (별표3 라목 6개월 이상 요건 기준)"),
  new_equity_paid_in_krw OPTIONS(description="유상증자·출자전환 등 신규 자본 확충 납입 금액 (원, 별표3 라목 상환능력 개선 기준)"),
  legal_proceeding_code OPTIONS(description="근거 법적 절차 코드 (CORP_RESTRUCT_ACT_WORKOUT 기촉법 워크아웃, REHAB_ACT_ART180_2_DIP 회생법 등)")
)
OPTIONS(
  description="[Node: WorkoutHistory] 채권재조정 여신의 연속 정상상환 개월 수·유상증자 금액·법적 구조조정 절차를 관리하는 이력 노드"
)
AS
SELECT
  workout_id, contract_id, customer_id, workout_start_dt,
  consecutive_normal_repay_months, new_equity_paid_in_krw, legal_proceeding_code
FROM `{PROJECT}.{SRC_DS}.workout_histories`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_collateral` (
  collateral_id OPTIONS(description="담보·보증서 고유 식별 번호 (PK)"),
  contract_id OPTIONS(description="피담보 여신계약 번호 (FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="담보 제공 차주 번호 (FK -> Customer.customer_id)"),
  collateral_type_code OPTIONS(description="담보 유형 코드 (CREDIT_GUARANTEE_CERT 신용보증서, REAL_ESTATE_TRUST_1ST 부동산신탁1순위)"),
  guarantee_agency_code OPTIONS(description="보증서 발급 기관 코드 (KODIT 신용보증기금, NONE 해당없음)"),
  guarantee_ratio_pct OPTIONS(description="보증기관 책임 보증비율 또는 담보인정비율 (%, 내규 제18조 85% 이상 요건 기준)"),
  appraised_collateral_krw OPTIONS(description="담보 감정평가액 또는 보증 인정 금액 (원)")
)
OPTIONS(
  description="[Node: Collateral] 여신계약에 설정된 신용보증기금(KODIT) 보증서·부동산 담보 유형과 보증비율(85% 기준 등)을 담는 Spanner 원장 노드"
)
AS
SELECT
  collateral_id, contract_id, customer_id, collateral_type_code,
  guarantee_agency_code, guarantee_ratio_pct, appraised_collateral_krw
FROM `{PROJECT}.{SRC_DS}.ont_collaterals`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_delinquency_event` (
  event_id OPTIONS(description="연체·상각 이벤트 고유 번호 (PK)"),
  contract_id OPTIONS(description="연체 발생 여신계약 번호 (FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="연체 차주 고객 번호 (FK -> Customer.customer_id)"),
  overdue_days OPTIONS(description="연체 경과 일수 (10일 이상 EWS, 30일 이상 공시연체, 90일 이상 고정이하 기준)"),
  overdue_principal_krw OPTIONS(description="연체 원금 또는 대손상각 특수채권 미회수 원금 잔액 (원)"),
  overdue_interest_krw OPTIONS(description="미수 연체 이자 금액 (원)"),
  write_off_yn OPTIONS(description="회계상 대손상각 특수채권 편입 여부 (Y: 공시 제외·EWS 포함 / N: 대차대조표 내 연체)")
)
OPTIONS(
  description="[Node: DelinquencyEvent] 여신계좌별 연체일수·연체원리금·대손상각 특수채권 편입 여부를 기록하는 Spanner 이벤트 노드"
)
AS
SELECT
  event_id, contract_id, customer_id, overdue_days,
  overdue_principal_krw, overdue_interest_krw, write_off_yn
FROM `{PROJECT}.{SRC_DS}.ont_delinquency_events`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_rate_cut_request` (
  request_id OPTIONS(description="금리인하요구권 신청 고유 번호 (PK)"),
  contract_id OPTIONS(description="신청 대상 여신계약 번호 (FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="신청 차주 고객 번호 (FK -> Customer.customer_id)"),
  request_dt OPTIONS(description="금리인하요구 신청 일자"),
  application_reason_code OPTIONS(description="신청 사유 코드 (PATENT_ACQUISITION_STANDALONE 단독특허 vs PATENT_AND_RATING_UPGRADE 특허+등급상승)"),
  patent_reg_no OPTIONS(description="제출된 특허권 등록번호"),
  credit_rating_before OPTIONS(description="금리인하 신청 직전 내부 신용등급"),
  credit_rating_after OPTIONS(description="금리인하 심사 시점 재평가 내부 신용등급"),
  yoy_revenue_growth_pct OPTIONS(description="전년 동기 대비 매출액 증가율 (%)"),
  review_status_code OPTIONS(description="심사 처리 결과 코드 (APPROVED 인하승인 vs REJECTED 거절)"),
  approved_cut_bp OPTIONS(description="승인된 금리인하 폭 (bp, 1bp = 0.01%p)")
)
OPTIONS(
  description="[Node: RateCutRequest] 차주의 금리인하요구 신청 사유(특허 취득 등)·신용등급 변동·심사 결과(승인/거절)를 기록하는 Spanner 노드"
)
AS
SELECT
  request_id, contract_id, customer_id, request_dt, application_reason_code,
  patent_reg_no, credit_rating_before, credit_rating_after,
  yoy_revenue_growth_pct, review_status_code, approved_cut_bp
FROM `{PROJECT}.{SRC_DS}.ont_rate_cut_requests`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_exception_approval` (
  approval_id OPTIONS(description="예외승인 결재 건 고유 번호 (PK)"),
  contract_id OPTIONS(description="결재 대상 여신계약 번호 (FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="결재 대상 차주 번호 (FK -> Customer.customer_id)"),
  approval_type_code OPTIONS(description="예외 결재 유형 코드 (EOD_DEFERRAL_AND_PRECAUTIONARY_RETENTION 등)"),
  approval_status OPTIONS(description="결재 최종 상태 (APPROVED 승인완료 vs REJECTED 반려)"),
  approver_role_code OPTIONS(description="전결 승인권자 직책 코드 (HQ_SENIOR_CREDIT_OFFICER 본부 여신심사역 등)"),
  approval_dt OPTIONS(description="예외승인 결재 완료 및 판단근거 문서화 일자")
)
OPTIONS(
  description="[Node: ExceptionApproval] 기한이익상실(EOD) 유예 및 채권재조정 건전성 예외분류에 대한 본부 여신심사역 결재·문서화 증적 노드"
)
AS
SELECT
  approval_id, contract_id, customer_id, approval_type_code,
  approval_status, approver_role_code, approval_dt
FROM `{PROJECT}.{SRC_DS}.ont_exception_approvals`;


-- ============================================================================
-- 2. 15 EDGE VIEWS IN `starlight_bank_ontology` (모든 뷰·컬럼 직관적 한 줄 설명 포함)
-- ============================================================================

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_borrowed_by` (
  contract_id OPTIONS(description="여신계약 고유 번호 (Source FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="차주 고객 고유 번호 (Destination FK -> Customer.customer_id)")
)
OPTIONS(description="[Edge: BORROWED_BY] 여신계약이 어느 기업 차주에게 실행되었는지 연결하는 엣지")
AS SELECT contract_id, customer_id FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_of_product` (
  contract_id OPTIONS(description="여신계약 고유 번호 (Source FK -> LoanContract.contract_id)"),
  product_code OPTIONS(description="가입 여신상품 코드 (Destination FK -> FinancialProduct.product_code)")
)
OPTIONS(description="[Edge: OF_PRODUCT] 여신계약이 어느 여신 금융상품으로 체결되었는지 연결하는 엣지")
AS SELECT contract_id, product_code FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_collateral` (
  contract_id OPTIONS(description="피담보 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  collateral_id OPTIONS(description="담보·보증서 고유 번호 (Destination FK -> Collateral.collateral_id)")
)
OPTIONS(description="[Edge: HAS_COLLATERAL] 여신계약에 설정된 담보 및 신용보증기금 보증서를 연결하는 엣지")
AS SELECT contract_id, collateral_id FROM `{PROJECT}.{SRC_DS}.ont_collaterals`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_delinquency` (
  contract_id OPTIONS(description="연체 발생 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  event_id OPTIONS(description="연체·상각 이벤트 고유 번호 (Destination FK -> DelinquencyEvent.event_id)")
)
OPTIONS(description="[Edge: HAS_DELINQUENCY] 여신계약에서 발생한 연체 및 대손상각 특수채권 이벤트를 연결하는 엣지")
AS SELECT contract_id, event_id FROM `{PROJECT}.{SRC_DS}.ont_delinquency_events`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_rate_cut_request` (
  contract_id OPTIONS(description="신청 대상 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  request_id OPTIONS(description="금리인하요구 신청 고유 번호 (Destination FK -> RateCutRequest.request_id)")
)
OPTIONS(description="[Edge: HAS_RATE_CUT_REQUEST] 여신계약에 대해 접수된 금리인하요구권 신청·심사 내역을 연결하는 엣지")
AS SELECT contract_id, request_id FROM `{PROJECT}.{SRC_DS}.ont_rate_cut_requests`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_exception_approval` (
  contract_id OPTIONS(description="결재 대상 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  approval_id OPTIONS(description="예외승인 결재 고유 번호 (Destination FK -> ExceptionApproval.approval_id)")
)
OPTIONS(description="[Edge: HAS_EXCEPTION_APPROVAL] 여신계약의 기한이익상실 유예 등 본부 예외승인 결재 내역을 연결하는 엣지")
AS SELECT contract_id, approval_id FROM `{PROJECT}.{SRC_DS}.ont_exception_approvals`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_workout_history` (
  contract_id OPTIONS(description="대상 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  workout_id OPTIONS(description="워크아웃·채권재조정 이력 고유 번호 (Destination FK -> WorkoutHistory.workout_id)")
)
OPTIONS(description="[Edge: HAS_WORKOUT_HISTORY] 여신계약의 채권재조정·워크아웃·회생절차 상환 및 증자 이력을 연결하는 엣지")
AS SELECT contract_id, workout_id FROM `{PROJECT}.{SRC_DS}.workout_histories`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_scopes_portfolio` (
  edge_id OPTIONS(description="부서맥락-여신계약 포트폴리오 관할 스코프 엣지 고유 식별자 (PK)"),
  context_id OPTIONS(description="관할 부서·업무목적 맥락 식별자 (Source FK -> BusinessContext.context_id)"),
  contract_id OPTIONS(description="관할 대상 여신계약 고유 번호 (Destination FK -> LoanContract.contract_id)"),
  portfolio_scope_rule OPTIONS(description="적용된 포트폴리오 편입 기준 (ON_BS_CORPORATE_PORTFOLIO 대차대조표 내 여신 vs EWS_INCLUDING_WRITTEN_OFF 상각특수채권 포함)")
)
OPTIONS(description="[Edge: SCOPES_PORTFOLIO] 부서·업무목적 맥락(BusinessContext)이 산출·심사·감리 시 관할하는 실시간 여신계약(LoanContract) 포트폴리오 스코프를 동적 연결하는 온톨로지 내부 엣지")
AS
SELECT
  CONCAT('SCOPE_', ctx.context_id, '_', l.contract_id) AS edge_id,
  ctx.context_id,
  l.contract_id,
  CASE
    WHEN l.account_status = 'WRITTEN_OFF_SPECIAL_CLAIM' THEN 'EWS_INCLUDING_WRITTEN_OFF'
    ELSE 'ON_BS_CORPORATE_PORTFOLIO'
  END AS portfolio_scope_rule
FROM `{PROJECT}.{ONT_DS}.ctx_business_contexts` ctx
CROSS JOIN `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
   OR ctx.context_id IN ('CREDIT_MGMT', 'COMPLIANCE');

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_invokes_provision` (
  edge_id OPTIONS(description="부서맥락-용어-조문 호출 엣지 고유 식별자 (PK)"),
  context_id OPTIONS(description="호출 주체 부서·업무목적 맥락 식별자 (Source FK -> BusinessContext.context_id)"),
  term_key OPTIONS(description="Dataplex Business Glossary 표준 금융 용어 식별자 (예: delinquency-rate, provision-criteria, loan-rate)"),
  glossary_term_uri OPTIONS(description="Dataplex Knowledge Catalog Business Glossary 용어 리소스 경로"),
  provision_slot_id OPTIONS(description="호출 대상 법령·내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  invocation_reason OPTIONS(description="해당 부서 맥락과 금융 용어 조합에서 이 조문을 호출하는 비즈니스 이유 한 줄 설명")
)
OPTIONS(description="[Edge: INVOKES_PROVISION] 부서·업무목적 맥락(BusinessContext)과 KC Glossary 용어(term_key) 조합에 따라 호출할 법령·내규 조문을 분기하는 브리지 엣지")
AS SELECT edge_id, context_id, term_key, glossary_term_uri, provision_slot_id, invocation_reason
FROM `{PROJECT}.{ONT_DS}.edge_invokes_provision`;

-- Pure Real-Time SQL View (Zero Ground-Truth Leakage): connects jurisdictional scope only
CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_governed_by_criteria` (
  edge_id OPTIONS(description="여신계약-조문 관할 연결 실시간 뷰 엣지 고유 식별자 (PK)"),
  contract_id OPTIONS(description="적용 대상 여신계약 고유 번호 (Source FK -> LoanContract.contract_id)"),
  provision_slot_id OPTIONS(description="심사 관할 법령·내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  binding_reason OPTIONS(description="해당 여신계약이 이 조문의 심사 관할 범위에 포함되는 구조적 사유 (정답 미유출)")
)
OPTIONS(
  description="[Edge: GOVERNED_BY_CRITERIA] 실시간 Spanner 여신계약의 구조적 범위(기업여신·연체·워크아웃·상품유형)에 따라 심사 관할 조문을 동적 연결하는 순수 SQL View 엣지 (정답 미유출)"
)
AS
SELECT
  CONCAT('GOV_ACT_27_', l.contract_id) AS edge_id,
  l.contract_id,
  'regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027' AS provision_slot_id,
  '은행업감독규정 제27조 자산건전성 5단계 분류 심사 관할 여신' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_ACT_29_', l.contract_id) AS edge_id,
  l.contract_id,
  'regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029' AS provision_slot_id,
  '은행업감독규정 제29조 대손충당금 최소적립기준 심사 관할 여신 (단서 해당 여부는 원장 컬럼 실시간 대조 필요)' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_ACT_21_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates' AS provision_slot_id,
  '별빛은행 내규 제21조 대출 3대 기준일자(등록일·체결일·실행일) 구분 적용 대상 여신' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_ACT_22_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc' AS provision_slot_id,
  '별빛은행 내규 제22조 대출금리 산식(A+B-C) 및 비교공시 기준 적용 대상 여신' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_WO_27_', l.contract_id) AS edge_id,
  l.contract_id,
  'regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027' AS provision_slot_id,
  '은행업감독규정 제27조제4항 대손상각 특수채권 사후관리 관할 계좌' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status = 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_WO_14_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency' AS provision_slot_id,
  '별빛은행 내규 제14조 대손상각 특수채권의 부서별 연체율 산입 여부 심사 대상 계좌' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.account_status = 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_WK_RA_', w.contract_id) AS edge_id,
  w.contract_id,
  'regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption' AS provision_slot_id,
  '채권재조정 이력 보유 여신 — 별표3 제3호 라목 고정이하 분류 제외 특례 심사 대상 (요건 충족 여부는 원장 대조 필요)' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.workout_histories` w
UNION ALL
SELECT
  CONCAT('GOV_OD_16_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule' AS provision_slot_id,
  '원리금 연체 발생 여신 — 내규 제16조 기한이익상실(EOD) 예정 통지 기준 심사 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.overdue_days > 0 AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_OD_18_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver' AS provision_slot_id,
  '원리금 연체 발생 여신 — 내규 제18조 기한이익상실 유예 특례 심사 대상 (요건 충족 여부는 담보·워크아웃·결재 원장 대조 필요)' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.overdue_days > 0 AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_TCB_25_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion' AS provision_slot_id,
  'TCB 기술혁신 운전자금 상품 — 내규 제25조제1항 우대금리 전결 상한 및 부채비율 상한 심사 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_loan_contracts` l
WHERE l.product_code = 'PROD_TCB_WORKING';

-- Pure Real-Time SQL View over Spanner `ont_rate_cut_requests`
CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_evaluated_under_provision` (
  edge_id OPTIONS(description="금리인하요구-조문 심사 실시간 뷰 엣지 고유 식별자 (PK)"),
  request_id OPTIONS(description="금리인하요구 신청 고유 번호 (Source FK -> RateCutRequest.request_id)"),
  provision_slot_id OPTIONS(description="심사 기준 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  evaluation_reason OPTIONS(description="금리인하요구 심사 시 해당 조문을 적용하는 구조적 사유")
)
OPTIONS(
  description="[Edge: EVALUATED_UNDER_PROVISION] 실시간 Spanner 금리인하요구 신청 건을 심사 관할 모범규준 및 당행 내규 조문과 동적 연결하는 순수 SQL View 엣지"
)
AS
SELECT
  CONCAT('EVAL_KFB_', r.request_id) AS edge_id,
  r.request_id,
  'regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion' AS provision_slot_id,
  '대출금리 산정 개선방안 Ⅱ-1-나 (금리인하요구권 심사 재량 및 거절 사유 통보 의무) 심사 관할' AS evaluation_reason
FROM `{PROJECT}.{SRC_DS}.ont_rate_cut_requests` r
UNION ALL
SELECT
  CONCAT('EVAL_INT25_', r.request_id) AS edge_id,
  r.request_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion' AS provision_slot_id,
  '별빛은행 내규 제25조제2항 (특허권 취득 사유 금리인하요구 심사 기준) 심사 관할' AS evaluation_reason
FROM `{PROJECT}.{SRC_DS}.ont_rate_cut_requests` r;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_part_of_document` (
  provision_slot_id OPTIONS(description="개별 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  doc_id OPTIONS(description="소속 원본 법령·내규 문서 식별자 (Destination FK -> SourceDocument.doc_id)")
)
OPTIONS(description="[Edge: PART_OF_DOCUMENT] 174개 개별 조문이 어느 원본 법령·내규 문서(10종)에 속하는지 연결하는 엣지")
AS SELECT provision_slot_id, doc_id FROM `{PROJECT}.{ONT_DS}.lex_provisions`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_exception_proviso` (
  edge_id OPTIONS(description="본칙-단서/특례 조문 연결 엣지 고유 식별자 (PK)"),
  base_slot_id OPTIONS(description="원칙(본칙) 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  proviso_slot_id OPTIONS(description="단서·예외·특례 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  exception_condition OPTIONS(description="본칙에서 단서·특례로 분기되는 예외 성립 요건 한 줄 요약")
)
OPTIONS(description="[Edge: HAS_EXCEPTION_PROVISO] 원칙 조문(본칙)에서 단서·예외·특례 조문으로 분기하는 법령 내부 엣지")
AS SELECT edge_id, base_slot_id, proviso_slot_id, exception_condition FROM `{PROJECT}.{ONT_DS}.edge_has_exception_proviso`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_delegates_to_internal` (
  edge_id OPTIONS(description="상위법령-당행내규 위임 엣지 고유 식별자 (PK)"),
  external_slot_id OPTIONS(description="상위 감독규정·모범규준 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  internal_slot_id OPTIONS(description="위임받아 구체화한 별빛은행 내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  delegation_scope OPTIONS(description="상위 규정이 당행 내규에 위임하거나 구체화한 세부 운영 기준 설명")
)
OPTIONS(description="[Edge: DELEGATES_TO_INTERNAL] 상위 감독규정·모범규준이 별빛은행 자체 내규 조문으로 세부 기준을 위임·구체화하는 엣지")
AS SELECT edge_id, external_slot_id, internal_slot_id, delegation_scope FROM `{PROJECT}.{ONT_DS}.edge_delegates_to_internal`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_conflicts_by_sector` (
  edge_id OPTIONS(description="업권·여신유형 충돌 대조 엣지 고유 식별자 (PK)"),
  bank_slot_id OPTIONS(description="시중은행 기업여신 정식 적용 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  distractor_slot_id OPTIONS(description="혼입 차단 대상 타업권(저축은행)·타세그먼트 교란 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  conflict_warning OPTIONS(description="두 조문을 혼동하면 안 되는 업권·세그먼트 차이 경고 설명")
)
OPTIONS(description="[Edge: CONFLICTS_BY_SECTOR] 시중은행 기업여신 규정과 상호저축은행(타업권)·가계여신 규정 간의 오적용 방지 대조 엣지")
AS SELECT edge_id, bank_slot_id, distractor_slot_id, conflict_warning FROM `{PROJECT}.{ONT_DS}.edge_conflicts_by_sector`;


-- ============================================================================
-- 3. CREATE OR REPLACE PROPERTY GRAPH `starlight_bank_ontology.finance_graph`
-- ============================================================================

CREATE OR REPLACE PROPERTY GRAPH `{PROJECT}.{ONT_DS}.{GRAPH_NAME}`
  NODE TABLES (
    `{PROJECT}.{ONT_DS}.v_node_business_context`
      KEY (context_id)
      LABEL BusinessContext,
    `{PROJECT}.{ONT_DS}.v_node_source_document`
      KEY (doc_id)
      LABEL SourceDocument,
    `{PROJECT}.{ONT_DS}.v_node_provision`
      KEY (provision_slot_id)
      LABEL Provision,
    `{PROJECT}.{ONT_DS}.v_node_loan_contract`
      KEY (contract_id)
      LABEL LoanContract,
    `{PROJECT}.{ONT_DS}.v_node_customer`
      KEY (customer_id)
      LABEL Customer,
    `{PROJECT}.{ONT_DS}.v_node_financial_product`
      KEY (product_code)
      LABEL FinancialProduct,
    `{PROJECT}.{ONT_DS}.v_node_workout_history`
      KEY (workout_id)
      LABEL WorkoutHistory,
    `{PROJECT}.{ONT_DS}.v_node_collateral`
      KEY (collateral_id)
      LABEL Collateral,
    `{PROJECT}.{ONT_DS}.v_node_delinquency_event`
      KEY (event_id)
      LABEL DelinquencyEvent,
    `{PROJECT}.{ONT_DS}.v_node_rate_cut_request`
      KEY (request_id)
      LABEL RateCutRequest,
    `{PROJECT}.{ONT_DS}.v_node_exception_approval`
      KEY (approval_id)
      LABEL ExceptionApproval
  )
  EDGE TABLES (
    `{PROJECT}.{ONT_DS}.v_edge_borrowed_by`
      KEY (contract_id, customer_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (customer_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_customer` (customer_id)
      LABEL BORROWED_BY,
    `{PROJECT}.{ONT_DS}.v_edge_of_product`
      KEY (contract_id, product_code)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (product_code) REFERENCES `{PROJECT}.{ONT_DS}.v_node_financial_product` (product_code)
      LABEL OF_PRODUCT,
    `{PROJECT}.{ONT_DS}.v_edge_has_collateral`
      KEY (contract_id, collateral_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (collateral_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_collateral` (collateral_id)
      LABEL HAS_COLLATERAL,
    `{PROJECT}.{ONT_DS}.v_edge_has_delinquency`
      KEY (contract_id, event_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (event_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_delinquency_event` (event_id)
      LABEL HAS_DELINQUENCY,
    `{PROJECT}.{ONT_DS}.v_edge_has_rate_cut_request`
      KEY (contract_id, request_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (request_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_rate_cut_request` (request_id)
      LABEL HAS_RATE_CUT_REQUEST,
    `{PROJECT}.{ONT_DS}.v_edge_has_exception_approval`
      KEY (contract_id, approval_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (approval_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_exception_approval` (approval_id)
      LABEL HAS_EXCEPTION_APPROVAL,
    `{PROJECT}.{ONT_DS}.v_edge_has_workout_history`
      KEY (contract_id, workout_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (workout_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_workout_history` (workout_id)
      LABEL HAS_WORKOUT_HISTORY,
    `{PROJECT}.{ONT_DS}.v_edge_scopes_portfolio`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_business_context` (context_id)
      DESTINATION KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      LABEL SCOPES_PORTFOLIO,
    `{PROJECT}.{ONT_DS}.v_edge_invokes_provision`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_business_context` (context_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL INVOKES_PROVISION,
    `{PROJECT}.{ONT_DS}.v_edge_governed_by_criteria`
      KEY (edge_id)
      SOURCE KEY (contract_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_loan_contract` (contract_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL GOVERNED_BY_CRITERIA,
    `{PROJECT}.{ONT_DS}.v_edge_evaluated_under_provision`
      KEY (edge_id)
      SOURCE KEY (request_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_rate_cut_request` (request_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL EVALUATED_UNDER_PROVISION,
    `{PROJECT}.{ONT_DS}.v_edge_part_of_document`
      KEY (provision_slot_id, doc_id)
      SOURCE KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (doc_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_source_document` (doc_id)
      LABEL PART_OF_DOCUMENT,
    `{PROJECT}.{ONT_DS}.v_edge_has_exception_proviso`
      KEY (edge_id)
      SOURCE KEY (base_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (proviso_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL HAS_EXCEPTION_PROVISO,
    `{PROJECT}.{ONT_DS}.v_edge_delegates_to_internal`
      KEY (edge_id)
      SOURCE KEY (external_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (internal_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL DELEGATES_TO_INTERNAL,
    `{PROJECT}.{ONT_DS}.v_edge_conflicts_by_sector`
      KEY (edge_id)
      SOURCE KEY (bank_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (distractor_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL CONFLICTS_BY_SECTOR
  );
"""
    os.makedirs(os.path.dirname(GRAPH_SQL_PATH), exist_ok=True)
    with open(GRAPH_SQL_PATH, "w", encoding="utf-8") as f:
        f.write(sql_statements.strip() + "\n")
    print(f"[SQL] Wrote DDL to {GRAPH_SQL_PATH}", flush=True)

    run_sql(client, sql_statements, "11 Node Views + 15 Edge Views + Property Graph `finance_graph`")
    print(f"[BQ] Successfully deployed `{PROJECT}.{ONT_DS}.{GRAPH_NAME}`!", flush=True)


def setup_dataplex_glossary(l1_cfg: dict, token: str) -> None:
    parent = f"projects/{PROJECT}/locations/{LOCATION}"
    glossary_name = f"{parent}/glossaries/{GLOSSARY_ID}"
    glossary_url = f"https://dataplex.googleapis.com/v1/{glossary_name}"

    g_payload = {
        "displayName": "별빛은행 기업여신·리스크·준법감시 표준 금융 용어집",
        "description": "부서·업무목적 맥락(BusinessContext)에 따라 해석과 적용 조문(Provision)이 분기되는 7대 핵심 금융 도메인 용어집 (INVOKES_PROVISION.term_key와 1:1 매핑)",
        "labels": {"domain": "finance-ontology", "bank": "starlight-bank"},
    }
    code, _ = dataplex_request("GET", glossary_url, token, ignore_status=(404,))
    if code == 404:
        print(f"[KC Glossary] Creating Glossary `{GLOSSARY_ID}`...", flush=True)
        create_url = f"https://dataplex.googleapis.com/v1/{parent}/glossaries?glossaryId={GLOSSARY_ID}"
        _, op = dataplex_request("POST", create_url, token, g_payload)
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)
    else:
        print(f"[KC Glossary] Updating Glossary `{GLOSSARY_ID}`...", flush=True)
        patch_url = f"{glossary_url}?updateMask=displayName,description,labels"
        _, op = dataplex_request("PATCH", patch_url, token, g_payload)
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)

    for term in l1_cfg.get("glossary_terms", []):
        tid = term["term_key"]
        term_name = f"{glossary_name}/terms/{tid}"
        term_url = f"https://dataplex.googleapis.com/v1/{term_name}"
        syns = ", ".join(term.get("synonyms", []))
        t_payload = {
            "displayName": term["display_name"],
            "description": f"{term['description']} [동의어·약칭: {syns}]",
            "parent": glossary_name,
            "labels": {"term_key": tid, "edge_binding": "invokes-provision"},
        }
        t_code, _ = dataplex_request("GET", term_url, token, ignore_status=(404,))
        if t_code == 404:
            create_t_url = f"https://dataplex.googleapis.com/v1/{glossary_name}/terms?termId={tid}"
            dataplex_request("POST", create_t_url, token, t_payload)
            print(f"  + Created Glossary Term `{tid}` ({term['display_name']})", flush=True)
        else:
            patch_t_url = f"{term_url}?updateMask=displayName,description,labels"
            dataplex_request("PATCH", patch_t_url, token, t_payload)
            print(f"  ~ Updated Glossary Term `{tid}` ({term['display_name']})", flush=True)


def setup_and_attach_kc_anchor_aspect(l1_cfg: dict, token: str) -> None:
    parent = f"projects/{PROJECT}/locations/{LOCATION}"
    aspect_type_name = f"{parent}/aspectTypes/{ANCHOR_ASPECT_ID}"
    aspect_type_url = f"https://dataplex.googleapis.com/v1/{aspect_type_name}"

    aspect_type_body = {
        "displayName": "Ontology Class Anchors & Planner Config",
        "description": "별빛은행 금융 온톨로지 그래프(finance_graph)의 11개 노드 클래스별 앵커 규칙·GQL MATCH 템플릿·15개 엣지·KC Glossary 매핑·프로퍼티 한 줄 설명을 정의하는 에이전트 플래너 설정 Aspect (l1.yaml SSOT 자동 생성)",
        "metadataTemplate": {
            "name": "OntologyClassAnchors",
            "type": "record",
            "annotations": {
                "displayName": "Ontology Class Anchors (ADK Agent Planner Config)",
                "description": "ADK 에이전트 기동 시 lookup_entry(view=CUSTOM)로 로드하여 GQL MATCH 바인딩 및 플래너 시스템 프롬프트에 주입하는 클래스별 앵커 설정",
            },
            "recordFields": [
                {
                    "name": "graph_id",
                    "type": "string",
                    "index": 1,
                    "annotations": {
                        "displayName": "Property Graph ID",
                        "description": "BigQuery Property Graph 전체 경로 (starlight_bank_ontology.finance_graph)",
                    },
                },
                {
                    "name": "ontology_version",
                    "type": "string",
                    "index": 2,
                    "annotations": {
                        "displayName": "Ontology Version",
                        "description": "ontology/l1.yaml 선언적 매니페스트 버전",
                    },
                },
                {
                    "name": "alias_table_fqn",
                    "type": "string",
                    "index": 3,
                    "annotations": {
                        "displayName": "Entity Alias Table FQN",
                        "description": "최장일치(Longest-Match-First) 기반 자연어 별칭->정규화 ID 변환 테이블 경로",
                    },
                },
                {
                    "name": "kc_glossary_resource",
                    "type": "string",
                    "index": 4,
                    "annotations": {
                        "displayName": "Dataplex Business Glossary Resource",
                        "description": "INVOKES_PROVISION.term_key와 1:1 매핑되는 Dataplex Business Glossary 리소스 경로",
                    },
                },
                {
                    "name": "governance_rule",
                    "type": "string",
                    "index": 5,
                    "annotations": {
                        "displayName": "KC Governance & Superseded Chain Rule",
                        "description": "Provision 노드 도달 시 KC okf Aspect 유효성 검증 및 superseded_by 체인 추적 원칙",
                    },
                },
                {
                    "name": "class_anchors",
                    "type": "array",
                    "index": 6,
                    "annotations": {
                        "displayName": "11 Node Class Anchors",
                        "description": "11개 노드 클래스별 한 줄 설명, PK, 앵커 유형, GQL MATCH 템플릿 및 플래너 지침 배열",
                    },
                    "arrayItems": {
                        "name": "class_anchor",
                        "type": "record",
                        "recordFields": [
                            {"name": "class_label", "type": "string", "index": 1, "annotations": {"displayName": "Class Label", "description": "그래프 노드 라벨명"}},
                            {"name": "layer", "type": "string", "index": 2, "annotations": {"displayName": "Ontology Layer", "description": "온톨로지 계층 (LDM / CTX / LEX)"}},
                            {"name": "korean_name", "type": "string", "index": 3, "annotations": {"displayName": "Korean Name", "description": "클래스 한글 명칭"}},
                            {"name": "description", "type": "string", "index": 4, "annotations": {"displayName": "Class Description", "description": "클래스 역할 한 줄 한글 설명"}},
                            {"name": "source_plane", "type": "string", "index": 5, "annotations": {"displayName": "Source Plane", "description": "물리 원천 플레인 구분"}},
                            {"name": "graph_view", "type": "string", "index": 6, "annotations": {"displayName": "Graph View", "description": "매핑된 BigQuery 그래프 뷰 이름"}},
                            {"name": "primary_key", "type": "string", "index": 7, "annotations": {"displayName": "Primary Key", "description": "노드 기본키 컬럼명"}},
                            {"name": "anchor_type", "type": "string", "index": 8, "annotations": {"displayName": "Anchor Type", "description": "플래너 앵커 바인딩 유형"}},
                            {"name": "alias_group", "type": "string", "index": 9, "annotations": {"displayName": "Alias Group", "description": "별칭 테이블 매핑 그룹명"}},
                            {"name": "match_bind_key", "type": "string", "index": 10, "annotations": {"displayName": "MATCH Bind Key", "description": "GQL MATCH 절 내부 바인딩 프로퍼티 키"}},
                            {"name": "gql_match_template", "type": "string", "index": 11, "annotations": {"displayName": "GQL MATCH Template", "description": "GQL MATCH 인라인 바인딩 패턴 템플릿"}},
                            {"name": "planner_instruction", "type": "string", "index": 12, "annotations": {"displayName": "Planner Instruction", "description": "ADK 에이전트 플래너용 클래스 탐색 지침"}},
                            {"name": "outgoing_edges_csv", "type": "string", "index": 13, "annotations": {"displayName": "Outgoing Edges", "description": "연결 가능한 주요 엣지 목록"}},
                            {"name": "properties_summary", "type": "string", "index": 14, "annotations": {"displayName": "Properties & 1-Line Descriptions", "description": "노드 프로퍼티별 한 줄 한글 설명 요약"}},
                        ],
                    },
                },
                {
                    "name": "edge_definitions_json",
                    "type": "string",
                    "index": 7,
                    "annotations": {
                        "displayName": "15 Edge Definitions JSON",
                        "description": "15개 엣지 라벨·소스·타깃·한 줄 설명 JSON",
                    },
                },
                {
                    "name": "glossary_terms_json",
                    "type": "string",
                    "index": 8,
                    "annotations": {
                        "displayName": "7 Glossary Terms JSON",
                        "description": "7개 Dataplex Glossary 표준 용어(term_key) 및 동의어 매핑 JSON",
                    },
                },
            ],
        },
    }

    code, _ = dataplex_request("GET", aspect_type_url, token, ignore_status=(404,))
    if code == 404:
        print(f"[KC AspectType] Creating `{ANCHOR_ASPECT_ID}`...", flush=True)
        create_url = f"https://dataplex.googleapis.com/v1/{parent}/aspectTypes?aspectTypeId={ANCHOR_ASPECT_ID}"
        _, op = dataplex_request("POST", create_url, token, aspect_type_body)
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)
    else:
        print(f"[KC AspectType] Updating `{ANCHOR_ASPECT_ID}`...", flush=True)
        patch_url = f"{aspect_type_url}?updateMask=displayName,description,metadataTemplate"
        _, op = dataplex_request("PATCH", patch_url, token, aspect_type_body)
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)

    # Compile Aspect payload directly from `ontology/l1.yaml` (SSOT)
    class_anchors_list = []
    for nc in l1_cfg["node_classes"]:
        acfg = nc["kc_anchor_config"]
        props_str = " | ".join(
            f"{p['name']}({p['type']}): {p['description']}" for p in nc.get("properties", [])
        )
        class_anchors_list.append({
            "class_label": nc["class_label"],
            "layer": nc["layer"],
            "korean_name": nc["korean_name"],
            "description": nc["description"],
            "source_plane": nc["source_plane"],
            "graph_view": nc["graph_view"],
            "primary_key": nc["primary_key"],
            "anchor_type": acfg["anchor_type"],
            "alias_group": acfg["alias_group"],
            "match_bind_key": acfg["match_bind_key"],
            "gql_match_template": acfg["gql_match_template"],
            "planner_instruction": acfg["planner_instruction"],
            "outgoing_edges_csv": ", ".join(acfg.get("outgoing_edges", [])),
            "properties_summary": props_str,
        })

    aspect_key = f"{PROJECT_NUMBER}.{LOCATION}.{ANCHOR_ASPECT_ID}"
    aspect_data = {
        "graph_id": f"{PROJECT}.{ONT_DS}.{GRAPH_NAME}",
        "ontology_version": str(l1_cfg["meta"]["version"]),
        "alias_table_fqn": f"{PROJECT}.{ONT_DS}.ont_entity_aliases",
        "kc_glossary_resource": f"projects/{PROJECT}/locations/{LOCATION}/glossaries/{GLOSSARY_ID}",
        "governance_rule": (
            "Single Source of Governance: BigQuery Provision 노드는 불변 provision_slot_id와 kc_entry_id만 보유하며, "
            "문서 유효성(status∈{'stable','verified'} vs 'deprecated')과 대체 문서 체인(superseded_by)은 오직 Dataplex Knowledge Catalog의 "
            "okf Aspect에서만 실시간 검증합니다 (최대 3홉 추적, 유효 대체문서 부재 시 판정 즉시 차단)."
        ),
        "class_anchors": class_anchors_list,
        "edge_definitions_json": json.dumps(l1_cfg.get("edge_definitions", []), ensure_ascii=False),
        "glossary_terms_json": json.dumps(l1_cfg.get("glossary_terms", []), ensure_ascii=False),
    }

    target_entries = [
        f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT}/datasets/{ONT_DS}/propertyGraphs/{GRAPH_NAME}",
        f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT}/datasets/{ONT_DS}",
    ]
    for entry_path in target_entries:
        patch_entry_url = (
            f"https://dataplex.googleapis.com/v1/{entry_path}"
            f"?updateMask=aspects&aspectKeys={aspect_key}"
        )
        body = {
            "name": entry_path,
            "aspects": {
                aspect_key: {
                    "aspectType": aspect_type_name,
                    "data": aspect_data,
                }
            },
        }
        dataplex_request("PATCH", patch_entry_url, token, body)
        print(f"[KC Entry] Attached `{aspect_key}` to `{entry_path.split('/entries/')[-1]}`", flush=True)


def main() -> None:
    with open(L1_YAML, "r", encoding="utf-8") as f:
        l1_cfg = yaml.safe_load(f)

    client = get_bq_client()
    build_lex_and_ctx_data(client, l1_cfg)
    build_views_and_property_graph(client)

    token = get_gcloud_token()
    setup_dataplex_glossary(l1_cfg, token)
    setup_and_attach_kc_anchor_aspect(l1_cfg, token)
    print("[DONE] All BigQuery Graph Views, Property Graph, Dataplex Glossary, and KC Class Anchor Aspect are live!", flush=True)


if __name__ == "__main__":
    main()
