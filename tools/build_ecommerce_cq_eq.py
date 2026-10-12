#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates explicit YAML manifests for K-Market (ecommerce-ontology):
  1. ecommerce/ontology/cq/competency_questions.yaml (20 CQs: CQ01..CQ20)
  2. ecommerce/ontology/eval_question/eval_questions.yaml (20 EQs: EQ01..EQ20)

All PDF evidence quotes are sliced verbatim from ecommerce/okf/verification.json
so every quote is guaranteed to match the exact page of ecommerce/data/un_data/*.pdf.
"""

from __future__ import annotations

import json
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VER_PATH = os.path.join(ROOT, "ecommerce", "okf", "verification.json")
CQ_OUT = os.path.join(ROOT, "ecommerce", "ontology", "cq", "competency_questions.yaml")
EQ_OUT = os.path.join(ROOT, "ecommerce", "ontology", "eval_question", "eval_questions.yaml")

with open(VER_PATH, "r", encoding="utf-8") as f:
    VER = json.load(f)

PROV_BY_ID: dict[str, dict] = {p["concept_id"]: p for p in VER["provisions"]}


SOURCES = {
    "01": {"file": "01_LAW_대규모유통업법_전문_2025.pdf", "authority": "binding"},
    "02": {"file": "02_FTC_대규모유통업법_판매촉진비용부담전가_심사지침_2025.pdf", "authority": "advisory"},
    "03": {"file": "03_LAW_전자상거래법_전문_2025.pdf", "authority": "binding"},
    "04": {"file": "04_FTC_전자상거래_다크패턴_및_맞춤형광고_가이드라인_2025.pdf", "authority": "advisory"},
    "05": {"file": "05_PIPC_온라인_맞춤형광고_행태정보_가이드라인_2025.pdf", "authority": "advisory"},
    "06": {"file": "06_DISTRACTOR_관세청_해외직구_목록통관_및_특송물품_고시_2025.pdf", "authority": "distractor"},
    "07": {"file": "07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf", "authority": "internal"},
    "08": {"file": "08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf", "authority": "internal"},
    "09": {"file": "09_INTERNAL_K마켙_입점브랜드_공동프로모션_정산내규_2025.pdf", "authority": "internal"},
    "10": {"file": "10_INTERNAL_K마켙_CS반품환불_및_물류SLA_보상내규_2025.pdf", "authority": "internal"},
}



def ev(concept_id: str, start_substr: str | None = None, length: int = 110) -> dict:
    """Builds a verbatim PDF evidence dict from verification.json."""
    p = PROV_BY_ID[concept_id]
    body = " ".join(p["verbatim_body"].split())
    if start_substr:
        idx = body.find(start_substr)
        if idx == -1:
            raise ValueError(f"Substring {start_substr!r} not found in {concept_id}")
        quote = body[idx : idx + length].strip()
    else:
        quote = body[:length].strip()
    doc_code = p["pdf_file"][:2]
    return {
        "doc": doc_code,
        "pdf": p["pdf_file"],
        "page": p["source_page"],
        "locator": p["section_number"],
        "section": p["section_number"],
        "authority": SOURCES[doc_code]["authority"],
        "role": "rule",
        "quote": quote,
    }


def df(store: str, table: str, column: str, role: str) -> dict:
    return {"store": store, "table": table, "column": column, "role": role}



# Shorthand concept IDs (all 36 provisions available)
P_LAW01_DEF = "regulations/01_law_large_retail_fair_trade/ch01_general_and_contract/art_001_002_purpose_definitions"
P_LAW01_WRITTEN = "regulations/01_law_large_retail_fair_trade/ch01_general_and_contract/art_006_written_contract"
P_LAW01_PAY = "regulations/01_law_large_retail_fair_trade/ch02_payment_and_return_ban/art_008_payment_deadline"
P_LAW01_RETBAN = "regulations/01_law_large_retail_fair_trade/ch02_payment_and_return_ban/art_010_unfair_return_ban"
P_LAW01_PRIOR = "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p1_p2_prior_written_agreement"
P_LAW01_CAP50 = "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso"
P_LAW01_REC5Y = "regulations/01_law_large_retail_fair_trade/ch04_exclusivity_and_record_keeping/art_012_017_018_fair_trade_duties"

P_FTC02_SCOPE = "regulations/02_ftc_promo_cost_guideline/sec01_scope_and_prior_agreement/guide_01_02_promo_coupon_scope"
P_FTC02_PRIOR = "regulations/02_ftc_promo_cost_guideline/sec01_scope_and_prior_agreement/guide_03_prior_written_agreement_rule"
P_FTC02_CAP = "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_04_fifty_percent_cap_invalidity"
P_FTC02_VOL = "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test"

P_ECOM03_SUPPLY = "regulations/03_law_ecommerce_consumer_protection/ch01_disclosure_and_supply/ecom_art_001_013_015_disclosure_supply"
P_ECOM03_WPERIOD = "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods"
P_ECOM03_WRESTRICT = "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p2_withdrawal_restrictions"
P_ECOM03_REFUND = "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_018_refund_and_return_shipping"
P_ECOM03_DARK = "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_021_2_dark_pattern_ban"

P_DP04_PRICE = "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_001_002_price_display"
P_DP04_STOCK = "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_003_stock_truthfulness"
P_DP04_OPTIN = "regulations/04_ftc_dark_pattern_and_reco_guideline/ch02_reco_transparency_and_optin/dp_art_004_005_reco_transparency_optin"

P_PIPC05_DEF = "regulations/05_pipc_behavioral_targeting_guideline/ch01_behavioral_info_definition/pipc_art_001_002_behavioral_def"
P_PIPC05_OPTIN = "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement"
P_PIPC05_NIGHT = "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_004_005_retention_and_night_ban"

P_DIST06_SCOPE = "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_001_002_scope"
P_DIST06_FEE = "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee"

P_CRM07_OPTIN = "internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin"
P_CRM07_BUNDLE = "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle"
P_CRM07_TIER = "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule"

P_MD08_25PCT = "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail"
P_MD08_AGED = "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor"
P_MD08_EXC = "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override"

P_PRT09_PRIOR = "internal_policies/09_kmarket_vendor_promo_settlement/ch01_prior_agreement_verification/partner_art_001_002_prior_agreement"
P_PRT09_CAP = "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula"
P_PRT09_VOL = "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review"

P_CS10_REASON = "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules"
P_CS10_REFUND = "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs"
P_CS10_SLA = "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_004_fulfillment_sla_compensation"


def build_cqs() -> dict:
    questions = [
        # ---------------- THEME A (4): 초개인화 추천 · 장바구니 이탈 · 마진 가드레일 · 체화재고 ----------------
        {
            "id": "CQ01",
            "theme": "A",
            "cq_type": "multi_hop",
            "persona": "그로스마케팅본부 AI추천랩 매니저",
            "question": "장바구니 미결제 이탈 세션(`SES-1001-A`)이 발생한 VIP 회원 김서연(`USR-1001`)에게 주상품 `PRD-3001`(발마칸 코트)과 코디 보완상품 `PRD-3002`(터틀넥 니트) 번들 쿠폰을 제안할 때, 각 상품의 기본 마진율 및 체화재고 예외승인(`EXC-KM-2026-01`, 하한 10%)을 반영한 합산 최대 쿠폰 할인액과 최종 번들 제안가는 얼마인가?",
            "evidence": [ev(P_CRM07_BUNDLE), ev(P_CRM07_TIER), ev(P_MD08_25PCT), ev(P_MD08_EXC)],
            "data_fields": [
                df("spanner", "events", "event_type", "filter"),
                df("bigquery", "users", "membership_tier", "filter"),
                df("bigquery", "users", "marketing_opt_in_yn", "filter"),
                df("bigquery", "products", "cost_krw", "measure"),
                df("bigquery", "products", "retail_price_krw", "measure"),
                df("bigquery", "products", "coord_product_id", "join_key"),
                df("spanner", "inventory_items", "age_days", "filter"),
                df("spanner", "campaign_exceptions", "approved_floor_margin_pct", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  u.user_id,
  u.membership_tier,
  u.marketing_opt_in_yn,
  p1.product_id AS main_product_id,
  p1.retail_price_krw AS main_retail_krw,
  ROUND((p1.retail_price_krw - p1.cost_krw) / p1.retail_price_krw, 2) AS main_base_margin,
  p2.product_id AS coord_product_id,
  p2.retail_price_krw AS coord_retail_krw,
  ROUND((p2.retail_price_krw - p2.cost_krw) / p2.retail_price_krw, 2) AS coord_base_margin,
  inv2.age_days AS coord_age_days,
  ce.approval_id,
  ce.approved_floor_margin_pct,
  CAST(p1.retail_price_krw * 0.15 + p2.retail_price_krw * 0.15 AS INT64) AS naive_rag_discount_krw,
  CAST(p1.retail_price_krw * 0.15 + FLOOR(p2.retail_price_krw - p2.cost_krw / (1.0 - ce.approved_floor_margin_pct / 100.0)) AS INT64) AS ontology_max_discount_krw,
  CAST((p1.retail_price_krw + p2.retail_price_krw) - (p1.retail_price_krw * 0.15 + FLOOR(p2.retail_price_krw - p2.cost_krw / (1.0 - ce.approved_floor_margin_pct / 100.0))) AS INT64) AS final_bundle_price_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` e
JOIN `finance-ontology-changseop.kmarket_ecommerce.users` u ON e.user_id = u.user_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p1 ON e.product_id = p1.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p2 ON p1.coord_product_id = p2.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv2 ON p2.product_id = inv2.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce ON p2.product_id = ce.product_id AND ce.status = 'ACTIVE'
WHERE e.session_id = 'SES-1001-A' AND e.event_type = 'cart'
""".strip(),
                    "expect": {
                        "exact_rows": 1,
                        "must_contain": [
                            {
                                "user_id": "USR-1001",
                                "main_product_id": "PRD-3001",
                                "coord_product_id": "PRD-3002",
                                "approval_id": "EXC-KM-2026-01",
                                "naive_rag_discount_krw": 90000,
                                "ontology_max_discount_krw": 86666,
                                "final_bundle_price_krw": 513334,
                            }
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[INVOKES_PROVISION {term_key: 'hyper-personalized-reco'}]--> Provision",
                "UserBehaviorEvent --[LOGGED_EVENT_ON_PRODUCT]--> Product --[STOCKED_AT_INVENTORY]--> InventoryItem",
                "Product --[HAS_CAMPAIGN_EXCEPTION]--> CampaignException",
            ],
        },
        {
            "id": "CQ02",
            "theme": "A",
            "cq_type": "multi_hop",
            "persona": "그로스마케팅본부 CRM 캠페인 매니저",
            "question": "현재 물류 원장에서 실시간 가용재고가 0개인 일시품절(`avail_qty = 0`, `OUT_OF_STOCK`) 상품은 무엇이며, 공정위 다크패턴 가이드라인 제3조 및 K마켙 내규 제3조제1항에 따라 전환 추천해야 할 대체 상품(`substitute_product_id`)의 입고 경과일수(`age_days`)와 가용재고 수량, 체화재고(`age_days >= 90` & `avail_qty >= 30`) 해당 여부는 어떻게 되는가?",
            "evidence": [ev(P_DP04_STOCK), ev(P_CRM07_BUNDLE), ev(P_MD08_AGED)],
            "data_fields": [
                df("spanner", "inventory_items", "avail_qty", "filter"),
                df("spanner", "inventory_items", "stock_status", "filter"),
                df("bigquery", "products", "substitute_product_id", "join_key"),
                df("spanner", "inventory_items", "age_days", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  p.product_id AS stockout_product_id,
  inv.avail_qty AS stockout_avail_qty,
  p.substitute_product_id,
  psub.product_name AS substitute_name,
  inv_sub.age_days AS sub_age_days,
  inv_sub.avail_qty AS sub_avail_qty,
  (inv_sub.age_days >= 90 AND inv_sub.avail_qty >= 30) AS is_aged_clearance_eligible
FROM `finance-ontology-changseop.kmarket_ecommerce.products` p
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON p.product_id = inv.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` psub ON p.substitute_product_id = psub.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv_sub ON psub.product_id = inv_sub.product_id
WHERE inv.avail_qty = 0
ORDER BY p.product_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {"stockout_product_id": "PRD-3009", "substitute_product_id": "PRD-3002", "sub_age_days": 125, "sub_avail_qty": 50, "is_aged_clearance_eligible": True},
                            {"stockout_product_id": "PRD-3010", "substitute_product_id": "PRD-3011", "sub_age_days": 105, "sub_avail_qty": 45, "is_aged_clearance_eligible": True},
                        ],
                    },
                }
            ],
            "graph_path": [
                "Product --[STOCKED_AT_INVENTORY]--> InventoryItem",
                "BusinessContext --[INVOKES_PROVISION {term_key: 'clearance-exception'}]--> Provision",
            ],
        },
        {
            "id": "CQ03",
            "theme": "A",
            "cq_type": "exception_path",
            "persona": "MD본부 가격전략실 심사역",
            "question": "기본 마진율이 상시 가드레일(25.0%) 미만인 저마진 상품 3종(`PRD-3002`, `PRD-3005`, `PRD-3012`)에 대하여 입고 경과일수(`age_days`)와 캠페인 예외승인 원장(`campaign_exceptions`)의 결재 상태(`ACTIVE` vs `EXPIRED`)를 대조할 때, 실제로 마진 하한 완화 특례가 적용되는 상품과 기각/차단되는 상품은 각각 무엇인가?",
            "evidence": [ev(P_MD08_25PCT), ev(P_MD08_AGED), ev(P_MD08_EXC)],
            "data_fields": [
                df("bigquery", "products", "cost_krw", "measure"),
                df("bigquery", "products", "retail_price_krw", "measure"),
                df("spanner", "inventory_items", "age_days", "filter"),
                df("spanner", "campaign_exceptions", "target_kind", "filter"),
                df("spanner", "campaign_exceptions", "approved_floor_margin_pct", "measure"),
                df("spanner", "campaign_exceptions", "status", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  p.product_id,
  ROUND((p.retail_price_krw - p.cost_krw) / p.retail_price_krw * 100, 1) AS base_margin_pct,
  inv.age_days,
  ce.approval_id,
  ce.target_kind,
  ce.status AS exception_status,
  CASE
    WHEN ce.status = 'ACTIVE' THEN ce.approved_floor_margin_pct
    ELSE 25.0
  END AS effective_margin_floor_pct
FROM `finance-ontology-changseop.kmarket_ecommerce.products` p
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON p.product_id = inv.product_id
LEFT JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce ON p.product_id = ce.product_id
WHERE (p.retail_price_krw - p.cost_krw) / p.retail_price_krw < 0.25
ORDER BY p.product_id
""".strip(),
                    "expect": {
                        "exact_rows": 3,
                        "must_contain": [
                            {"product_id": "PRD-3002", "base_margin_pct": 22.0, "exception_status": "ACTIVE", "effective_margin_floor_pct": 10.0},
                            {"product_id": "PRD-3005", "base_margin_pct": 20.0, "exception_status": "EXPIRED", "effective_margin_floor_pct": 25.0},
                            {"product_id": "PRD-3012", "base_margin_pct": 22.0, "exception_status": "ACTIVE", "effective_margin_floor_pct": 12.0},
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[INVOKES_PROVISION {term_key: 'margin-guardrail'}]--> Provision --[HAS_EXCEPTION_PROVISO]--> Provision",
                "Product --[HAS_CAMPAIGN_EXCEPTION]--> CampaignException",
            ],
        },
        {
            "id": "CQ04",
            "theme": "A",
            "cq_type": "lookup",
            "persona": "그로스마케팅본부 데이터 엔지니어",
            "question": "장바구니 담기(`event_type = 'cart'`) 이벤트가 발생한 전체 세션 중 같은 세션 내 결제 완료(`event_type = 'purchase'`)로 이어지지 않은 미결제 이탈 세션 건수와 식별된 회원 ID 목록은 무엇인가?",
            "evidence": [ev(P_DP04_OPTIN), ev(P_CRM07_OPTIN)],
            "data_fields": [
                df("spanner", "events", "session_id", "join_key"),
                df("spanner", "events", "event_type", "filter"),
                df("spanner", "events", "user_id", "join_key"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  c.session_id,
  c.user_id,
  c.product_id,
  u.membership_tier,
  u.marketing_opt_in_yn
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` c
JOIN `finance-ontology-changseop.kmarket_ecommerce.users` u ON c.user_id = u.user_id
WHERE c.event_type = 'cart'
  AND NOT EXISTS (
    SELECT 1 FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` p
    WHERE p.session_id = c.session_id AND p.event_type = 'purchase'
  )
ORDER BY c.session_id
""".strip(),
                    "expect": {
                        "exact_rows": 5,
                        "must_contain": [
                            {"session_id": "SES-1001-A", "user_id": "USR-1001", "product_id": "PRD-3001", "marketing_opt_in_yn": "Y"},
                            {"session_id": "SES-1004-A", "user_id": "USR-1004", "product_id": "PRD-3008", "marketing_opt_in_yn": "N"},
                            {"session_id": "SES-1007-A", "user_id": "USR-1007", "product_id": "PRD-3009", "marketing_opt_in_yn": "Y"},
                        ],
                    },
                }
            ],
            "graph_path": [
                "UserBehaviorEvent --[EVALUATED_UNDER_PROVISION]--> Provision",
                "UserBehaviorEvent --[LOGGED_EVENT_ON_PRODUCT]--> Product",
            ],
        },

        # ---------------- THEME B (3): 부서·맥락별 지표 정의 분기 (Context Branching) ----------------
        {
            "id": "CQ05",
            "theme": "B",
            "cq_type": "context_branch",
            "persona": "그로스마케팅본부장 vs 고객경험(CX)본부장",
            "question": "최근 90일 내 반품 이력이 존재하는 VIP 회원 박준혁(`USR-1002`, 단순변심 반품 2건)과 GOLD 회원 이수빈(`USR-1003`, 상품불량 반품 2건)에 대하여, 전체 반품 건수를 산입하는 CS 총 반품률과 귀책사유(`CHANGE_OF_MIND`만 산입, `DEFECTIVE` 제외)를 분리하는 CRM 프로모션 제한 반품률은 각각 몇 %인가?",
            "evidence": [ev(P_CRM07_TIER), ev(P_CS10_REASON)],
            "data_fields": [
                df("spanner", "order_items", "user_id", "join_key"),
                df("spanner", "order_items", "status", "filter"),
                df("spanner", "order_items", "return_reason_cd", "filter"),
                df("bigquery", "users", "membership_tier", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  oi.user_id,
  u.user_name,
  u.membership_tier,
  COUNT(*) AS total_items,
  COUNTIF(oi.status = 'Returned') AS total_returned_items,
  ROUND(COUNTIF(oi.status = 'Returned') / COUNT(*) * 100, 1) AS cs_gross_return_rate_pct,
  COUNTIF(oi.status = 'Returned' AND oi.return_reason_cd = 'CHANGE_OF_MIND') AS change_of_mind_items,
  ROUND(COUNTIF(oi.status = 'Returned' AND oi.return_reason_cd = 'CHANGE_OF_MIND') / COUNT(*) * 100, 1) AS crm_cherrypicker_return_rate_pct
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.users` u ON oi.user_id = u.user_id
WHERE oi.user_id IN ('USR-1002', 'USR-1003')
GROUP BY oi.user_id, u.user_name, u.membership_tier
ORDER BY oi.user_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {"user_id": "USR-1002", "cs_gross_return_rate_pct": 50.0, "crm_cherrypicker_return_rate_pct": 50.0},
                            {"user_id": "USR-1003", "cs_gross_return_rate_pct": 50.0, "crm_cherrypicker_return_rate_pct": 0.0},
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[SCOPES_PORTFOLIO]--> OrderItem --[BELONGS_TO_ORDER]--> Order --[PLACED_BY_USER]--> Customer",
                "BusinessContext --[INVOKES_PROVISION {term_key: 'return-withdrawal-eligibility'}]--> Provision",
            ],
        },
        {
            "id": "CQ06",
            "theme": "B",
            "cq_type": "context_branch",
            "persona": "그로스마케팅본부 vs 파트너상생본부 정산실",
            "question": "기준일(`2026-09-29`) 현재 VIP 회원 김서연(`USR-1001`)의 주문 건에 대하여, 결제·배송 완료 즉시 산입하는 CRM 누적 구매액(`retail_price_krw` 합계)과 배송완료 후 청약철회 가능 기한(7일)이 도과한 주문만 인정하는 정산실 확정매출 정산대상 금액은 각각 얼마인가?",
            "evidence": [ev(P_ECOM03_WPERIOD), ev(P_PRT09_CAP)],
            "data_fields": [
                df("spanner", "orders", "delivered_at", "filter"),
                df("spanner", "order_items", "retail_price_krw", "measure"),
                df("spanner", "order_items", "sale_price_krw", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  oi.user_id,
  SUM(oi.retail_price_krw) AS crm_total_purchase_retail_krw,
  SUM(CASE WHEN oi.delivered_at <= '2026-09-22T23:59:59Z' THEN oi.retail_price_krw ELSE 0 END) AS settlement_confirmed_retail_krw,
  SUM(CASE WHEN oi.delivered_at > '2026-09-22T23:59:59Z' THEN oi.retail_price_krw ELSE 0 END) AS unconfirmed_within_7d_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
WHERE oi.user_id = 'USR-1001' AND oi.status = 'Complete'
GROUP BY oi.user_id
""".strip(),
                    "expect": {
                        "exact_rows": 1,
                        "must_contain": [
                            {
                                "user_id": "USR-1001",
                                "crm_total_purchase_retail_krw": 2100000,
                                "settlement_confirmed_retail_krw": 2000000,
                                "unconfirmed_within_7d_krw": 100000,
                            }
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[SCOPES_PORTFOLIO]--> OrderItem --[BELONGS_TO_ORDER]--> Order",
                "BusinessContext --[INVOKES_PROVISION {term_key: 'promo-cost-sharing'}]--> Provision",
            ],
        },
        {
            "id": "CQ07",
            "theme": "B",
            "cq_type": "context_branch",
            "persona": "풀필먼트운영실장 vs MD본부 재고관리팀장",
            "question": "스윔수트(`PRD-3006`), 실크 브라렛(`PRD-3007`), 알파인 자켓(`PRD-3008`) 3개 상품의 물류 배치(`INV-1006`~`INV-1010`)를 조회할 때, 장바구니·반품검수·결제예약 배치를 포함한 물리적 총 보관수량과 즉시 출고 가능한 `AVAILABLE` 상태 가용재고 수량의 차이는 어떠한가?",
            "evidence": [ev(P_DP04_STOCK), ev(P_CRM07_BUNDLE), ev(P_MD08_AGED)],
            "data_fields": [
                df("spanner", "inventory_items", "product_id", "join_key"),
                df("spanner", "inventory_items", "avail_qty", "measure"),
                df("spanner", "inventory_items", "stock_status", "filter"),
                df("spanner", "inventory_items", "age_days", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  product_id,
  SUM(avail_qty) AS total_physical_qty,
  SUM(CASE WHEN stock_status = 'AVAILABLE' THEN avail_qty ELSE 0 END) AS immediate_available_qty,
  SUM(CASE WHEN stock_status = 'AVAILABLE' AND age_days <= 180 THEN avail_qty ELSE 0 END) AS fresh_dispatchable_qty,
  MAX(age_days) AS max_age_days
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items`
WHERE product_id IN ('PRD-3006', 'PRD-3007', 'PRD-3008')
GROUP BY product_id
ORDER BY product_id
""".strip(),
                    "expect": {
                        "exact_rows": 3,
                        "must_contain": [
                            {"product_id": "PRD-3006", "total_physical_qty": 40, "immediate_available_qty": 25, "fresh_dispatchable_qty": 25},
                            {"product_id": "PRD-3007", "total_physical_qty": 35, "immediate_available_qty": 35, "fresh_dispatchable_qty": 0},
                            {"product_id": "PRD-3008", "total_physical_qty": 30, "immediate_available_qty": 20, "fresh_dispatchable_qty": 20},
                        ],
                    },
                }
            ],
            "graph_path": [
                "Product --[STOCKED_AT_INVENTORY]--> InventoryItem",
                "BusinessContext --[INVOKES_PROVISION {term_key: 'hyper-personalized-reco'}]--> Provision",
            ],
        },

        # ---------------- THEME C (4): 대규모유통업법 판촉비 50% 상한 · 서면약정 · 자발성 단서 ----------------
        {
            "id": "CQ08",
            "theme": "C",
            "cq_type": "multi_hop",
            "persona": "파트너상생본부 정산실장",
            "question": "특약매입 브랜드 아틀리에누아르(`BRD-01`, 계약서상 약정 분담률 60%, 서면약정 `Y`)의 공동판촉(`JOINT_PROMO`) 주문품목 4건(`OIT-2026-0001`~`OIT-2026-0004`)에 대하여, 계약서 약정대로 60%를 청구할 때의 금액과 대규모유통업법 제11조제4항 및 정산내규 제3조의 50% 상한 캡(`MIN(promo_cost_share_ratio, 0.50)`)을 적용했을 때의 적법 분담금, 그리고 K마켙이 흡수해야 할 50% 초과분(위법 과다청구 위험액)은 각각 얼마인가?",
            "evidence": [ev(P_LAW01_CAP50), ev(P_FTC02_CAP), ev(P_PRT09_CAP)],
            "data_fields": [
                df("bigquery", "brand_vendor_contracts", "agreed_promo_share_pct", "measure"),
                df("bigquery", "brand_vendor_contracts", "written_promo_agreement_yn", "filter"),
                df("spanner", "order_items", "coupon_discount_krw", "measure"),
                df("spanner", "order_items", "coupon_type", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  b.brand_id,
  b.brand_name,
  COUNT(oi.item_id) AS promo_item_count,
  SUM(oi.retail_price_krw) AS total_retail_krw,
  SUM(oi.coupon_discount_krw) AS total_coupon_discount_krw,
  CAST(SUM(oi.coupon_discount_krw * (b.agreed_promo_share_pct / 100.0)) AS INT64) AS contract_60pct_share_krw,
  CAST(SUM(oi.coupon_discount_krw * LEAST(b.agreed_promo_share_pct / 100.0, 0.50)) AS INT64) AS legal_50pct_cap_share_krw,
  CAST(SUM(oi.coupon_discount_krw * (b.agreed_promo_share_pct / 100.0)) - SUM(oi.coupon_discount_krw * LEAST(b.agreed_promo_share_pct / 100.0, 0.50)) AS INT64) AS kmarket_absorbed_overcharge_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
WHERE b.brand_id = 'BRD-01' AND oi.coupon_type = 'JOINT_PROMO'
GROUP BY b.brand_id, b.brand_name
""".strip(),
                    "expect": {
                        "exact_rows": 1,
                        "must_contain": [
                            {
                                "brand_id": "BRD-01",
                                "promo_item_count": 4,
                                "total_retail_krw": 2000000,
                                "total_coupon_discount_krw": 300000,
                                "contract_60pct_share_krw": 180000,
                                "legal_50pct_cap_share_krw": 150000,
                                "kmarket_absorbed_overcharge_krw": 30000,
                            }
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[INVOKES_PROVISION {term_key: 'promo-cost-sharing'}]--> Provision --[DELEGATES_TO_INTERNAL]--> Provision",
                "OrderItem --[OF_PRODUCT]--> Product --[SUPPLIED_BY_BRAND]--> BrandVendorContract",
            ],
        },
        {
            "id": "CQ09",
            "theme": "C",
            "cq_type": "exception_path",
            "persona": "준법감시실 공정거래 CP 심사역",
            "question": "사전 서면 판매촉진약정이 미체결(`written_promo_agreement_yn = 'N'`)된 특약매입 브랜드 마린블루(`BRD-03`)의 주문품목 `OIT-2026-0013`(쿠폰할인 20,000원)에 대하여, 대규모유통업법 제11조제1항·제2항 및 정산내규 제2조에 따른 브랜드 분담금과 K마켙 부담금은 각각 얼마인가?",
            "evidence": [ev(P_LAW01_PRIOR), ev(P_FTC02_PRIOR), ev(P_PRT09_PRIOR)],
            "data_fields": [
                df("bigquery", "brand_vendor_contracts", "written_promo_agreement_yn", "filter"),
                df("bigquery", "brand_vendor_contracts", "agreed_promo_share_pct", "measure"),
                df("spanner", "order_items", "coupon_discount_krw", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  oi.item_id,
  b.brand_id,
  b.brand_name,
  b.written_promo_agreement_yn,
  b.agreed_promo_share_pct,
  oi.coupon_discount_krw,
  CASE WHEN b.written_promo_agreement_yn = 'Y' THEN CAST(oi.coupon_discount_krw * LEAST(b.agreed_promo_share_pct / 100.0, 0.50) AS INT64) ELSE 0 END AS legal_brand_share_krw,
  CASE WHEN b.written_promo_agreement_yn = 'Y' THEN CAST(oi.coupon_discount_krw * (1.0 - LEAST(b.agreed_promo_share_pct / 100.0, 0.50)) AS INT64) ELSE oi.coupon_discount_krw END AS kmarket_share_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
WHERE oi.item_id = 'OIT-2026-0013'
""".strip(),
                    "expect": {
                        "exact_rows": 1,
                        "must_contain": [
                            {
                                "item_id": "OIT-2026-0013",
                                "brand_id": "BRD-03",
                                "written_promo_agreement_yn": "N",
                                "coupon_discount_krw": 20000,
                                "legal_brand_share_krw": 0,
                                "kmarket_share_krw": 20000,
                            }
                        ],
                    },
                }
            ],
            "graph_path": [
                "OrderItem --[OF_PRODUCT]--> Product --[SUPPLIED_BY_BRAND]--> BrandVendorContract",
                "OrderItem --[GOVERNED_BY_CRITERIA]--> Provision",
            ],
        },
        {
            "id": "CQ10",
            "theme": "C",
            "cq_type": "exception_path",
            "persona": "준법감시실장",
            "question": "대규모유통업법 제11조제5항 단서(자발적·차별화 행사 예외)와 관련하여 캠페인 예외승인 원장(`campaign_exceptions`)에 등재된 `VENDOR_VOLUNTARY_PROMO` 2건(`EXC-KM-2026-03` 노르딕아웃도어 `PRD-3008` vs `EXC-KM-2026-06` 아틀리에누아르 `PRD-3001`)의 자발적 요청서 제출 여부(`vendor_voluntary_req_yn`) 및 결재 상태(`ACTIVE` vs `REJECTED`)에 따라 주문품목 `OIT-2026-0017`과 `OIT-2026-0004`에 적용될 최종 브랜드 분담률과 분담금은 얼마인가?",
            "evidence": [ev(P_LAW01_CAP50), ev(P_FTC02_VOL), ev(P_PRT09_VOL)],
            "data_fields": [
                df("spanner", "campaign_exceptions", "target_kind", "filter"),
                df("spanner", "campaign_exceptions", "vendor_voluntary_req_yn", "filter"),
                df("spanner", "campaign_exceptions", "status", "filter"),
                df("bigquery", "brand_vendor_contracts", "agreed_promo_share_pct", "measure"),
                df("spanner", "order_items", "coupon_discount_krw", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  ce.approval_id,
  oi.item_id,
  b.brand_id,
  b.agreed_promo_share_pct,
  ce.vendor_voluntary_req_yn,
  ce.status AS approval_status,
  oi.coupon_discount_krw,
  CASE
    WHEN ce.status = 'ACTIVE' AND ce.vendor_voluntary_req_yn = 'Y' THEN b.agreed_promo_share_pct
    ELSE LEAST(b.agreed_promo_share_pct, 50.0)
  END AS applied_share_pct,
  CAST(oi.coupon_discount_krw * (
    CASE
      WHEN ce.status = 'ACTIVE' AND ce.vendor_voluntary_req_yn = 'Y' THEN b.agreed_promo_share_pct / 100.0
      ELSE LEAST(b.agreed_promo_share_pct / 100.0, 0.50)
    END
  ) AS INT64) AS final_vendor_share_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON ce.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
  ON oi.product_id = p.product_id AND (IFNULL(ce.item_id, '') = '' OR ce.item_id = oi.item_id)
WHERE ce.target_kind = 'VENDOR_VOLUNTARY_PROMO' AND oi.coupon_type = 'JOINT_PROMO'
ORDER BY ce.approval_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {"approval_id": "EXC-KM-2026-03", "item_id": "OIT-2026-0017", "brand_id": "BRD-05", "approval_status": "ACTIVE", "applied_share_pct": 70.0, "final_vendor_share_krw": 42000},
                            {"approval_id": "EXC-KM-2026-06", "item_id": "OIT-2026-0004", "brand_id": "BRD-01", "approval_status": "REJECTED", "applied_share_pct": 50.0, "final_vendor_share_krw": 75000},
                        ],
                    },
                }
            ],
            "graph_path": [
                "Provision --[HAS_EXCEPTION_PROVISO]--> Provision",
                "OrderItem --[OF_PRODUCT]--> Product --[HAS_CAMPAIGN_EXCEPTION]--> CampaignException",
            ],
        },
        {
            "id": "CQ11",
            "theme": "C",
            "cq_type": "lookup",
            "persona": "파트너상생본부 계약관리자",
            "question": "대규모유통업법 제2조·제6조·제8조·제10조·제18조에 따라 K마켙에 입점한 8개 브랜드(`BRD-01`~`BRD-08`)의 거래형태(`직매입`, `특약매입`, `위수탁`)별 브랜드 수와 직매입(60일) vs 특약매입·위수탁(40일) 법정 대금지급 기한 구분은 어떠한가?",
            "evidence": [ev(P_LAW01_DEF), ev(P_LAW01_WRITTEN), ev(P_LAW01_PAY), ev(P_LAW01_RETBAN), ev(P_LAW01_REC5Y)],
            "data_fields": [
                df("bigquery", "brand_vendor_contracts", "trade_type", "filter"),
                df("bigquery", "brand_vendor_contracts", "brand_id", "join_key"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  trade_type,
  COUNT(*) AS brand_count,
  CASE WHEN trade_type = '직매입' THEN 60 ELSE 40 END AS statutory_payment_deadline_days
FROM `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts`
GROUP BY trade_type
ORDER BY trade_type
""".strip(),
                    "expect": {
                        "exact_rows": 3,
                        "must_contain": [
                            {"trade_type": "위수탁", "brand_count": 3, "statutory_payment_deadline_days": 40},
                            {"trade_type": "직매입", "brand_count": 2, "statutory_payment_deadline_days": 60},
                            {"trade_type": "특약매입", "brand_count": 3, "statutory_payment_deadline_days": 40},
                        ],
                    },
                }
            ],
            "graph_path": [
                "Product --[SUPPLIED_BY_BRAND]--> BrandVendorContract",
                "BusinessContext --[INVOKES_PROVISION {term_key: 'promo-cost-sharing'}]--> Provision",
            ],
        },

        # ---------------- THEME D (4): 전자상거래법 청약철회(7일 vs 90일) · 홀로그램 검수 · 물류 SLA · 해외직구 대조군 ----------------
        {
            "id": "CQ12",
            "theme": "D",
            "cq_type": "exception_path",
            "persona": "고객경험(CX)본부 CS심사팀장",
            "question": "위생제한 태그(`return_policy_tag = 'HYGIENE_RESTRICTED'`)가 부여된 수영복(`PRD-3006`, 주문품목 `OIT-2026-0013`)과 실크 브라렛(`PRD-3007`, 주문품목 `OIT-2026-0014`) 반품 건에 대하여, 반품 검수 원장(`campaign_exceptions`)의 홀로그램 실링 택 보존 여부(`hologram_tag_intact_yn`)를 기준으로 전자상거래법 제17조제2항에 따른 환불 승인 대상과 거절 대상을 판별하라.",
            "evidence": [ev(P_ECOM03_WRESTRICT), ev(P_CS10_REASON)],
            "data_fields": [
                df("bigquery", "products", "return_policy_tag", "filter"),
                df("spanner", "order_items", "item_id", "join_key"),
                df("spanner", "campaign_exceptions", "hologram_tag_intact_yn", "filter"),
                df("spanner", "order_items", "sale_price_krw", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  oi.item_id,
  oi.user_id,
  p.product_id,
  p.return_policy_tag,
  ce.approval_id,
  ce.hologram_tag_intact_yn,
  oi.sale_price_krw,
  CASE WHEN ce.hologram_tag_intact_yn = 'Y' THEN 'APPROVE_WITHDRAWAL' ELSE 'REJECT_WITHDRAWAL' END AS cs_decision
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce ON oi.item_id = ce.item_id
WHERE ce.target_kind = 'RETURN_HYGIENE'
ORDER BY oi.item_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {"item_id": "OIT-2026-0013", "product_id": "PRD-3006", "hologram_tag_intact_yn": "Y", "sale_price_krw": 100000, "cs_decision": "APPROVE_WITHDRAWAL"},
                            {"item_id": "OIT-2026-0014", "product_id": "PRD-3007", "hologram_tag_intact_yn": "N", "sale_price_krw": 90000, "cs_decision": "REJECT_WITHDRAWAL"},
                        ],
                    },
                }
            ],
            "graph_path": [
                "OrderItem --[OF_PRODUCT]--> Product --[HAS_CAMPAIGN_EXCEPTION]--> CampaignException",
                "OrderItem --[GOVERNED_BY_CRITERIA]--> Provision --[HAS_EXCEPTION_PROVISO]--> Provision",
            ],
        },
        {
            "id": "CQ13",
            "theme": "D",
            "cq_type": "multi_hop",
            "persona": "고객경험(CX)본부 반품심사역",
            "question": "전자상거래법 제17조·제18조 및 CS 내규 제2조에 따라 반품 사유 코드가 기록된 주문품목(`CHANGE_OF_MIND`, `DEFECTIVE`, `SIZE_MISMATCH_SPEC_DIFF`, `WEAR_AND_WASH_DAMAGE`)을 전수 조회할 때, 배송완료 후 20일 만에 접수된 `OIT-2026-0018`(`SIZE_MISMATCH_SPEC_DIFF`)과 착용·세탁 흔적이 발견된 `OIT-2026-0019`(`WEAR_AND_WASH_DAMAGE`)의 청약철회 적격성 및 왕복 반품배송비(6,000원) 부담 주체는 누구인가?",
            "evidence": [ev(P_ECOM03_WPERIOD), ev(P_ECOM03_REFUND), ev(P_CS10_REASON)],
            "data_fields": [
                df("spanner", "order_items", "return_reason_cd", "filter"),
                df("spanner", "order_items", "delivered_at", "filter"),
                df("spanner", "order_items", "returned_at", "filter"),
                df("spanner", "order_items", "sale_price_krw", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  item_id,
  order_id,
  return_reason_cd,
  sale_price_krw,
  CASE
    WHEN return_reason_cd = 'WEAR_AND_WASH_DAMAGE' THEN 'REJECTED'
    ELSE 'APPROVED'
  END AS return_eligibility,
  CASE
    WHEN return_reason_cd = 'CHANGE_OF_MIND' THEN 6000
    ELSE 0
  END AS customer_return_shipping_fee_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items`
WHERE return_reason_cd != 'NONE'
ORDER BY item_id
""".strip(),
                    "expect": {
                        "exact_rows": 6,
                        "must_contain": [
                            {"item_id": "OIT-2026-0007", "return_reason_cd": "CHANGE_OF_MIND", "return_eligibility": "APPROVED", "customer_return_shipping_fee_krw": 6000},
                            {"item_id": "OIT-2026-0018", "return_reason_cd": "SIZE_MISMATCH_SPEC_DIFF", "return_eligibility": "APPROVED", "customer_return_shipping_fee_krw": 0},
                            {"item_id": "OIT-2026-0019", "return_reason_cd": "WEAR_AND_WASH_DAMAGE", "return_eligibility": "REJECTED", "customer_return_shipping_fee_krw": 0},
                        ],
                    },
                }
            ],
            "graph_path": [
                "OrderItem --[GOVERNED_BY_CRITERIA]--> Provision --[DELEGATES_TO_INTERNAL]--> Provision",
                "OrderItem --[BELONGS_TO_ORDER]--> Order",
            ],
        },
        {
            "id": "CQ14",
            "theme": "D",
            "cq_type": "exception_path",
            "persona": "준법감시실 소비자보호 심사역",
            "question": "국내 물류센터(`DC-ICN`, `DC-YIN`, `DC-BUS`)에서 출고된 주문품목의 반품 심사 시, 관세청 해외직구 특송물품 고시(`DOC_06_DISTRACTOR_CUSTOMS`, 14일 반송기한 및 국제반송수수료 35,000원)를 적용할 수 없는 법적 근거와 `CONFLICTS_BY_SECTOR` 엣지로 분리된 정당한 국내 적용 조문은 무엇인가?",
            "evidence": [ev(P_DIST06_SCOPE), ev(P_DIST06_FEE), ev(P_CS10_REFUND)],
            "data_fields": [
                df("spanner", "inventory_items", "distribution_center_id", "filter"),
                df("bigquery", "lex_source_documents", "applicable_sector", "filter"),
                df("bigquery", "edge_conflicts_by_sector", "conflict_warning", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  c.edge_id,
  c.ecommerce_slot_id,
  c.distractor_slot_id,
  d_dom.applicable_sector AS domestic_sector,
  d_dist.applicable_sector AS distractor_sector,
  d_dist.authority_level AS distractor_authority
FROM `finance-ontology-changseop.kmarket_ontology.edge_conflicts_by_sector` c
JOIN `finance-ontology-changseop.kmarket_ontology.lex_provisions` p_dom ON c.ecommerce_slot_id = p_dom.provision_slot_id
JOIN `finance-ontology-changseop.kmarket_ontology.lex_source_documents` d_dom ON p_dom.doc_id = d_dom.doc_id
JOIN `finance-ontology-changseop.kmarket_ontology.lex_provisions` p_dist ON c.distractor_slot_id = p_dist.provision_slot_id
JOIN `finance-ontology-changseop.kmarket_ontology.lex_source_documents` d_dist ON p_dist.doc_id = d_dist.doc_id
ORDER BY c.edge_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {
                                "edge_id": "CONF_DOMESTIC_VS_CUSTOMS_01",
                                "domestic_sector": "DOMESTIC_ECOMMERCE",
                                "distractor_sector": "OVERSEAS_DIRECT_CUSTOMS",
                                "distractor_authority": "distractor",
                            },
                            {
                                "edge_id": "CONF_CS_POLICY_VS_CUSTOMS_02",
                                "domestic_sector": "DOMESTIC_ECOMMERCE",
                                "distractor_sector": "OVERSEAS_DIRECT_CUSTOMS",
                                "distractor_authority": "distractor",
                            },
                        ],
                    },
                }
            ],
            "graph_path": [
                "Provision --[CONFLICTS_BY_SECTOR]--> Provision --[PART_OF_DOCUMENT]--> SourceDocument",
            ],
        },
        {
            "id": "CQ15",
            "theme": "D",
            "cq_type": "multi_hop",
            "persona": "풀필먼트운영실 물류 SLA 관리자",
            "question": "K마켙 CS·물류 내규 제4조에 따른 물류센터별 표준 출고 목표시간(김포 `DC-ICN` 24h, 용인 `DC-YIN` 36h, 양산/부산 `DC-BUS` 48h)을 초과하여 출고된 지연 주문 3건(`ORD-2026-0009`, `ORD-2026-0014`, `ORD-2026-0015`)의 실제 출고 소요시간(시간)과 지연보상 적립금(건당 3,000P) 지급 대상 여부는 어떠한가?",
            "evidence": [ev(P_ECOM03_SUPPLY), ev(P_CS10_SLA)],
            "data_fields": [
                df("spanner", "orders", "created_at", "filter"),
                df("spanner", "orders", "shipped_at", "filter"),
                df("spanner", "inventory_items", "distribution_center_id", "filter"),
                df("bigquery", "brand_vendor_contracts", "sla_ship_hours", "measure"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  o.order_id,
  oi.item_id,
  inv.distribution_center_id,
  CASE inv.distribution_center_id
    WHEN 'DC-ICN' THEN 24
    WHEN 'DC-YIN' THEN 36
    WHEN 'DC-BUS' THEN 48
  END AS center_sla_hours,
  b.sla_ship_hours AS brand_contract_sla_hours,
  TIMESTAMP_DIFF(TIMESTAMP(o.shipped_at), TIMESTAMP(o.created_at), HOUR) AS elapsed_ship_hours,
  3000 AS compensation_points
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_orders` o
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi ON o.order_id = oi.order_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON oi.inventory_item_id = inv.inventory_item_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
WHERE TIMESTAMP_DIFF(TIMESTAMP(o.shipped_at), TIMESTAMP(o.created_at), HOUR) >
  CASE inv.distribution_center_id WHEN 'DC-ICN' THEN 24 WHEN 'DC-YIN' THEN 36 WHEN 'DC-BUS' THEN 48 END
ORDER BY o.order_id
""".strip(),
                    "expect": {
                        "exact_rows": 3,
                        "must_contain": [
                            {"order_id": "ORD-2026-0009", "distribution_center_id": "DC-YIN", "center_sla_hours": 36, "elapsed_ship_hours": 60, "compensation_points": 3000},
                            {"order_id": "ORD-2026-0014", "distribution_center_id": "DC-YIN", "center_sla_hours": 36, "elapsed_ship_hours": 42, "compensation_points": 3000},
                            {"order_id": "ORD-2026-0015", "distribution_center_id": "DC-BUS", "center_sla_hours": 48, "elapsed_ship_hours": 60, "compensation_points": 3000},
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[INVOKES_PROVISION {term_key: 'fulfillment-sla-compensation'}]--> Provision",
                "OrderItem --[BELONGS_TO_ORDER]--> Order",
                "OrderItem --[OF_PRODUCT]--> Product --[STOCKED_AT_INVENTORY]--> InventoryItem",
            ],
        },

        # ---------------- THEME E (2): 전사 파급효과 · 개인정보/마케팅 동의 리스크 집계 (Impact) ----------------
        {
            "id": "CQ16",
            "theme": "E",
            "cq_type": "impact",
            "persona": "개인정보보호책임자(CPO) · 준법감시실",
            "question": "개인정보보호위원회 맞춤형 광고 행태정보 가이드라인 제3조 및 K마켙 CRM 내규 제2조에 따라, 장바구니 미결제 이탈 세션 5건 중 마케팅 수신동의(`marketing_opt_in_yn = 'Y'`)가 확인되어 외부 리마인드·타겟팅 쿠폰 발송이 허용되는 회원과 수신거부(`marketing_opt_in_yn = 'N'`)로 발송이 즉시 차단되어야 하는 회원은 각각 몇 명이며 누구인가?",
            "evidence": [ev(P_PIPC05_DEF), ev(P_PIPC05_OPTIN), ev(P_CRM07_OPTIN)],
            "data_fields": [
                df("spanner", "events", "event_type", "filter"),
                df("bigquery", "users", "marketing_opt_in_yn", "filter"),
                df("bigquery", "users", "membership_tier", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  u.marketing_opt_in_yn,
  COUNT(DISTINCT c.session_id) AS abandon_session_count,
  STRING_AGG(c.user_id, ',' ORDER BY c.user_id) AS user_ids
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` c
JOIN `finance-ontology-changseop.kmarket_ecommerce.users` u ON c.user_id = u.user_id
WHERE c.event_type = 'cart'
  AND NOT EXISTS (
    SELECT 1 FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` p
    WHERE p.session_id = c.session_id AND p.event_type = 'purchase'
  )
GROUP BY u.marketing_opt_in_yn
ORDER BY u.marketing_opt_in_yn DESC
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {"marketing_opt_in_yn": "Y", "abandon_session_count": 4, "user_ids": "USR-1001,USR-1002,USR-1003,USR-1007"},
                            {"marketing_opt_in_yn": "N", "abandon_session_count": 1, "user_ids": "USR-1004"},
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[INVOKES_PROVISION {term_key: 'behavioral-privacy-optin'}]--> Provision --[DELEGATES_TO_INTERNAL]--> Provision",
                "UserBehaviorEvent --[EVALUATED_UNDER_PROVISION]--> Provision",
            ],
        },
        {
            "id": "CQ17",
            "theme": "E",
            "cq_type": "impact",
            "persona": "최고재무책임자(CFO) · 파트너상생본부장",
            "question": "전사 공동판촉(`JOINT_PROMO`) 쿠폰이 적용된 전체 주문품목(6건, 총 쿠폰할인액 380,000원)에 대하여 브랜드별 계약 조건(`BRD-01` 60% 약정, `BRD-03` 서면약정 미비, `BRD-05` 70% 자발적 단독행사 승인)을 전수 정산할 때, 법령·내규 적용 전 명목 브랜드 청구액 합계 대비 적법 브랜드 정산액 합계와 K마켙이 최종 부담해야 할 총 판촉비 흡수액은 얼마인가?",
            "evidence": [ev(P_LAW01_CAP50), ev(P_FTC02_SCOPE), ev(P_PRT09_CAP)],
            "data_fields": [
                df("spanner", "order_items", "coupon_discount_krw", "measure"),
                df("spanner", "order_items", "coupon_type", "filter"),
                df("bigquery", "brand_vendor_contracts", "agreed_promo_share_pct", "measure"),
                df("bigquery", "brand_vendor_contracts", "written_promo_agreement_yn", "filter"),
                df("spanner", "campaign_exceptions", "status", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  b.brand_id,
  COUNT(oi.item_id) AS item_cnt,
  SUM(oi.coupon_discount_krw) AS total_discount_krw,
  CAST(SUM(oi.coupon_discount_krw * (b.agreed_promo_share_pct / 100.0)) AS INT64) AS nominal_contract_vendor_krw,
  CAST(SUM(
    CASE
      WHEN b.written_promo_agreement_yn = 'N' THEN 0
      WHEN ce.status = 'ACTIVE' AND ce.vendor_voluntary_req_yn = 'Y' THEN oi.coupon_discount_krw * (b.agreed_promo_share_pct / 100.0)
      ELSE oi.coupon_discount_krw * LEAST(b.agreed_promo_share_pct / 100.0, 0.50)
    END
  ) AS INT64) AS legal_vendor_share_krw,
  CAST(SUM(oi.coupon_discount_krw) - SUM(
    CASE
      WHEN b.written_promo_agreement_yn = 'N' THEN 0
      WHEN ce.status = 'ACTIVE' AND ce.vendor_voluntary_req_yn = 'Y' THEN oi.coupon_discount_krw * (b.agreed_promo_share_pct / 100.0)
      ELSE oi.coupon_discount_krw * LEAST(b.agreed_promo_share_pct / 100.0, 0.50)
    END
  ) AS INT64) AS kmarket_final_burden_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
LEFT JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce
  ON ce.product_id = p.product_id AND ce.target_kind = 'VENDOR_VOLUNTARY_PROMO' AND ce.status = 'ACTIVE'
WHERE oi.coupon_type = 'JOINT_PROMO'
GROUP BY b.brand_id
ORDER BY b.brand_id
""".strip(),
                    "expect": {
                        "exact_rows": 3,
                        "must_contain": [
                            {"brand_id": "BRD-01", "total_discount_krw": 300000, "nominal_contract_vendor_krw": 180000, "legal_vendor_share_krw": 150000, "kmarket_final_burden_krw": 150000},
                            {"brand_id": "BRD-03", "total_discount_krw": 20000, "nominal_contract_vendor_krw": 10000, "legal_vendor_share_krw": 0, "kmarket_final_burden_krw": 20000},
                            {"brand_id": "BRD-05", "total_discount_krw": 60000, "nominal_contract_vendor_krw": 42000, "legal_vendor_share_krw": 42000, "kmarket_final_burden_krw": 18000},
                        ],
                    },
                }
            ],
            "graph_path": [
                "OrderItem --[OF_PRODUCT]--> Product --[SUPPLIED_BY_BRAND]--> BrandVendorContract",
                "OrderItem --[GOVERNED_BY_CRITERIA]--> Provision",
            ],
        },

        # ---------------- THEME F (3): 스키마 공백(Absence) · 미매핑 법령 요건 진단 ----------------
        {
            "id": "CQ18",
            "theme": "F",
            "cq_type": "absence",
            "persona": "개인정보보호팀 · 데이터 아키텍트",
            "question": "개보위 행태정보 가이드라인 제5조 및 K마켙 CRM 내규 제5조는 야간 시간대(21:00~익일 08:00)에 발생한 장바구니 이탈 세션(`SES-1002-A`~`SES-1007-A`)에 대해 야간 광고성 푸시 별도 수신동의 확인 또는 익일 08:30 예약 발송을 요구한다. 현재 `kmarket_ontology.lex_provisions`에 기록된 해당 조문의 스키마 공백(`missing_schema_columns`)은 무엇인가?",
            "evidence": [ev(P_PIPC05_NIGHT), ev(P_CRM07_TIER)],
            "data_fields": [
                df("bigquery", "users", "marketing_opt_in_yn", "filter"),
                df("spanner", "events", "created_at", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  provision_slot_id,
  doc_id,
  article_no,
  missing_schema_columns
FROM `finance-ontology-changseop.kmarket_ontology.lex_provisions`
WHERE missing_schema_columns LIKE '%night_push_opt_in_yn%'
ORDER BY doc_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {
                                "doc_id": "DOC_05_PIPC_BEHAVIORAL",
                                "article_no": "제4조~제5조",
                                "missing_schema_columns": "users.night_push_opt_in_yn,events.push_scheduled_at",
                            },
                            {
                                "doc_id": "DOC_07_KMARKET_CRM_POLICY",
                                "article_no": "제4조~제5조",
                                "missing_schema_columns": "users.night_push_opt_in_yn,events.push_scheduled_at",
                            },
                        ],
                    },
                }
            ],
            "graph_path": [
                "BusinessContext --[INVOKES_PROVISION {term_key: 'hyper-personalized-reco'}]--> Provision",
            ],
        },
        {
            "id": "CQ19",
            "theme": "F",
            "cq_type": "absence",
            "persona": "준법감시실 · 데이터 거버넌스 아키텍트",
            "question": "공정위 판매촉진비용 심사지침 Ⅱ.5 및 K마켙 정산내규 제4조에서 요구하는 납품업자 자발적 행사 요청 공문 원본 URI 및 예상 순증편익(ROI) 산출 근거와 관련하여, 현재 정형 원장에 구현되지 않아 `lex_provisions.missing_schema_columns`로 진단되는 미매핑 컬럼은 무엇인가?",
            "evidence": [ev(P_FTC02_VOL), ev(P_PRT09_VOL)],
            "data_fields": [
                df("spanner", "campaign_exceptions", "vendor_voluntary_req_yn", "filter"),
                df("spanner", "campaign_exceptions", "status", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  provision_slot_id,
  doc_id,
  article_no,
  missing_schema_columns
FROM `finance-ontology-changseop.kmarket_ontology.lex_provisions`
WHERE missing_schema_columns LIKE '%voluntary_request_doc_uri%'
ORDER BY doc_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [
                            {
                                "doc_id": "DOC_02_FTC_PROMO_GUIDE",
                                "article_no": "Ⅱ.5",
                                "missing_schema_columns": "campaign_exceptions.voluntary_request_doc_uri,campaign_exceptions.expected_uplift_roi_pct",
                            },
                            {
                                "doc_id": "DOC_09_KMARKET_PARTNER_POLICY",
                                "article_no": "제4조",
                                "missing_schema_columns": "campaign_exceptions.voluntary_request_doc_uri,campaign_exceptions.expected_uplift_roi_pct",
                            },
                        ],
                    },
                }
            ],
            "graph_path": [
                "Provision --[HAS_EXCEPTION_PROVISO]--> Provision",
            ],
        },
        {
            "id": "CQ20",
            "theme": "F",
            "cq_type": "absence",
            "persona": "전사 데이터 거버넌스 위원회",
            "question": "전자상거래법 제21조의2·공정위 다크패턴 가이드라인 제2조(직전 20일 최저 판매가격 검증), 대규모유통업법 제8조(월 판매마감일 및 대금 실지급일), 전자상거래법 제17조제2항(반품 검수 촬영 이미지 URI) 등 K마켙 온톨로지 `lex_provisions` 전체에서 스키마 공백(`missing_schema_columns != ''`)이 존재하는 조문은 총 몇 건이며 어떤 문서들에 분포하는가?",
            "evidence": [ev(P_ECOM03_DARK), ev(P_DP04_PRICE), ev(P_LAW01_PAY), ev(P_ECOM03_WRESTRICT)],
            "data_fields": [
                df("bigquery", "products", "retail_price_krw", "measure"),
                df("spanner", "orders", "delivered_at", "filter"),
                df("spanner", "campaign_exceptions", "hologram_tag_intact_yn", "filter"),
            ],
            "answer_queries": [
                {
                    "engine": "bigquery_sql",
                    "sql": """
SELECT
  doc_id,
  article_no,
  missing_schema_columns
FROM `finance-ontology-changseop.kmarket_ontology.lex_provisions`
WHERE missing_schema_columns != ''
ORDER BY doc_id, article_no
""".strip(),
                    "expect": {
                        "exact_rows": 8,
                        "must_contain": [
                            {"doc_id": "DOC_01_LAW_LARGE_RETAIL", "article_no": "제8조", "missing_schema_columns": "orders.monthly_closing_date,orders.vendor_payout_paid_at"},
                            {"doc_id": "DOC_04_FTC_DARK_PATTERN", "article_no": "제1조~제2조", "missing_schema_columns": "products.min_sale_price_20d_krw,products.price_reference_verified_at"},
                            {"doc_id": "DOC_10_KMARKET_CS_SLA_POLICY", "article_no": "제1조~제2조", "missing_schema_columns": "campaign_exceptions.inspection_photo_gcs_uri,order_items.seal_serial_no"},
                        ],
                    },
                }
            ],
            "graph_path": [
                "Provision --[PART_OF_DOCUMENT]--> SourceDocument",
            ],
        },
    ]

    # Map each CQ to its primary BusinessContext ID
    ctx_by_theme = {
        "A": "CX_GROWTH_MKT",
        "B": "MD_MERCHANDISING",
        "C": "PARTNER_SETTLEMENT",
        "D": "CX_CS_REFUND",
        "E": "COMPLIANCE_AUDIT",
        "F": "COMPLIANCE_AUDIT",
    }
    ctx_override = {
        "CQ03": "MD_MERCHANDISING",
        "CQ04": "MD_MERCHANDISING",
        "CQ05": "CX_CS_REFUND",
        "CQ06": "PARTNER_SETTLEMENT",
        "CQ07": "FULFILLMENT_OPS",
        "CQ15": "FULFILLMENT_OPS",
        "CQ17": "PARTNER_SETTLEMENT",
    }

    # Read actual CSV column headers from ecommerce/data/structured/*.csv
    struct_dir = os.path.join(ROOT, "ecommerce", "data", "structured")
    csv_cols: dict[str, list[str]] = {}
    spanner_tables = {"orders", "order_items", "inventory_items", "events", "campaign_exceptions"}
    bq_native_tables = {"users", "products", "brand_vendor_contracts"}
    for t in spanner_tables | bq_native_tables:
        with open(os.path.join(struct_dir, f"{t}.csv"), "r", encoding="utf-8") as cf:
            header = cf.readline().strip().split(",")
            csv_cols[t] = header

    import re as _re

    def to_cypher_path(paths: list[str]) -> str:
        cypher_segments = []
        for p_str in paths:
            parts = [x.strip() for x in p_str.split("-->")]
            seg = ""
            for idx, part in enumerate(parts):
                if "--[" in part:
                    node_part, edge_part = part.split("--[", 1)
                    node_label = node_part.strip()
                    edge_label = edge_part.split("]", 1)[0].split("{", 1)[0].strip()
                    if idx == 0:
                        seg += f"(:{node_label})-[:{edge_label}]->"
                    else:
                        seg += f"(:{node_label})-[:{edge_label}]->"
                else:
                    node_label = part.strip()
                    seg += f"(:{node_label})"
            cypher_segments.append(seg)
        return " ; ".join(cypher_segments)

    cqs_normalized = []
    for q in questions:
        cid = q["id"]
        ctx_id = ctx_override.get(cid, ctx_by_theme[q["theme"]])
        sql_text = " ".join(aq["sql"] for aq in q["answer_queries"])
        # Group data_fields by (store, table) for LDM tables only
        grouped_df: dict[tuple[str, str], list[str]] = {}
        for item in q["data_fields"]:
            raw_t = item["table"]
            if raw_t not in (spanner_tables | bq_native_tables):
                continue
            store = "spanner" if raw_t in spanner_tables else "bigquery"
            t_name = f"ont_{raw_t}" if store == "spanner" else raw_t
            cols = grouped_df.setdefault((store, t_name), [])
            if item["column"] in csv_cols[raw_t] and item["column"] not in cols:
                cols.append(item["column"])
        # Also auto-include any table/column from the 8 LDM tables that appears in this CQ's SQL
        for raw_t, valid_cols in csv_cols.items():
            store = "spanner" if raw_t in spanner_tables else "bigquery"
            t_name = f"ont_{raw_t}" if store == "spanner" else raw_t
            if t_name in sql_text or f".{raw_t}" in sql_text or (store, t_name) in grouped_df:
                cols = grouped_df.setdefault((store, t_name), [])
                for c in valid_cols:
                    if _re.search(rf"\b{_re.escape(c)}\b", sql_text) and c not in cols:
                        cols.append(c)
                if not cols:
                    cols.append(valid_cols[0])

        df_list = [
            {"table": t_name, "source_store": store, "columns": cols}
            for (store, t_name), cols in grouped_df.items()
        ]
        cqs_normalized.append({
            "id": cid,
            "theme": q["theme"],
            "cq_type": q["cq_type"],
            "persona": q["persona"],
            "question": q["question"],
            "business_context": {"id": ctx_id},
            "why_hard": f"{q['persona']} 맥락에서 법령·내규 조문과 Spanner/BigQuery 정형 원장을 다중 홉으로 결합해야 정확한 의사결정이 가능함.",
            "trap": "단일 규정만 보거나 예외승인 결재 상태(ACTIVE vs EXPIRED/REJECTED)·부서별 분모 차이를 누락하면 오답 산출.",
            "evidence": q["evidence"],
            "data_fields": df_list,
            "answer_queries": q["answer_queries"],
            "answer": "라이브 BigQuery + Spanner 연합 쿼리(ont_*) 실측 결과 참조.",
            "graph_path": to_cypher_path(q["graph_path"]),
            "graph_status": "aligned_l1_v1.2",
        })

    return {
        "meta": {
            "version": "1.1.0",
            "created": "2026-10-06",
            "updated": "2026-10-06",
            "owner": "ecommerce_ontology",
            "status": "approved",
            "theme_allocation": {"A": 4, "B": 3, "C": 4, "D": 4, "E": 2, "F": 3},
            "themes": {
                "A": "초개인화 추천 · 장바구니 이탈 · 마진 가드레일 · 체화재고 (4)",
                "B": "부서·맥락별 지표 정의 분기 — 반품률·확정매출·가용재고 (3)",
                "C": "대규모유통업법 판촉비 50% 상한 · 서면약정 · 자발성 단서 (4)",
                "D": "전자상거래법 청약철회(7일 vs 90일) · 홀로그램 검수 · 물류 SLA · 해외직구 대조군 (4)",
                "E": "전사 파급효과 · 개인정보 동의 및 판촉비 정산 리스크 집계 (2)",
                "F": "스키마 공백(Absence) · 미매핑 법령 요건 진단 (3)",
            },
            "cq_types": {
                "lookup": "단일 사실 조회이나 용어·컬럼 선택이 규정에 의해 결정됨",
                "multi_hop": "규정 → 단서 → 마스터 → 원장 등 3홉 이상 연결 필요",
                "exception_path": "원칙 조항과 예외·단서·결재 상태를 함께 평가해야 정답",
                "context_branch": "같은 용어가 본부/목적(BusinessContext)에 따라 다른 규정·컬럼으로 분기",
                "impact": "규정·조건 적용 시 전사 대상 계약·금액 파급효과 집계",
                "absence": "법령·내규상 요구되나 현재 원장에 없는 스키마 공백(missing_schema_columns) 진단",
            },
            "required_tables": [
                "ont_orders",
                "ont_order_items",
                "ont_inventory_items",
                "ont_events",
                "ont_campaign_exceptions",
                "users",
                "products",
                "brand_vendor_contracts",
            ],
        },
        "business_contexts": {
            "CX_GROWTH_MKT": {"dept": "그로스마케팅본부 AI추천랩", "purpose": "초개인화 추천 · 장바구니 이탈 리타겟팅"},
            "MD_MERCHANDISING": {"dept": "MD본부 가격전략실", "purpose": "프로모션 쿠폰 마진 가드레일(25%) · 체화재고 특례"},
            "PARTNER_SETTLEMENT": {"dept": "파트너상생본부 정산관리팀", "purpose": "대규모유통업법 판촉비 50% 상한 · 서면약정 · 수수료 정산"},
            "CX_CS_REFUND": {"dept": "고객경험(CX)본부 CS심사팀", "purpose": "전자상거래법 청약철회(7일/90일) · 홀로그램 검수 · 반품배송비"},
            "FULFILLMENT_OPS": {"dept": "풀필먼트운영실 물류관리팀", "purpose": "물류센터 가용재고 · 출고 SLA(24h/36h/48h) · 지연보상"},
            "COMPLIANCE_AUDIT": {"dept": "준법감시실 · 개인정보보호팀", "purpose": "행태정보 수신동의 · 다크패턴 · 타업권 고시 혼입 차단"},
        },
        "sources": SOURCES,
        "cqs": cqs_normalized,
    }


def build_eqs() -> dict:
    questions = [
        # =========================================================================
        # GRAPH-FAVORED (8): EQ01 ~ EQ08 (expected_winner: graphrag)
        # =========================================================================
        {
            "id": "EQ01",
            "category": "graph_favored",
            "sibling_cq": "CQ01",
            "question": "박준혁 고객이 장바구니 세션 SES-1002-A에 담아둔 주상품 PRD-3003과 코디상품 PRD-3004를 묶어 15% 번들 쿠폰 할인을 적용하려고 할 때, 각 상품의 마진 가드레일 충족 여부를 반영한 합산 할인액과 최종 결제 제안 금액은 얼마인가?",
            "expected_winner": "graphrag",
            "rationale": "장바구니 세션(SES-1002-A) → 주상품(PRD-3003, 정상가 200,000원, 원가 120,000원)은 15% 할인 시 실결제가 170,000원으로 할인 후 실현마진율 29.4% ≥ 25% 가드레일을 통과(30,000원 할인)하나, 코디상품(PRD-3004, 정상가 100,000원, 원가 65,000원, 기본마진 35%)은 15% 할인 시 실결제가 85,000원으로 할인 후 실현마진율이 23.5% < 25.0%로 하락하며 비체화(입고 25일차)·예외승인 부재로 쿠폰 할인이 차단(0원 할인, 정가 100,000원 유지)되어 합산 할인액 30,000원·최종 제안가 270,000원을 도출해야 함.",
            "evidence": [ev(P_CRM07_BUNDLE), ev(P_CRM07_TIER), ev(P_MD08_25PCT)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  u.user_id,
  u.membership_tier,
  p1.product_id AS main_product_id,
  ROUND((p1.retail_price_krw * 0.85 - p1.cost_krw) / (p1.retail_price_krw * 0.85) * 100, 1) AS main_realized_margin_pct,
  p2.product_id AS coord_product_id,
  ROUND((p2.retail_price_krw * 0.85 - p2.cost_krw) / (p2.retail_price_krw * 0.85) * 100, 1) AS coord_realized_margin_pct,
  inv2.age_days AS coord_age_days,
  CAST(p1.retail_price_krw * 0.15 AS INT64) AS allowed_coupon_discount_krw,
  CAST(p1.retail_price_krw * 0.85 + p2.retail_price_krw AS INT64) AS final_bundle_price_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` e
JOIN `finance-ontology-changseop.kmarket_ecommerce.users` u ON e.user_id = u.user_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p1 ON e.product_id = p1.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p2 ON p1.coord_product_id = p2.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv2 ON p2.product_id = inv2.product_id
WHERE e.session_id = 'SES-1002-A' AND e.event_type = 'cart'
""".strip(),
                    "expect": {
                        "scalar": {
                            "user_id": "USR-1002",
                            "membership_tier": "VIP",
                            "main_product_id": "PRD-3003",
                            "main_realized_margin_pct": 29.4,
                            "coord_product_id": "PRD-3004",
                            "coord_realized_margin_pct": 23.5,
                            "coord_age_days": 25,
                            "allowed_coupon_discount_krw": 30000,
                            "final_bundle_price_krw": 270000,
                        }
                    },
                }
            ],
            "gold_answer": "합산 쿠폰 할인액은 30,000원이며 최종 번들 결제 제안 금액은 270,000원이다. 주상품 PRD-3003(정상가 200,000원, 매입원가 120,000원)은 15% 할인(30,000원) 시 실결제가 170,000원 기준 실현마진율이 29.4%로 상시 가드레일(25.0%)을 충족하지만, 코디상품 PRD-3004(정상가 100,000원, 매입원가 65,000원, 기본마진 35.0%)는 15% 할인(15,000원) 시 실결제가 85,000원 기준 실현마진율이 23.5%로 하락하여 상시 최저마진율(25.0%)에 미달하고, 입고 경과일수 25일차(비체화) 및 예외승인 부재로 쿠폰 할인이 차단(0원 할인, 정가 100,000원 유지)되기 때문이다.",
            "grading": {
                "must_include": [r"30,?000", r"270,?000", r"23\.5%"],
                "must_not_include": [r"255,?000"],
                "cite": [{"doc": "07", "locator": "제3조"}, {"doc": "08", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ02",
            "category": "graph_favored",
            "sibling_cq": "CQ02",
            "question": "장바구니 세션 SES-1007-A에서 고객이 담은 상품 PRD-3009는 현재 출고 가능한 재고가 있는가? 만약 품절이라면 대체 추천해야 할 상품 코드와 해당 대체상품의 체화재고 기준에 따른 최저마진율 하한은 몇 %인가?",
            "expected_winner": "graphrag",
            "rationale": "행동로그(SES-1007-A) → 주상품(PRD-3009) 재고(avail_qty=0 품절) 확인 → 대체상품(PRD-3002) 전환 → 대체상품 입고 경과일수(125일, 50개) 및 MD 내규 제3조(체화재고 10% 마진 하한 완화)까지 다중 홉 그래프 순회가 필요함.",
            "evidence": [ev(P_DP04_STOCK), ev(P_CRM07_BUNDLE), ev(P_MD08_AGED)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  p.product_id AS main_product_id,
  inv.avail_qty AS main_avail_qty,
  p.substitute_product_id,
  inv_sub.age_days AS sub_age_days,
  inv_sub.avail_qty AS sub_avail_qty,
  CASE WHEN inv_sub.age_days >= 90 AND inv_sub.avail_qty >= 30 THEN 10.0 ELSE 25.0 END AS clearance_floor_margin_pct
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` e
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON e.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON p.product_id = inv.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv_sub ON p.substitute_product_id = inv_sub.product_id
WHERE e.session_id = 'SES-1007-A' AND e.event_type = 'cart'
""".strip(),
                    "expect": {
                        "scalar": {
                            "main_product_id": "PRD-3009",
                            "main_avail_qty": 0,
                            "substitute_product_id": "PRD-3002",
                            "sub_age_days": 125,
                            "sub_avail_qty": 50,
                            "clearance_floor_margin_pct": 10.0,
                        }
                    },
                }
            ],
            "gold_answer": "PRD-3009는 현재 가용재고가 0개인 일시품절(OUT_OF_STOCK) 상태이므로 추천이 차단되며, 대체 상품인 PRD-3002(아틀리에 메리노울 터틀넥 니트 아이보리, 입고 125일차·가용재고 50개)로 전환 추천해야 한다. PRD-3002는 입고 90일 이상 및 가용재고 30개 이상 체화재고 요건을 충족하여 MD 내규 제3조에 따라 최저마진율 하한이 10.0%(10%)로 완화된다.",
            "grading": {
                "must_include": [r"PRD-3002", r"125일", r"10(\.0)?%"],
                "must_not_include": [],
                "cite": [{"doc": "07", "locator": "제3조"}, {"doc": "08", "locator": "제3조"}],
            },
        },
        {
            "id": "EQ03",
            "category": "graph_favored",
            "sibling_cq": "CQ03",
            "question": "입고된 지 얼마 안 된 신상품 PRD-3012는 기본 마진율이 상시 가드레일인 25%에 미달하는데 이번 프로모션에서 차단되는가, 아니면 등록된 캠페인 예외승인 결재에 따라 완화된 마진 하한이 적용되는가?",
            "expected_winner": "graphrag",
            "rationale": "입고 35일차라 체화재고(90일+) 요건은 충족하지 못하지만, CampaignException 노드의 VIP_RETENTION 결재(EXC-KM-2026-07, 하한 12.0%, ACTIVE)를 통해 기본마진 22.0% 상품이 프로모션 적격임을 추론해야 함.",
            "evidence": [ev(P_MD08_25PCT), ev(P_MD08_EXC)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  p.product_id,
  inv.age_days,
  ROUND((p.retail_price_krw - p.cost_krw) / p.retail_price_krw * 100, 1) AS base_margin_pct,
  ce.approval_id,
  ce.target_kind,
  ce.approved_floor_margin_pct,
  ce.status
FROM `finance-ontology-changseop.kmarket_ecommerce.products` p
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON p.product_id = inv.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce ON p.product_id = ce.product_id
WHERE p.product_id = 'PRD-3012'
""".strip(),
                    "expect": {
                        "scalar": {
                            "product_id": "PRD-3012",
                            "age_days": 35,
                            "base_margin_pct": 22.0,
                            "approval_id": "EXC-KM-2026-07",
                            "approved_floor_margin_pct": 12.0,
                            "status": "ACTIVE",
                        }
                    },
                }
            ],
            "gold_answer": "완화된 마진 하한이 적용되어 프로모션이 허용된다. PRD-3012는 입고 35일차로 체화재고(90일 이상)에는 해당하지 않으나, 유효한 VIP_RETENTION 예외승인(EXC-KM-2026-07, 승인 하한 12.0%, ACTIVE)이 존재하므로 기본마진 22.0%에서 최저마진 하한 12.0%(12%)까지 할인 캠페인이 가능하다.",
            "grading": {
                "must_include": [r"EXC-KM-2026-07", r"22(\.0)?%", r"12(\.0)?%"],
                "must_not_include": [],
                "cite": [{"doc": "08", "locator": "제4조"}],
            },
        },
        {
            "id": "EQ04",
            "category": "graph_favored",
            "sibling_cq": "CQ05",
            "question": "전체 주문품목 중 반품 사유가 등록된 품목들에 대해, MD본부의 총반품 건수와 CS심사팀의 판매자 귀책 무상반품 건수는 각각 몇 건이며 두 본부 간 집계 차이는 몇 건인가?",
            "expected_winner": "graphrag",
            "rationale": "동일한 반품 데이터라도 BusinessContext(MD본부 vs CS심사팀)에 따라 호출하는 조문과 필터링 조건(전체 반품 6건 vs 판매자 귀책 3건)이 달라지는 맥락 분기 문제.",
            "evidence": [ev(P_ECOM03_WPERIOD), ev(P_CS10_REASON)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  COUNTIF(return_reason_cd != 'NONE') AS md_total_return_cnt,
  COUNTIF(return_reason_cd IN ('DEFECTIVE', 'SIZE_MISMATCH_SPEC_DIFF')) AS cs_seller_fault_cnt,
  COUNTIF(return_reason_cd != 'NONE') - COUNTIF(return_reason_cd IN ('DEFECTIVE', 'SIZE_MISMATCH_SPEC_DIFF')) AS diff_cnt
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items`
""".strip(),
                    "expect": {
                        "scalar": {
                            "md_total_return_cnt": 6,
                            "cs_seller_fault_cnt": 3,
                            "diff_cnt": 3,
                        }
                    },
                }
            ],
            "gold_answer": "MD본부의 총반품 건수는 6건(단순변심 2건, 불량 2건, 실측사이즈 상이 1건, 착용·세탁 훼손 1건)이고, CS심사팀의 판매자 귀책 무상반품 건수는 3건(DEFECTIVE 2건, SIZE_MISMATCH_SPEC_DIFF 1건)으로 두 본부 간 집계 차이는 3건이다.",
            "grading": {
                "must_include": [r"6건", r"3건", r"DEFECTIVE"],
                "must_not_include": [],
                "cite": [{"doc": "03", "locator": "제17조제1항"}, {"doc": "10", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ05",
            "category": "graph_favored",
            "sibling_cq": "CQ08",
            "question": "아틀리에누아르의 공동판촉 쿠폰 적용 주문품목들을 정산할 때, 계약서상 판촉비 분담률 대신 대규모유통업법 제11조제4항의 법정 상한을 적용하면 K마켙이 의무적으로 추가 흡수해야 하는 초과 분담액 합계는 얼마인가?",
            "expected_winner": "graphrag",
            "rationale": "계약서상 분담율(60%)을 그대로 곱하면 180,000원이지만, 법정 50% 상한(150,000원) 및 OIT-2026-0004의 자발적 특례 기각(EXC-KM-2026-06 REJECTED)을 결합해 K마켙 추가 흡수분 30,000원(총 부담 150,000원)을 도출해야 함.",
            "evidence": [ev(P_LAW01_CAP50), ev(P_FTC02_CAP), ev(P_PRT09_CAP)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  b.brand_id,
  COUNT(*) AS promo_item_cnt,
  SUM(oi.coupon_discount_krw) AS total_discount_krw,
  CAST(SUM(oi.coupon_discount_krw * 0.60) AS INT64) AS contract_60pct_krw,
  CAST(SUM(oi.coupon_discount_krw * 0.50) AS INT64) AS legal_50pct_krw,
  CAST(SUM(oi.coupon_discount_krw * 0.10) AS INT64) AS kmarket_excess_absorbed_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
WHERE b.brand_id = 'BRD-01' AND oi.coupon_type = 'JOINT_PROMO'
GROUP BY b.brand_id
""".strip(),
                    "expect": {
                        "scalar": {
                            "brand_id": "BRD-01",
                            "promo_item_cnt": 4,
                            "total_discount_krw": 300000,
                            "contract_60pct_krw": 180000,
                            "legal_50pct_krw": 150000,
                            "kmarket_excess_absorbed_krw": 30000,
                        }
                    },
                }
            ],
            "gold_answer": "총 쿠폰할인액 300,000원에 대해 계약서상 60% 분담액은 180,000원이나, 대규모유통업법 제11조제4항의 50% 상한이 적용되어 아틀리에누아르(BRD-01)의 적법 분담액은 150,000원으로 제한되고, 10%p 초과분인 30,000원(K마켙 총 부담액 150,000원 중 초과 흡수분)은 K마켙이 의무 흡수해야 한다.",
            "grading": {
                "must_include": [r"30,?000", r"150,?000", r"50%"],
                "must_not_include": [],
                "cite": [{"doc": "01", "locator": "제11조제3항~제5항"}, {"doc": "09", "locator": "제3조"}],
            },
        },
        {
            "id": "EQ06",
            "category": "graph_favored",
            "sibling_cq": "CQ10",
            "question": "노르딕아웃도어의 다운 파카 주문품목 OIT-2026-0017에 대해 납품업자 판촉비 분담률 70%가 그대로 인정되어 브랜드에 청구할 수 있는지, 캠페인 예외승인 원장의 유효 결재 건과 기각 건을 대조하여 판정하라.",
            "expected_winner": "graphrag",
            "rationale": "대규모유통업법 제11조제5항 단서(자발적·차별화 행사 시 50% 상한 예외)와 CampaignException 원장의 ACTIVE(EXC-KM-2026-03) vs REJECTED(EXC-KM-2026-06) 상태를 결합 추론해야 함.",
            "evidence": [ev(P_LAW01_CAP50), ev(P_FTC02_VOL), ev(P_PRT09_VOL)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  oi.item_id,
  b.brand_id,
  oi.coupon_discount_krw,
  ce.approval_id,
  ce.status,
  CAST(oi.coupon_discount_krw * (b.agreed_promo_share_pct / 100.0) AS INT64) AS vendor_share_krw,
  CAST(oi.coupon_discount_krw * (1.0 - b.agreed_promo_share_pct / 100.0) AS INT64) AS kmarket_share_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts` b ON p.brand_id = b.brand_id
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce ON p.product_id = ce.product_id
WHERE oi.item_id = 'OIT-2026-0017'
""".strip(),
                    "expect": {
                        "scalar": {
                            "item_id": "OIT-2026-0017",
                            "brand_id": "BRD-05",
                            "coupon_discount_krw": 60000,
                            "approval_id": "EXC-KM-2026-03",
                            "status": "ACTIVE",
                            "vendor_share_krw": 42000,
                            "kmarket_share_krw": 18000,
                        }
                    },
                }
            ],
            "gold_answer": "인정된다. OIT-2026-0017(BRD-05, PRD-3008)은 자발성·차별성 심사를 통과한 유효 결재(EXC-KM-2026-03, ACTIVE)가 존재하므로 대규모유통업법 제11조제5항 단서에 따라 70% 분담율이 적용되어 브랜드가 42,000원, K마켙이 18,000원을 분담한다(반면 기각된 EXC-KM-2026-06은 50% 상한 적용).",
            "grading": {
                "must_include": [r"42,?000", r"18,?000", r"EXC-KM-2026-03"],
                "must_not_include": [],
                "cite": [{"doc": "01", "locator": "제11조제3항~제5항"}, {"doc": "09", "locator": "제4조"}],
            },
        },
        {
            "id": "EQ07",
            "category": "graph_favored",
            "sibling_cq": "CQ14",
            "question": "용인 물류센터에서 출고된 주문 ORD-2026-0012의 실측 사이즈 상이 반품 건(OIT-2026-0018)에 관세청 해외직구 특송고시상 국제반송수수료를 부과할 수 있는지 판정하고, 고객이 부담할 실제 반품배송비와 환급액을 산출하라.",
            "expected_winner": "graphrag",
            "rationale": "벡터 검색 시 '반품 수수료' 키워드로 관세청 해외직구 고시(35,000원)가 혼입되기 쉬우나, 그래프는 DC-YIN 국내 물류센터 출고 확인 및 CONFLICTS_BY_SECTOR 엣지로 타업권 고시를 차단하고 전자상거래법 제17조제3항(표시·광고 상이 무상반품)을 적용함.",
            "evidence": [ev(P_DIST06_SCOPE), ev(P_DIST06_FEE), ev(P_CS10_REFUND)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  oi.item_id,
  oi.order_id,
  inv.distribution_center_id,
  oi.return_reason_cd,
  oi.sale_price_krw,
  0 AS customer_return_fee_krw,
  oi.sale_price_krw AS refund_amount_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON oi.inventory_item_id = inv.inventory_item_id
WHERE oi.item_id = 'OIT-2026-0018'
""".strip(),
                    "expect": {
                        "scalar": {
                            "item_id": "OIT-2026-0018",
                            "order_id": "ORD-2026-0012",
                            "distribution_center_id": "DC-YIN",
                            "return_reason_cd": "SIZE_MISMATCH_SPEC_DIFF",
                            "customer_return_fee_krw": 0,
                            "refund_amount_krw": 100000,
                        }
                    },
                }
            ],
            "gold_answer": "부과할 수 없다. ORD-2026-0012(OIT-2026-0018)는 국내 용인 물류센터(DC-YIN)에서 출고된 국내 이커머스(DOMESTIC_ECOMMERCE) 거래이므로 관세청 해외직구 고시(OVERSEAS_DIRECT_CUSTOMS, 35,000원)는 적용이 차단된다. 또한 실측 사이즈 상이(SIZE_MISMATCH_SPEC_DIFF)는 판매자 귀책 사유이므로 고객 부담 반품배송비는 0원이며 결제금액 100,000원 전액을 환급해야 한다.",
            "grading": {
                "must_include": [r"0원", r"100,?000", r"DC-YIN"],
                "must_not_include": [],
                "cite": [{"doc": "06", "locator": "제3조"}, {"doc": "10", "locator": "제3조"}],
            },
        },
        {
            "id": "EQ08",
            "category": "graph_favored",
            "sibling_cq": "CQ15",
            "question": "물류센터별 출고 목표 SLA를 위반한 지연 출고 주문들에 대해 K마켙이 지급해야 할 지연보상 적립금의 전사 합계 포인트와 물류센터별 지연 건수는 각각 얼마인가?",
            "expected_winner": "graphrag",
            "rationale": "Order(주문·출고 시각) → OrderItem → InventoryItem(물류센터 코드) → CS 내규 제4조(센터별 SLA 목표시간 및 건당 3,000P 보상)를 연결해 전사 지연 건수(3건)와 보상 합계(9,000P)를 집계해야 함.",
            "evidence": [ev(P_CS10_SLA)],
            "answer_queries": [
                {
                    "sql": """
WITH sla_breach AS (
  SELECT
    o.order_id,
    inv.distribution_center_id,
    TIMESTAMP_DIFF(TIMESTAMP(o.shipped_at), TIMESTAMP(o.created_at), HOUR) AS elapsed_hours
  FROM `finance-ontology-changseop.kmarket_ecommerce.ont_orders` o
  JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi ON o.order_id = oi.order_id
  JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items` inv ON oi.inventory_item_id = inv.inventory_item_id
  WHERE TIMESTAMP_DIFF(TIMESTAMP(o.shipped_at), TIMESTAMP(o.created_at), HOUR) >
    CASE inv.distribution_center_id WHEN 'DC-ICN' THEN 24 WHEN 'DC-YIN' THEN 36 WHEN 'DC-BUS' THEN 48 END
)
SELECT
  COUNT(*) AS total_breach_orders,
  COUNTIF(distribution_center_id = 'DC-YIN') AS dc_yin_breach_cnt,
  COUNTIF(distribution_center_id = 'DC-BUS') AS dc_bus_breach_cnt,
  COUNT(*) * 3000 AS total_compensation_points
FROM sla_breach
""".strip(),
                    "expect": {
                        "scalar": {
                            "total_breach_orders": 3,
                            "dc_yin_breach_cnt": 2,
                            "dc_bus_breach_cnt": 1,
                            "total_compensation_points": 9000,
                        }
                    },
                }
            ],
            "gold_answer": "SLA 위반 지연 출고 주문은 총 3건(용인 DC-YIN 2건: ORD-2026-0009 60시간, ORD-2026-0014 42시간 / 양산 DC-BUS 1건: ORD-2026-0015 60시간)이며, 건당 3,000P씩 전사 합계 9,000P의 지연보상 적립금을 지급해야 한다.",
            "grading": {
                "must_include": [r"3건", r"9,?000P", r"3,?000P"],
                "must_not_include": [],
                "cite": [{"doc": "10", "locator": "제4조"}],
            },
        },

        # =========================================================================
        # RAG-FAVORED (6): EQ09 ~ EQ14 (expected_winner: rag)
        # =========================================================================
        {
            "id": "EQ09",
            "category": "rag_favored",
            "sibling_cq": "CQ11",
            "question": "대규모유통업법 제6조에서 계약 체결 즉시 서면을 교부할 때 요구하는 서명·기명날인 방식과 제18조에 명시된 계약 종료일로부터의 서류 보존 의무 기간은 몇 년인가?",
            "expected_winner": "rag",
            "rationale": "법 제6조의 서면 교부·전자서명 요건과 제18조의 5년 서류 보존 의무는 PDF 원문 조항의 서술형 사실 조회로 RAG 검색이 직접적임.",
            "graph_risk": "온톨로지 그래프의 BrandVendorContract 노드는 서면약정 체결 여부(written_promo_agreement_yn)만 보유하며, 전자서명 정의나 5년 서류보존 세부 항목은 원문 텍스트에만 존재함.",
            "evidence": [ev(P_LAW01_WRITTEN), ev(P_LAW01_REC5Y)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  COUNT(*) AS total_brands,
  COUNTIF(written_promo_agreement_yn = 'Y') AS signed_brands
FROM `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts`
""".strip(),
                    "expect": {"scalar": {"total_brands": 8, "signed_brands": 7}},
                }
            ],
            "gold_answer": "대규모유통업법 제6조제2항에 따라 서면 계약서에는 대규모유통업자와 납품업자 쌍방이 서명(전자서명법 제2조제2호에 따른 전자서명 포함) 또는 기명날인하여야 하며, 제18조제1항·제2항에 따라 계약이 끝난 날부터 5년간 계약서 및 판매촉진비용 분담 약정서 등 대통령령으로 정하는 서류를 보존하여야 한다.",
            "grading": {
                "must_include": [r"전자서명", r"기명날인", r"5년"],
                "must_not_include": [],
                "cite": [{"doc": "01", "locator": "제6조"}, {"doc": "01", "locator": "제12조·제17조·제18조"}],
            },
        },
        {
            "id": "EQ10",
            "category": "rag_favored",
            "sibling_cq": "CQ09",
            "question": "공정위 판매촉진비용 부담전가 심사지침에서 판촉행사 개시 이후 사후에 서면을 소급 보완하거나 분담비율을 공란으로 둔 약정의 효력과 법 위반 여부를 어떻게 규정하는가?",
            "expected_winner": "rag",
            "rationale": "심사지침 Ⅱ.3의 사후 소급 서면 교부 금지 및 공란 약정의 위법성 판단 기준은 비정형 지침 본문 서술에 상세히 기재되어 있어 RAG가 유리함.",
            "graph_risk": "그래프는 written_promo_agreement_yn(Y/N) 이진 플래그로만 분담금을 계산하므로, '사후 소급 약정'이나 '공란 약정'의 법리적 무효 사유 서술은 텍스트 청크 검색이 필요함.",
            "evidence": [ev(P_FTC02_SCOPE), ev(P_FTC02_PRIOR)],
            "answer_queries": [
                {
                    "sql": """
SELECT brand_id, brand_name, agreed_promo_share_pct
FROM `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts`
WHERE written_promo_agreement_yn = 'N'
ORDER BY brand_id
""".strip(),
                    "expect": {
                        "exact_rows": 1,
                        "must_contain": [{"brand_id": "BRD-03", "brand_name": "마린블루", "agreed_promo_share_pct": 50.0}],
                    },
                }
            ],
            "gold_answer": "공정위 판매촉진비용 심사지침 Ⅱ.3에 따르면 판매촉진행사가 시작된 이후에 사후적으로 서면을 교부하거나 소급하여 서명받은 경우, 또는 약정서에 예상 분담액이나 분담비율을 공란('추후 정산 시 합의' 등)으로 둔 경우에는 적법한 사전 서면약정으로 인정되지 아니하며 납품업자에게 판매촉진비용을 부담시키는 행위는 위법하다.",
            "grading": {
                "must_include": [r"사후", r"소급", r"공란"],
                "must_not_include": [],
                "cite": [{"doc": "02", "locator": "Ⅰ.3~Ⅱ.2"}, {"doc": "02", "locator": "Ⅱ.3"}],
            },
        },
        {
            "id": "EQ11",
            "category": "rag_favored",
            "sibling_cq": "CQ20",
            "question": "전자상거래법 제21조의2제1항에서 금지하는 온라인 다크패턴 4가지 행위 유형의 명칭과 공정위 다크패턴 가이드라인 제2조에서 허위할인 방지를 위해 요구하는 종전거래가격의 산정 기준은 무엇인가?",
            "expected_winner": "rag",
            "rationale": "전자상거래법 제21조의2제1항 각호의 4대 다크패턴 명칭과 가이드라인 제2조의 '직전 20일 최저 판매가격' 정의는 전형적인 법령·가이드라인 텍스트 질의임.",
            "graph_risk": "Provision 노드는 missing_schema_columns(min_sale_price_20d_krw)만 구조화하고 있어 제21조의2제1항 1~4호의 세부 행위 유형 열거는 원문 조회가 필수적임.",
            "evidence": [ev(P_ECOM03_DARK), ev(P_DP04_PRICE)],
            "answer_queries": [
                {
                    "sql": """
SELECT COUNT(*) AS active_products
FROM `finance-ontology-changseop.kmarket_ecommerce.products`
""".strip(),
                    "expect": {"scalar": {"active_products": 30}},
                }
            ],
            "gold_answer": "전자상거래법 제21조의2제1항이 금지하는 4대 다크패턴 유형은 ① 숨은 갱신, ② 순차공개 가격책정, ③ 특정옵션의 사전선택, ④ 잘못된 계층구조이며, 공정위 다크패턴 가이드라인 제2조에 따른 종전거래가격은 할인 표시 시점 직전 20일 동안 실제 판매된 최저 판매가격을 기준으로 표시하여야 한다.",
            "grading": {
                "must_include": [r"숨은 갱신", r"순차공개 가격책정", r"20일"],
                "must_not_include": [],
                "cite": [{"doc": "03", "locator": "제21조의2"}, {"doc": "04", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ12",
            "category": "rag_favored",
            "sibling_cq": "CQ18",
            "question": "개인정보보호위원회 맞춤형 광고 행태정보 가이드라인 제4조·제5조에서 규정하는 비식별 행태정보의 최대 보유·이용 기간과 심야 시간대 광고성 푸시 제한 원칙은 무엇인가?",
            "expected_winner": "rag",
            "rationale": "가이드라인 제4조의 비식별 행태정보 최대 90일 보유 후 지체 없이 파기 원칙은 문서 내 서술형 조항으로 RAG 검색에 적합함.",
            "graph_risk": "온톨로지 그래프는 실시간 장바구니 이벤트만 노드로 보유하며 비식별 행태정보의 90일 보유기간 상한은 그래프 필터 속성에 모델링되어 있지 않음.",
            "evidence": [ev(P_PIPC05_DEF), ev(P_PIPC05_NIGHT)],
            "answer_queries": [
                {
                    "sql": """
SELECT COUNT(*) AS event_cnt, COUNT(DISTINCT session_id) AS session_cnt
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events`
""".strip(),
                    "expect": {"scalar": {"event_cnt": 11, "session_cnt": 6}},
                }
            ],
            "gold_answer": "개보위 맞춤형 광고 행태정보 가이드라인 제4조에 따라 비식별 행태정보의 보유 및 이용 기간은 수집일로부터 최대 90일을 초과할 수 없으며 목적 달성 시 지체 없이 파기해야 한다. 또한 제5조에 따라 야간 시간대(21:00부터 익일 08:00까지)에는 별도의 야간 광고성 정보 수신동의가 없는 한 행태정보 기반 실시간 타겟팅 푸시 알림 전송이 금지된다.",
            "grading": {
                "must_include": [r"90일", r"21:00", r"08:00"],
                "must_not_include": [],
                "cite": [{"doc": "05", "locator": "제4조~제5조"}],
            },
        },
        {
            "id": "EQ13",
            "category": "rag_favored",
            "sibling_cq": "CQ13",
            "question": "전자상거래법 제18조 및 K마켙 CS 내규 제3조에 따라 통신판매업자가 소비자로부터 재화등을 반환받은 날부터 대금을 환급해야 하는 법정 기한과 환급 지연 시 지급해야 하는 지연배상금 연 이율은 얼마인가?",
            "expected_winner": "rag",
            "rationale": "환급 법정 기한(3영업일 이내)과 지연배상금 산정 이율(연 15%)은 법 제18조 및 내규 제3조 본문에 직접 명시된 서술형 규정 수치임.",
            "graph_risk": "그래프는 반품 적격성과 반품배송비(6,000원)를 계산하지만 3영업일 환급 기한 도과 시 연 15% 지연배상금 이율은 그래프 엣지 속성에 포함되어 있지 않음.",
            "evidence": [ev(P_ECOM03_REFUND), ev(P_CS10_REFUND)],
            "answer_queries": [
                {
                    "sql": """
SELECT COUNT(*) AS returned_cnt, SUM(sale_price_krw) AS returned_amount_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items`
WHERE status = 'Returned'
""".strip(),
                    "expect": {"scalar": {"returned_cnt": 5, "returned_amount_krw": 650000}},
                }
            ],
            "gold_answer": "전자상거래법 제18조제2항 및 K마켙 CS 내규 제3조제1항에 따라 재화등을 반환받은 날부터 3영업일 이내에 대금을 환급하여야 하며, 대금 환급을 지연한 때에는 그 지연기간에 대하여 연 100분의 15(연 15%)의 지연배상금을 함께 지급하여야 한다.",
            "grading": {
                "must_include": [r"3영업일", r"15%"],
                "must_not_include": [],
                "cite": [{"doc": "03", "locator": "제18조"}, {"doc": "10", "locator": "제3조"}],
            },
        },
        {
            "id": "EQ14",
            "category": "rag_favored",
            "sibling_cq": "CQ11",
            "question": "대규모유통업법 제10조제1항에서 금지하는 부당 반품의 원칙과, 직매입 거래에서 예외적으로 납품업자에게 반품이 허용되는 정당한 사유는 무엇인가?",
            "expected_winner": "rag",
            "rationale": "대규모유통업법 제10조제1항 각호의 납품업자 대상 B2B 반품 예외 사유 열거는 법령 본문 독해 문제로 RAG에 유리함.",
            "graph_risk": "온톨로지 그래프는 B2C 소비자 청약철회(OrderItem)만 모델링하고 대규모유통업자와 직매입 납품업자 간 B2B 반품 예외 요건은 원문 서술에만 존재함.",
            "evidence": [ev(P_LAW01_RETBAN)],
            "answer_queries": [
                {
                    "sql": """
SELECT brand_id, brand_name
FROM `finance-ontology-changseop.kmarket_ecommerce.brand_vendor_contracts`
WHERE trade_type = '직매입'
ORDER BY brand_id
""".strip(),
                    "expect": {
                        "exact_rows": 2,
                        "must_contain": [{"brand_id": "BRD-05"}, {"brand_id": "BRD-08"}],
                    },
                }
            ],
            "gold_answer": "대규모유통업법 제10조제1항은 정당한 사유 없이 납품받은 상품의 전부 또는 일부를 반품하는 행위를 금지하며, 직매입 거래에서는 ① 납품업자의 책임 있는 사유로 상품이 오손·훼손된 경우, ② 납품받은 상품이 계약한 상품과 다른 경우, ③ 시즌상품 등 일정 기간 동안만 판매되는 상품에 대해 사전에 반품조건을 구체적으로 약정한 경우 등에 한하여 예외적으로 반품이 허용된다.",
            "grading": {
                "must_include": [r"오손", r"훼손", r"직매입"],
                "must_not_include": [],
                "cite": [{"doc": "01", "locator": "제10조"}],
            },
        },

        # =========================================================================
        # PARITY (6): EQ15 ~ EQ20 (expected_winner: tie)
        # =========================================================================
        {
            "id": "EQ15",
            "category": "parity",
            "sibling_cq": "CQ06",
            "question": "주문품목 OIT-2026-0001에 쿠폰 할인이 적용된 후의 단건 실현마진율은 소수 첫째 자리 기준 몇 %이며, MD본부 상시 마진 가드레일을 충족하는가?",
            "expected_winner": "tie",
            "rationale": "단일 주문품목(OIT-2026-0001)과 상품 원가(PRD-3001)를 조인해 실현마진율 산식((340,000-240,000)/340,000 = 29.4%)을 계산하는 기본 문항으로 두 암 모두 정확히 수행 가능함.",
            "evidence": [ev(P_MD08_25PCT)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  oi.item_id,
  oi.sale_price_krw,
  p.cost_krw,
  ROUND((oi.sale_price_krw - p.cost_krw) / oi.sale_price_krw * 100, 1) AS realized_margin_pct
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.products` p ON oi.product_id = p.product_id
WHERE oi.item_id = 'OIT-2026-0001'
""".strip(),
                    "expect": {
                        "scalar": {
                            "item_id": "OIT-2026-0001",
                            "sale_price_krw": 340000,
                            "cost_krw": 240000,
                            "realized_margin_pct": 29.4,
                        }
                    },
                }
            ],
            "gold_answer": "OIT-2026-0001의 실현마진율은 (실결제가 340,000원 - 매입원가 240,000원) / 340,000원 = 29.4%이며, MD본부 상시 최저마진 가드레일(25.0%)을 충족한다.",
            "grading": {
                "must_include": [r"29\.4%", r"25(\.0)?%"],
                "must_not_include": [],
                "cite": [{"doc": "08", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ16",
            "category": "parity",
            "sibling_cq": "CQ16",
            "question": "장바구니 이탈 세션 SES-1004-A를 발생시킨 VIP 등급 최현우 고객에게 맞춤형 리마인드 푸시나 타겟팅 쿠폰을 발송할 수 없는 이유를 회원 마스터의 동의 컬럼 값과 개보위 가이드라인 제3조를 근거로 답하라.",
            "expected_winner": "tie",
            "rationale": "USR-1004의 marketing_opt_in_yn = 'N' 단일 필터 확인과 개보위 가이드라인 제3조 매칭으로 두 암 모두 쉽게 해결 가능함.",
            "evidence": [ev(P_PIPC05_OPTIN), ev(P_CRM07_OPTIN)],
            "answer_queries": [
                {
                    "sql": """
SELECT u.user_id, u.user_name, u.membership_tier, u.marketing_opt_in_yn
FROM `finance-ontology-changseop.kmarket_ecommerce.users` u
WHERE u.user_id = 'USR-1004'
""".strip(),
                    "expect": {
                        "scalar": {
                            "user_id": "USR-1004",
                            "user_name": "최현우",
                            "membership_tier": "VIP",
                            "marketing_opt_in_yn": "N",
                        }
                    },
                }
            ],
            "gold_answer": "최현우(USR-1004, VIP)는 회원 마스터상 마케팅 및 맞춤형 추천 수신동의가 거부(marketing_opt_in_yn = 'N') 상태이므로, 개인정보보호위원회 맞춤형 광고 행태정보 가이드라인 제3조 및 K마켙 CRM 내규 제2조에 따라 회원 식별 기반 장바구니 리마인드 푸시 및 타겟팅 쿠폰 발송이 즉시 차단된다.",
            "grading": {
                "must_include": [r"USR-1004", r"marketing_opt_in_yn", r"제3조"],
                "must_not_include": [],
                "cite": [{"doc": "05", "locator": "제3조"}, {"doc": "07", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ17",
            "category": "parity",
            "sibling_cq": "CQ12",
            "question": "위생제한 상품인 실크 레이스 브라렛에 대한 반품 신청 건 OIT-2026-0014의 청약철회 승인 여부와 그 물리적 검수 근거는 무엇인가?",
            "expected_winner": "tie",
            "rationale": "OIT-2026-0014와 EXC-KM-2026-05(hologram_tag_intact_yn='N')이 직접 연결되어 있어 SQL 조인이나 그래프 탐색 모두 동일한 결론에 도달함.",
            "evidence": [ev(P_ECOM03_WRESTRICT), ev(P_CS10_REASON)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  oi.item_id,
  oi.product_id,
  oi.sale_price_krw,
  ce.approval_id,
  ce.hologram_tag_intact_yn
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
JOIN `finance-ontology-changseop.kmarket_ecommerce.ont_campaign_exceptions` ce ON oi.item_id = ce.item_id
WHERE oi.item_id = 'OIT-2026-0014'
""".strip(),
                    "expect": {
                        "scalar": {
                            "item_id": "OIT-2026-0014",
                            "product_id": "PRD-3007",
                            "sale_price_krw": 90000,
                            "approval_id": "EXC-KM-2026-05",
                            "hologram_tag_intact_yn": "N",
                        }
                    },
                }
            ],
            "gold_answer": "청약철회(반품)가 거절(REJECT_WITHDRAWAL)되어 결제가 90,000원은 환불되지 않는다. PRD-3007은 위생제한(HYGIENE_RESTRICTED) 상품인데 반품 검수 원장 EXC-KM-2026-05에서 홀로그램 실링 택이 훼손(hologram_tag_intact_yn = 'N')된 것으로 확인되었으므로 전자상거래법 제17조제2항에 따라 반품이 불가하다.",
            "grading": {
                "must_include": [r"EXC-KM-2026-05", r"90,?000", r"제17조제2항"],
                "must_not_include": [],
                "cite": [{"doc": "03", "locator": "제17조제2항"}, {"doc": "10", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ18",
            "category": "parity",
            "sibling_cq": "CQ13",
            "question": "배송완료 후 3일 만에 단순변심으로 반품 접수된 주문품목 OIT-2026-0007의 청약철회 적격 여부, 차감할 왕복 반품배송비, 그리고 고객에게 최종 환급할 금액은 얼마인가?",
            "expected_winner": "tie",
            "rationale": "단순변심 7일 이내 반품 적격 판정 및 표준 왕복 반품배송비 6,000원 차감(200,000 - 6,000 = 194,000원)은 두 암 모두 명확히 계산 가능함.",
            "evidence": [ev(P_ECOM03_WPERIOD), ev(P_CS10_REASON)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  oi.item_id,
  oi.sale_price_krw,
  6000 AS return_ship_fee_krw,
  oi.sale_price_krw - 6000 AS net_refund_krw
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_order_items` oi
WHERE oi.item_id = 'OIT-2026-0007'
""".strip(),
                    "expect": {
                        "scalar": {
                            "item_id": "OIT-2026-0007",
                            "sale_price_krw": 200000,
                            "return_ship_fee_krw": 6000,
                            "net_refund_krw": 194000,
                        }
                    },
                }
            ],
            "gold_answer": "배송완료 후 7일 이내(3일 경과)에 신청되었으므로 전자상거래법 제17조제1항에 따라 청약철회가 승인되며, 단순변심 사유이므로 고객 부담 왕복 반품배송비 6,000원을 차감한 194,000원을 최종 환급한다.",
            "grading": {
                "must_include": [r"6,?000", r"194,?000", r"7일"],
                "must_not_include": [],
                "cite": [{"doc": "03", "locator": "제17조제1항"}, {"doc": "10", "locator": "제1조~제2조"}],
            },
        },
        {
            "id": "EQ19",
            "category": "parity",
            "sibling_cq": "CQ07",
            "question": "물류센터 재고 원장 전체 32개 항목을 재고상태별로 집계할 때 각 상태의 항목 수와 수량 합계는 얼마인가?",
            "expected_winner": "tie",
            "rationale": "단일 재고 원장 테이블의 상태별 집계 쿼리로 두 암 모두 동일하게 조회 가능함.",
            "evidence": [ev(P_CRM07_BUNDLE)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  stock_status,
  COUNT(*) AS item_cnt,
  SUM(avail_qty) AS total_qty
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_inventory_items`
GROUP BY stock_status
ORDER BY stock_status
""".strip(),
                    "expect": {
                        "exact_rows": 4,
                        "must_contain": [
                            {"stock_status": "AVAILABLE", "item_cnt": 28, "total_qty": 715},
                            {"stock_status": "OUT_OF_STOCK", "item_cnt": 2, "total_qty": 0},
                            {"stock_status": "RESERVED", "item_cnt": 1, "total_qty": 10},
                            {"stock_status": "RETURN_INSPECTION", "item_cnt": 1, "total_qty": 15},
                        ],
                    },
                }
            ],
            "gold_answer": "재고상태별 집계 결과 AVAILABLE(즉시 출고 가용) 28건·715개, RESERVED(결제 진행 예약) 1건·10개, RETURN_INSPECTION(반품 검수 대기) 1건·15개, OUT_OF_STOCK(일시품절) 2건·0개이다.",
            "grading": {
                "must_include": [r"715", r"28", r"OUT_OF_STOCK"],
                "must_not_include": [],
                "cite": [{"doc": "07", "locator": "제3조"}],
            },
        },
        {
            "id": "EQ20",
            "category": "parity",
            "sibling_cq": "CQ16",
            "question": "실시간 행동로그에서 장바구니 담기 이후 이탈하지 않고 동일 세션 내에 결제완료까지 정상 전환된 세션 ID와 회원 ID, 구매 상품 ID 및 해당 회원의 멤버십 등급은 무엇인가?",
            "expected_winner": "tie",
            "rationale": "ont_events에서 event_type='purchase'가 존재하는 세션을 찾고 users와 조인하는 기본 조회로 두 암 모두 동등하게 수행함.",
            "evidence": [ev(P_CRM07_OPTIN)],
            "answer_queries": [
                {
                    "sql": """
SELECT
  e.session_id,
  e.user_id,
  e.product_id,
  u.membership_tier
FROM `finance-ontology-changseop.kmarket_ecommerce.ont_events` e
JOIN `finance-ontology-changseop.kmarket_ecommerce.users` u ON e.user_id = u.user_id
WHERE e.event_type = 'purchase'
""".strip(),
                    "expect": {
                        "scalar": {
                            "session_id": "SES-1008-A",
                            "user_id": "USR-1008",
                            "product_id": "PRD-3004",
                            "membership_tier": "VIP",
                        }
                    },
                }
            ],
            "gold_answer": "장바구니 담기 후 동일 세션 내 결제완료(purchase)까지 전환된 세션은 SES-1008-A이며, 회원 ID는 USR-1008(VIP 등급), 구매 상품 ID는 PRD-3004이다.",
            "grading": {
                "must_include": [r"SES-1008-A", r"USR-1008", r"PRD-3004", r"VIP"],
                "must_not_include": [],
                "cite": [{"doc": "07", "locator": "제1조~제2조"}],
            },
        },
    ]


    return {
        "meta": {
            "version": "1.1.0",
            "created": "2026-10-06",
            "updated": "2026-10-06",
            "status": "approved",
            "allocation": {"graph_favored": 8, "rag_favored": 6, "parity": 6},
            "holdout_from": "ecommerce/ontology/cq/competency_questions.yaml",
        },
        "protocol": {
            "arms": {
                "rag": {
                    "retrieval": "GCP Vertex AI RAG Engine — ecommerce/data/un_data/*.pdf 10종 벡터 검색 + BigQuery 관계형 SQL",
                    "tools": ["vertex_rag_search", "bigquery_sql"],
                },
                "graphrag": {
                    "retrieval": "단일 통합 GraphRAG 파이프라인 — Alias(34행) & KC Aspect 고정 GQL 템플릿 바인딩 → GQL 플래너 + BQ Dry-Run 검증 → KC 유효성 검증(kc_lookup) → 단일 통합 GQL(graph_query) + ObjectRef 원문 조회(fetch_provision)",
                    "tools": ["graph_query", "kc_lookup", "fetch_provision"],
                },
            },
            "scoring": {
                "per_question": "2 = must_include 전부 + must_not_include 0 + 필수 인용 충족 / 1 = must_include 절반 이상 & must_not_include 0 / 0 = 그 외",
                "judge": "정규식 기반 결정론적 채점 (LLM-judge 미사용)",
            },
        },
        "sources": SOURCES,
        "questions": questions,
    }


def main() -> None:
    os.makedirs(os.path.dirname(CQ_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(EQ_OUT), exist_ok=True)
    cq_doc = build_cqs()
    eq_doc = build_eqs()
    with open(CQ_OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(cq_doc, f, allow_unicode=True, sort_keys=False, width=120)
    with open(EQ_OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(eq_doc, f, allow_unicode=True, sort_keys=False, width=120)
    print(f"Wrote {len(cq_doc['cqs'])} CQs to {CQ_OUT}")
    print(f"Wrote {len(eq_doc['questions'])} EQs to {EQ_OUT}")


if __name__ == "__main__":
    main()

