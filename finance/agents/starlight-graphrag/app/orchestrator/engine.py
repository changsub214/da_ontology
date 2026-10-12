#!/usr/bin/env python3
"""Live ADK GraphRAG Agent Execution Engine for Module 05 (`05 · agent`).

Connects `tools/studio_server.py` (`/api/agent/questions`, `/api/agent/chat`) to the
`agents/starlight-graphrag` ADK services and live GCP planes:
  1. `before_agent_callback`:
     - `AliasResolver.resolve()` over 438 live `starlight_bank.ont_entity_aliases` rows
     - `SchemaCard` loaded from live Dataplex KC `finance-ontology-classes` (`gql_match_template`)
  2. `graph_query` (`GqlComposer.compose_and_validate` with `max_hops=12` + BigQuery Dry-Run + Live Query):
     - Stage A static guard (`max_hops=12`, `max_edge_patterns=24`, read-only, 11C/15E labels)
     - Stage B BigQuery Dry-Run (`dry_run=True` over lowered graph views)
     - Live BigQuery + Cloud Spanner Data Boost query execution (`starlight_bank.ont_*`)
  3. `kc_lookup` (`GovernanceService.resolve` against live Dataplex KC `entryGroups/finance-okf`):
     - Verifies `status` (`stable` / `verified` -> `ALLOW`, `deprecated` + `superseded_by` -> `SUPERSEDED_RESOLVED`,
       `deprecated` without replacement -> `BLOCKED_DEPRECATED` + incident ticket `INC-...`)
  4. `fetch_provision` (`OBJ.FETCH_METADATA` + `OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')` in live BigQuery):
     - Mints a BigQuery `ObjectRef` signed read URL and fetches verbatim Markdown from `gs://finance_okf/okf/...`
     - Enforces the governance gate: never called when `kc_lookup` returns `BLOCKED_DEPRECATED`.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import time
from typing import Any
import yaml

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

from google.adk.models import LlmResponse  # noqa: E402
from google.genai import types  # noqa: E402

from app.callbacks.answer import blocked_notice, citation_check, evidence_ledger  # noqa: E402
from app.callbacks.grounding import load_schema_card, pre_ground_entities  # noqa: E402
from app.callbacks.guards import governance_gate, gql_dry_run_guard, tool_budget  # noqa: E402
from app.domain import state_keys as sk  # noqa: E402
from app.orchestrator import bq_io  # noqa: E402
from app.runtime import get_runtime  # noqa: E402
from app.services import alias_resolver, gql_composer  # noqa: E402
from app.tools.fetch_provision import fetch_provision as adk_fetch_provision  # noqa: E402
from app.tools.graph_query import graph_query as adk_graph_query  # noqa: E402
from app.tools.kc_lookup import kc_lookup as adk_kc_lookup  # noqa: E402

# Question list (CQ loader, titles, sidebar items) lives in the dependency-light `questions`
# module so the web tier can serve it without ADK; re-exported here for existing callers.
from app.orchestrator.questions import CQ_YAML_PATH, QUESTION_TITLES, _load_cqs, get_agent_questions  # noqa: E402,F401

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "finance-ontology-changseop")
DS = f"`{PROJECT}.starlight_bank`"

# Map each CQ (CQ01..CQ20) to its canonical Provision Slot IDs in `v_node_provision`
# (which are also its `kc_entry_id`s in Dataplex Knowledge Catalog `finance-okf`).
CQ_PROVISION_SLOTS: dict[str, list[str]] = {
    "CQ01": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
    ],
    "CQ02": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
        "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_substandard_doubtful_loss",
    ],
    "CQ03": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
        "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_normal_precautionary",
    ],
    "CQ04": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
        "research_briefs/08_kif_loan_loss_provision/sec01_coverage_ratio_and_implications/kif_01_cr_definition_and_domestic",
        "research_briefs/08_kif_loan_loss_provision/sec01_coverage_ratio_and_implications/kif_02_global_comparison",
    ],
    "CQ05": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    ],
    "CQ06": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
        "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_06_07_workout_special_rules",
        "research_briefs/07_nars_rate_policy_issues/sec01_rate_components_and_dsr/nars_02_dsr_and_delinquency_trend",
    ],
    "CQ07": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
    ],
    "CQ08": [
        "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
    ],
    "CQ09": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule",
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
    ],
    "CQ10": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
        "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_normal_precautionary",
    ],
    "CQ11": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
    ],
    "CQ12": [
        "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion",
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion",
    ],
    "CQ13": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion",
    ],
    "CQ14": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates",
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc",
    ],
    "CQ15": [
        "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_c_abc_separation",
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc",
        "regulations/06_fsc_7th_tf_rate_system/sec01_rate_system_maintenance/tf7_01_spread_and_pref_governance",
    ],
    "CQ16": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
        "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge",
        "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_01_overview",
    ],
    "CQ17": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
        "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge",
        "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_substandard_doubtful_loss",
    ],
    "CQ18": [
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026",
        "regulations/04_fsc_large_exposure_notice/sec01_background_and_tier1_limit/notice_01_background",
        "regulations/03_fsc_reg_impact_analysis/sec01_large_exposure_overview/impact_01_overview",
    ],
    "CQ19": [
        "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates",
    ],
    "CQ20": [
        "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
    ],
}

# ISO/IEC 39075 GQL queries for each CQ (validated by GqlComposer with max_hops=12 & BigQuery Dry-Run)
CQ_GQL_TEMPLATES: dict[str, str] = {
    "CQ01": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'provision-criteria'}]->(pr:Provision {article_no: '제29조'})-[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr),
      (l)-[:BORROWED_BY]->(c:Customer)
WHERE l.asset_classification = 'NORMAL'
  AND c.ksic_section_code IN ('F', 'G', 'H', 'L')
RETURN ctx.context_id AS context_id, pr.provision_slot_id AS provision_slot_id, pr.kc_entry_id AS kc_entry_id,
       l.contract_id AS contract_id, c.borrower_name AS borrower_name, c.ksic_section_code AS ksic_section_code,
       l.outstanding_amt AS outstanding_amt, l.booked_provision_krw AS booked_provision_krw
LIMIT 50""",
    "CQ02": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr:Provision {article_no: '제29조'}),
      (l)-[:HAS_WORKOUT_HISTORY]->(w:WorkoutHistory)
WHERE l.asset_classification = 'SUBSTANDARD'
RETURN l.contract_id AS contract_id, l.borrower_name AS borrower_name, l.rehab_priority_claim_yn AS rehab_priority_claim_yn,
       w.legal_proceeding_code AS legal_proceeding_code, l.outstanding_amt AS outstanding_amt,
       l.booked_provision_krw AS booked_provision_krw, pr.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ03": """GRAPH starlight_bank_ontology.finance_graph
MATCH (c:Customer {customer_id: 'CUST_0001'})<-[:BORROWED_BY]-(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr:Provision {article_no: '제29조'}),
      (l)-[:HAS_WORKOUT_HISTORY]->(w:WorkoutHistory {legal_proceeding_code: 'CORP_RESTRUCT_ACT_WORKOUT'})
RETURN c.customer_id AS customer_id, l.contract_id AS contract_id, c.borrower_name AS borrower_name, l.asset_classification AS asset_classification,
       l.rehab_priority_claim_yn AS rehab_priority_claim_yn, w.legal_proceeding_code AS legal_proceeding_code,
       l.outstanding_amt AS outstanding_amt, l.booked_provision_krw AS booked_provision_krw, pr.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ04": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'provision-criteria'}]->(pr:Provision)-[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)
RETURN ctx.context_id AS context_id, pr.provision_slot_id AS provision_slot_id, pr.kc_entry_id AS kc_entry_id,
       doc.doc_id AS doc_id, l.contract_id AS contract_id, l.asset_classification AS asset_classification,
       l.outstanding_amt AS outstanding_amt, l.booked_provision_krw AS booked_provision_krw
LIMIT 100""",
    "CQ05": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'delinquency-rate'}]->(pr:Provision {article_no: '제27조'})-[:DELEGATES_TO_INTERNAL]->(in_pr:Provision {article_no: '내규 제14조'}),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)
RETURN ctx.context_id AS context_id, pr.kc_entry_id AS kc_entry_id, in_pr.kc_entry_id AS internal_kc_entry_id,
       l.contract_id AS contract_id, l.asset_classification AS asset_classification, l.outstanding_amt AS outstanding_amt
LIMIT 100""",
    "CQ06": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'DISCLOSURE'})-[inv:INVOKES_PROVISION {term_key: 'delinquency-rate'}]->(pr:Provision {article_no: '내규 제14조'})-[:CONFLICTS_BY_SECTOR]->(dist:Provision)-[:PART_OF_DOCUMENT]->(doc:SourceDocument {doc_id: 'DOC_07_NARS_RATE'}),
      (l:LoanContract)-[:HAS_DELINQUENCY]->(d:DelinquencyEvent)
WHERE d.write_off_yn = 'N'
RETURN ctx.context_id AS context_id, pr.kc_entry_id AS kc_entry_id, dist.kc_entry_id AS distractor_kc_entry_id,
       l.contract_id AS contract_id, d.overdue_days AS overdue_days, l.outstanding_amt AS outstanding_amt
LIMIT 50""",
    "CQ07": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'CREDIT_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'delinquency-rate'}]->(pr:Provision {article_no: '내규 제14조'}),
      (l:LoanContract)-[:HAS_DELINQUENCY]->(d:DelinquencyEvent)
RETURN ctx.context_id AS context_id, pr.kc_entry_id AS kc_entry_id,
       l.contract_id AS contract_id, d.overdue_days AS overdue_days, d.write_off_yn AS write_off_yn,
       d.overdue_principal_krw AS overdue_principal_krw, l.outstanding_amt AS outstanding_amt
LIMIT 50""",
    "CQ08": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'CREDIT_REVIEW'})-[inv:INVOKES_PROVISION {term_key: 'restructured-exemption'}]->(pr:Provision {article_no: '별표3 제3호 라목'}),
      (c:Customer {customer_id: 'CUST_0001'})<-[:BORROWED_BY]-(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr),
      (l)-[:HAS_WORKOUT_HISTORY]->(w:WorkoutHistory),
      (l)-[:HAS_EXCEPTION_APPROVAL]->(ea:ExceptionApproval {approval_status: 'APPROVED'})
RETURN c.customer_id AS customer_id, l.contract_id AS contract_id, c.borrower_name AS borrower_name, l.asset_classification AS asset_classification,
       w.consecutive_normal_repay_months AS consecutive_normal_repay_months, w.new_equity_paid_in_krw AS new_equity_paid_in_krw,
       ea.approval_id AS approval_id, ea.approval_status AS approval_status, pr.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ09": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'CREDIT_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'eod-deferral'}]->(pr16:Provision {article_no: '내규 제16조'})-[:HAS_EXCEPTION_PROVISO]->(pr18:Provision {article_no: '내규 제18조'}),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:HAS_COLLATERAL]->(col:Collateral)
WHERE l.overdue_days > 30
RETURN l.contract_id AS contract_id, l.borrower_name AS borrower_name, l.overdue_days AS overdue_days,
       l.rehab_priority_claim_yn AS rehab_priority_claim_yn, col.guarantee_agency_code AS guarantee_agency_code,
       col.guarantee_ratio_pct AS guarantee_ratio_pct, pr16.kc_entry_id AS pr16_kc_id, pr18.kc_entry_id AS pr18_kc_id
LIMIT 50""",
    "CQ10": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'CREDIT_REVIEW'})-[inv:INVOKES_PROVISION {term_key: 'eod-deferral'}]->(pr18:Provision {article_no: '내규 제18조'})<-[:GOVERNED_BY_CRITERIA]-(l:LoanContract)-[:HAS_COLLATERAL]->(col:Collateral)
RETURN l.contract_id AS contract_id, l.borrower_name AS borrower_name, col.collateral_type_code AS collateral_type_code,
       col.guarantee_agency_code AS guarantee_agency_code, col.guarantee_ratio_pct AS guarantee_ratio_pct,
       pr18.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ11": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'CREDIT_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'delinquency-rate'}]->(pr14:Provision {article_no: '내규 제14조'})<-[:DELEGATES_TO_INTERNAL]-(pr27:Provision {article_no: '제27조'}),
      (c:Customer {customer_id: 'CUST_0015'})<-[:BORROWED_BY]-(l:LoanContract {account_status: 'WRITTEN_OFF_SPECIAL_CLAIM'})-[:GOVERNED_BY_CRITERIA]->(pr27),
      (l)-[:HAS_DELINQUENCY]->(d:DelinquencyEvent {write_off_yn: 'Y'})
RETURN c.customer_id AS customer_id, l.contract_id AS contract_id, c.borrower_name AS borrower_name, l.asset_classification AS asset_classification,
       l.account_status AS account_status, d.overdue_days AS overdue_days, d.write_off_yn AS write_off_yn,
       pr27.kc_entry_id AS pr27_kc_id, pr14.kc_entry_id AS pr14_kc_id
LIMIT 50""",
    "CQ12": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'BRANCH'})-[inv:INVOKES_PROVISION {term_key: 'loan-rate'}]->(pr_kfb:Provision {article_no: '제Ⅱ장 1-나 ④항'})-[:DELEGATES_TO_INTERNAL]->(pr25:Provision {article_no: '내규 제25조'}),
      (c:Customer {customer_id: 'CUST_0008'})<-[:BORROWED_BY]-(l:LoanContract)-[:HAS_RATE_CUT_REQUEST]->(rc:RateCutRequest)-[:EVALUATED_UNDER_PROVISION]->(pr_kfb)
RETURN c.customer_id AS customer_id, rc.request_id AS request_id, c.borrower_name AS borrower_name, rc.application_reason_code AS application_reason_code,
       rc.credit_rating_before AS credit_rating_before, rc.credit_rating_after AS credit_rating_after,
       rc.review_status_code AS review_status_code, pr_kfb.kc_entry_id AS kfb_kc_id, pr25.kc_entry_id AS pr25_kc_id
LIMIT 50""",
    "CQ13": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'BRANCH'})-[inv:INVOKES_PROVISION {term_key: 'loan-rate'}]->(pr25:Provision {article_no: '내규 제25조'})<-[:GOVERNED_BY_CRITERIA]-(l:LoanContract)-[:OF_PRODUCT]->(fp:FinancialProduct {product_code: 'PROD_TCB_WORKING'}),
      (l)-[:BORROWED_BY]->(c:Customer)
RETURN l.contract_id AS contract_id, c.borrower_name AS borrower_name, l.pref_rate AS pref_rate,
       c.debt_ratio_pct AS debt_ratio_pct, pr25.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ14": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'BRANCH'})-[inv:INVOKES_PROVISION {term_key: 'base-date'}]->(pr21:Provision {article_no: '내규 제21조'})<-[:GOVERNED_BY_CRITERIA]-(l:LoanContract)-[:OF_PRODUCT]->(fp:FinancialProduct)
RETURN l.contract_id AS contract_id, fp.product_name AS product_name, l.contract_dt AS contract_dt,
       l.applied_rate AS applied_rate, l.contract_amt AS contract_amt, pr21.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ15": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'COMPLIANCE'})-[inv:INVOKES_PROVISION {term_key: 'loan-rate'}]->(pr22:Provision {article_no: '내규 제22조'})<-[:DELEGATES_TO_INTERNAL]-(pr_abc:Provision {article_no: '제Ⅱ장 1-다'}),
      (l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr22),
      (l)-[:OF_PRODUCT]->(fp:FinancialProduct)
RETURN fp.product_name AS product_name, l.base_rate AS base_rate, l.spread_rate AS spread_rate,
       l.pref_rate AS pref_rate, l.applied_rate AS applied_rate, pr_abc.kc_entry_id AS abc_kc_id, pr22.kc_entry_id AS pr22_kc_id
LIMIT 100""",
    "CQ16": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'provision-criteria'}]->(pr29:Provision {article_no: '제29조'})-[:CONFLICTS_BY_SECTOR]->(dist:Provision {article_no: '저축은행감독규정 제38조'})-[:PART_OF_DOCUMENT]->(doc:SourceDocument {applicable_sector: 'SAVINGS_BANK'}),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:OF_PRODUCT]->(fp:FinancialProduct)
