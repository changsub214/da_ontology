-- ============================================================================
-- [Step 1-4] K-Market BigQuery Property Graph (`ecommerce_graph`) CQ 기반 멀티홉 GQL 검증 쿼리 4선
--   * 모든 검증 및 평가는 비즈니스 현업과 사전 합의된 CQ(Competency Questions)로 일원화됩니다.
-- ============================================================================

-- [검증 쿼리 1: CQ01] 김서연(USR-1001) 장바구니 이탈 세션(SES-9001) ➔ 코디 번들(PRD-3002) ➔ 90일 체화재고(105일) ➔ 10% 마진 특례(APR-7001) 4-Hop 탐색
GRAPH `YOUR_PROJECT_ID.kmarket_ontology.ecommerce_graph`
MATCH (ev:UserBehaviorEvent {event_id: 'EVT-8001'})-[:LOGGED_EVENT_ON_PRODUCT]->(anchor:Product),
      (bundle:Product {product_id: anchor.complementary_product_id})-[:STOCKED_AT_INVENTORY]->(inv:InventoryItem),
      (bundle)-[:HAS_CAMPAIGN_EXCEPTION]->(exc:CampaignException {status: 'APPROVED'})
RETURN
  ev.session_id,
  anchor.product_id AS anchor_product_id,
  anchor.product_name AS anchor_product_name,
  bundle.product_id AS bundle_product_id,
  bundle.product_name AS bundle_product_name,
  bundle.cost_krw,
  bundle.retail_price_krw,
  inv.stock_age_days,
  inv.available_stock,
  exc.exception_id,
  exc.approved_margin_floor;

-- [검증 쿼리 2: CQ04] 동일 주문원장(`OrderItem`)에 대해 MD본부(프로모션 6건) vs CS심사팀(반품 3건) 맥락별 `SCOPES_PORTFOLIO` 분기 검증
GRAPH `YOUR_PROJECT_ID.kmarket_ontology.ecommerce_graph`
MATCH (ctx:BusinessContext)-[sp:SCOPES_PORTFOLIO]->(oi:OrderItem)-[:OF_PRODUCT]->(p:Product)
WHERE (ctx.context_id = 'MD_MERCHANDISING' AND sp.portfolio_scope_rule = 'PROMO_MARGIN_AND_VENDOR_SHARE_SCOPE')
   OR (ctx.context_id = 'CX_CS_SUPPORT' AND sp.portfolio_scope_rule = 'CS_RETURN_AND_WITHDRAWAL_SCOPE')
RETURN
  ctx.context_id,
  ctx.dept_name,
  sp.portfolio_scope_rule,
  oi.order_item_id,
  p.product_name,
  oi.status,
  oi.return_reason_code,
  oi.sale_price_krw
ORDER BY ctx.context_id, oi.order_item_id;

-- [검증 쿼리 3: CQ06] 벨로체(BRD-02, 상시 프로모션 70% 약정 ➔ 50% 법정 캡 적용) vs 메종드실크(BRD-04, 자발적 단독 행사 APR-7004 ACTIVE ➔ 70% 특례 허용) 대조
GRAPH `YOUR_PROJECT_ID.kmarket_ontology.ecommerce_graph`
MATCH (oi:OrderItem)-[:OF_PRODUCT]->(p:Product)-[:SUPPLIED_BY_BRAND]->(b:BrandVendorContract)
WHERE oi.order_item_id IN ('OI-6004', 'OI-6012')
RETURN
  oi.order_item_id,
  p.product_id,
  p.product_name,
  b.brand_id,
  b.brand_name,
  b.signed_promo_agreement,
  b.promo_cost_share_ratio AS contract_share_ratio,
  oi.coupon_discount_krw,
  CASE
    WHEN b.brand_id = 'BRD-04' THEN ROUND(oi.coupon_discount_krw * b.promo_cost_share_ratio)
    ELSE ROUND(oi.coupon_discount_krw * LEAST(b.promo_cost_share_ratio, 0.50))
  END AS legal_vendor_share_krw,
  CASE
    WHEN b.brand_id = 'BRD-04' THEN 0
    ELSE ROUND(oi.coupon_discount_krw * (1.0 - LEAST(b.promo_cost_share_ratio, 0.50)))
  END AS kmarket_absorbed_krw
ORDER BY oi.order_item_id;

-- [검증 쿼리 4: CQ07] 전자상거래법 제17조 청약철회 심사 — 수령 5일차 세탁훼손(OI-6007, 거절) vs 수령 17일차 치수오차(OI-6008, 90일 특례 무상승인)
GRAPH `YOUR_PROJECT_ID.kmarket_ontology.ecommerce_graph`
MATCH (ctx:BusinessContext {context_id: 'CX_CS_SUPPORT'})-[:INVOKES_PROVISION {term_key: 'return-withdrawal-eligibility'}]->(prov:Provision),
      (oi:OrderItem)-[:BELONGS_TO_ORDER]->(o:`Order`)-[:PLACED_BY_USER]->(u:Customer),
      (oi)-[:OF_PRODUCT]->(p:Product)
WHERE oi.order_item_id IN ('OI-6007', 'OI-6008')
RETURN DISTINCT
  oi.order_item_id,
  u.user_name,
  p.product_name,
  oi.return_reason_code,
  o.delivered_at,
  o.return_requested_at,
  oi.sale_price_krw,
  prov.provision_slot_id,
  prov.article_no
ORDER BY oi.order_item_id, prov.provision_slot_id;
