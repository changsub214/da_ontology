-- ============================================================================
-- 1. 11 NODE VIEWS IN `YOUR_PROJECT_ID.kmarket_ontology`
-- ============================================================================

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_business_context` AS
SELECT context_id, dept_name, purpose_summary, primary_metric_scope
FROM `YOUR_PROJECT_ID.kmarket_ontology.ctx_business_contexts`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_source_document` AS
SELECT
  doc_id, doc_code, title, authority_level, applicable_sector, issuing_body, kc_entry_id, gcs_uri
FROM `YOUR_PROJECT_ID.kmarket_ontology.lex_source_documents`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` AS
SELECT
  provision_slot_id, doc_id, kc_entry_id, article_no, title,
  provision_role, target_columns, missing_schema_columns, gcs_uri, full_text
FROM `YOUR_PROJECT_ID.kmarket_ontology.lex_provisions`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_order_item` AS
SELECT
  item_id AS order_item_id,
  item_id,
  order_id, user_id, product_id, inventory_item_id,
  status, retail_price_krw, coupon_discount_krw, sale_price_krw,
  coupon_type AS campaign_id,
  coupon_type,
  return_reason_cd AS return_reason_code,
  return_reason_cd,
  created_at, shipped_at, delivered_at, returned_at
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_order` AS
SELECT
  order_id, user_id, status, created_at, shipped_at,
  delivered_at,
  returned_at AS return_requested_at,
  returned_at,
  num_of_item
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_orders`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_customer` AS
SELECT
  user_id, user_name, age, gender, city, membership_tier,
  (marketing_opt_in_yn = 'Y') AS marketing_opt_in,
  marketing_opt_in_yn,
  preferred_style AS primary_category,
  preferred_style,
  traffic_source,
  CAST(created_at AS STRING) AS created_at
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.users`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_product` AS
SELECT
  product_id,
  sku AS sku_code,
  sku,
  product_name, category, department, brand_id, brand_name,
  cost_krw, retail_price_krw,
  style_tag AS style_tags,
  style_tag,
  coord_product_id AS complementary_product_id,
  coord_product_id,
  substitute_product_id,
  return_policy_tag,
  distribution_center_id,
  TRUE AS is_active
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.products`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_brand_vendor_contract` AS
SELECT
  brand_id, brand_name,
  trade_type AS contract_type,
  trade_type,
  ROUND(base_commission_pct / 100.0, 4) AS commission_rate,
  base_commission_pct,
  ROUND(agreed_promo_share_pct / 100.0, 4) AS promo_cost_share_ratio,
  agreed_promo_share_pct,
  (written_promo_agreement_yn = 'Y') AS signed_promo_agreement,
  written_promo_agreement_yn,
  0.25 AS min_margin_guardrail,
  6000 AS return_shipping_fee_krw,
  sla_ship_hours
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.brand_vendor_contracts`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_inventory_item` AS
SELECT
  inventory_item_id, product_id,
  distribution_center_id AS distribution_center,
  distribution_center_id,
  avail_qty AS available_stock,
  avail_qty,
  age_days AS stock_age_days,
  age_days,
  inbound_date,
  stock_status
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_inventory_items`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_user_behavior_event` AS
SELECT
  event_id, user_id, session_id, sequence_number,
  product_id, event_type, traffic_source, created_at
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_events`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_node_campaign_exception` AS
SELECT
  approval_id AS exception_id,
  approval_id,
  target_kind AS exception_type,
  target_kind,
  product_id,
  item_id,
  ROUND(approved_floor_margin_pct / 100.0, 4) AS approved_margin_floor,
  approved_floor_margin_pct,
  hologram_tag_intact_yn,
  vendor_voluntary_req_yn,
  approver_dept AS approved_by_role,
  approver_dept,
  approved_date AS valid_until,
  approved_date,
  status
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_campaign_exceptions`;