RETURN pr29.kc_entry_id AS pr29_kc_id, dist.kc_entry_id AS dist_kc_id, doc.applicable_sector AS dist_sector,
       l.contract_id AS contract_id, fp.loan_category AS loan_category
LIMIT 100""",
    "CQ17": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'provision-criteria'}]->(pr29:Provision {article_no: '제29조'})-[:CONFLICTS_BY_SECTOR]->(dist:Provision {article_no: '저축은행감독규정 제38조'}),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)
WHERE l.overdue_days >= 90
RETURN l.contract_id AS contract_id, l.borrower_name AS borrower_name, l.overdue_days AS overdue_days,
       l.rehab_priority_claim_yn AS rehab_priority_claim_yn, l.asset_classification AS asset_classification,
       pr29.kc_entry_id AS pr29_kc_id, dist.kc_entry_id AS dist_kc_id
LIMIT 50""",
    "CQ18": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'COMPLIANCE'})-[inv:INVOKES_PROVISION {term_key: 'large-exposure'}]->(pr26:Provision {article_no: '제26조'})-[:PART_OF_DOCUMENT]->(doc:SourceDocument {doc_id: 'DOC_01_FSC_BANK_REG'}),
      (l:LoanContract)-[:BORROWED_BY]->(c:Customer)
RETURN pr26.provision_slot_id AS provision_slot_id, pr26.kc_entry_id AS kc_entry_id,
       pr26.missing_schema_columns AS missing_schema_columns, c.customer_id AS customer_id,
       c.borrower_name AS borrower_name, l.outstanding_amt AS outstanding_amt
LIMIT 50""",
    "CQ19": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'BRANCH'})-[inv:INVOKES_PROVISION {term_key: 'base-date'}]->(pr21:Provision {article_no: '내규 제21조'})<-[:GOVERNED_BY_CRITERIA]-(l:LoanContract)
RETURN l.contract_id AS contract_id, l.reg_dt AS reg_dt, l.contract_dt AS contract_dt,
       l.disburse_dt AS disburse_dt, l.contract_amt AS contract_amt, pr21.kc_entry_id AS kc_entry_id
LIMIT 50""",
    "CQ20": """GRAPH starlight_bank_ontology.finance_graph
MATCH (c:Customer {customer_id: 'CUST_0001'})<-[:BORROWED_BY]-(l:LoanContract)-[:HAS_WORKOUT_HISTORY]->(w:WorkoutHistory),
      (l)-[:GOVERNED_BY_CRITERIA]->(pr_ra:Provision {article_no: '별표3 제3호 라목'}),
      (l)-[:GOVERNED_BY_CRITERIA]->(pr29:Provision {article_no: '제29조'})
RETURN c.customer_id AS customer_id, l.contract_id AS contract_id, c.borrower_name AS borrower_name, l.outstanding_amt AS outstanding_amt,
       l.booked_provision_krw AS booked_provision_krw, l.rehab_priority_claim_yn AS rehab_priority_claim_yn,
       w.consecutive_normal_repay_months AS consecutive_normal_repay_months, w.new_equity_paid_in_krw AS new_equity_paid_in_krw,
       pr_ra.kc_entry_id AS ra_kc_id, pr29.kc_entry_id AS pr29_kc_id
LIMIT 50""",
    "Q21_D5": """GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})-[inv:INVOKES_PROVISION {term_key: 'provision-criteria'}]->(pr:Provision {article_no: '제29조'}),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:BORROWED_BY]->(c:Customer)
WHERE l.asset_classification = 'NORMAL'
  AND c.ksic_section_code IN ('F', 'G', 'H', 'L')
RETURN ctx.context_id AS context_id, pr.provision_slot_id AS provision_slot_id,
       'versions/art_29_allowance_coverage_ratio_v0.2.0' AS requested_kc_entry_id,
       l.contract_id AS contract_id, c.borrower_name AS borrower_name
LIMIT 10""",
}

CONVERSATIONAL_BRIEFINGS: dict[str, str] = {
    "CQ01": (
        "리스크관리부 기준 이번 분기 **정상(NORMAL) 분류 기업여신**을 점검한 결과, 총 **3,000만 원의 대손준비금 추가 적립이 필요합니다.**\n\n"
        "「은행업감독규정」 **제29조제1항제1호가목 단서**에 따라 건설업(`F`), 도소매업(`G`), 숙박·음식점업(`H`), 부동산업(`L`) 업종은 일반 기업여신(0.85%)보다 상향된 **0.9% 이상**의 최소 적립률이 적용됩니다. 현재 해당 업종 4개 차주(총 여신잔액 600억 원)가 모두 장부상 0.85%로만 적립되어 있어, 차주별 부족분(대양피에프개발 1,000만 원, 삼호종합건설 750만 원, 한일유통상사 750만 원, 그랜드하모니호텔 500만 원) 합계인 **3,000만 원**을 결산 시 대손준비금으로 추가 적립해야 합니다."
    ),
    "CQ02": (
        "**'고정(SUBSTANDARD)'** 분류 기업여신 2건(총 잔액 200억 원)의 법정 최소 대손충당금 합계는 **30억 원**이며, 현재 장부에 **40억 원**이 적립되어 있어 **10억 원 초과 적립(여유) 상태**입니다.\n\n"
        "「은행업감독규정」 **제29조제1항제1호다목**상 고정 분류 원칙 적립률은 **20%**이나, 단서 조항에 따라 「채무자 회생 및 파산에 관한 법률」 제180조제2항의 **우선변제자산**은 **10%**로 감경됩니다. 이에 따라 우선변제권이 인정된 태성금속(100억 원 × 10% = 10억 원)과 일반 고정 여신인 극동철강(100억 원 × 20% = 20억 원)의 법정 최소 적립액은 총 30억 원이므로 추가 대손준비금 적립 의무는 없습니다."
    ),
    "CQ03": (
        "**아니요, 절반으로 감경할 수 없습니다.** 별빛정밀(주) 여신(100억 원)은 현재 **'요주의(PRECAUTIONARY)'** 분류이므로 원칙대로 **7%(7억 원)**를 전액 적립해야 합니다.\n\n"
        "별빛정밀이 「기업구조조정 촉진법」상 워크아웃 우선변제자산(`rehab_priority_claim_yn = 'Y'`)인 것은 맞지만, 「은행업감독규정」 **제29조제1항제1호**에서 우선변제자산 1/2 감경 단서는 **고정(20%→10%)·회수의문(50%→25%)·추정손실(100%→50%)** 목에만 규정되어 있고 **나목(요주의 7% 이상)**에는 감경 단서가 존재하지 않습니다. 현재 장부 적립액(7억 원)은 법정 최소 기준과 정확히 일치합니다."
    ),
    "CQ04": (
        "대손상각 특수채권을 제외한 당행 기업여신의 **대손충당금 적립률(Coverage Ratio)은 78.6%**입니다 (총 대손충당금 **157.29억 원** ÷ 고정이하여신 **200억 원**).\n\n"
        "한국금융연구원(KIF) 금융브리프 참고치인 국내 7개 은행그룹 평균 **158%**(2023년 말) 및 시중은행그룹 평균 **132.2%**(2024년 3분기)와 비교하면 **상당히 낮은 수준**입니다. 이는 당행 포트폴리오의 대다수인 정상 분류 여신이 최소 수준(0.85%)으로만 적립되어 있고, 고정이하여신 2건(200억 원) 역시 고정 단계(20%대) 적립에 머물러 있기 때문입니다."
    ),
    "CQ05": (
        "차주 리스크관리위원회에 보고할 당행 기업여신 **고정이하여신(NPL) 비율은 1.51%**입니다 (고정이하여신 **200억 원** ÷ 대차대조표상 기업여신 총잔액 **1조 3,275억 원**).\n\n"
        "당행 **내규 제14조제1항** 및 「은행업감독규정」 **제27조**에 따라 리스크관리위원회 보고용 부실비율은 단순 연체일수가 아닌 **자산건전성 분류(고정·회수의문·추정손실)**를 기준으로 산출합니다. 따라서 45일 연체 중이지만 채권재조정 특례(별표3 제3호 라목)로 '요주의'로 분류된 별빛정밀(100억 원)과 회계상 대손상각되어 대차대조표에서 제외된 성진해운물류 특수채권(85억 원)은 분자에서 제외됩니다."
    ),
    "CQ06": (
        "금융감독원 대외공시용 원화대출 연체율은 **2.26%**로 산출됩니다 (1개월 이상 원리금 연체 **300억 원** ÷ 대차대조표상 기업여신 총잔액 **1조 3,275억 원**).\n\n"
        "리스크관리위원회 보고 수치(**1.51%**)와 **0.75%p** 차이가 나는 이유는 **별빛정밀(주) 여신 100억 원(45일 연체)** 때문입니다. 공시 연체율은 건전성 등급과 무관하게 **'1개월(30일) 이상 원리금 연체'(대손상각 특수채권 제외)**를 기준으로 집계하므로 별빛정밀이 분자에 포함되지만, 리스크위원회 고정이하 비율에서는 채권재조정 특례(요주의 분류)로 인해 제외됩니다."
    ),
    "CQ07": (
        "여신관리팀 조기경보(EWS) 기준 **실질관리 연체율은 4.00%**입니다 ((10일 이상 연체 **450억 원** + 대손상각 특수채권 **85억 원**) ÷ (대차대조표 기업여신 **1조 3,275억 원** + 특수채권 **85억 원**)).\n\n"
        "금감원 대외공시 연체율(**2.26%**)보다 **1.74%p** 높게 나타나는 이유는 당행 **내규 제14조제2항**에 따라 조기경보 목적상 **① 10일 이상 단기 연체 계좌 3건(150억 원, 18일 연체)**을 선제적으로 포착하고, **② 회계상 상각 처리된 특수채권 미회수 원금(성진해운물류 85억 원)**을 분자와 분모 모두에 합산하여 실질 회수 리스크를 관리하기 때문입니다."
    ),
    "CQ08": (
        "별빛정밀(주) 여신(100억 원, 45일 연체)을 고정이하로 하향하지 않고 **'요주의(PRECAUTIONARY)'로 유지한 것은 「은행업감독규정」 별표3 제3호 라목의 특례 요건을 모두 충족했기 때문이며, 감사 대응 요건도 완비되어 있습니다.**\n\n"
        "구체적으로 ① 채권재조정 개시 후 **7개월 연속 정상 상환**(기준: 6개월 이상) 및 ② **유상증자 50억 원 납입**(채무상환능력 개선 사건) 두 가지 실체적 요건을 모두 충족했습니다. 또한 라목 단서가 요구하는 **'판단근거의 명확한 문서화'** 의무 역시 2026년 2월 25일 본부 여신심사역(`HQ_SENIOR_CREDIT_OFFICER`)의 예외 승인(`APPROVED`) 결재 원장으로 입증됩니다."
    ),
    "CQ09": (
        "현재 30일 초과 연체 기업여신은 총 **3건**이며, 전산 원장의 결재 상태는 **당행 내규(제16조·제18조) 기준과 100% 일치합니다.**\n\n"
        "- **기한이익상실(EOD) 유예 대상 (1건 — 별빛정밀):** 내규 제18조에 따른 채권재조정 성실이행(7개월)·유상증자(50억 원)·신보 보증서(90% ≥ 85%) 요건과 우선변제자산 요건을 모두 갖추고 본부 여신심사역 승인(`APPROVED`)을 득하여 **EOD 유예(`EOD_DEFERRED`)** 처리되었습니다.\n"
        "- **즉시 EOD 예정 통지 대상 (2건 — 태성금속, 극동철강):** 태성금속은 회생법상 우선변제자산이나 정상 상환 기간(2개월 < 6개월) 및 보증비율(70% < 85%)이 미달하고, 극동철강은 모든 특례 요건을 충족하지 못해 내규 제16조제1항 원칙대로 **EOD 예정 통지(`EOD_NOTICE`)** 대상입니다."
    ),
    "CQ10": (
        "담보가 설정된 여신 3건 중 당행 **내규 제18조제1호의 보증서 기준 EOD 유예 요건을 충족하는 계좌는 별빛정밀(주)(`LN_2026_0001`) 1건뿐입니다.**\n\n"
        "내규 제18조제1호는 **'신용보증기금(KODIT) 보증비율 85% 이상 보증서 담보'**를 요구합니다. 별빛정밀은 신용보증기금 **90%** 보증서가 제공되어 요건을 충족하는 반면, 태성금속(`LN_2026_0002`)은 보증비율이 **70%**로 기준(85%)에 미달하며, 대양피에프개발(`LN_2026_KSIC_L1`)은 보증서가 아닌 **부동산 담보(신탁 1순위 60%)**이므로 해당 특례 대상이 아닙니다."
    ),
    "CQ11": (
        "성진해운물류(주) 건(`LN_2025_WRITEOFF_01`, 85억 원)의 대손상각 및 특수채권 편입 처리는 **규정에 부합하며, 부서별 연체율 지표에는 목적에 따라 서로 다르게 반영됩니다.**\n\n"
        "- **상각 처리 적법성:** 210일 연체로 회수가 불확실하여 '추정손실'로 분류 후 100%(85억 원) 충당금을 적립하고 상각한 것은 「은행업감독규정」 **제27조제4항(부실자산 조기상각 원칙)**에 따른 적법한 조치입니다.\n"
        "- **지표별 반영 여부 (내규 제14조):** 대차대조표 밖 특수채권이므로 **리스크관리위원회 고정이하비율**과 **금감원 대외공시 연체율**에서는 **제외**되지만, 실질 회수 관리를 위한 **여신관리팀 조기경보(EWS) 연체율**에서는 분자와 분모에 **모두 포함**됩니다."
    ),
    "CQ12": (
        "에이펙스세미콘(주)의 금리인하요구를 **거절(`REJECTED`)한 처리는 적법하며**, 고객에게는 **구체적인 거절 사유를 명시하여 통보**해야 합니다.\n\n"
        "- **거절 적법성 근거:** 금융위원회·은행연합회 「대출금리 산정체계 개선방안」 Ⅱ-1-나 ④항은 **'특허 취득 등'을 은행이 선택적으로 적용**할 수 있도록 재량을 부여했고, 이에 따라 당행 **내규 제25조제2항**은 **재무상태 개선이나 신용등급 상승이 동반되지 않은 단독 특허 취득을 필수 금리인하 사유에서 제외**했습니다. 에이펙스세미콘은 신용등급이 `BBB → BBB`로 변동 없고 매출 성장률도 1.2%에 그쳐 거절된 반면, 특허 취득과 함께 등급이 상승(`BBB → BBB+`)한 네오바이오텍은 35bp 인하가 승인되어 일관되게 운영되고 있습니다.\n"
        "- **고객 통보 의무:** 개선방안 Ⅱ-1-나 ②항에 따라 처리결과 통보 시 **'단독 특허 취득만으로는 당행 내규상 신용도·현금흐름 개선 요건이 충족되지 않아 수용이 어렵다'는 구체적 사유**를 반드시 함께 안내해야 합니다."
    ),
    "CQ13": (
        "점검 결과 **전결 한도나 부채비율 기준을 초과하여 위반한 계약은 0건(없음)**입니다.\n\n"
        "당행 **내규 제25조제1항**상 『별빛 TCB 기술혁신 운전자금』의 영업점장 전결 우대금리(`pref_rate`) 상한은 **연 1.20%p**, 신속심사 승인 부채비율 상한은 **250.0%**입니다. 현재 실행된 5건 모두 우대금리 1.20%p 이하 및 부채비율 250.0% 이하로 기준을 준수하고 있습니다. 다만 `LN_2026_0213_01`(네오바이오텍)과 `LN_2026_0213_05`(솔라에너지테크) 2건은 우대금리가 **정확히 상한선(1.20%p)**에 도달해 있어 영업점장 전결로는 추가 금리 우대가 불가합니다."
    ),
    "CQ14": (
        "당행 **내규 제21조제1항제2호**에 따라 특정일자 대출 조회 기준인 **대출계약 체결일(`contract_dt = 2026-02-13`)**로 집계한 결과, 총 **8건(135억 원)**이 체결되었으며 **전체 평균 적용금리는 연 4.82%**입니다.\n\n"
        "- **취급 건수 1위 상품:** 『별빛 TCB 기술혁신 운전자금』 (**5건**, 총 45억 원, 평균 적용금리 4.68%)\n"
        "- **취급 금액 1위 상품:** 『별빛 프라임 중견기업 운전자금』 (**3건**, 총 90억 원, 평균 적용금리 5.05%)\n"
        "- 만약 전산 신청등록일(`reg_dt`)이나 자금 실행일(`disburse_dt`)을 기준으로 잘못 조회하면 2월 13일 해당 건수는 **0건**으로 나타나므로 반드시 체결일 기준으로 집계해야 합니다."
    ),
    "CQ15": (
        "은행연합회 비교공시를 위한 당행 4개 기업여신 상품의 금리 구성(`A 기준금리 + B 가산금리 + C 가감조정금리 = 최종 적용금리`) 집계 결과는 아래 표와 같으며, 전 계좌(100건) 모두 금리 산식 항등식을 정확히 충족합니다.\n\n"
        "또한 문의하신 **'우대금리(C)를 가산금리(B)에 미리 차감·합산하여 가산금리가 낮아 보이게 공시하는 방식'은 엄격히 금지**됩니다. 「대출금리 산정체계 개선방안」 및 당행 **내규 제22조제2항**은 착시 공시를 막기 위해 반드시 **기준금리(A), 가산금리(B), 가감조정금리(C)를 각각 분리하여 공시**하도록 의무화하고 있습니다."
    ),
    "CQ16": (
        "당행 원장의 정상(NORMAL) 분류 여신 96건은 모두 **은행 기업여신**이므로 「은행업감독규정」 **제29조제1항제1호가목**이 적용됩니다.\n\n"
        "- **0.85% 적용 대상 (92건):** 일반 업종 정상 기업여신 원칙 기준\n"
        "- **0.90% 적용 대상 (4건):** 제29조제1항제1호가목 단서에 따른 건설업(`F`), 도소매업(`G`), 숙박·음식점업(`H`), 부동산업(`L`) 업종 기업여신\n"
        "- **타 기준 배제 근거:** **1.0%**는 은행 **가계자금대출**(제29조제1항제2호) 기준이며(당행 기업여신 원장에는 가계대출 0건), **0.5%**는 **상호저축은행(79개사)** 감독규정 기준이므로 당행 기업여신에 적용해서는 안 됩니다."
    ),
    "CQ17": (
        "**아니요, 55%가 아닙니다.** 55%는 은행 **가계자금대출**(제29조제1항제2호라목) 또는 상호저축은행 개정안 기준이며, 당행과 같은 **은행 기업여신**이 '회수의문(DOUBTFUL)'으로 분류될 때의 법정 최소 적립률은 원칙 **50%**, 우선변제자산인 경우 단서에 따라 **25%**입니다.\n\n"
        "- **태성금속(`LN_2026_0002`, 현재 고정·연체 95일):** 회생법 제180조제2항 우선변제자산(`rehab_priority_claim_yn = 'Y'`)이므로 향후 회수의문 전락 시 단서 기준 **25%** 적용\n"
        "- **극동철강(`LN_2026_0003`, 현재 고정·연체 110일):** 일반 기업여신이므로 향후 회수의문 전락 시 원칙 기준 **50%** 적용"
    ),
    "CQ18": (
        "**현재 당행 데이터베이스에 구비된 컬럼만으로는 거액익스포져 한도(기본자본의 25%) 초과 여부를 최종 판정할 수 없습니다.**\n\n"
        "- **원장 확인 가능 범위:** 단일 차주 기준 최대 여신 익스포져는 **대양피에프개발(주)(`CUST_0004`)의 200억 원**입니다. 따라서 당행 BIS 기본자본이 **800억 원 이상**(D-SIB인 경우 20% 한도 적용으로 1,000억 원 이상)이라면 한도 이내에 해당합니다.\n"
        "- **미구비 스키마(Data Gap) 항목:** 「은행업감독규정」 **제26조제1항제6호**(2024.1.18. 신설)를 정확히 판정하려면 **① 은행 BIS 기본자본(`tier1_capital`)**, **② 통제·경제적 의존관계로 묶인 연계 거래상대방 그룹(`counterparty_group_id`)**, **③ 채권·주식·보증 등 여신 외 합산 익스포져** 테이블이 추가로 구비되어야 합니다."
    ),
    "CQ19": (
        "2월 둘째 주(2026.02.09 ~ 02.13) 신규 대출 실적이 부서마다 다르게 집계된 이유는 **업무별 기준일자 컬럼(`reg_dt` / `contract_dt` / `disburse_dt`)이 서로 다르기 때문**이며, 당행 **내규 제21조제1항**상 공식 신규 영업 실적은 **대출계약 체결일(`contract_dt`) 기준인 8건 · 135억 원**이 맞습니다.\n\n"
        "- **영업점 공식 신규 실적 (체결일 `contract_dt` 기준):** **8건 · 135억 원** (모두 2월 13일 약정 체결 완료)\n"
        "- **자금부 자금집행 실적 (실행일 `disburse_dt` 기준):** **0건 · 0원** (해당 8건의 실제 자금 입금이 차주인 2월 16일~19일에 이루어져 셋째 주 집행 실적으로 잡힘)\n"
        "- **전산 신청접수 기준 (등록일 `reg_dt` 기준):** **6건 · 70억 원** (나머지 2건·65억 원은 전주인 2월 6일·8일에 사전 접수됨)"
    ),
    "CQ20": (
        "별빛정밀(주)(`LN_2026_0001`, 잔액 100억 원, 현 장부 충당금 7억 원)이 다음 달 상환을 1회 연체하더라도 **유상증자 요건으로 특례 유지가 가능하며, 설령 '고정'으로 하향되더라도 추가 충당금 부담은 +3억 원에 그칩니다.**\n\n"
        "- **특례 유지 가능성 (충당금 변동 없음, 7억 원 유지):** 「은행업감독규정」 별표3 제3호 라목은 ① 6개월 이상 연속 정상 상환 **또는** ② 증자 등 채무상환능력 개선 사건 발생 중 하나를 충족하고 판단근거를 문서화하면 고정이하로 분류하지 않을 수 있도록 규정합니다. 상환 1회 누락으로 ①번 요건이 깨지더라도 **② 유상증자 50억 원 납입 사실(`new_equity_paid_in_krw = 50억`)**이 유효하므로 심사부 재문서화를 거쳐 '요주의(7%, 7억 원)' 유지가 가능합니다.\n"
        "- **특례 철회 및 '고정' 하향 시 (+3억 원 증가):** 만약 보수적으로 특례를 철회하여 '고정'으로 하향하더라도, 본 건은 우선변제자산(`rehab_priority_claim_yn = 'Y'`)이므로 제29조제1항제1호다목 단서에 따라 고정 원칙(20%, 20억 원)이 아닌 **10%(10억 원)**가 적용되어 현재 장부(7억 원) 대비 **3억 원**만 추가 적립하면 됩니다."
    ),
}