-- ============================================================================
-- 2. 15 EDGE VIEWS IN `YOUR_PROJECT_ID.kmarket_ontology`
-- ============================================================================

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_scopes_portfolio` AS
SELECT
  CONCAT('SCOPE_', ctx.context_id, '_', oi.item_id) AS edge_id,
  ctx.context_id,
  oi.item_id AS order_item_id,
  CASE
    WHEN oi.status = 'Returned' OR oi.return_reason_cd != 'NONE' THEN 'CS_RETURN_AND_WITHDRAWAL_SCOPE'
    WHEN oi.coupon_discount_krw > 0 THEN 'PROMO_MARGIN_AND_VENDOR_SHARE_SCOPE'
    ELSE 'STANDARD_ORDER_FULFILLMENT_SCOPE'
  END AS portfolio_scope_rule
FROM `YOUR_PROJECT_ID.kmarket_ontology.ctx_business_contexts` ctx
CROSS JOIN `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_belongs_to_order` AS
SELECT item_id AS order_item_id, order_id
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_placed_by_user` AS
SELECT order_id, user_id
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_orders`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_of_product` AS
SELECT item_id AS order_item_id, product_id
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_supplied_by_brand` AS
SELECT product_id, brand_id
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.products`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_stocked_at_inventory` AS
SELECT product_id, inventory_item_id
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_inventory_items`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_logged_event_on_product` AS
SELECT event_id, product_id, user_id, event_type
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_events`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_has_campaign_exception` AS
SELECT
  product_id,
  approval_id AS exception_id,
  target_kind AS exception_type,
  status
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_campaign_exceptions`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_invokes_provision` AS
SELECT edge_id, context_id, term_key, glossary_term_uri, provision_slot_id, invocation_reason
FROM `YOUR_PROJECT_ID.kmarket_ontology.edge_invokes_provision`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_governed_by_criteria` AS
SELECT
  CONCAT('GOV_PROMO_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso' AS provision_slot_id,
  '쿠폰할인 적용 주문품목 — 대규모유통업법 제11조제3항~제5항 납품업자 판촉비 50% 상한 심사 대상' AS binding_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi
WHERE oi.coupon_discount_krw > 0
UNION ALL
SELECT
  CONCAT('GOV_SETTLE_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula' AS provision_slot_id,
  '쿠폰할인 적용 주문품목 — K마켙 정산내규 제3조 브랜드 분담률 50% 캡 및 초과분 흡수 정산 대상' AS binding_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi
WHERE oi.coupon_discount_krw > 0
UNION ALL
SELECT
  CONCAT('GOV_MARGIN_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail' AS provision_slot_id,
  '주문품목 실현마진율 산식 및 상시 25% 최저마진 가드레일 점검 대상' AS binding_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi
UNION ALL
SELECT
  CONCAT('GOV_RET_LAW_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods' AS provision_slot_id,
  '반품 신청 품목 — 전자상거래법 제17조 청약철회 가능 기한(7일 vs 90일) 심사 대상' AS binding_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi
WHERE oi.status = 'Returned' OR oi.return_reason_cd != 'NONE'
UNION ALL
SELECT
  CONCAT('GOV_RET_CS_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules' AS provision_slot_id,
  '반품 신청 품목 — K마켙 CS내규 제2조 반품사유 코드별 승인 여부 및 배송비(6,000원) 귀속 판정 대상' AS binding_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi
WHERE oi.status = 'Returned' OR oi.return_reason_cd != 'NONE'
UNION ALL
SELECT
  CONCAT('GOV_SLA_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_004_fulfillment_sla_compensation' AS provision_slot_id,
  '물류센터 출고 품목 — K마켙 내규 제4조 센터별 출고 SLA 준수 및 지연보상 판정 대상' AS binding_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_order_items` oi;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_evaluated_under_provision` AS
SELECT
  CONCAT('EVAL_PIPC_', ev.event_id) AS edge_id,
  ev.event_id,
  'regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement' AS provision_slot_id,
  '고객 행동로그 기반 타겟팅 시 개보위 가이드라인 제3조 마케팅 수신동의(marketing_opt_in=True) 필수 검증' AS evaluation_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_events` ev
WHERE ev.event_type = 'cart'
UNION ALL
SELECT
  CONCAT('EVAL_CRM02_', ev.event_id) AS edge_id,
  ev.event_id,
  'internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin' AS provision_slot_id,
  '장바구니 이탈 세션 탐지 및 마케팅 수신동의 검증 게이트' AS evaluation_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_events` ev
WHERE ev.event_type = 'cart'
UNION ALL
SELECT
  CONCAT('EVAL_CRM03_', ev.event_id) AS edge_id,
  ev.event_id,
  'internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle' AS provision_slot_id,
  '장바구니 상품 가용재고 연동 품절 대체상품 전환 및 코디 번들 크로스셀 추천 규칙' AS evaluation_reason
FROM `YOUR_PROJECT_ID.kmarket_ecommerce.ont_events` ev
WHERE ev.event_type = 'cart';

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_part_of_document` AS
SELECT provision_slot_id, doc_id
FROM `YOUR_PROJECT_ID.kmarket_ontology.lex_provisions`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_has_exception_proviso` AS
SELECT edge_id, base_slot_id, proviso_slot_id, exception_condition
FROM `YOUR_PROJECT_ID.kmarket_ontology.edge_has_exception_proviso`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_delegates_to_internal` AS
SELECT edge_id, external_slot_id, internal_slot_id, delegation_scope
FROM `YOUR_PROJECT_ID.kmarket_ontology.edge_delegates_to_internal`;

CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.kmarket_ontology.v_edge_conflicts_by_sector` AS
SELECT edge_id, ecommerce_slot_id, distractor_slot_id, conflict_warning
FROM `YOUR_PROJECT_ID.kmarket_ontology.edge_conflicts_by_sector`;

-- ============================================================================
-- 3. CREATE OR REPLACE PROPERTY GRAPH `YOUR_PROJECT_ID.kmarket_ontology.ecommerce_graph`
-- ============================================================================

CREATE OR REPLACE PROPERTY GRAPH `YOUR_PROJECT_ID.kmarket_ontology.ecommerce_graph`
  NODE TABLES (
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_business_context`
      KEY (context_id)
      LABEL BusinessContext,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_source_document`
      KEY (doc_id)
      LABEL SourceDocument,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision`
      KEY (provision_slot_id)
      LABEL Provision,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_order_item`
      KEY (order_item_id)
      LABEL OrderItem,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_order`
      KEY (order_id)
      LABEL `Order`,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_customer`
      KEY (user_id)
      LABEL Customer,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_product`
      KEY (product_id)
      LABEL Product,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_brand_vendor_contract`
      KEY (brand_id)
      LABEL BrandVendorContract,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_inventory_item`
      KEY (inventory_item_id)
      LABEL InventoryItem,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_user_behavior_event`
      KEY (event_id)
      LABEL UserBehaviorEvent,
    `YOUR_PROJECT_ID.kmarket_ontology.v_node_campaign_exception`
      KEY (exception_id)
      LABEL CampaignException
  )
  EDGE TABLES (
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_scopes_portfolio`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_business_context` (context_id)
      DESTINATION KEY (order_item_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_order_item` (order_item_id)
      LABEL SCOPES_PORTFOLIO,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_belongs_to_order`
      KEY (order_item_id, order_id)
      SOURCE KEY (order_item_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_order_item` (order_item_id)
      DESTINATION KEY (order_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_order` (order_id)
      LABEL BELONGS_TO_ORDER,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_placed_by_user`
      KEY (order_id, user_id)
      SOURCE KEY (order_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_order` (order_id)
      DESTINATION KEY (user_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_customer` (user_id)
      LABEL PLACED_BY_USER,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_of_product`
      KEY (order_item_id, product_id)
      SOURCE KEY (order_item_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_order_item` (order_item_id)
      DESTINATION KEY (product_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_product` (product_id)
      LABEL OF_PRODUCT,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_supplied_by_brand`
      KEY (product_id, brand_id)
      SOURCE KEY (product_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_product` (product_id)
      DESTINATION KEY (brand_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_brand_vendor_contract` (brand_id)
      LABEL SUPPLIED_BY_BRAND,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_stocked_at_inventory`
      KEY (product_id, inventory_item_id)
      SOURCE KEY (product_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_product` (product_id)
      DESTINATION KEY (inventory_item_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_inventory_item` (inventory_item_id)
      LABEL STOCKED_AT_INVENTORY,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_logged_event_on_product`
      KEY (event_id, product_id)
      SOURCE KEY (event_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_user_behavior_event` (event_id)
      DESTINATION KEY (product_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_product` (product_id)
      LABEL LOGGED_EVENT_ON_PRODUCT,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_has_campaign_exception`
      KEY (product_id, exception_id)
      SOURCE KEY (product_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_product` (product_id)
      DESTINATION KEY (exception_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_campaign_exception` (exception_id)
      LABEL HAS_CAMPAIGN_EXCEPTION,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_invokes_provision`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_business_context` (context_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      LABEL INVOKES_PROVISION,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_governed_by_criteria`
      KEY (edge_id)
      SOURCE KEY (order_item_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_order_item` (order_item_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      LABEL GOVERNED_BY_CRITERIA,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_evaluated_under_provision`
      KEY (edge_id)
      SOURCE KEY (event_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_user_behavior_event` (event_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      LABEL EVALUATED_UNDER_PROVISION,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_part_of_document`
      KEY (provision_slot_id, doc_id)
      SOURCE KEY (provision_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (doc_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_source_document` (doc_id)
      LABEL PART_OF_DOCUMENT,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_has_exception_proviso`
      KEY (edge_id)
      SOURCE KEY (base_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (proviso_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      LABEL HAS_EXCEPTION_PROVISO,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_delegates_to_internal`
      KEY (edge_id)
      SOURCE KEY (external_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (internal_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      LABEL DELEGATES_TO_INTERNAL,
    `YOUR_PROJECT_ID.kmarket_ontology.v_edge_conflicts_by_sector`
      KEY (edge_id)
      SOURCE KEY (ecommerce_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (distractor_slot_id) REFERENCES `YOUR_PROJECT_ID.kmarket_ontology.v_node_provision` (provision_slot_id)
      LABEL CONFLICTS_BY_SECTOR
  );