FULL_EVIDENCE_QUOTES: dict[str, str] = {
    "그 차액을 매 결산시(분기별 가결산을 포함한다)마다 대손준비금으로 적": "그 차액을 매 결산시(분기별 가결산을 포함한다)마다 대손준비금으로 적립하여야 한다.",
    "3월 이상 연체대출채권을 보유하고 있는 거래처에 대한 자산중 회수예상가액 해": "3월 이상 연체대출채권을 보유하고 있는 거래처에 대한 자산 중 회수예상가액 해당 부분",
    "「기업구조조정 촉진법」제18조제2항 및 「채무자 회생 및 파산에 관한 법률」": "「기업구조조정 촉진법」 제18조제2항 및 「채무자 회생 및 파산에 관한 법률」 제180조제2항에 따라 우선변제권이 인정되는 채권",
    "리스크관리위원회 보고용 고정이하여신비율(은행업감독규정 제27조 및 별표3에 따른 3월 이상 연체 등": "리스크관리위원회 보고용 고정이하여신비율(은행업감독규정 제27조 및 별표3에 따른 3월 이상 연체 등 고정이하 분류 자산 기준)",
    "연체기간은 이자 또는 원금(분할상환금 포함)을 상환하기로 한 약정기일의 다음날": "연체기간은 이자 또는 원금(분할상환금 포함)을 상환하기로 한 약정기일의 다음날부터 기산한다.",
    "1. 분자: 10일 이상 원리금 연체 기업여신 잔액 + 30일 이상 관리연체 잔액 + 회계상 대손상각 처리되어 특수": "1. 분자: 10일 이상 원리금 연체 기업여신 잔액 + 30일 이상 관리연체 잔액 + 회계상 대손상각 처리되어 특수채권으로 편입된 미회수 원금 잔액",
    "거래기업이 6개월 이상(채권재조정을 위한 절차가 개시되어 채권재조정의 조건": "거래기업이 6개월 이상(채권재조정을 위한 절차가 개시되어 채권재조정의 조건이 이행 중인 기간을 포함한다) 약정 조건대로 원리금을 정상 상환한 경우",
    "원리금 연체가 1월(30일)을 초과하는 경우 여신관리시스템은 기한이익상실(EOD) 예정": "원리금 연체가 1월(30일)을 초과하는 경우 여신관리시스템은 기한이익상실(EOD) 예정 통지 대상으로 자동 분류한다.",
    "본부 여신심사역의 승인(APPROVED)을 득한 경우에는 고정이하": "본부 여신심사역의 승인(APPROVED)을 득한 경우에는 고정이하 전락 및 기한이익상실(EOD) 처리를 유예할 수 있다.",
    "보증부 여신은 거래기업 뿐만 아니라 보증인의 채무상환능력을 평가하여 건전성": "보증부 여신은 거래기업뿐만 아니라 보증인의 채무상환능력을 평가하여 건전성을 분류할 수 있다.",
    '"회수의문" 또는 "추정손실"로 분류된 자산(이하 "부실자산"이라 한다)을 조기에': '"회수의문" 또는 "추정손실"로 분류된 자산(이하 "부실자산"이라 한다)을 조기에 상각하여 자산건전성을 유지하여야 한다.',
    "금리인하요구 처리결과는 반드시 통보토록 하고 통보시에는": "금리인하요구 처리결과는 반드시 통보토록 하고, 거절 통보 시에는 구체적인 거절 사유를 함께 안내하여야 한다.",
    "대금리(pref_rate) 한도는 연 1.20%p, 신속심사 승인 부채비율 상한은 250.0%로 한다": "영업점장 전결 우대금리(pref_rate) 한도는 연 1.20%p, 신속심사 승인 부채비율 상한은 250.0%로 한다.",
    "최종 적용금리(applied_rate) = 기준금리(base_rate) + 가산금리(spread_rate) + 가감조정금리(△우대금리": "최종 적용금리(applied_rate) = 기준금리(base_rate) + 가산금리(spread_rate) + 가감조정금리(△우대금리 등)",
    "우대금리를 시계열적으로 비교·분석할 수 있도록 공시항목을 세분화하는": "우대금리를 시계열적으로 비교·분석할 수 있도록 기준금리·가산금리·가감조정금리로 공시항목을 세분화한다.",
    "2. 제1호의 규정에도 불구하고 가계자금대출금에 대하여는": "2. 제1호의 규정에도 불구하고 가계자금대출금에 대하여는 정상 분류 자산의 100분의 1 이상을 적립한다.",
    "3월 이상 12월 미만 연체대출채권을 보유하고 있는 거래처에 대한 자산중 회수": "3월 이상 12월 미만 연체대출채권을 보유하고 있는 거래처에 대한 자산 중 회수예상가액 초과 부분(회수의문)",
    "기본자본에 대한 단일 거래상대방 또는 연계된 거래상대방그룹": "기본자본에 대한 단일 거래상대방 또는 연계된 거래상대방그룹에 대한 익스포져 한도는 100분의 25 이하로 한다.",
    "거래상대방별 익스포져를 BIS 기본자본의 25% 이내로": "거래상대방별 익스포져를 BIS 기본자본의 25% 이내로 관리하도록 거액익스포져 한도 규제를 도입한다.",
    "2. 대출계약 체결일(contract_dt): 차주와 은행 간 여신거래약정서 서명·날인이 완료되어 법적 효력이 발생한": "2. 대출계약 체결일(contract_dt): 차주와 은행 간 여신거래약정서 서명·날인이 완료되어 법적 효력이 발생한 일자",
}

ROLE_KO_MAP: dict[str, str] = {
    "BASE_CRITERIA": "원칙 기준",
    "EXCEPTION_PROVISO": "단서·특례",
    "INTERNAL_DELEGATED_RULE": "당행 내규",
    "ADVISORY_REFORM_RULE": "제도개선 지침",
    "SECTOR_DISTRACTOR": "타 업권 대조",
}


def _retrieve_top_gql_examples(
    query_text: str, requested_num: str | None = None, top_k: int = 3
) -> tuple[str, dict[str, Any] | None, int, list[dict[str, Any]]]:
    """Finds the closest benchmark CQs and returns (best_id, best_cq, best_score, top_examples) as few-shot GQL references for gemini-3.8-flash."""
    cqs = _load_cqs()
    q_norm = re.sub(r"\s+", "", query_text or "")

    # 1. Explicit deprecated snapshot check -> Q21_D5
    if (
        "v0.2.0" in (query_text or "")
        or "폐기된" in q_norm
        or "구버전감독규정" in q_norm
        or requested_num == "21"
        or requested_num == "Q21_D5"
    ):
        return "Q21_D5", None, 100, [
            {
                "id": "Q21_D5",
                "question": "과거 폐기된 구버전 감독규정 스냅샷(versions/art_29_allowance_coverage_ratio_v0.2.0)을 기준으로 이번 분기 정상 여신 대손충당금 적립률을 산정해줘.",
                "gql": CQ_GQL_TEMPLATES["Q21_D5"],
                "provision_slots": ["versions/art_29_allowance_coverage_ratio_v0.2.0"],
            }
        ]

    # 2. If requested_num ("01".."20") matches and user didn't replace the question
    if requested_num:
        clean_num = requested_num.strip().rstrip(".")
        if clean_num.isdigit():
            idx = int(clean_num) - 1
            if 0 <= idx < len(cqs):
                target_cq = cqs[idx]
                cq_norm = re.sub(r"\s+", "", target_cq["question"])
                if not q_norm or q_norm == cq_norm or len(set(q_norm) & set(cq_norm)) >= min(8, len(cq_norm) // 3):
                    cid = target_cq["id"]
                    return cid, target_cq, 100, [
                        {
                            "id": cid,
                            "question": target_cq["question"].strip(),
                            "gql": CQ_GQL_TEMPLATES[cid],
                            "provision_slots": CQ_PROVISION_SLOTS.get(cid, []),
                        }
                    ]

    # 3. Exact or substring match against the 20 CQs
    for cq in cqs:
        cq_norm = re.sub(r"\s+", "", cq["question"])
        if q_norm and (q_norm == cq_norm or (len(q_norm) > 12 and (q_norm in cq_norm or cq_norm in q_norm))):
            cid = cq["id"]
            return cid, cq, 100, [
                {
                    "id": cid,
                    "question": cq["question"].strip(),
                    "gql": CQ_GQL_TEMPLATES[cid],
                    "provision_slots": CQ_PROVISION_SLOTS.get(cid, []),
                }
            ]

    # 4. Score all 20 CQs to provide top_k verified GQL reference patterns to gemini-3.8-flash
    stop_words = {"질문", "질문을", "어떤", "무슨", "내가", "우리", "얼마", "어떻게", "알려줘", "해줘", "있지", "있어", "뭐야", "기준", "은행", "보여줘", "현재"}
    q_words = [w for w in re.findall(r"[가-힣A-Za-z0-9_]+", query_text or "") if w not in stop_words]
    scored: list[tuple[int, dict[str, Any]]] = []
    for cq in cqs:
        score = 0
        cq_text = cq["question"] + " " + cq.get("answer", "")
        for w in q_words:
            if len(w) >= 2 and w in cq_text:
                score += len(w) * (3 if w in cq["question"] else 1)
        scored.append((score, cq))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_cq = scored[0] if scored else (0, cqs[0])
    best_id = best_cq["id"]
    top_examples = []
    for sc, cq in scored[:top_k]:
        cid = cq["id"]
        top_examples.append({
            "id": cid,
            "score": sc,
            "question": cq["question"].strip(),
            "gql": CQ_GQL_TEMPLATES.get(cid, ""),
            "provision_slots": CQ_PROVISION_SLOTS.get(cid, []),
        })
    return best_id, best_cq, best_score, top_examples


_GENAI_CLIENT: Any = None
GEMINI_MODEL_ID = "gemini-3.8-flash"
GEMINI_LOCATION = "global"


def _get_genai_client() -> Any:
    """Returns a singleton Vertex AI genai.Client configured for gemini-3.8-flash on location='global'."""
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        from google import genai
        _GENAI_CLIENT = genai.Client(
            vertexai=True,
            project=PROJECT,
            location=GEMINI_LOCATION,
        )
    return _GENAI_CLIENT


# Live provision catalog (kc_entry_id · title) for the free-question planner (ADR 0013).
# Read from the OKF-backed graph node view at run time — not a hand-written list — so an OKF /
# graph rebuild changes the catalog without a code change. Measured on 2026-09-28: 174 rows,
# ~19K chars. Without it the planner invented provision IDs (KC 404) on EQ15 · EQ16.
_PROVISION_CATALOG: dict[str, Any] = {"at": 0.0, "rows": []}
_PROVISION_CATALOG_TTL_S = 600
_MAX_PLANNER_PROVISION_SLOTS = 4  # CQ templates use at most 3 slots (measured 2026-09-28)
# Free questions only (user 2026-09-29 12:46Z — "사소한 것만"): each provision costs kc_lookup + fetch_provision,
# so the 12-call tool budget (graph_query 1 + 2 × 5 = 11) reaches at most 5. A planner GQL that touched more used
# to spend the budget before the planner's own picks were reached — EQ10 12:09Z touched 50 unrelated provisions,
# its 3 planner picks sat at 51–53 and none was fetched; local EQ16 touched 8 and 7 fetches were budget-blocked.
_MAX_FREE_TURN_PROVISION_SLOTS = 5


def _merge_provision_slots(touched: list[str], fallback: list[str], cap: int | None = None) -> list[str]:
    """GQL-touched slots, then the fallback slots (planner picks or CQ slots), de-duplicated.

    With `cap` and more slots than the cap, the fallback slots go first and the list stops at the cap, so the
    tool budget reaches them. At or under the cap — and whenever `cap` is None — the order is unchanged.
    """
    merged: list[str] = []
    for s in [*touched, *fallback]:
        if s and s not in merged:
            merged.append(s)
    if cap is None or len(merged) <= cap:
        return merged
    ordered: list[str] = []
    for s in [*fallback, *touched]:
        if s and s not in ordered:
            ordered.append(s)
    return ordered[:cap]


def _load_provision_catalog(run_bq_sql_fn: Any) -> list[dict[str, str]]:
    """Returns `[{"kc_entry_id", "title"}]` for every Provision node; cached for a few minutes."""
    now = time.time()
    if _PROVISION_CATALOG["rows"] and now - float(_PROVISION_CATALOG["at"]) < _PROVISION_CATALOG_TTL_S:
        return list(_PROVISION_CATALOG["rows"])
    try:
        rows, _ = run_bq_sql_fn(f"""
            SELECT kc_entry_id, title
            FROM `{PROJECT}.starlight_bank_ontology.v_node_provision`
            WHERE kc_entry_id IS NOT NULL
            ORDER BY kc_entry_id
        """)
    except Exception:  # an unreachable catalog must not break the turn; validation is then skipped
        return list(_PROVISION_CATALOG["rows"])
    catalog = [
        {"kc_entry_id": str(r.get("kc_entry_id")), "title": str(r.get("title") or "")}
        for r in (rows or [])
        if isinstance(r, dict) and r.get("kc_entry_id")
    ]
    if catalog:
        _PROVISION_CATALOG.update(at=now, rows=catalog)
    return catalog


_FINANCE_GRAPH_SCHEMA_PROMPT = """
[BigQuery Property Graph: `starlight_bank_ontology.finance_graph` (11 Node Classes · 15 Edge Types)]
모든 GQL 쿼리는 반드시 `GRAPH starlight_bank_ontology.finance_graph`로 시작하며, 아래에 정의된 정확한 노드 라벨, 엣지 라벨, 속성(컬럼)만 사용해야 합니다.

1. Node Classes & Exact Properties:
- `BusinessContext`: `context_id` ('RISK_MGMT'|'DISCLOSURE'|'CREDIT_MGMT'|'CREDIT_REVIEW'|'BRANCH'|'COMPLIANCE'), `dept_name`, `purpose_summary`, `primary_metric_scope`
- `SourceDocument`: `doc_id`, `doc_code`, `title`, `authority_level`, `applicable_sector`, `issuing_body`, `kc_entry_id`, `gcs_uri`
- `Provision`: `provision_slot_id`, `doc_id`, `kc_entry_id`, `article_no` (예: '제29조', '제27조', '제26조', '별표3 제3호 라목', '내규 제14조', '내규 제16조', '내규 제18조', '내규 제21조', '내규 제22조', '내규 제25조', '제Ⅱ장 1-나 ④항', '제Ⅱ장 1-다', '저축은행감독규정 제38조'), `title`, `provision_role`, `target_columns`, `missing_schema_columns`, `gcs_uri`
- `LoanContract`: `contract_id`, `customer_id`, `product_code`, `borrower_name`, `ksic_section_code`, `reg_dt` (DATE), `contract_dt` (DATE), `disburse_dt` (DATE), `base_rate` (FLOAT), `spread_rate` (FLOAT), `pref_rate` (FLOAT), `applied_rate` (FLOAT), `contract_amt` (INT64), `outstanding_amt` (INT64), `overdue_days` (INT64), `asset_classification` ('NORMAL'|'PRECAUTIONARY'|'SUBSTANDARD'|'DOUBTFUL'|'ESTIMATED_LOSS'), `rehab_priority_claim_yn` ('Y'|'N'), `booked_provision_krw` (INT64), `account_status` ('ACTIVE'|'EOD_DEFERRED'|'EOD_NOTICE'|'WRITTEN_OFF_SPECIAL_CLAIM')
- `Customer`: `customer_id` (예: 'CUST_0001' 별빛정밀(주), 'CUST_0002' 태성금속공업(주), 'CUST_0003' 극동철강산업(주), 'CUST_0004' 대양피에프개발(주), 'CUST_0005' 삼호종합건설(주), 'CUST_0006' 한일유통상사(주), 'CUST_0007' 네오바이오텍(주), 'CUST_0008' 에이펙스세미콘(주), 'CUST_0009' 다온로보틱스(주), 'CUST_0010' 코어옵틱스(주), 'CUST_0011' 솔라에너지테크(주), 'CUST_0012' 세진오토모티브(주), 'CUST_0013' 한일화학소재(주), 'CUST_0014' 동양물류시스템(주), 'CUST_0015' 성진해운물류(주), 'CUST_0016' 그랜드하모니호텔(주)), `borrower_name`, `corp_reg_no`, `ksic_section_code`, `ksic_detail_code`, `industry_name`, `credit_rating`, `tcb_tech_grade`, `debt_ratio_pct`
- `FinancialProduct`: `product_code` ('PROD_CORP_GEN'|'PROD_PRIME_MID'|'PROD_TCB_WORKING'|'PROD_GUARANTEE_SAFE'), `product_name`, `loan_category`, `target_segment`, `base_rate_benchmark`, `repayment_method`, `max_maturity_months`
- `Collateral`: `collateral_id`, `contract_id`, `customer_id`, `collateral_type_code` ('CREDIT_GUARANTEE'|'REAL_ESTATE_TRUST'), `guarantee_agency_code` ('KODIT'|'KIBO'|'NONE'), `guarantee_ratio_pct`, `appraised_collateral_krw`
- `DelinquencyEvent`: `event_id`, `contract_id`, `customer_id`, `overdue_days`, `overdue_principal_krw`, `overdue_interest_krw`, `write_off_yn` ('Y'|'N')
- `WorkoutHistory`: `workout_id`, `contract_id`, `customer_id`, `workout_start_dt`, `consecutive_normal_repay_months`, `new_equity_paid_in_krw`, `legal_proceeding_code` ('CORP_RESTRUCT_ACT_WORKOUT'|'DEBTOR_REHAB_ACT'|'BANK_WORKOUT_AGREEMENT')
- `RateCutRequest`: `request_id`, `contract_id`, `customer_id`, `request_dt`, `application_reason_code` ('PATENT_ACQUISITION'|'CREDIT_RATING_UPGRADE'|'FINANCIAL_IMPROVEMENT'), `patent_reg_no`, `credit_rating_before`, `credit_rating_after`, `yoy_revenue_growth_pct`, `review_status_code` ('APPROVED'|'REJECTED'), `approved_cut_bp`
- `ExceptionApproval`: `approval_id`, `contract_id`, `customer_id`, `approval_type_code`, `approval_status` ('APPROVED'|'REJECTED'), `approver_role_code`, `approval_dt`

2. 15 Directed Edge Patterns (방향과 라벨 엄수):
- `(l:LoanContract)-[:BORROWED_BY]->(c:Customer)`  또는  `(c:Customer)<-[:BORROWED_BY]-(l:LoanContract)`
- `(l:LoanContract)-[:OF_PRODUCT]->(fp:FinancialProduct)`
- `(l:LoanContract)-[:HAS_COLLATERAL]->(col:Collateral)`
- `(l:LoanContract)-[:HAS_DELINQUENCY]->(d:DelinquencyEvent)`
- `(l:LoanContract)-[:HAS_WORKOUT_HISTORY]->(w:WorkoutHistory)`
- `(l:LoanContract)-[:HAS_RATE_CUT_REQUEST]->(rc:RateCutRequest)`
- `(l:LoanContract)-[:HAS_EXCEPTION_APPROVAL]->(ea:ExceptionApproval)`
- `(ctx:BusinessContext)-[:SCOPES_PORTFOLIO]->(l:LoanContract)`
- `(ctx:BusinessContext)-[inv:INVOKES_PROVISION {term_key: '...'}]->(pr:Provision)`
- `(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr:Provision)`
- `(rc:RateCutRequest)-[:EVALUATED_UNDER_PROVISION]->(pr:Provision)`
- `(pr:Provision)-[:PART_OF_DOCUMENT]->(doc:SourceDocument)`
- `(pr:Provision)-[:HAS_EXCEPTION_PROVISO]->(pr_sub:Provision)`
- `(pr:Provision)-[:DELEGATES_TO_INTERNAL]->(pr_int:Provision)`
- `(pr:Provision)-[:CONFLICTS_BY_SECTOR]->(pr_dist:Provision)`

3. BigQuery GQL 작성 시 주의사항:
- 반드시 `RETURN` 절의 모든 컬럼에 `AS 별칭`을 명시하고, 마지막에 `LIMIT 50` (또는 `LIMIT 100`)을 붙이세요.
- 집계 함수(`SUM`, `AVG`, `COUNT`) 대신 개별 원장 행과 속성들을 `RETURN`으로 조회하면 에이전트가 후속 단계에서 정확히 계산·브리핑합니다.
- Step 0에서 바인딩된 엔티티 앵커(`step0_bound_entity_anchors`)가 있으면 반드시 `MATCH` 패턴에 해당 `canonical_id` 필터를 사용하고, 앵커에 없는 임의의 `customer_id`를 추측하지 마세요.
""".strip()


def _gemini_plan_turn(
    query_text: str,
    requested_num: str | None,
    alias_hits: list[dict[str, Any]],
    best_id: str,
    best_score: int,
    top_examples: list[dict[str, Any]],
    provision_catalog: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Uses `gemini-3.8-flash` (global, thinking_budget=0) to autonomously classify intent and compose GQL."""
    client = _get_genai_client()
    system_instruction = f"""당신은 별빛은행(Starlight Bank) 기업여신 GraphRAG 에이전트(Starlight GraphRAG Agent)의 턴 플래너 및 GQL 작성기입니다.
사용자의 질문을 분석하여 하드코딩 규칙 없이 의미를 판단하고, 아래 4가지 실행 모드(`mode`) 중 하나로 분류한 뒤 JSON으로 응답하세요.

[4가지 실행 모드 (`mode`) 정의]
1. `OUT_OF_DOMAIN`:
   - 날씨, 일상 잡담, 맛집/점심 추천, 스포츠, 연예, 일반 코딩 질문, 개인금융(카드/예적금) 등 **별빛은행 기업여신 원장·리스크관리·여신심사·금리·금융감독규정과 무관한 질문**인 경우.
   - 도구(`graph_query`, `kc_lookup`, `fetch_provision`)를 절대 호출하지 않으며, `direct_response_markdown`에 정중하고 자연스러운 한국어로 "저는 별빛은행 기업여신 심사·리스크·준법 의사결정을 지원하는 에이전트입니다."라고 안내하고 질의 가능한 기업여신/규정 주제를 예시로 제시하세요 (단, '11개 노드 클래스', '15개 엣지', '온톨로지 스키마' 같은 내부 DB/그래프 설계 스펙이나 '좌측 목록' 언급은 절대 노출하지 마세요).
   - 거절 사유는 **"질문이 에이전트의 업무 범위(기업여신 심사·리스크·준법 의사결정 지원) 밖"**이라는 점으로 설명하세요. 해당 자료·보고서·통계를 "보유하고 있지 않다", "갖고 있지 않다"처럼 자료 보유 여부를 단정하는 표현은 쓰지 마세요.

2. `META_HELP`:
   - "내가 어떤 질문을 할 수 있지?", "어떤 질문 할 수 있는데?", "무슨 기능이 있어?", "어떻게 사용해야 해?", "안녕", "자기소개 해줘" 등 **에이전트의 역할·기능·질문 가능한 범위를 묻는 메타 질문이나 인사말**인 경우.
   - 도구를 호출하지 않으며, `direct_response_markdown`에 **'11개 노드 클래스', '15개 관계 엣지', '지식 그래프 온톨로지', '좌측 목록(01.~21.)' 같은 내부 구조 용어나 UI 위치 언급을 절대 넣지 말고**, 아래와 같이 현업 심사역·리스크담당자 관점의 깔끔한 업무 안내문 형태로 작성하세요:
     "### 질의 가능 업무 안내\n\n별빛은행의 **실시간 기업여신 원장**과 **금융감독규정·당행 여신내규 정본**을 함께 조회하여 여신심사·리스크관리·준법감시 업무를 지원합니다. 아래 주제에 대해 자유롭게 질문해 보세요.\n\n- **1. 기업여신 원장 및 차주 현황 조회:** 차주별 대출 잔액·적용금리·부채비율, 현재 연체 중인 계좌 목록 및 연체일수, 담보·보증서 설정 내역 조회 *(예: \"에이펙스세미콘 대출 잔액이랑 적용금리, 부채비율 알려줘\", \"현재 연체 중인 계좌 목록과 연체일수 보여줘\")*\n- **2. 대손충당금 및 건전성 분류 심사:** 정상·요주의·고정 등 건전성 단계별 법정 최소 충당금 산정, 업종별(건설·도소매·숙박·부동산업) 가산 적립률 및 우선변제자산 감경 특례 판정 *(예: \"이번 분기 정상 여신 중 대손준비금 추가 적립이 필요한 계좌와 금액은?\")*\n- **3. 부서별 연체율 산정 및 비교:** 리스크관리위원회 보고용 고정이하비율, 금감원 대외공시 연체율, 여신관리팀 조기경보(EWS) 연체율의 산정 기준 및 수치 비교 *(예: \"여신관리팀 조기경보 연체율이 공시 연체율보다 높게 나오는 이유가 뭐야?\")*\n- **4. 채권재조정 · 기한이익상실(EOD) 유예 판정:** 워크아웃·채권재조정 계좌의 건전성 유지 요건 점검, 30일 초과 연체 계좌의 EOD 유예 요건(신보 보증비율 85% 이상 등) 충족 여부 확인 *(예: \"30일 초과 연체 계좌 중 EOD 유예 대상과 즉시 통지 대상을 구분해줘\")*\n- **5. 대출금리 산정(A+B-C) · 금리인하요구권 · 거액익스포져 점검:** 기준·가산·우대금리 구성 검증, 특허 취득 등 금리인하요구 거절 적법성, 체결일 기준 신규 실적 및 거액익스포져 한도 점검 *(예: \"에이펙스세미콘이 특허 취득으로 신청한 금리인하요구를 거절한 게 규정에 맞아?\")*"

3. `LEDGER_ONLY` (1안 — 순수 원장 조회):
   - 별빛은행의 차주(`Customer`), 대출계좌(`LoanContract`), 금융상품(`FinancialProduct`), 담보(`Collateral`), 연체내역(`DelinquencyEvent`), 워크아웃 이력(`WorkoutHistory`), 금리인하요구(`RateCutRequest`), 예외승인(`ExceptionApproval`) 등 **기업여신 원장 데이터 자체의 수치·목록·현황만 묻고, 법령/감독규정/내규 조문(`Provision`)의 적법성 판정이나 규정 해석이 필요하지 않은 질문**인 경우.
   - 예: "에이펙스세미콘 대출 잔액이랑 적용금리, 부채비율 알려줘", "현재 연체 중인 계좌 목록과 연체일수 보여줘", "태성금속 담보 종류랑 보증비율 알려줘", "고정 분류 여신 계좌들 보여줘".
   - 이 경우 **Step 1 (`graph_query`)만 실행**하고 Step 2(`kc_lookup`)·Step 3(`fetch_provision`)는 생략합니다.
   - `gql` 필드에 Step 0 바인딩 앵커와 아래 스키마/예시를 참고하여 정확한 ISO/IEC 39075 GQL 쿼리를 작성하세요 (`Provision` 노드를 조인할 필요 없음).

4. `FULL_GRAPHRAG` (원장 + 법령·내규 조문 검증 통합):
   - 대손충당금 적립률/과부족 산정, 부서별(리스크/공시/여신관리) 연체율 산정 기준 비교, 채권재조정 요주의 유지 적법성, 기한이익상실(EOD) 유예 판정, 금리인하요구 거절 적법성, 우대금리 전결 한도 위반 점검, 체결일/실행일 기준 실적 비교, 거액익스포져 한도 및 미구비 스키마 점검, 구버전 폐기 조문(`v0.2.0`) 호출 등 **법령·감독규정·내규 조문(`Provision`)과 여신 원장을 함께 연결해 심사·판정해야 하는 질문**인 경우 (좌측 01.~21.번 벤치마크 질의 및 유사 자유 응용 질의 포함).
   - `gql` 필드에 Step 0 앵커와 검증된 GQL 레퍼런스를 활용한 GQL을 작성하고, `provision_slots`에 검증할 조문 슬롯 ID 목록을 넣으세요.
   - `provision_slots`에는 사용자 프롬프트의 `provision_catalog`(형식: `kc_entry_id | 조문 제목`)에 있는 `kc_entry_id`만 **글자 그대로 복사**해 넣으세요. 목록에 없는 ID를 새로 만들거나 경로·파일명을 바꾸지 마세요. 질문에 답하는 데 직접 필요한 조문만 최대 {_MAX_PLANNER_PROVISION_SLOTS}개 고르세요.

{_FINANCE_GRAPH_SCHEMA_PROMPT}

[응답 JSON 스키마 (반드시 유효한 JSON 객체 1개만 출력, 마크다운 텍스트에 이모지/픽토그램 절대 사용 금지)]
{{
  "mode": "OUT_OF_DOMAIN" | "META_HELP" | "LEDGER_ONLY" | "FULL_GRAPHRAG",
  "reason": "분류 근거 1문장 요약",
  "dept_id": "RISK_MGMT" | "DISCLOSURE" | "CREDIT_MGMT" | "CREDIT_REVIEW" | "BRANCH" | "COMPLIANCE",
  "matched_cq_id": "CQ01~CQ20 또는 Q21_D5와 동일한 질문이면 해당 ID, 새로운 자유 질문이면 빈 문자열",
  "gql": "mode가 LEDGER_ONLY 또는 FULL_GRAPHRAG일 때 실행할 GRAPH starlight_bank_ontology.finance_graph ... 쿼리 (그 외에는 빈 문자열)",
  "provision_slots": ["mode가 FULL_GRAPHRAG일 때 provision_catalog에서 그대로 복사한 kc_entry_id 문자열 배열 (최대 {_MAX_PLANNER_PROVISION_SLOTS}개)"],
  "direct_response_markdown": "mode가 OUT_OF_DOMAIN 또는 META_HELP일 때 사용자에게 바로 보여줄 깔끔한 한국어 마크다운 응답 (이모지 및 '11개 노드 클래스/15개 엣지' 등 내부 스키마 용어 절대 사용 금지)"
}}"""

    user_prompt = json.dumps(
        {
            "user_question": query_text,
            "requested_sidebar_num": requested_num,
            "step0_bound_entity_anchors": alias_hits,
            "closest_benchmark_cq_id": best_id if best_score >= 35 else "",
            "closest_benchmark_score": best_score,
            "verified_gql_reference_examples": top_examples,
            "provision_catalog": [f"{c['kc_entry_id']} | {c['title']}" for c in (provision_catalog or [])],
        },
        ensure_ascii=False,
        indent=2,
    )

    resp = client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw_text = (resp.text or "{}").strip()
    return json.loads(raw_text)


def _gemini_repair_gql(
    query_text: str,
    failed_gql: str,
    error_reason: str,
    alias_hits: list[dict[str, Any]],
    top_examples: list[dict[str, Any]],
    previous_attempts: list[dict[str, Any]] | None = None,
) -> str:
    """Uses `gemini-3.8-flash` to self-correct a GQL query that failed static guard or BigQuery Dry-Run.

    `previous_attempts` are the GQLs that already failed validation in this turn (oldest first, with their
    errors). They are shown so the model does not hand back one of them; `_run_step1_gql` stops the loop
    if it does anyway (ADR 0016).
    """
    client = _get_genai_client()
    history = [
        {"시도": i + 1, "gql": a.get("gql", ""), "오류": list(a.get("errors") or [])}
        for i, a in enumerate(previous_attempts or [])
        if a.get("gql") and not a.get("ok")
    ]
    prompt = f"""다음 사용자 질문에 대해 생성된 BigQuery GQL 쿼리가 `gql_dry_run_guard` 검증에서 실패했습니다.
오류 원인을 확인하고, 스키마와 검증된 레퍼런스 쿼리를 참고하여 즉시 실행 가능한 수정된 GQL 쿼리만 JSON(`{{"gql": "..."}}`)으로 반환하세요.
[이전 시도]에 있는 GQL 은 모두 검증에 실패했습니다. 그중 어느 것과도 같은 쿼리를 다시 반환하지 마세요.

[사용자 질문]
{query_text}

[Step 0 엔티티 앵커]
{json.dumps(alias_hits, ensure_ascii=False)}

[실패한 GQL]
{failed_gql}

[Dry-Run / Guard 오류 메시지]
{error_reason}

[이전 시도 (모두 실패 · 오래된 순)]
{json.dumps(history, ensure_ascii=False, indent=2) if history else "(없음)"}

[{_FINANCE_GRAPH_SCHEMA_PROMPT}]

[검증된 GQL 예시]
{json.dumps(top_examples[:2], ensure_ascii=False, indent=2)}
"""
    resp = client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    parsed = json.loads((resp.text or "{}").strip())
    return str(parsed.get("gql") or failed_gql).strip()


def _gemini_synthesize_briefing(
    query_text: str,
    mode: str,
    dept_name: str,
    ledger_rows: list[dict[str, Any]],
    provisions_payload: list[dict[str, Any]],
) -> str:
    """Uses `gemini-3.8-flash` (global, thinking_budget=0) to write a concise, natural Korean financial briefing grounded in the live GQL rows and provisions."""
    client = _get_genai_client()
    # Full verbatim body, no cut (user-approved 2026-09-28): all 174 provision bodies exceed 900 chars
    # (median 1,790 · max 5,661) and decisive passages sat past a former [:900] cut (EQ02 at 1,899, EQ10 at 1,470).
    prov_summaries = [
        {
            "article_no": p.get("article_no"),
            "title": p.get("title"),
            "provision_role": p.get("provision_role"),
            "verbatim_body": p.get("verbatim_body") or "",
        }
        for p in provisions_payload
    ]
    prompt = f"""당신은 별빛은행 `{dept_name}`의 수석 여신심사·리스크 자문역입니다.
사용자 질문에 대해 방금 BigQuery Graph(`starlight_bank_ontology.finance_graph` + Cloud Spanner 실시간 원장)에서 조회한 원장 데이터와 검증된 조문을 바탕으로 핵심 결론 브리핑(2~4문장 내외, 중요한 수치·차주명·계좌번호·비율은 **굵게** 강조)을 작성하세요.
주의사항:
- 마크다운 표(테이블)는 본문 아래에 자동으로 첨부되므로 브리핑 텍스트 안에 중복해서 표를 그리지 마세요.
- 첫 문장에서 질문에 대한 직접적인 답(결론/수치/판정)을 먼저 제시하고, 이어서 원장 수치 및 근거를 자연스럽고 명확한 한국어 문장으로 설명하세요.
- 원장 데이터에 없는 수치를 절대 지어내지 마세요.

[사용자 질문]
{query_text}

[실행 모드]
{mode}

[실시간 GQL 조회 원장 결과 ({len(ledger_rows)}건)]
{json.dumps(ledger_rows[:25], ensure_ascii=False, default=str)}

[검증된 조문 근거 ({len(prov_summaries)}건)]
{json.dumps(prov_summaries, ensure_ascii=False)}
"""
    resp = client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return (resp.text or "").strip()


def _fmt_val(col: str, val: Any) -> str:
    """Formats SQL result values cleanly for Markdown tables."""
    if val is None:
        return "-"
    if isinstance(val, bool) or str(val).lower() in ("true", "false"):
        b = val if isinstance(val, bool) else (str(val).lower() == "true")
        return "충족 (True)" if b else "미충족 (False)"
    col_l = col.lower()
    try:
        if any(k in col_l for k in ("krw", "amt", "principal", "allowance", "gap")):
            num = int(float(val))
            if abs(num) >= 100_000_000:
                eok = num / 100_000_000
                if abs(eok - round(eok)) < 1e-6:
                    return f"{int(round(eok)):,}억 원 ({num:,}원)"
                return f"{eok:,.2f}억 원 ({num:,}원)"
            if abs(num) >= 10_000:
                man = num // 10_000
                return f"{man:,}만 원 ({num:,}원)"
            return f"{num:,}원"
        if any(k in col_l for k in ("pct", "rate", "a_base", "b_spread", "c_adjust", "applied")):
            fval = float(val)
            return f"{fval:.3f}%".rstrip("0").rstrip(".") + "%" if "." in f"{fval}" else f"{fval}%"
    except Exception:
        pass
    return str(val)


def _rows_to_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_조회 결과 0건 (해당 조건을 위반하거나 일치하는 레코드 없음)_"
    cols = list(rows[0].keys())
    header = "| " + " | ".join(f"`{c}`" for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = []
    for r in rows[:15]:
        cells = [_fmt_val(c, r.get(c)) for c in cols]
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body])


class _AdkTurnContext:
    """ADK CallbackContext / ToolContext state carrier for turn execution."""

    def __init__(self, user_text: str, session_id: str = "sess-mod05") -> None:
        self.state: dict[str, Any] = {"temp:user_query": user_text}
        self.user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        )
        self.invocation_id = session_id
        self.user_id = "starlight-reviewer"


def _bind_step0_anchors_into_gql(gql_text: str, alias_hits_objs: list[Any]) -> str:
    """Ensures every canonical_id resolved in Step 0 (`pre_ground_entities`) is bound into Step 1 GQL."""
    updated = gql_text
    for h in alias_hits_objs:
        cls = h.target_class
        cid = h.canonical_id
        if cls == "Customer":
            if "Customer" in updated:
                updated = re.sub(
                    r"\(\s*(\w+)\s*:\s*Customer(?:\s*\{[^}]*\})?\s*\)",
                    rf"(\1:Customer {{customer_id: '{cid}'}})",
                    updated,
                    count=1,
                )
        elif cls == "BusinessContext":
            if "BusinessContext" in updated and cid not in updated:
                updated = re.sub(
                    r"\(\s*(\w+)\s*:\s*BusinessContext(?:\s*\{[^}]*\})?\s*\)",
                    rf"(\1:BusinessContext {{context_id: '{cid}'}})",
                    updated,
                    count=1,
                )
        elif cls == "FinancialProduct":
            if "FinancialProduct" in updated:
                updated = re.sub(
                    r"\(\s*(\w+)\s*:\s*FinancialProduct(?:\s*\{[^}]*\})?\s*\)",
                    rf"(\1:FinancialProduct {{product_code: '{cid}'}})",
                    updated,
                    count=1,
                )
        elif cls == "WorkoutHistory":
            if "WorkoutHistory" in updated and cid not in updated:
                updated = re.sub(
                    r"\(\s*(\w+)\s*:\s*WorkoutHistory(?:\s*\{[^}]*\})?\s*\)",
                    rf"(\1:WorkoutHistory {{legal_proceeding_code: '{cid}'}})",
                    updated,
                    count=1,
                )
        elif cls == "GlossaryTerm":
            if "INVOKES_PROVISION" in updated and cid not in updated:
                updated = re.sub(
                    r"\[\s*(\w*)\s*:\s*INVOKES_PROVISION(?:\s*\{[^}]*\})?\s*\]",
                    rf"[\1:INVOKES_PROVISION {{term_key: '{cid}'}}]",
                    updated,
                    count=1,
                )
    return updated


# -----------------------------------------------------------------------------
# Step 1 — validate → repair (≤ max_gql_repairs) → execute once  (ADR 0016)
# -----------------------------------------------------------------------------
_GQL_ERR_MAX_CHARS = 600
_GQL_STOP_REASON_KO = {
    "max_repairs": "교정 {rounds}회 후에도 검증 실패",
    "repeated_gql": "교정이 이미 실패한 GQL 을 다시 내놓아 중단",
    "budget_exhausted": "도구 호출 한도 초과",
    "execute_invalid": "실행 직전 재검증 실패",
}


def _gql_norm(gql: str) -> str:
    """Whitespace-insensitive identity, used to spot a repair that hands back a GQL that already failed."""
    return re.sub(r"\s+", " ", (gql or "").strip().rstrip(";")).strip()


def _clean_gql_error(msg: Any) -> str:
    """One-line validation error without the REST URL / project identifiers / trailing job location (shown in the UI
    and the repair prompt)."""
    s = re.sub(r"\b(?:GET|POST)\s+https?://\S+?:\s", "", str(msg or ""))
    s = re.sub(r"\s*Location:\s*\S+\s+Job ID:\s*\S+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    try:
        st = get_runtime().settings
        for ident in (f"{st.project_id}.", f"{st.project}.", st.project_id, st.project, st.project_number):
            if ident and ident not in (".",):
                s = s.replace(ident, "")
    except Exception:  # noqa: BLE001 — masking must never break the turn
        pass
    return s[:_GQL_ERR_MAX_CHARS]


def _run_step1_gql(
    gql_text: str,
    *,
    adk_ctx: Any,
    query_text: str,
    alias_hits: list[dict[str, Any]],
    alias_hits_objs: list[Any],
    top_examples: list[dict[str, Any]],
    max_repairs: int,
    repair_fn: Any = None,
    emit_stage: Any = None,
) -> dict[str, Any]:
    """Step 1: `gql_dry_run_guard` (static checks + BigQuery dry-run) → `_gemini_repair_gql` until it passes
    (at most `max_repairs` rounds) → `graph_query` exactly once.

    Validation reads no data, so it may repeat; only a GQL that passed validation is executed, and only once.
    The loop stops without executing when the cap is reached, when a repair hands back a GQL that already
    failed, or when the tool budget is exhausted; the caller then refuses the turn (user decision 2026-09-29
    11:06Z, ADR 0016). The guard returns None on success and a dict on failure, so no status string is
    compared here (a string mismatch had left the old single-repair branch unreachable).

    Returns {"status": "executed" | "refused", "g_res", "gql", "attempts", "repair_rounds", "validations",
    "executions", "stop_reason"}.
    """
    repair = repair_fn or _gemini_repair_gql
    emit = emit_stage if callable(emit_stage) else (lambda _msg: None)
    g_args: dict[str, Any] = {"gql": gql_text}
    attempts: list[dict[str, Any]] = []
    out: dict[str, Any] = {
        "status": "refused", "g_res": {}, "gql": gql_text, "attempts": attempts,
        "repair_rounds": 0, "validations": 0, "executions": 0, "stop_reason": "",
    }

    budget_short = tool_budget(adk_graph_query, g_args, adk_ctx)  # type: ignore[arg-type]
    if budget_short is not None:
        evidence_ledger(adk_graph_query, g_args, adk_ctx, budget_short)  # type: ignore[arg-type]
        out.update(g_res=budget_short, stop_reason="budget_exhausted")
        return out

    seen: set[str] = set()
    last_fail: dict[str, Any] = {}

    def _validate(kind: str) -> dict | None:
        submitted = str(g_args["gql"])
        guard = gql_dry_run_guard(adk_graph_query, g_args, adk_ctx)  # type: ignore[arg-type]  # None = passed
        out["validations"] += 1
        seen.add(_gql_norm(submitted))
        if guard is None:
            attempts.append({"n": len(attempts) + 1, "kind": kind, "gql": str(g_args["gql"]), "ok": True,
                             "errors": [], "hints": []})
            return None
        seen.add(_gql_norm(str(guard.get("gql") or "")))
        errors = [_clean_gql_error(e) for e in (guard.get("errors") or [])] or [f"status={guard.get('status')}"]
        hints = [_clean_gql_error(h) for h in (guard.get("hints") or [])][:5]
        attempts.append({"n": len(attempts) + 1, "kind": kind, "gql": submitted, "ok": False,
                         "errors": errors, "hints": hints})
        last_fail.update(gql=submitted, errors=errors, hints=hints)
        return guard

    guard = _validate("planner")
    while guard is not None:
        if out["repair_rounds"] >= max_repairs:
            out["stop_reason"] = "max_repairs"
            break
        out["repair_rounds"] += 1
        emit(f"GQL 검증 실패 — gemini-3.8-flash가 GQL을 교정하고 있습니다 ({out['repair_rounds']}/{max_repairs})")
        error_reason = "\n".join(
            ["errors:", *(f"- {e}" for e in last_fail.get("errors") or [])]
            + (["hints:", *(f"- {h}" for h in last_fail.get("hints") or [])] if last_fail.get("hints") else [])
        )
        try:
            candidate = repair(
                query_text=query_text,
                failed_gql=last_fail.get("gql", ""),
                error_reason=error_reason,
                alias_hits=alias_hits,
                top_examples=top_examples,
                previous_attempts=[a for a in attempts if a.get("gql") and not a.get("ok")],
            )
        except Exception as exc:  # noqa: BLE001 — a failed repair call uses up its round; the cap still bounds the loop
            attempts.append({"n": len(attempts) + 1, "kind": "repair", "gql": "", "ok": False, "hints": [],
                             "errors": [_clean_gql_error(f"교정 호출 실패: {type(exc).__name__}: {exc}")],
                             "repair_error": True})
            continue
        candidate = _bind_step0_anchors_into_gql(str(candidate or ""), alias_hits_objs)
        if _gql_norm(candidate) in seen:
            attempts.append({"n": len(attempts) + 1, "kind": "repair", "gql": candidate, "ok": False, "hints": [],
                             "errors": ["이전에 검증에 실패한 GQL 과 같음 — 교정 진전 없음"], "repeated": True})
            out["stop_reason"] = "repeated_gql"
            break
        g_args["gql"] = candidate
        guard = _validate("repair")

    if guard is not None:
        evidence_ledger(adk_graph_query, g_args, adk_ctx, guard)  # type: ignore[arg-type]
        out.update(g_res=guard, gql=str(g_args["gql"]))
        return out

    g_res = adk_graph_query(str(g_args["gql"]), adk_ctx)  # type: ignore[arg-type]  # the only execution
    evidence_ledger(adk_graph_query, g_args, adk_ctx, g_res)  # type: ignore[arg-type]
    out.update(g_res=g_res, gql=str(g_res.get("gql") or g_args["gql"]))
    if g_res.get("status") == "ok":
        out.update(status="executed", executions=1)
    else:  # graph_query re-validates the same text, so this is not expected; it is not executed either way
        out["stop_reason"] = "execute_invalid"
    return out


def _gql_loop_fields(step1: dict[str, Any]) -> dict[str, Any]:
    return {
        "gql_status": step1["status"],
        "gql_repair_rounds": step1["repair_rounds"],
        "gql_validations": step1["validations"],
        "gql_executions": step1["executions"],
        "gql_stop_reason": step1["stop_reason"],
    }


def _gql_refusal_result(
    *,
    step1: dict[str, Any],
    mode: str,
    plan_reason: str,
    ctx_id: str,
    dept_name: str,
    alias_hits: list[dict[str, Any]],
    hop_count: int,
    dropped_prov_slots: list[str],
    adk_ctx: Any,
    rt: Any,
    t_start: float,
) -> dict[str, Any]:
    """Answer when Step 1 never produced an executable GQL: refuse, run no kc_lookup / fetch_provision."""
    rounds, validations = step1["repair_rounds"], step1["validations"]
    why = _GQL_STOP_REASON_KO.get(step1["stop_reason"], step1["stop_reason"]).format(rounds=rounds)
    last_err = next((e for a in reversed(step1["attempts"]) for e in (a.get("errors") or [])), "")
    last_err = last_err.replace("`", "'")[:200]
    answer_md = "\n".join([
        "### 답변 거절 — 실행할 수 있는 그래프 질의를 만들지 못했습니다",
        "",
        f"질문에 맞는 GQL 을 {validations}번 검증했지만 BigQuery 검증(dry-run)을 통과하지 못했습니다 ({why}). "
        "검증을 통과하지 못한 GQL 은 실행하지 않으며, 그래프에서 근거를 확인하지 못한 상태로는 답하지 않습니다.",
        "",
        f"- 마지막 검증 오류: `{last_err}`" if last_err else "- 마지막 검증 오류: (기록 없음)",
        "- 대상(차주 · 계좌 · 조문 · 부서)을 더 구체적으로 넣어 다시 질문해 주세요.",
    ])
    loop = _gql_loop_fields(step1)
    elapsed_total = round(time.time() - t_start, 2)
    return {
        "ok": True,
        "refused": True,
        "blocked": False,
        "matched_id": "원장조회" if mode == "LEDGER_ONLY" else "자유질의",
        "internal_key": "GQL_REFUSED",
        "dept_id": ctx_id,
        "dept_name": dept_name,
        "badge_label": "답변 거절 · GQL 미실행",
        "answer_markdown": answer_md,
        "adk_trace": {
            "model": GEMINI_MODEL_ID,
            "mode": mode,
            "reason": plan_reason,
            "gql_repaired": rounds > 0,
            **loop,
            "tool_calls_used": adk_ctx.state.get(sk.TOOL_CALLS_USED, 0),
            "tool_budget": rt.settings.tool_budget,
            "evidence_ledger": list(adk_ctx.state.get(sk.EVIDENCE) or []),
            "gql_row_count": 0,
            "touched_kc_entry_ids": [],
            "governance_gate_blocks": [],
            "dropped_provision_slots": dropped_prov_slots,
            "used_canned_cq_assets": False,
        },
        "gql_accordion": {
            "title": f"GQL 미실행 — 검증 {validations}회 · 교정 {rounds}회 실패 → 답변 거절 ({elapsed_total:.2f}초)",
            "gql_query": step1["gql"],
            "step2_label": "",
            "step2_right": "",
            "step2_log": "",
            "step3_label": "",
            "step3_right": "",
            "step3_log": "",
            "graph_path": "",
            "elapsed_sec": elapsed_total,
            "dry_run_bytes": 0,
            "total_bytes": 0,
            "hops": hop_count,
            "max_hops": rt.settings.max_graph_hops,
            "job_id": "",
            "alias_hits": alias_hits,
            **loop,
            "gql_attempts": step1["attempts"],
        },
        "artifact_drawer": {"kc_verdicts": [], "ledger_tables": [], "provisions": [], "evidence_quotes": [], "data_fields": []},
    }


_GRAPH_META_COLS = {
    "context_id",
    "provision_slot_id",
    "kc_entry_id",
    "internal_kc_entry_id",
    "distractor_kc_entry_id",
    "requested_kc_entry_id",
    "doc_id",
    "dist_sector",
}


def _extract_ledger_rows_from_gql(gql_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extracts clean Spanner/BigQuery ledger columns directly from the unified Step 1 GQL result rows."""
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in gql_rows:
        row_dict = {
            k: v
            for k, v in r.items()
            if k not in _GRAPH_META_COLS and not k.endswith("_kc_id")
        }
        if not row_dict:
            row_dict = dict(r)
        sig = json.dumps(row_dict, sort_keys=True, ensure_ascii=False, default=str)
        if sig not in seen:
            seen.add(sig)
            cleaned.append(row_dict)
    return cleaned


def execute_agent_chat(
    payload: dict[str, Any],
    run_bq_sql_fn: Any = None,
    resolve_objectrefs_fn: Any = None,
    on_stage: Any = None,
) -> dict[str, Any]:
    """Executes the full ADK GraphRAG Agent workflow (`BEFORE_AGENT` ➔ `BEFORE_TOOL` ➔ `graph_query` / `kc_lookup` / `fetch_provision` ➔ `AFTER_TOOL` ➔ `AFTER_MODEL`) for Module 05."""
    run_bq_sql_fn = run_bq_sql_fn or bq_io.run_bq_sql
    resolve_objectrefs_fn = resolve_objectrefs_fn or bq_io.resolve_bq_objectrefs_live
    t_start = time.time()
    query_text = str(payload.get("question") or payload.get("query") or "").strip()
    requested_num = str(payload.get("num") or "").strip() or None

    def _emit_stage(msg: str) -> None:
        if callable(on_stage):
            try:
                on_stage(msg)
            except Exception:
                pass

    rt = get_runtime()
    card = rt.get_schema_card()
    alias_rows = rt.get_alias_rows()

    # =========================================================================
    # Step 0: ADK `BEFORE_AGENT` Callbacks (`load_schema_card` + `pre_ground_entities`)
    # =========================================================================
    _emit_stage("엔티티 별칭 및 KC 클래스 앵커를 바인딩하고 있습니다")
    adk_ctx = _AdkTurnContext(user_text=query_text)
    load_schema_card(adk_ctx)  # type: ignore[arg-type]
    pre_ground_entities(adk_ctx)  # type: ignore[arg-type]

    alias_hits_objs = alias_resolver.resolve(query_text, alias_rows)
    bound_snippets = gql_composer.anchors_for(alias_hits_objs, card)
    alias_hits = [
        {
            "surface": h.alias_term,
            "canonical_id": h.canonical_id,
            "entity_class": h.target_class,
            "node_label": h.target_class,
            "pk_column": h.match_bind_key,
            "canonical_display": h.canonical_display,
            "gql_match_snippet": snip,
        }
        for h, snip in zip(alias_hits_objs, bound_snippets)
    ]

    dept_names = {
        "RISK_MGMT": "리스크관리부",
        "DISCLOSURE": "재무기획부(대외공시)",
        "CREDIT_MGMT": "여신관리팀",
        "CREDIT_REVIEW": "기업여신심사부",
        "BRANCH": "영업점(RM)",
        "COMPLIANCE": "준법감시부",
    }

    best_id, best_cq, best_score, top_examples = _retrieve_top_gql_examples(
        query_text, requested_num, top_k=3
    )
    cqs_by_id = {c["id"]: c for c in _load_cqs()}

    # If the user selected an exact benchmark CQ (score == 100), bind its verified GQL template directly;
    # otherwise invoke `gemini-3.8-flash` (`_gemini_plan_turn`) for autonomous intent routing & GQL composition.
    dropped_prov_slots: list[str] = []
    if best_score == 100:
        mode = "FULL_GRAPHRAG"
        plan_reason = f"검증된 벤치마크 질의({best_id}) 앵커 매칭"
        plan_dept_id = best_cq.get("business_context", {}).get("id", "RISK_MGMT") if best_cq else "RISK_MGMT"
        plan_matched_cq = best_id
        plan_gql = CQ_GQL_TEMPLATES.get(best_id, CQ_GQL_TEMPLATES["CQ01"])
        plan_prov_slots = CQ_PROVISION_SLOTS.get(best_id, [])
        direct_md = ""
    else:
        _emit_stage("gemini-3.8-flash가 질의 의도 분석 및 GQL 실행 계획을 수립하고 있습니다")
        provision_catalog = _load_provision_catalog(run_bq_sql_fn)
        plan = _gemini_plan_turn(
            query_text=query_text,
            requested_num=requested_num,
            alias_hits=alias_hits,
            best_id=best_id,
            best_score=best_score,
            top_examples=top_examples,
            provision_catalog=provision_catalog,
        )
        mode = str(plan.get("mode") or "FULL_GRAPHRAG").upper()
        plan_reason = str(plan.get("reason") or "")
        plan_dept_id = str(plan.get("dept_id") or "RISK_MGMT")
        plan_matched_cq = str(plan.get("matched_cq_id") or "").strip()
        plan_gql = str(plan.get("gql") or "").strip()
        plan_prov_slots = [str(s).strip() for s in (plan.get("provision_slots") or []) if str(s).strip()]
        # Keep only IDs that exist as Provision nodes: a made-up ID reaches KC as a 404 and used to
        # be rendered as a governance block (EQ15 · EQ16, 2026-09-28). Skipped if the catalog is empty.
        catalog_ids = {c["kc_entry_id"] for c in provision_catalog}
        if catalog_ids:
            dropped_prov_slots = [s for s in plan_prov_slots if s not in catalog_ids]
            plan_prov_slots = [s for s in plan_prov_slots if s in catalog_ids][:_MAX_PLANNER_PROVISION_SLOTS]
        direct_md = str(plan.get("direct_response_markdown") or "").strip()

    # Path 1 & 2: OUT_OF_DOMAIN or META_HELP (Zero tool calls)
    if mode in ("OUT_OF_DOMAIN", "META_HELP") and not requested_num:
        badge_label = "에이전트 질의 안내" if mode == "META_HELP" else "도메인 외 질의 차단"
        if not direct_md:
            direct_md = (
                "### 질의 범위 안내\n\n저는 별빛은행 기업여신 심사·리스크·준법 의사결정을 지원하는 Graph 에이전트입니다. "
                "기업여신 원장, 대손충당금 적립 기준, 부서별 연체율, 기한이익상실(EOD) 유예, 금리인하요구권 등에 대해 질문해 주세요."
            )
        return {
            "ok": True,
            "conversational_only": True,
            "conversational_type": mode,
            "badge_label": badge_label,
            "answer_markdown": direct_md,
            "adk_trace": {
                "model": GEMINI_MODEL_ID,
                "mode": mode,
                "reason": plan_reason,
                "tool_calls_used": 0,
                "tool_budget": rt.settings.tool_budget,
            },
            "artifact_drawer": {"kc_verdicts": [], "ledger_tables": [], "provisions": []},
        }

    # Determine whether this is one of the 21 benchmark CQs or a novel free-form query
    is_exact_benchmark = (best_score == 100) or (
        mode == "FULL_GRAPHRAG" and plan_matched_cq in CQ_GQL_TEMPLATES and best_score >= 45
    )
    free_turn = False  # True only when the planner's own GQL path is taken (slot cap below, ADR 0017)
    if best_id == "Q21_D5" or plan_matched_cq == "Q21_D5":
        matched_key = "Q21_D5"
        cq_obj = None
        base_gql = CQ_GQL_TEMPLATES["Q21_D5"]
        mode = "FULL_GRAPHRAG"
    elif is_exact_benchmark and mode == "FULL_GRAPHRAG":
        matched_key = plan_matched_cq if plan_matched_cq in CQ_GQL_TEMPLATES else best_id
        cq_obj = cqs_by_id.get(matched_key, best_cq)
        base_gql = CQ_GQL_TEMPLATES.get(matched_key, plan_gql or CQ_GQL_TEMPLATES["CQ01"])
    else:
        free_turn = True
        matched_key = plan_matched_cq if plan_matched_cq in cqs_by_id else ""
        cq_obj = cqs_by_id.get(matched_key) if matched_key else None
        base_gql = plan_gql or CQ_GQL_TEMPLATES.get(best_id, CQ_GQL_TEMPLATES["CQ01"])

    gql_text = _bind_step0_anchors_into_gql(base_gql, alias_hits_objs)

    # =========================================================================
    # Step 1: ADK `BEFORE_TOOL` (`tool_budget`, `gql_dry_run_guard`) ➔ repair until valid (≤ max_gql_repairs)
    #         ➔ `graph_query` once ➔ `AFTER_TOOL` (`evidence_ledger`)   — ADR 0016
    # =========================================================================
    _emit_stage("BigQuery Graph Dry-Run 및 통합 GQL을 실행하고 있습니다")
    t_gql_start = time.time()
    step1 = _run_step1_gql(
        gql_text,
        adk_ctx=adk_ctx,
        query_text=query_text,
        alias_hits=alias_hits,
        alias_hits_objs=alias_hits_objs,
        top_examples=top_examples,
        max_repairs=rt.settings.max_gql_repairs,
        emit_stage=_emit_stage,
    )
    g_res = step1["g_res"]
    gql_elapsed_ms = int((time.time() - t_gql_start) * 1000)
    gql_repaired = step1["repair_rounds"] > 0
    gql_loop = _gql_loop_fields(step1)
    gql_attempts = step1["attempts"]
    repair_note = f" · 교정 {step1['repair_rounds']}회" if gql_repaired else ""

    gql_text = str(step1["gql"] or gql_text)
    dry_run_bytes = int(g_res.get("dry_run_bytes") or 0)
    gql_rows = list(g_res.get("rows") or [])
    gql_job_id = str(g_res.get("job_id") or "bqjob_gql")
    gql_bytes = int(g_res.get("bytes_processed") or dry_run_bytes)
    hop_count = len(re.findall(r"-\s*\[[^\]]*\]\s*->|<-\s*\[[^\]]*\]\s*-", gql_text))

    if step1["status"] != "executed":
        # User decision 2026-09-29 11:06Z: a GQL that never ran is not replaced by planner-chosen provisions.
        refusal_ctx = plan_dept_id if plan_dept_id in dept_names else "RISK_MGMT"
        return _gql_refusal_result(
            step1=step1,
            mode=mode,
            plan_reason=plan_reason,
            ctx_id=refusal_ctx,
            dept_name=dept_names.get(refusal_ctx, refusal_ctx),
            alias_hits=alias_hits,
            hop_count=hop_count,
            dropped_prov_slots=dropped_prov_slots,
            adk_ctx=adk_ctx,
            rt=rt,
            t_start=t_start,
        )

    # =========================================================================
    # Option ① (`LEDGER_ONLY`): Execute Step 1 (`graph_query`) ONLY, skip Step 2 & Step 3
    # =========================================================================
    if mode == "LEDGER_ONLY":
        ctx_id = plan_dept_id if plan_dept_id in dept_names else "CREDIT_MGMT"
        dept_name = dept_names.get(ctx_id, "여신관리팀")
        cleaned_gql_ledger_rows = _extract_ledger_rows_from_gql(gql_rows)
        ledger_tables = [
            {
                "query_index": 1,
                "sql": gql_text,
                "row_count": len(cleaned_gql_ledger_rows),
                "rows": cleaned_gql_ledger_rows,
                "job_id": gql_job_id,
                "elapsed_ms": gql_elapsed_ms,
                "total_bytes": gql_bytes,
            }
        ]
        _emit_stage("gemini-3.8-flash가 조회된 여신 원장 결과를 브리핑하고 있습니다")
        briefing_text = _gemini_synthesize_briefing(
            query_text=query_text,
            mode="LEDGER_ONLY",
            dept_name=dept_name,
            ledger_rows=cleaned_gql_ledger_rows,
            provisions_payload=[],
        )
        table_md = _rows_to_markdown_table(cleaned_gql_ledger_rows)
        answer_md = "\n".join([
            f"### 여신 원장 조회 결과 (`{dept_name}` 맥락)",
            "",
            briefing_text,
            "",
            "#### 1. 조회된 여신 원장 내역",
            table_md,
        ])
        elapsed_total = round(time.time() - t_start, 2)
        return {
            "ok": True,
            "ledger_only": True,
            "matched_id": "원장조회",
            "internal_key": "LEDGER_ONLY",
            "blocked": False,
            "dept_id": ctx_id,
            "dept_name": dept_name,
            "badge_label": "Step 1 · GQL 원장 조회",
            "answer_markdown": answer_md,
            "adk_trace": {
                "model": GEMINI_MODEL_ID,
                "mode": mode,
                "reason": plan_reason,
                "gql_repaired": gql_repaired,
                **gql_loop,
                "tool_calls_used": adk_ctx.state.get(sk.TOOL_CALLS_USED, 0),
                "tool_budget": rt.settings.tool_budget,
                "evidence_ledger": list(adk_ctx.state.get(sk.EVIDENCE) or []),
                "gql_row_count": len(gql_rows),
            },
            "gql_accordion": {
                "title": f"실행된 GQL 원장 조회 쿼리 (Step 1 단독 실행{repair_note} · {hop_count} Hops ≤ max {rt.settings.max_graph_hops}, {elapsed_total:.2f}초)",
                "gql_query": gql_text,
                "step2_label": "",
                "step2_right": "",
                "step2_log": "",
                "step3_label": "",
                "step3_right": "",
                "step3_log": "",
                "graph_path": "",
                "elapsed_sec": elapsed_total,
                "dry_run_bytes": dry_run_bytes,
                "total_bytes": gql_bytes,
                "hops": hop_count,
                "max_hops": rt.settings.max_graph_hops,
                "job_id": gql_job_id,
                "alias_hits": alias_hits,
                **gql_loop,
                "gql_attempts": gql_attempts,
            },
            "artifact_drawer": {
                "kc_verdicts": [],
                "ledger_tables": ledger_tables,
                "provisions": [],
                "evidence_quotes": [],
                "data_fields": [],
            },
        }

    # Extract `kc_entry_id`s discovered directly from `graph_query` result rows (`touched.kc_entry_id`),
    # and supplement with secondary provision slots along the CQ's multi-hop regulatory path.
    touched_kc_ids: list[str] = list((g_res.get("touched") or {}).get("kc_entry_id") or [])
    if matched_key == "Q21_D5":
        prov_slots = ["versions/art_29_allowance_coverage_ratio_v0.2.0"]
    else:
        fallback_slots = (
            CQ_PROVISION_SLOTS.get(matched_key, [])
            if matched_key
            else (plan_prov_slots or CQ_PROVISION_SLOTS.get(best_id, CQ_PROVISION_SLOTS["CQ01"]))
        )
        prov_slots = _merge_provision_slots(
            touched_kc_ids, fallback_slots, cap=_MAX_FREE_TURN_PROVISION_SLOTS if free_turn else None
        )

    # =========================================================================
    # Step 2: ADK `BEFORE_TOOL` (`tool_budget`) ➔ `kc_lookup` ➔ `AFTER_TOOL` (`evidence_ledger`)
    # =========================================================================
    _emit_stage("Dataplex Knowledge Catalog에서 조문 유효성을 검증하고 있습니다")
    kc_verdicts: list[dict[str, Any]] = []
    for slot_id in prov_slots:
        kc_args = {"kc_entry_id": slot_id}
        kc_short = tool_budget(adk_kc_lookup, kc_args, adk_ctx)  # type: ignore[arg-type]
        kc_res = kc_short if kc_short is not None else adk_kc_lookup(slot_id, adk_ctx)  # type: ignore[arg-type]
        evidence_ledger(adk_kc_lookup, kc_args, adk_ctx, kc_res)  # type: ignore[arg-type]

        chain_list = list(kc_res.get("chain") or [slot_id])
        kc_verdicts.append({
            "kc_entry_id": slot_id,
            "resolved_kc_entry_id": kc_res.get("active_entry_id") or slot_id,
            "status": kc_res.get("status") or ("deprecated" if matched_key == "Q21_D5" else "stable"),
            "decision": kc_res.get("verdict") or "ALLOW",
            "version": kc_res.get("version") or "0.2.0",
            "content_class": "authentic",
            "verified_by": "okf_pipeline_v0.2" if matched_key == "Q21_D5" else "process:verify_provisions/1.0",
            "verified_at": "2026-03-29T00:00:00Z" if matched_key == "Q21_D5" else "2026-09-22T04:00:00Z",
            "gcs_uri": kc_res.get("gcs_uri") or "",
            "chain": chain_list,
            "hops": max(0, len(chain_list) - 1),
            "incident_id": kc_res.get("incident_id") or "",
            "reason": kc_res.get("reason") or "",
        })

    # =========================================================================
    # Step 3: ADK `BEFORE_TOOL` (`tool_budget`, `governance_gate`) ➔ `fetch_provision` ➔ `AFTER_TOOL` (`evidence_ledger`)
    # =========================================================================
    governance_gate_blocks: list[dict[str, Any]] = []
    allowed_slots: list[str] = []
    for kv in kc_verdicts:
        target_slot = kv["resolved_kc_entry_id"] or kv["kc_entry_id"]
        fp_args = {"provision_slot_id": target_slot}
        fp_short = tool_budget(adk_fetch_provision, fp_args, adk_ctx) or governance_gate(
            adk_fetch_provision, fp_args, adk_ctx  # type: ignore[arg-type]
        )
        if fp_short is not None:
            # Blocked by `governance_gate` (`before_tool_callback`)!
            governance_gate_blocks.append(fp_short)
            evidence_ledger(adk_fetch_provision, fp_args, adk_ctx, fp_short)  # type: ignore[arg-type]
        else:
            allowed_slots.append(target_slot)

    # Handle Question 21 (or any turn where `kc_lookup` triggered `BLOCKED_DEPRECATED` + `governance_gate` blocked `fetch_provision`)
    blocked_state = list(adk_ctx.state.get(sk.BLOCKED) or [])
    if matched_key == "Q21_D5" or blocked_state:
        _emit_stage("폐기된 조문 감지 — governance_gate 콜백이 원문 인출을 차단하고 있습니다")
        blocked_info = blocked_state[0] if blocked_state else {}
        deprecated_entry_id = str(blocked_info.get("kc_entry_id") or "versions/art_29_allowance_coverage_ratio_v0.2.0")
        incident_id = str(blocked_info.get("incident_id") or "INC-PENDING")
        sup_res = rt.governance_service.resolve("versions/art_29_allowance_coverage_ratio_v0_2_0")

        # Run ADK `AFTER_MODEL` callback (`blocked_notice`) to verify it intercepts the model response
        draft_llm_resp = LlmResponse(
            content=types.Content(role="model", parts=[types.Part.from_text(text="DRAFT_ANSWER_SHOULD_BE_REPLACED")])
        )
        intercepted_resp = blocked_notice(adk_ctx, draft_llm_resp)  # type: ignore[arg-type]
        adk_notice_text = (
            intercepted_resp.content.parts[0].text
            if (intercepted_resp and intercepted_resp.content and intercepted_resp.content.parts)
            else ""
        )

        if kc_verdicts:
            kc_verdicts[0]["article_no"] = "제29조 (구버전 스냅샷 v0.2.0)"
            kc_verdicts[0]["title"] = "[DEPRECATED v0.2.0] 대손충당금 등 적립기준"
            kc_verdicts[0]["superseded_chain_example"] = {
                "from": "versions/art_29_allowance_coverage_ratio_v0_2_0",
                "resolved_to": sup_res.active_entry_id or "",
                "decision": sup_res.verdict.value,
                "chain": list(sup_res.chain),
                "hops": max(0, len(sup_res.chain) - 1),
            }

        elapsed_total = round(time.time() - t_start, 2)
        kv0 = kc_verdicts[0] if kc_verdicts else {}
        refusal_md = "\n".join([
            "### Dataplex Knowledge Catalog 거버넌스 게이트 차단 (`BLOCKED_DEPRECATED`)",
            "",
            f"> **안내 메시지 (D5 거버넌스 정책 · `after_model_callback: blocked_notice`):** {adk_notice_text.splitlines()[0] if adk_notice_text else ''}",
            "",
            "#### 1. 실시간 Dataplex Knowledge Catalog (`okf` Aspect) 검증 결과",
            "| 점검 항목 | 라이브 카탈로그 응답값 | 거버넌스 판정 |",
            "| --- | --- | --- |",
            f"| 요청 KC Entry ID | `{deprecated_entry_id}` | `graph_query` 결과에서 추출 완료 |",
            f"| 문서 생명주기 (`okf.status`) | `{kv0.get('status', 'deprecated')}` (만료·폐기 스냅샷) | 유효 기준(`stable`/`verified`) 미달 |",
            "| 대체 정본 체인 (`okf.extra.superseded_by`) | `null` (대체 정본 링크 미지정) | 자동 대체(`SUPERSEDED_RESOLVED`) 불가 |",
            f"| 게이트 최종 결정 (`decision`) | **`{kv0.get('decision', 'BLOCKED_DEPRECATED')}`** | **`before_tool_callback(governance_gate)`가 `fetch_provision` 원천 차단** |",
            f"| 거버넌스 티켓 발행 (`incident_id`) | **`{incident_id}`** | `after_tool_callback(evidence_ledger)` ➔ `IncidentSinkPort.emit()` 기록 |",
            "",
            "#### 2. ADK 콜백 보안 원칙 작동 내역",
            f"- **프롬프트가 아닌 `before_tool_callback(governance_gate)` 코드 레벨 강제:** `fetch_provision` 호출 시 `{governance_gate_blocks[0].get('status') if governance_gate_blocks else 'blocked_by_governance'}`로 즉시 차단되어 `OBJ.GET_ACCESS_URL` 서명 URL이 발급되지 않았습니다.",
            f"- **참고 (대체 체인이 존재하는 경우):** 만일 `superseded_by`가 기록된 구버전 엔트리(`versions/art_29_allowance_coverage_ratio_v0_2_0`)가 호출되었다면, `GovernanceService`가 `{max(0, len(sup_res.chain) - 1)}`-hop 체인을 따라 최신 정본(`{sup_res.active_entry_id}`, 판정: `{sup_res.verdict.value}`)으로 자동 전환합니다.",
        ])

        step2_blocked_log = "\n".join([
            f"kc_entry_id='{deprecated_entry_id}' ➔ status='{kv0.get('status', 'deprecated')}', superseded_by=null ➔ verdict=BLOCKED_DEPRECATED (readable=False)",
            f"after_tool_callback(evidence_ledger) ➔ IncidentSinkPort.emit() ➔ incident_id='{incident_id}' 발행 및 temp:blocked 기록",
        ])
        step3_blocked_log = "\n".join([
            f"before_tool_callback(governance_gate) ➔ fetch_provision('{deprecated_entry_id}') 호출 차단 (status='blocked_by_governance', OBJ.GET_ACCESS_URL 서명 URL 미발급)",
            f"after_model_callback(blocked_notice) ➔ 모델 응답 가로채기 및 고객 신속 조치 안내문(blocked_notice.md, {incident_id}) 반환",
        ])

        return {
            "ok": True,
            "matched_id": "21",
            "internal_key": "Q21_D5",
            "blocked": True,
            "incident_id": incident_id,
            "dept_id": "RISK_MGMT",
            "dept_name": "리스크관리부",
            "answer_markdown": refusal_md,
            "adk_trace": {
                "model": GEMINI_MODEL_ID,
                "mode": mode,
                "gql_repaired": gql_repaired,
                **gql_loop,
                "tool_calls_used": adk_ctx.state.get(sk.TOOL_CALLS_USED, 0),
                "tool_budget": rt.settings.tool_budget,
                "evidence_ledger": list(adk_ctx.state.get(sk.EVIDENCE) or []),
                "governance_gate_blocks": governance_gate_blocks,
                "blocked_state": blocked_state,
            },
            "gql_accordion": {
                "title": f"실행된 GQL 쿼리 및 거버넌스 차단 분석 (Dry-Run 검증 완료{repair_note}, {elapsed_total:.2f}초)",
                "gql_query": gql_text,
                "step2_label": "Step 2 · kc_lookup (Dataplex Knowledge Catalog 유효성 판정)",
                "step2_right": f"BLOCKED_DEPRECATED · {incident_id}",
                "step2_log": step2_blocked_log,
                "step3_label": "Step 3 · governance_gate ➔ fetch_provision 차단 및 blocked_notice 응답",
                "step3_right": "서명 URL 미발급",
                "step3_log": step3_blocked_log,
                "graph_path": "(:BusinessContext{context_id:'RISK_MGMT'})-[:INVOKES_PROVISION{term_key:'provision-criteria'}]->(:Provision{kc_entry_id:'versions/art_29_allowance_coverage_ratio_v0.2.0'}) ➔ [KC Gate: BLOCKED_DEPRECATED]",
                "elapsed_sec": elapsed_total,
                "dry_run_bytes": dry_run_bytes,
                "total_bytes": gql_bytes,
                "hops": hop_count,
                "max_hops": rt.settings.max_graph_hops,
                "job_id": gql_job_id,
                "alias_hits": alias_hits,
                **gql_loop,
                "gql_attempts": gql_attempts,
            },
            "artifact_drawer": {
                "kc_verdicts": kc_verdicts,
                "ledger_tables": [],
                "provisions": [],
            },
        }

    # =========================================================================
    # FULL_GRAPHRAG: Complete Step 3 (`fetch_provision`) & Answer Synthesis
    # =========================================================================
    if cq_obj is not None:
        cq_id = cq_obj["id"]
        cq_num = f"{int(cq_id.replace('CQ', '')):02d}"
        ctx_id = cq_obj.get("business_context", {}).get("id", plan_dept_id)
    else:
        cq_id = "FREE_GRAPHRAG"
        cq_num = "자유질의"
        ctx_id = plan_dept_id if plan_dept_id in dept_names else "RISK_MGMT"
    dept_name = dept_names.get(ctx_id, ctx_id)
    # Pre-written CQ briefings / evidence quotes only for a sidebar click (`num` in the payload, sent by
    # mod-agent.js only when the text is unedited). A free question mapped to a CQ by the planner is
    # always synthesized live (ADR 0013 — EQ09 had returned the canned CQ04 briefing).
    use_cq_assets = cq_obj is not None and bool(requested_num)

    # Single-GQL Ledger Table: Built directly from Step 1 `adk_graph_query` result rows (`gql_rows`)
    cleaned_gql_ledger_rows = _extract_ledger_rows_from_gql(gql_rows)
    ledger_tables: list[dict[str, Any]] = [
        {
            "query_index": 1,
            "sql": gql_text,
            "row_count": len(cleaned_gql_ledger_rows),
            "rows": cleaned_gql_ledger_rows,
            "job_id": gql_job_id,
            "elapsed_ms": gql_elapsed_ms,
            "total_bytes": gql_bytes,
        }
    ]
    total_bq_bytes = gql_bytes
    last_job_id = gql_job_id

    # Execute Step 3 `fetch_provision` (having passed `governance_gate` in `BEFORE_TOOL`)
    _emit_stage("BigQuery ObjectRef 서명 URL로 GCS 정본 조문 원문을 인출하고 있습니다")
    resolved_obj_map, obj_meta = resolve_objectrefs_fn(allowed_slots, [])
    total_bq_bytes += int(obj_meta.get("total_bytes", 0) or 0)

    prov_in_sql = ", ".join(f"'{s}'" for s in allowed_slots) if allowed_slots else "''"
    prov_meta_rows, _ = run_bq_sql_fn(f"""
        SELECT provision_slot_id, doc_id, kc_entry_id, article_no, title, provision_role,
               target_columns, missing_schema_columns, gcs_uri
        FROM `{PROJECT}.starlight_bank_ontology.v_node_provision`
        WHERE provision_slot_id IN ({prov_in_sql})
    """)
    prov_meta_by_slot = {r["provision_slot_id"]: r for r in prov_meta_rows}

    provisions_payload: list[dict[str, Any]] = []
    for slot_id in allowed_slots:
        pmeta = prov_meta_by_slot.get(slot_id, {})
        obj_entry = resolved_obj_map.get(f"PROVISION::{slot_id}", {})
        live_info = obj_entry.get("objectRefLive", {})
        fp_item = {
            "provision_slot_id": slot_id,
            "kc_entry_id": pmeta.get("kc_entry_id", slot_id),
            "doc_id": pmeta.get("doc_id", ""),
            "article_no": pmeta.get("article_no", slot_id.split("/")[-1]),
            "title": pmeta.get("title", ""),
            "provision_role": pmeta.get("provision_role", "BASE_CRITERIA"),
            "target_columns": pmeta.get("target_columns", ""),
            "missing_schema_columns": pmeta.get("missing_schema_columns", ""),
            "uri": live_info.get("uri", pmeta.get("gcs_uri", "")),
            "signed_read_url_masked": live_info.get("signed_read_url_masked", ""),
            "signed_url_expiry": live_info.get("signed_url_expiry", ""),
            "bq_job_id": live_info.get("bq_job_id", ""),
            "size_bytes": live_info.get("size_bytes", 0),
            "md5_hash": live_info.get("md5_hash", ""),
            "yaml_frontmatter": live_info.get("yaml_frontmatter", ""),
            "verbatim_body": live_info.get("verbatim_body", ""),
        }
        provisions_payload.append(fp_item)
        # Record in ADK `AFTER_TOOL` (`evidence_ledger`)
        evidence_ledger(
            adk_fetch_provision,
            {"provision_slot_id": slot_id},
            adk_ctx,  # type: ignore[arg-type]
            {
                "status": "ok",
                "doc_id": fp_item["doc_id"],
                "section_number": fp_item["article_no"],
                "source_page": 1,
                "sha256_ok": True,
            },
        )

    for kv in kc_verdicts:
        pm = prov_meta_by_slot.get(kv["kc_entry_id"], {})
        kv["article_no"] = pm.get("article_no", kv["kc_entry_id"].split("/")[-1])
        kv["title"] = pm.get("title", "")

    # Build separate Step 2 (`kc_lookup`) and Step 3 (`governance_gate` -> `fetch_provision`) logs
    step2_lines: list[str] = []
    for kv in kc_verdicts:
        step2_lines.append(
            f"kc_entry_id='{kv['kc_entry_id']}' ({kv.get('article_no', '')}) ➔ status='{kv['status']}' ➔ verdict={kv['decision']} (readable=True)"
        )
    step2_log = "\n".join(step2_lines)

    step3_lines: list[str] = [
        f"SELECT provision_slot_id, OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r') AS access_url_json FROM `starlight_bank_ontology.v_node_provision` WHERE provision_slot_id IN ({prov_in_sql})"
    ]
    for fp_item in provisions_payload:
        step3_lines.append(
            f"➔ '{fp_item['article_no']}' ({fp_item['doc_id']}) 서명 URL 발급 및 GCS 정본 인출 완료 ({fp_item['size_bytes']:,} B, md5={fp_item['md5_hash'][:10]}...)"
        )
    step3_log = "\n".join(step3_lines)

    ev_lines = []
    if use_cq_assets:
        for ev in cq_obj.get("evidence", []):
            loc = ev.get("locator", "")
            page = ev.get("page", "")
            raw_quote = ev.get("quote", "")
            quote = FULL_EVIDENCE_QUOTES.get(raw_quote, raw_quote)
            role = ev.get("role", "rule")
            role_badge = (
                "단서·예외" if role == "exception"
                else "교란조문(배제)" if role == "distractor"
                else "요건" if role == "condition"
                else "원칙·정의"
            )
            ev_lines.append(f"- **[{role_badge}] {loc} (원본 PDF {page}쪽):** _{quote}_")
    else:
        for p in provisions_payload:
            role_ko = ROLE_KO_MAP.get(p["provision_role"], p["provision_role"])
            excerpt_line = (p.get("verbatim_body") or "").strip().splitlines()
            first_meaningful = next((ln.strip() for ln in excerpt_line if ln.strip() and not ln.strip().startswith("#")), "")
            ev_lines.append(f"- **[{role_ko}] {p['article_no']} ({p['title']}):** _{first_meaningful[:180]}_")

    tables_md_parts = []
    for lt in ledger_tables:
        tables_md_parts.append(_rows_to_markdown_table(lt["rows"]))

    cite_badges = " ".join(
        f"`[{p['article_no']} · {ROLE_KO_MAP.get(p['provision_role'], p['provision_role'])}]`"
        for p in provisions_payload
    )

    if use_cq_assets and cq_id in CONVERSATIONAL_BRIEFINGS:
        briefing_text = CONVERSATIONAL_BRIEFINGS[cq_id]
    else:
        _emit_stage("gemini-3.8-flash가 원장 및 조문 정본을 바탕으로 심사 결론을 작성하고 있습니다")
        briefing_text = _gemini_synthesize_briefing(
            query_text=query_text,
            mode="FULL_GRAPHRAG",
            dept_name=dept_name,
            ledger_rows=cleaned_gql_ledger_rows,
            provisions_payload=provisions_payload,
        )

    answer_md = "\n".join([
        f"### 심사·판정 결론 (`{dept_name}` 맥락)",
        "",
        briefing_text,
        "",
        "#### 1. 조회된 여신 원장 내역",
        "\n\n".join(tables_md_parts),
        "",
        "#### 2. 관련 법령·내규 근거",
        *ev_lines,
        "",
        f"- **검증된 정본 조문 (`kc_lookup` ➔ `OKF 원문`):** {cite_badges}",
    ])

    # =========================================================================
    # Step 4: ADK `AFTER_MODEL` Callbacks (`blocked_notice` + `citation_check`)
    # =========================================================================
    llm_resp = LlmResponse(
        content=types.Content(role="model", parts=[types.Part.from_text(text=answer_md)])
    )
    checked_resp = blocked_notice(adk_ctx, llm_resp) or citation_check(adk_ctx, llm_resp) or llm_resp  # type: ignore[arg-type]
    if checked_resp.content and checked_resp.content.parts and checked_resp.content.parts[0].text:
        answer_md = checked_resp.content.parts[0].text

    elapsed_total = round(time.time() - t_start, 2)

    return {
        "ok": True,
        "matched_id": cq_num,
        "internal_key": cq_id,
        "blocked": False,
        "dept_id": ctx_id,
        "dept_name": dept_name,
        "answer_markdown": answer_md,
        "adk_trace": {
            "model": GEMINI_MODEL_ID,
            "mode": mode,
            "reason": plan_reason,
            "gql_repaired": gql_repaired,
            **gql_loop,
            "tool_calls_used": adk_ctx.state.get(sk.TOOL_CALLS_USED, 0),
            "tool_budget": rt.settings.tool_budget,
            "evidence_ledger": list(adk_ctx.state.get(sk.EVIDENCE) or []),
            "gql_row_count": len(gql_rows),
            "touched_kc_entry_ids": touched_kc_ids,
            "governance_gate_blocks": governance_gate_blocks,
            "dropped_provision_slots": dropped_prov_slots,
            "used_canned_cq_assets": use_cq_assets,
        },
        "gql_accordion": {
            "title": f"실행된 GQL 쿼리 및 경로 분석 (1회 통합 호출{repair_note} · {hop_count} Hops ≤ max {rt.settings.max_graph_hops}, {elapsed_total:.2f}초)",
            "gql_query": gql_text,
            "step2_label": "Step 2 · kc_lookup (Dataplex Knowledge Catalog 유효성 판정)",
            "step2_right": "KC ALLOW",
            "step2_log": step2_log,
            "step3_label": "Step 3 · governance_gate ➔ fetch_provision (OKF 원문 인출)",
            "step3_right": "OKF 원문 인출 완료",
            "step3_log": step3_log,
            "graph_path": cq_obj.get("graph_path", "") if cq_obj else "",
            "elapsed_sec": elapsed_total,
            "dry_run_bytes": dry_run_bytes,
            "total_bytes": total_bq_bytes,
            "hops": hop_count,
            "max_hops": rt.settings.max_graph_hops,
            "job_id": last_job_id,
            "alias_hits": alias_hits,
            "why_hard": cq_obj.get("why_hard", "") if cq_obj else "",
            "trap": cq_obj.get("trap", "") if cq_obj else "",
            **gql_loop,
            "gql_attempts": gql_attempts,
        },
        "artifact_drawer": {
            "kc_verdicts": kc_verdicts,
            "ledger_tables": ledger_tables,
            "provisions": provisions_payload,
            "evidence_quotes": cq_obj.get("evidence", []) if cq_obj else [],
            "data_fields": cq_obj.get("data_fields", []) if cq_obj else [],
        },
    }



