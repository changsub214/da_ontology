/* ==========================================================================
   okf_veri_web/js/data-ecommerce.js
   K마켙 (K-Market · ecommerce-ontology) Domain Dataset for Modules 01 ~ 06
   and Dynamic Project Domain Switcher (`applyProjectDomainData`).
   ========================================================================== */

const ECOMMERCE_DOC_SHORT_NAMES = {
  DOC_01_LAW_LARGE_RETAIL: "대규모유통업법",
  DOC_02_FTC_PROMO_GUIDE: "판촉지침",
  DOC_03_LAW_ECOMMERCE: "전자상거래법",
  DOC_04_FTC_DARK_PATTERN: "다크패턴지침",
  DOC_05_PIPC_BEHAVIORAL: "행태정보안내서",
  DOC_06_DISTRACTOR_CUSTOMS: "관세청고시",
  DOC_07_KMARKET_CRM_POLICY: "CRM내규",
  DOC_08_KMARKET_MD_POLICY: "MD내규",
  DOC_09_KMARKET_PARTNER_POLICY: "정산내규",
  DOC_10_KMARKET_CS_SLA_POLICY: "CS내규"
};

const ECOMMERCE_SEMANTIC_ENTITIES = [
  {
    id: "ENT_PROMO_50_CAP",
    name: "판촉비 분담 50% 상한 (대규모유통업법 제11조④)",
    matchIds: [
      "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso",
      "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_04_fifty_percent_cap_invalidity",
      "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula"
    ],
    matchSec: ["대규모유통업법 제11조제3항~제5항", "판촉지침 Ⅱ.4", "정산내규 제3조"]
  },
  {
    id: "ENT_VOLUNTARY_PROMO",
    name: "납품업자 자발적·차별화 판촉 50% 상한 적용 제외",
    matchIds: [
      "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test",
      "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review"
    ],
    matchSec: ["판촉지침 Ⅱ.5", "정산내규 제4조"]
  },
  {
    id: "ENT_MARGIN_25",
    name: "상시 실현마진율 25% 가드레일 (MD내규 제1조~제2조)",
    matchIds: [
      "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
      "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle"
    ],
    matchSec: ["MD내규 제1조~제2조", "CRM내규 제3조"]
  },
  {
    id: "ENT_CLEARANCE_90D",
    name: "체화재고(90일+) 10% 마진하한 완화 및 예외승인(APR)",
    matchIds: [
      "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor",
      "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override"
    ],
    matchSec: ["MD내규 제3조", "MD내규 제4조"]
  },
  {
    id: "ENT_OPT_IN_GATE",
    name: "행태정보 타겟팅 동의 (marketing_opt_in=True) & 야간 푸시 제한",
    matchIds: [
      "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement",
      "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_004_005_retention_and_night_ban",
      "internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin",
      "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule"
    ],
    matchSec: ["행태정보안내서 제3조", "행태정보안내서 제4조~제5조", "CRM내규 제1조~제2조", "CRM내규 제4조~제5조"]
  },
  {
    id: "ENT_DARK_PATTERN_STOCK",
    name: "실시간 가용재고(available_stock<=5) 기반 품절임박 표시",
    matchIds: [
      "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_021_2_dark_pattern_ban",
      "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_003_stock_truthfulness",
      "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle"
    ],
    matchSec: ["전자상거래법 제21조의2", "다크패턴지침 제3조", "CRM내규 제3조"]
  },
  {
    id: "ENT_RETURN_7D_90D",
    name: "청약철회 기한 (단순변심 7일·왕복 6,000원 vs 표시광고상이 90일)",
    matchIds: [
      "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
      "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_018_refund_and_return_shipping",
      "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules"
    ],
    matchSec: ["전자상거래법 제17조제1항", "전자상거래법 제18조", "CS내규 제1조~제2조"]
  },
  {
    id: "ENT_HOLOGRAM_TAG",
    name: "명품 홀로그램 택 훼손 시 반품 제한 & 해외직구 고시 혼용 금지",
    matchIds: [
      "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p2_withdrawal_restrictions",
      "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee",
      "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs"
    ],
    matchSec: ["전자상거래법 제17조제2항", "관세청고시 제3조", "CS내규 제3조"]
  }
];

const ECOMMERCE_SEMANTIC_EDGES = [
  {
    fromId: "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
    toId: "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor",
    fromSec: "MD내규 제1조~제2조",
    toSec: "MD내규 제3조",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "입고 후 90일 이상 경과(stock_age_days>=90) 및 가용재고 30개 이상 체화재고는 상시 25% 마진 가드레일에서 10% 하한으로 완화"
  },
  {
    fromId: "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
    toId: "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override",
    fromSec: "MD내규 제1조~제2조",
    toSec: "MD내규 제4조",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "MD본부장 사전 예외승인(campaign_exceptions · CLEARANCE_OVERRIDE / VIP_RETENTION APPROVED) 품목은 승인 하한마진(10~15%) 특례 적용"
  },
  {
    fromId: "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso",
    toId: "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test",
    fromSec: "대규모유통업법 제11조제3항~제5항",
    toSec: "판촉지침 Ⅱ.5",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "납품업자의 자발적 선요청(자발성)과 타 브랜드 대비 차별성이 모두 입증된 단독 행사에 한하여 50% 분담 상한 적용 제외(상시 캠페인 배제)"
  },
  {
    fromId: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula",
    toId: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review",
    fromSec: "정산내규 제3조",
    toSec: "정산내규 제4조",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "입점브랜드 자발적·차별화 단독 행사 사전 심사 승인(VOLUNTARY_PROMO_FILING, APPROVED) 시에만 50% 캡 예외 허용, 상시 캠페인은 기각(REJECTED)"
  },
  {
    fromId: "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
    toId: "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p2_withdrawal_restrictions",
    fromSec: "전자상거래법 제17조제1항",
    toSec: "전자상거래법 제17조제2항",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "수령 후 7일 이내라도 소비자 귀책으로 세탁·수선·착용 훼손 또는 명품 정품 홀로그램 택 제거 시 단순변심 청약철회 제한"
  },
  {
    fromId: "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso",
    toId: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula",
    fromSec: "대규모유통업법 제11조제3항~제5항",
    toSec: "정산내규 제3조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "대규모유통업법 제11조④의 판촉비 50% 분담 상한을 정산내규 제3조(MIN(약정분담률, 50%)) 산식으로 구체화"
  },
  {
    fromId: "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_04_fifty_percent_cap_invalidity",
    toId: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula",
    fromSec: "판촉지침 Ⅱ.4",
    toSec: "정산내규 제3조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "공정위 심사지침 Ⅱ.4의 50% 초과 약정 무효 기준을 정산내규 제3조 자동 캡(Cap) 정산 로직으로 위임"
  },
  {
    fromId: "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test",
    toId: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review",
    fromSec: "판촉지침 Ⅱ.5",
    toSec: "정산내규 제4조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "공정위 심사지침 Ⅱ.5의 자발적·차별화 판촉행사 심사 요건을 정산내규 제4조 사전 적격성 심사 절차로 구체화"
  },
  {
    fromId: "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
    toId: "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules",
    fromSec: "전자상거래법 제17조제1항",
    toSec: "CS내규 제1조~제2조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "전자상거래법 제17조 청약철회 기한(단순변심 7일 vs 표시·광고 상이 90일)을 CS내규 반품사유 코드 및 왕복배송비(6,000원) 기준으로 구체화"
  },
  {
    fromId: "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_018_refund_and_return_shipping",
    toId: "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs",
    fromSec: "전자상거래법 제18조",
    toSec: "CS내규 제3조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "전자상거래법 제18조 회수 후 3영업일 이내 대금 환급 및 지연배상금(연 15%) 의무를 CS내규 제3조 자동 환급 기준으로 구체화"
  },
  {
    fromId: "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement",
    toId: "internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin",
    fromSec: "행태정보안내서 제3조",
    toSec: "CRM내규 제1조~제2조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "개인정보위 행태정보 사전 동의 원칙을 CRM내규 marketing_opt_in=True 발송 게이트로 구체화"
  },
  {
    fromId: "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_004_005_retention_and_night_ban",
    toId: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule",
    fromSec: "행태정보안내서 제4조~제5조",
    toSec: "CRM내규 제4조~제5조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "행태정보 안내서 야간(21시~익일 08시) 광고성 푸시 제한을 CRM내규 제5조 주간 발송 대기열 이관 규칙으로 구체화"
  },
  {
    fromId: "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_021_2_dark_pattern_ban",
    toId: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle",
    fromSec: "전자상거래법 제21조의2",
    toSec: "CRM내규 제3조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "전자상거래법 제21조의2 다크패턴(거짓 품절임박·유인) 금지 규정을 CRM내규 실시간 가용재고 검증 및 코디 번들 기준으로 구체화"
  },
  {
    fromId: "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_003_stock_truthfulness",
    toId: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle",
    fromSec: "다크패턴지침 제3조",
    toSec: "CRM내규 제3조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "공정위 다크패턴 가이드라인 제3조 실시간 재고·대체상품 안내 원칙을 CRM내규 제3조 품절 대체·코디 번들 추천 규칙으로 구체화"
  },
  {
    fromId: "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
    toId: "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee",
    fromSec: "전자상거래법 제17조제1항",
    toSec: "관세청고시 제3조",
    rel: "CONFLICTS_BY_SECTOR",
    color: "#b88a44",
    reason: "국내 풀필먼트 출고 주문에는 전자상거래법 제17조(단순변심 7일·왕복 6,000원)가 적용되며, 관세청 해외직구 특송고시 제3조(14일·국제반송수수료 35,000원)를 혼동 적용 금지"
  },
  {
    fromId: "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs",
    toId: "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee",
    fromSec: "CS내규 제3조",
    toSec: "관세청고시 제3조",
    rel: "CONFLICTS_BY_SECTOR",
    color: "#b88a44",
    reason: "CS내규 제3조제3항에 따라 국내 물류센터(김포·용인·양산) 출고 상품 반품 심사 시 관세청 해외직구 고시 제3조(14일 반송기한·35,000원 국제반송수수료) 적용 엄격 금지"
  },
  {
    fromId: "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs",
    toId: "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_001_002_scope",
    fromSec: "CS내규 제3조",
    toSec: "관세청고시 제1조~제2조",
    rel: "CONFLICTS_BY_SECTOR",
    color: "#b88a44",
    reason: "K마켙 국내 물류센터 직매입·특약매입 출고 건에 관세청 해외직구 목록통관(미화 150달러) 및 국제반송 적용범위 고시를 혼입 적용 금지"
  }
];

const ECOMMERCE_CAVEAT_SECTIONS = new Set([
  "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso",
  "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_04_fifty_percent_cap_invalidity",
  "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test",
  "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
  "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p2_withdrawal_restrictions",
  "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_018_refund_and_return_shipping",
  "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_021_2_dark_pattern_ban",
  "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_003_stock_truthfulness",
  "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement",
  "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_004_005_retention_and_night_ban",
  "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_001_002_scope",
  "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee",
  "internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin",
  "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle",
  "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule",
  "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
  "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor",
  "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override",
  "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula",
  "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review",
  "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules",
  "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs"
]);

const ECOMMERCE_GRAPH_SCOPE_LABELS = {
  ALL: "전체 10개 PDF · 36개 조문 (46개 Concept 전체)",
  DOC_01_LAW_LARGE_RETAIL: "01. 대규모유통업법 제11조 판촉비 분담 (7개 조문)",
  DOC_02_FTC_PROMO_GUIDE: "02. 공정위 판촉비용 부담전가 심사지침 (4개 조문)",
  DOC_03_LAW_ECOMMERCE: "03. 전자상거래 소비자보호법 청약철회 (5개 조문)",
  DOC_07_KMARKET_CRM_POLICY: "07. K마켙 초개인화 추천·타겟팅 내규 (3개 조문)",
  DOC_08_KMARKET_MD_POLICY: "08. K마켙 MD 마진·체화재고 특례 내규 (3개 조문)",
  DOC_09_KMARKET_PARTNER_POLICY: "09. K마켙 파트너 판촉비 정산 내규 (3개 조문)",
  DOC_10_KMARKET_CS_SLA_POLICY: "10. K마켙 CS 반품·물류 SLA 내규 (3개 조문)",
  CORE: "핵심 시나리오 및 단서·예외 서브그래프 (22개 조문)"
};

const ECOMMERCE_BQ_CLASS_NODES = [
  {
    id: "CLS_CONTEXT",
    label: "BusinessContext",
    ko: "본부·업무목적 맥락 (6건)",
    subRole: "CTX · 해석 분기 앵커",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 15,
    x: -255,
    z: -75,
    pk: "context_id",
    view: "kmarket_ontology.v_node_business_context",
    table: "kmarket_ontology.ctx_business_contexts (BigQuery Native · 6 rows)",
    desc: "동일 커머스 용어(쿠폰 할인, 마진율, 반품 기한) 호출 시 본부와 업무목적에 따라 적용 법령·내규 조문과 참조 물리 컬럼을 분기하는 맥락 노드",
    anchor: {
      anchor_type: "ALIAS_INTENT_MAP",
      alias_group: "BUSINESS_CONTEXT",
      match_bind_key: "context_id",
      gql_match_template: "(ctx:BusinessContext {context_id: '$CANONICAL_ID'})",
      planner_instruction: "질문의 발화 본부·목적(CRM_GROWTH, MD_MERCHANDISING, PARTNER_SETTLEMENT, CX_CS_SUPPORT, FULFILLMENT_OPS, LEGAL_COMPLIANCE)을 정규화하여 시작 노드로 MATCH 하세요."
    },
    props: [
      { name: "context_id", type: "STRING (PK)", desc: "본부·업무목적 맥락 고유 식별자 (CRM_GROWTH, MD_MERCHANDISING, PARTNER_SETTLEMENT, CX_CS_SUPPORT 등)" },
      { name: "dept_name", type: "STRING", desc: "업무를 주관하는 K마켙 내 본부·부서명" },
      { name: "purpose_summary", type: "STRING", desc: "해당 본부의 핵심 의사결정 및 가드레일 점검 목적 요약" },
      { name: "primary_metric_scope", type: "STRING", desc: "해당 맥락에서 주로 산출·점검하는 핵심 지표 및 심사 범위" }
    ],
    ddl: `kmarket_ontology.v_node_business_context
  KEY (context_id)
  LABEL BusinessContext
  PROPERTIES (context_id, dept_name, purpose_summary, primary_metric_scope)`
  },
  {
    id: "CLS_LOAN",
    label: "OrderItem",
    ko: "주문 품목·쿠폰·반품 허브 (21건)",
    subRole: "LDM · 주문·정산·반품 중심 허브 (Spanner OLTP)",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 19,
    x: -85,
    z: -10,
    pk: "order_item_id",
    view: "kmarket_ontology.v_node_order_item",
    table: "kmarket_ecommerce.ont_order_items (Cloud Spanner Data Boost Federated · 21 rows)",
    desc: "Cloud Spanner Data Boost로 실시간 연합 조회되는 주문 품목 원장이자 주문헤더·상품·입점브랜드 정산·반품 규정이 만나는 중심 허브 노드",
    anchor: {
      anchor_type: "CENTRAL_HUB_ANCHOR",
      alias_group: "ORDER_ITEM_ID",
      match_bind_key: "order_item_id",
      gql_match_template: "(oi:OrderItem {order_item_id: '$CANONICAL_ID'})",
      planner_instruction: "Spanner 실시간 주문품목 원장이자 그래프 중심 허브입니다. 쿠폰할인액(coupon_discount_krw), 실결제가(sale_price_krw), 반품사유(return_reason_code)가 모두 담겨 있습니다."
    },
    props: [
      { name: "order_item_id", type: "STRING (PK)", desc: "주문 품목 고유 식별자 (예: OIT-2026-0001 ~ OIT-2026-0021)" },
      { name: "order_id / user_id / product_id", type: "STRING (FK)", desc: "소속 주문번호, 구매 회원 ID, 전시 상품 ID" },
      { name: "retail_price_krw / coupon_discount_krw / sale_price_krw", type: "INT64", desc: "정가 · 쿠폰할인액 · 실결제가 (원)" },
      { name: "coupon_type", type: "STRING", desc: "적용 쿠폰 구분 (JOINT_PROMO 공동판촉 vs PLATFORM_TIER 플랫폼단독 vs NONE)" },
      { name: "status / return_reason_code", type: "STRING", desc: "품목 상태(Complete, Returned, Shipped) 및 반품사유 코드(CHANGE_OF_MIND, DEFECTIVE)" }
    ],
    ddl: `kmarket_ontology.v_node_order_item
  KEY (order_item_id)
  LABEL OrderItem
  PROPERTIES (
    order_item_id, order_id, user_id, product_id, inventory_item_id,
    status, retail_price_krw, coupon_discount_krw, sale_price_krw,
    coupon_type, return_reason_code
  )`
  },
  {
    id: "CLS_CUSTOMER",
    label: "Customer",
    ko: "회원 마스터·수신동의 (60건)",
    subRole: "LDM · BigQuery Master",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: -245,
    z: 35,
    pk: "user_id",
    view: "kmarket_ontology.v_node_customer",
    table: "kmarket_ecommerce.users (BigQuery Native · 60 rows)",
    desc: "회원의 멤버십 등급(VVIP/VIP/GOLD/SILVER), 마케팅 수신동의(marketing_opt_in_yn), 선호 스타일을 관리하는 마스터 노드",
    anchor: {
      anchor_type: "ALIAS_TABLE_LOOKUP",
      alias_group: "CUSTOMER_NAME",
      match_bind_key: "user_id",
      gql_match_template: "(u:Customer {user_id: '$CANONICAL_ID'})",
      planner_instruction: "회원명('김서연'->USR-1001, '박준혁'->USR-1002, '이수빈'->USR-1003)을 ont_entity_aliases에서 조회해 user_id로 바인딩하세요."
    },
    props: [
      { name: "user_id", type: "STRING (PK)", desc: "회원 고유 식별자 (USR-1001 ~ USR-1060)" },
      { name: "user_name / membership_tier", type: "STRING", desc: "회원 성명 및 멤버십 등급 (VVIP, VIP, GOLD, SILVER)" },
      { name: "marketing_opt_in_yn", type: "STRING", desc: "행태정보 기반 맞춤형 추천·타겟팅 푸시 동의 여부 (Y/N)" },
      { name: "preferred_style", type: "STRING", desc: "회원 선호 패션 스타일 카테고리" }
    ],
    ddl: `kmarket_ontology.v_node_customer
  KEY (user_id)
  LABEL Customer
  PROPERTIES (
    user_id, user_name, age, gender, city,
    membership_tier, marketing_opt_in, primary_category, traffic_source
  )`
  },
  {
    id: "CLS_PRODUCT",
    label: "Product",
    ko: "전시 상품·코디·대체 허브 (30건)",
    subRole: "LDM · 상품·재고·브랜드·캠페인 허브 (BigQuery Master)",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 17,
    x: 75,
    z: -10,
    pk: "product_id",
    view: "kmarket_ontology.v_node_product",
    table: "kmarket_ecommerce.products (BigQuery Native · 30 rows)",
    desc: "상품의 정가·매입원가·입점브랜드 및 초개인화 코디 번들(complementary_product_id)·품절 대체상품(substitute_product_id)을 연결하는 상품 마스터 허브 노드",
    anchor: {
      anchor_type: "ALIAS_TABLE_LOOKUP",
      alias_group: "PRODUCT_NAME",
      match_bind_key: "product_id",
      gql_match_template: "(p:Product {product_id: '$CANONICAL_ID'})",
      planner_instruction: "상품명 약칭('발마칸 코트'->PRD-3001, '터틀넥 니트'->PRD-3002, '트러커 자켓'->PRD-3003)을 ont_entity_aliases에서 조회해 바인딩하세요."
    },
    props: [
      { name: "product_id", type: "STRING (PK)", desc: "상품 고유 코드 (PRD-3001 ~ PRD-3030)" },
      { name: "product_name / brand_id", type: "STRING", desc: "상품 한글명 및 공급 입점브랜드 코드" },
      { name: "cost_krw / retail_price_krw", type: "INT64", desc: "매입 원가 및 정상 판매가 (원, 마진 가드레일 산출 기준)" },
      { name: "complementary_product_id / substitute_product_id", type: "STRING", desc: "코디 번들 추천 상품 ID 및 품절 시 대체 추천 상품 ID" }
    ],
    ddl: `kmarket_ontology.v_node_product
  KEY (product_id)
  LABEL Product
  PROPERTIES (
    product_id, sku_code, product_name, category, department, brand_id,
    cost_krw, retail_price_krw, complementary_product_id, substitute_product_id,
    distribution_center_id, return_policy_tag, is_active
  )`
  },
  {
    id: "CLS_WORKOUT",
    label: "Order",
    ko: "주문 헤더·출고·배송 원장 (15건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: -135,
    z: 85,
    pk: "order_id",
    view: "kmarket_ontology.v_node_order",
    table: "kmarket_ecommerce.ont_orders (Cloud Spanner Data Boost Federated · 15 rows)",
    desc: "주문 결제 시각·출고 시각·배송완료 시각·반품요청 시각을 관리하는 Spanner 실시간 주문 헤더 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "ORDER_ID",
      match_bind_key: "order_id",
      gql_match_template: "(o:`Order` {order_id: '$CANONICAL_ID'})",
      planner_instruction: "OrderItem에서 BELONGS_TO_ORDER 엣지로 탐색하여 결제~출고 소요시간(SLA) 및 배송완료 후 반품 신청 경과일수를 계산하세요."
    },
    props: [
      { name: "order_id", type: "STRING (PK)", desc: "주문 고유 번호 (ORD-2026-0001 ~ ORD-2026-0015)" },
      { name: "user_id / status", type: "STRING", desc: "주문 회원 ID 및 주문 상태 (Complete, Returned, Shipped)" },
      { name: "created_at / shipped_at / delivered_at / return_requested_at", type: "STRING", desc: "결제·출고·배송완료·반품접수 ISO 시각" }
    ],
    ddl: `kmarket_ontology.v_node_order
  KEY (order_id)
  LABEL \`Order\`
  PROPERTIES (
    order_id, user_id, status, created_at,
    shipped_at, delivered_at, return_requested_at, num_of_item
  )`
  },
  {
    id: "CLS_COLLATERAL",
    label: "BrandVendorContract",
    ko: "입점브랜드 계약·분담률 마스터 (8건)",
    subRole: "LDM · BigQuery Master",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 185,
    z: -95,
    pk: "brand_id",
    view: "kmarket_ontology.v_node_brand_vendor_contract",
    table: "kmarket_ecommerce.brand_vendor_contracts (BigQuery Native · 8 rows)",
    desc: "입점브랜드별 거래유형(특약매입/위수탁/직매입)·약정 판촉비 분담률(promo_cost_share_ratio)·사전 서면약정 여부·목표 출고 SLA를 담는 계약 노드",
    anchor: {
      anchor_type: "ALIAS_TABLE_LOOKUP",
      alias_group: "BRAND_NAME",
      match_bind_key: "brand_id",
      gql_match_template: "(b:BrandVendorContract {brand_id: '$CANONICAL_ID'})",
      planner_instruction: "Product에서 SUPPLIED_BY_BRAND 엣지로 탐색하여 promo_cost_share_ratio와 대규모유통업법 제11조 50% 상한을 대조하세요."
    },
    props: [
      { name: "brand_id / brand_name", type: "STRING (PK)", desc: "입점브랜드 고유 코드(BRD-01 ~ BRD-08) 및 브랜드명" },
      { name: "agreed_promo_share_pct / promo_cost_share_ratio", type: "FLOAT64", desc: "계약서상 약정 판촉비 분담률 (예: 60.0% -> 법정 상한 50.0% 캡 적용 대상)" },
      { name: "signed_promo_agreement", type: "BOOL", desc: "사전 서면 판촉비 분담 약정 체결 여부 (True/False)" },
      { name: "sla_ship_hours", type: "INT64", desc: "입점브랜드 목표 출고 SLA 시간 (24h / 36h / 48h)" }
    ],
    ddl: `kmarket_ontology.v_node_brand_vendor_contract
  KEY (brand_id)
  LABEL BrandVendorContract
  PROPERTIES (
    brand_id, brand_name, contract_type, commission_rate,
    promo_cost_share_ratio, signed_promo_agreement,
    min_margin_guardrail, return_shipping_fee_krw, sla_ship_hours
  )`
  },
  {
    id: "CLS_DELINQ",
    label: "InventoryItem",
    ko: "창고별 가용재고·체화일수 원장 (32건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 250,
    z: -15,
    pk: "inventory_item_id",
    view: "kmarket_ontology.v_node_inventory_item",
    table: "kmarket_ecommerce.ont_inventory_items (Cloud Spanner Data Boost Federated · 32 rows)",
    desc: "물류센터별 실시간 가용재고(available_stock)와 입고 후 체화일수(stock_age_days)를 기록하는 Spanner Data Boost 원장 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "NONE",
      match_bind_key: "inventory_item_id",
      gql_match_template: "(inv:InventoryItem)",
      planner_instruction: "Product에서 STOCKED_AT_INVENTORY 엣지로 탐색하여 품절(available_stock=0) 및 90일 이상 체화재고(stock_age_days>=90) 여부를 확인하세요."
    },
    props: [
      { name: "inventory_item_id", type: "STRING (PK)", desc: "재고 슬롯 고유 번호 (INV-1001 ~ INV-1032)" },
      { name: "product_id / distribution_center", type: "STRING", desc: "상품 ID 및 물류센터 코드 (DC-ICN, DC-YIN, DC-BUS)" },
      { name: "available_stock", type: "INT64", desc: "실시간 가용 재고 수량 (0이면 품절 OUT_OF_STOCK)" },
      { name: "stock_age_days", type: "INT64", desc: "입고 후 경과 체화일수 (90일 이상 시 마진 하한 10% 완화 대상)" }
    ],
    ddl: `kmarket_ontology.v_node_inventory_item
  KEY (inventory_item_id)
  LABEL InventoryItem
  PROPERTIES (
    inventory_item_id, product_id, distribution_center,
    available_stock, stock_age_days, inbound_date, stock_status
  )`
  },
  {
    id: "CLS_RATECUT",
    label: "UserBehaviorEvent",
    ko: "실시간 장바구니 이탈 이벤트 (11건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 65,
    z: 95,
    pk: "event_id",
    view: "kmarket_ontology.v_node_user_behavior_event",
    table: "kmarket_ecommerce.ont_events (Cloud Spanner Data Boost Federated · 11 rows)",
    desc: "고객의 장바구니 담기(event_type='cart') 및 미결제 이탈 세션을 실시간 포착하는 Spanner 행동로그 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "EVENT_ID",
      match_bind_key: "event_id",
      gql_match_template: "(ev:UserBehaviorEvent)",
      planner_instruction: "LOGGED_EVENT_ON_PRODUCT 및 EVALUATED_UNDER_PROVISION 엣지로 탐색하여 개보위 행태정보 동의 및 초개인화 추천 규칙과 대조하세요."
    },
    props: [
      { name: "event_id", type: "STRING (PK)", desc: "행동 이벤트 고유 번호 (EVT-5001 ~ EVT-5011)" },
      { name: "user_id / product_id", type: "STRING (FK)", desc: "행동 발생 회원 ID 및 대상 상품 ID" },
      { name: "event_type / traffic_source", type: "STRING", desc: "이벤트 유형(cart, product, purchase) 및 유입 채널" }
    ],
    ddl: `kmarket_ontology.v_node_user_behavior_event
  KEY (event_id)
  LABEL UserBehaviorEvent
  PROPERTIES (
    event_id, user_id, session_id, sequence_number,
    product_id, event_type, traffic_source, created_at
  )`
  },
  {
    id: "CLS_APPROVAL",
    label: "CampaignException",
    ko: "마진완화·특례 예외승인 원장 (7건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 215,
    z: 80,
    pk: "exception_id",
    view: "kmarket_ontology.v_node_campaign_exception",
    table: "kmarket_ecommerce.ont_campaign_exceptions (Cloud Spanner Data Boost Federated · 7 rows)",
    desc: "프로모션 마진 가드레일(25%) 하한 완화·명품 홀로그램 검수·입점사 자발적 행사 여부에 대한 본부 예외승인 결재 원장 노드 (Spanner Data Boost)",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "NONE",
      match_bind_key: "exception_id",
      gql_match_template: "(ex:CampaignException)",
      planner_instruction: "Product에서 HAS_CAMPAIGN_EXCEPTION 엣지로 탐색하여 status='ACTIVE' 및 approved_floor_margin_pct를 확인하세요."
    },
    props: [
      { name: "exception_id", type: "STRING (PK)", desc: "예외승인 고유 번호 (EXC-KM-2026-01 ~ EXC-KM-2026-07)" },
      { name: "product_id / item_id", type: "STRING (FK)", desc: "대상 상품 ID 및 주문품목 ID" },
      { name: "approved_floor_margin_pct", type: "FLOAT64", desc: "승인된 최저 마진율 하한 (10.0% ~ 14.0%)" },
      { name: "hologram_tag_intact_yn / vendor_voluntary_req_yn", type: "STRING", desc: "명품 홀로그램 택 보존 여부(Y/N) 및 입점사 자발적 행사 요청 여부(Y/N)" },
      { name: "status", type: "STRING", desc: "결재 상태 (ACTIVE 유효승인 vs EXPIRED 만료 vs REJECTED 기각)" }
    ],
    ddl: `kmarket_ontology.v_node_campaign_exception
  KEY (exception_id)
  LABEL CampaignException
  PROPERTIES (
    exception_id, exception_type, product_id, item_id,
    approved_floor_margin_pct, hologram_tag_intact_yn,
    vendor_voluntary_req_yn, approved_by_role, status, valid_until
  )`
  },
  {
    id: "CLS_SRCDOC",
    label: "SourceDocument",
    ko: "이커머스 법령·지침·내규 문서 루트 (10건)",
    subRole: "LEX · OKF Document Root (ObjectRef)",
    layer: "LEX",
    color: 0x477a63,
    radius: 15,
    x: -175,
    z: 10,
    pk: "doc_id",
    view: "kmarket_ontology.v_node_source_document",
    table: "kmarket_ontology.lex_source_documents (10 OKF doc.md + BigQuery ObjectRef + KC 1:1)",
    desc: "대규모유통업법·전자상거래법·개보위 가이드라인·관세청 해외직구 대조군·K마켙 내규 등 10종 원본 문서 루트 노드",
    anchor: {
      anchor_type: "KC_GOVERNED_LEX_ROOT",
      alias_group: "SOURCE_DOCUMENT",
      match_bind_key: "doc_id",
      gql_match_template: "(doc:SourceDocument {doc_id: '$CANONICAL_ID'})",
      planner_instruction: "10개 원본 문서 루트입니다. gcs_obj_ref에 대해 OBJ.GET_ACCESS_URL을 호출해 gs://okf 원문 doc.md를 직접 인출하세요."
    },
    props: [
      { name: "doc_id", type: "STRING (PK)", desc: "원본 법령·내규 문서 고유 식별자 (DOC_01_LAW_LARGE_RETAIL 등 10종)" },
      { name: "title / authority_level", type: "STRING", desc: "문서 공식 명칭 및 구속력 구분 (binding / internal / advisory / distractor)" },
      { name: "applicable_sector", type: "STRING", desc: "적용 업권 (DOMESTIC_ECOMMERCE vs OVERSEAS_DIRECT_CUSTOMS)" },
      { name: "kc_entry_id / gcs_uri / gcs_obj_ref", type: "ObjectRef", desc: "Dataplex ecommerce-okf Entry ID 및 gs://okf ObjectRef" }
    ],
    ddl: `kmarket_ontology.v_node_source_document
  KEY (doc_id)
  LABEL SourceDocument
  PROPERTIES (
    doc_id, doc_code, title, authority_level,
    applicable_sector, issuing_body, kc_entry_id, gcs_uri,
    OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
  )`
  },
  {
    id: "CLS_PROVISION",
    label: "Provision",
    ko: "법령·지침·K마켙 내규 조문 (36건)",
    subRole: "LEX · 의사결정 기준 허브 (ObjectRef + KC Governed)",
    layer: "LEX",
    color: 0x3b735b,
    radius: 19,
    x: 45,
    z: 0,
    pk: "provision_slot_id",
    view: "kmarket_ontology.v_node_provision",
    table: "kmarket_ontology.lex_provisions (36 OKF Provisions + BigQuery ObjectRef + KC Aspect SSOT)",
    desc: "36개 개별 법령·지침·사내내규 조항 노드로, BigQuery ObjectRef(gcs_obj_ref)로 gs://okf 마크다운 원문을 인출하며 거버넌스 상태는 KC(ecommerce-okf)에서만 검증함",
    anchor: {
      anchor_type: "KC_GOVERNED_LEX_NODE",
      alias_group: "PROVISION_SYNONYM",
      match_bind_key: "provision_slot_id",
      gql_match_template: "(pr:Provision {provision_slot_id: '$CANONICAL_ID'})",
      planner_instruction: "도달 시 kc_entry_id로 Dataplex ecommerce-okf Aspect(status/superseded_by)를 검증하고 OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r')로 원문을 읽으세요."
    },
    props: [
      { name: "provision_slot_id", type: "STRING (PK)", desc: "불변 조문 슬롯 식별자" },
      { name: "doc_id / kc_entry_id", type: "STRING", desc: "소속 문서 ID 및 Dataplex ecommerce-okf Entry ID" },
      { name: "article_no / title / provision_role", type: "STRING", desc: "조문 번호, 제목 및 역할(BASE_CRITERIA / EXCEPTION_PROVISO / INTERNAL_RULE / DISTRACTOR_RULE)" },
      { name: "target_columns / gcs_uri / gcs_obj_ref", type: "ObjectRef", desc: "참조 정형 컬럼 목록 및 gs://okf ObjectRef" }
    ],
    ddl: `kmarket_ontology.v_node_provision
  KEY (provision_slot_id)
  LABEL Provision
  PROPERTIES (
    provision_slot_id, doc_id, kc_entry_id, article_no, title,
    provision_role, target_columns, missing_schema_columns, gcs_uri,
    OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
  )`
  }
];

const ECOMMERCE_BQ_CLASS_EDGES = [
  { source: "CLS_CONTEXT", target: "CLS_LOAN", rel: "SCOPES_PORTFOLIO", isBridge: false, color: 0x6b88a8, view: "v_edge_scopes_portfolio", desc: "본부·업무목적 맥락(BusinessContext)이 관할하는 실시간 주문품목(OrderItem) 포트폴리오 스코프 연결" },
  { source: "CLS_LOAN", target: "CLS_WORKOUT", rel: "BELONGS_TO_ORDER", isBridge: false, color: 0x6b88a8, view: "v_edge_belongs_to_order", desc: "주문 품목(OrderItem)이 어느 주문 헤더(Order)에 속하는지 연결 (N:1)" },
  { source: "CLS_WORKOUT", target: "CLS_CUSTOMER", rel: "PLACED_BY_USER", isBridge: false, color: 0x6b88a8, view: "v_edge_placed_by_user", desc: "주문(Order)을 결제한 회원(Customer) 연결 (N:1)" },
  { source: "CLS_LOAN", target: "CLS_PRODUCT", rel: "OF_PRODUCT", isBridge: false, color: 0x6b88a8, view: "v_edge_of_product", desc: "주문 품목(OrderItem)이 어느 전시 상품(Product)인지 연결 (N:1)" },
  { source: "CLS_PRODUCT", target: "CLS_COLLATERAL", rel: "SUPPLIED_BY_BRAND", isBridge: false, color: 0x6b88a8, view: "v_edge_supplied_by_brand", desc: "전시 상품(Product)을 공급하는 입점브랜드 계약(BrandVendorContract) 연결 (N:1)" },
  { source: "CLS_PRODUCT", target: "CLS_DELINQ", rel: "STOCKED_AT_INVENTORY", isBridge: false, color: 0x6b88a8, view: "v_edge_stocked_at_inventory", desc: "전시 상품(Product)의 물류센터별 실시간 재고·체화일수(InventoryItem) 연결 (1:N)" },
  { source: "CLS_RATECUT", target: "CLS_PRODUCT", rel: "LOGGED_EVENT_ON_PRODUCT", isBridge: false, color: 0x6b88a8, view: "v_edge_logged_event_on_product", desc: "고객 장바구니 이탈 이벤트(UserBehaviorEvent)가 발생한 대상 상품(Product) 연결 (N:1)" },
  { source: "CLS_PRODUCT", target: "CLS_APPROVAL", rel: "HAS_CAMPAIGN_EXCEPTION", isBridge: false, color: 0x6b88a8, view: "v_edge_has_campaign_exception", desc: "상품(Product)에 부여된 프로모션 마진 하한 완화·특례 예외승인(CampaignException) 연결 (1:N)" },

  { source: "CLS_CONTEXT", target: "CLS_PROVISION", rel: "INVOKES_PROVISION", isBridge: true, color: 0xb88a44, view: "v_edge_invokes_provision", desc: "본부 맥락(BusinessContext)과 Dataplex Glossary 용어(term_key) 조합에 따라 호출 조문을 분기하는 브리지 엣지" },
  { source: "CLS_LOAN", target: "CLS_PROVISION", rel: "GOVERNED_BY_CRITERIA", isBridge: true, color: 0xb88a44, view: "v_edge_governed_by_criteria", desc: "실시간 Spanner 주문품목(OrderItem)의 쿠폰·반품·출고 상태에 따라 심사 관할 조문을 동적 연결하는 SQL View 엣지" },
  { source: "CLS_RATECUT", target: "CLS_PROVISION", rel: "EVALUATED_UNDER_PROVISION", isBridge: true, color: 0xb88a44, view: "v_edge_evaluated_under_provision", desc: "실시간 Spanner 장바구니 이탈 이벤트(UserBehaviorEvent)를 개보위 가이드라인 및 CRM 내규 조문과 연결하는 브리지 엣지" },

  { source: "CLS_PROVISION", target: "CLS_SRCDOC", rel: "PART_OF_DOCUMENT", isBridge: false, color: 0x5a8770, view: "v_edge_part_of_document", desc: "36개 개별 조문이 어느 원본 법령·내규 문서(10종)에 속하는지 연결 (N:1)" },
  { source: "CLS_PROVISION", target: "CLS_PROVISION", rel: "HAS_EXCEPTION_PROVISO", isBridge: false, isSelfLoop: true, loopIdx: 0, color: 0xa85c56, view: "v_edge_has_exception_proviso", desc: "상시 25% 마진 본칙·판촉비 50% 상한 본칙에서 체화재고(10%)·VIP 특례(12%)·자발적 행사 단서로 분기하는 엣지" },
  { source: "CLS_PROVISION", target: "CLS_PROVISION", rel: "DELEGATES_TO_INTERNAL", isBridge: false, isSelfLoop: true, loopIdx: 1, color: 0x5a8770, view: "v_edge_delegates_to_internal", desc: "대규모유통업법·전자상거래법·개보위 지침이 K마켙 사내 내규 조문으로 세부 산식을 위임하는 엣지" },
  { source: "CLS_PROVISION", target: "CLS_PROVISION", rel: "CONFLICTS_BY_SECTOR", isBridge: false, isSelfLoop: true, loopIdx: 2, color: 0xb88a44, view: "v_edge_conflicts_by_sector", desc: "국내 이커머스 출고 반품 규정과 관세청 해외직구 특송고시(35,000원 반송수수료) 간의 오적용 방지 대조 엣지" }
];

const ECOMMERCE_BQ_GQL_PRESETS = [
  {
    cqId: "CQ01",
    theme: "Theme A · 초개인화 코디 번들 & MD 마진 예외승인 (Multi-Hop Proviso + ObjectRef)",
    title: "CQ01 · 장바구니 이탈 고객 코디 번들 추천 및 마진 예외승인 조회",
    question: "김서연 고객이 장바구니에 담아두고 결제하지 않은 코트와 함께 묶어 추천할 코디 니트가 현재 출고 가능한 재고인지 확인해 줘. 코디 상품에 적용할 수 있는 마진 완화 특례까지 반영하면 최대 얼마까지 할인해서 번들로 제안할 수 있어?",
    contextBadge: "BusinessContext: CRM_GROWTH × MD_MERCHANDISING · Glossary term_key: 'hyper-personalized-reco'",
    verdict: "[번들 프로모션 승인] 주상품 PRD-3001(가용 40개, 정가 40만·원가 24만, VIP 15% = 60,000원 할인) + 코디 PRD-3002(가용 50개, 체화 125일, 정가 20만·원가 15.6만) · EXC-KM-2026-01(하한 10.0% ACTIVE, 최대 26,666원 할인) ➔ 최대 합산 할인 86,666원 · 최종 번들 제안가 513,334원",
    answerDetail: "CRM_GROWTH 맥락에서 'hyper-personalized-reco' 용어로 호출된 CRM 내규 제3조·제4조(VIP 최대 15% 할인쿠폰 및 마진 가드레일 연동)와 MD 내규 제2조·제3조·제4조(실현마진율 산식 및 체화재고 10% 하한 예외승인)를 동시 평가합니다. 주상품 PRD-3001(아틀리에 캐시미어 발마칸 코트, 정가 400,000원·원가 240,000원)은 VIP 최대 15% 할인(60,000원, 실결제가 340,000원) 시 실현마진율 29.4%로 상시 가드레일(25.0%)을 충족하고, 코디상품 PRD-3002(아틀리에 메리노울 터틀넥 니트, 정가 200,000원·원가 156,000원, 체화 125일)는 Spanner 예외승인(EXC-KM-2026-01, 하한 10.0% ACTIVE)에 의해 최저 실결제가 173,334원(156,000 ÷ 0.90 올림), 최대 26,666원(13.33%)까지 할인이 허용되어 합산 최대 86,666원 할인 · 최종 번들 제안가 513,334원이 산출되며, OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r')로 조문 원문 서명 URL을 즉시 발급합니다.",
    gql: `GRAPH kmarket_ontology.ecommerce_graph
MATCH (ctx:BusinessContext {context_id: 'CRM_GROWTH'})
      -[inv:INVOKES_PROVISION {term_key: 'hyper-personalized-reco'}]->(pr:Provision {article_no: '제3조'})
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ev:UserBehaviorEvent {event_id: 'EVT-5002'})-[:LOGGED_EVENT_ON_PRODUCT]->(p1:Product)-[:STOCKED_AT_INVENTORY]->(inv1:InventoryItem),
      (ev)-[:EVALUATED_UNDER_PROVISION]->(pr),
      (p2:Product)-[:STOCKED_AT_INVENTORY]->(inv2:InventoryItem),
      (p2)-[:HAS_CAMPAIGN_EXCEPTION]->(ex:CampaignException),
      (pr_md:Provision {doc_id: 'DOC_08_KMARKET_MD_POLICY', article_no: '제1조~제2조'})
      -[:HAS_EXCEPTION_PROVISO]->(pr_ex:Provision {article_no: '제4조'})
WHERE p2.product_id = p1.complementary_product_id
RETURN ctx.context_id AS context_id, inv.term_key AS term_key,
       ev.event_id AS event_id, ev.user_id AS user_id,
       p1.product_id AS main_product_id, p1.retail_price_krw AS main_retail_krw, inv1.available_stock AS main_stock,
       p2.product_id AS coord_product_id, p2.retail_price_krw AS coord_retail_krw, inv2.stock_age_days AS coord_age_days,
       ex.exception_id AS approval_id, ex.approved_floor_margin_pct AS approved_floor_pct, ex.status AS approval_status,
       pr.article_no AS crm_article, pr_ex.article_no AS md_exception_article,
       OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r') AS pr_obj_url,
       OBJ.GET_ACCESS_URL(pr_ex.gcs_obj_ref, 'r') AS pr_ex_obj_url`,
    nodes: [
      { id: "CTX::CRM_GROWTH", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nCRM_GROWTH (그로스마케팅·AI추천랩)", title: "kmarket_ontology.v_node_business_context · CRM_GROWTH", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "CRM_GROWTH", dept_name: "그로스마케팅·AI추천랩", term_key: "hyper-personalized-reco" }, verdictNote: "장바구니 이탈 세션 탐지 및 코디 번들·등급별 쿠폰 추천 맥락" },
      { id: "EVT::EVT-5002", classLabel: "UserBehaviorEvent", layer: "ONT", label: "[UserBehaviorEvent]\nEVT-5002 (SES-1001-A · cart)\nUSR-1001 김서연 (VIP · 동의 Y)", title: "v_node_user_behavior_event · EVT-5002", color: "#3b6ea5", shape: "dot", size: 20, viewName: "v_node_user_behavior_event", sourceStore: "Cloud Spanner Federated (ont_events)", record: { event_id: "EVT-5002", session_id: "SES-1001-A", user_id: "USR-1001", product_id: "PRD-3001", event_type: "cart", marketing_opt_in_yn: "Y" }, verdictNote: "VIP 회원 김서연(USR-1001) 장바구니 미결제 이탈 포착 (cart_abandon_min=45 >= 30)" },
      { id: "PRD::PRD-3001", classLabel: "Product", layer: "ONT", label: "[Product · 주상품]\nPRD-3001 발마칸 코트\n(정가 400,000 · 원가 240,000)", title: "v_node_product · PRD-3001", color: "#3b6ea5", shape: "dot", size: 21, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3001", product_name: "아틀리에 캐시미어 발마칸 코트 블랙", retail_price_krw: 400000, cost_krw: 240000, complementary_product_id: "PRD-3002" }, verdictNote: "가용재고 40개 정상 · VIP 15% 할인(60,000원) 시 실현마진율 29.4% ≥ 25.0% 충족" },
      { id: "INV::INV-1001", classLabel: "InventoryItem", layer: "ONT", label: "[InventoryItem]\nINV-1001 김포센터(DC-ICN)\n(가용재고 40개 · 15일차)", title: "v_node_inventory_item · INV-1001", color: "#527a9a", size: 16, shape: "dot", viewName: "v_node_inventory_item", sourceStore: "Cloud Spanner Federated (ont_inventory_items)", record: { inventory_item_id: "INV-1001", product_id: "PRD-3001", warehouse_code: "DC-ICN", available_stock: 40, stock_age_days: 15 }, verdictNote: "주상품 가용재고 정상(40개 >= 1)" },
      { id: "PRD::PRD-3002", classLabel: "Product", layer: "ONT", label: "[Product · 코디 번들]\nPRD-3002 메리노울 터틀넥 니트\n(정가 200,000 · 원가 156,000)", title: "v_node_product · PRD-3002", color: "#3b6ea5", shape: "dot", size: 20, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3002", product_name: "아틀리에 메리노울 터틀넥 니트 아이보리", retail_price_krw: 200000, cost_krw: 156000 }, verdictNote: "기본마진 22.0% < 25%이나 EXC-KM-2026-01(하한 10.0%)로 최저 실결제가 173,334원(최대 26,666원 할인) 허용" },
      { id: "INV::INV-1002", classLabel: "InventoryItem", layer: "ONT", label: "[InventoryItem · 체화재고]\nINV-1002 김포센터(DC-ICN)\n(가용 50개 · 체화 125일 ≥ 90일)", title: "v_node_inventory_item · INV-1002", color: "#527a9a", size: 16, shape: "dot", viewName: "v_node_inventory_item", sourceStore: "Cloud Spanner Federated (ont_inventory_items)", record: { inventory_item_id: "INV-1002", product_id: "PRD-3002", warehouse_code: "DC-ICN", available_stock: 50, stock_age_days: 125 }, verdictNote: "입고 후 125일 경과(>= 90일) 및 가용수량 50개(>= 30개) 체화재고" },
      { id: "EXC::EXC-KM-2026-01", classLabel: "CampaignException", layer: "ONT", label: "[CampaignException · ACTIVE]\nEXC-KM-2026-01 (CLEARANCE_MARGIN)\n승인하한 10.0% 완화", title: "v_node_campaign_exception · EXC-KM-2026-01", color: "#3b735b", shape: "dot", size: 18, viewName: "v_node_campaign_exception", sourceStore: "Cloud Spanner Federated (ont_campaign_exceptions)", record: { exception_id: "EXC-KM-2026-01", product_id: "PRD-3002", exception_type: "CLEARANCE_MARGIN", approved_margin_floor: 10.0, status: "ACTIVE" }, verdictNote: "Spanner 예외승인 원장에서 최저마진 하한 10.0% ACTIVE 확인" },
      { id: "PROV::CRM제3조", classLabel: "Provision", layer: "LEX", label: "[Provision · CRM 내규 제3조]\n가용재고 연동 대체상품 및\n크로스셀 코디 번들 추천 규칙", title: "v_node_provision · CRM 내규 제3조", color: "#3b735b", shape: "box", matchSec: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle", doc_id: "DOC_07_KMARKET_CRM_POLICY", article_no: "제3조", provision_role: "BASE_CRITERIA", gcs_uri: "gs://okf/internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle.md" }, verdictNote: "정상재고 시 코디 번들(complementary_product_id) 결합 및 마진 가드레일 연동" },
      { id: "PROV::MD제1~2조", classLabel: "Provision", layer: "LEX", label: "[Provision · MD 내규 제1~2조]\n실현마진율 산식 및 상시\n프로모션 최저마진 25% 가드레일", title: "v_node_provision · MD 내규 제1조~제2조", color: "#3b735b", shape: "box", matchSec: "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail", doc_id: "DOC_08_KMARKET_MD_POLICY", article_no: "제1조~제2조", provision_role: "BASE_CRITERIA", gcs_uri: "gs://okf/internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail.md" }, verdictNote: "상시 프로모션 실현마진율 25.0% 본칙" },
      { id: "PROV::MD제4조", classLabel: "Provision", layer: "LEX", label: "[Provision · MD 내규 제4조]\n캠페인 마진 예외승인(ACTIVE) 시\n승인 하한율 우선 적용 특례", title: "v_node_provision · MD 내규 제4조", color: "#3b735b", shape: "box", matchSec: "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override", doc_id: "DOC_08_KMARKET_MD_POLICY", article_no: "제4조", provision_role: "EXCEPTION_PROVISO", gcs_uri: "gs://okf/internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override.md" }, verdictNote: "상시 25% 본칙의 예외 특례 조문 (HAS_EXCEPTION_PROVISO)" },
      { id: "DOC::DOC_07", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_07_KMARKET_CRM_POLICY\n07 K마켙 초개인화 추천 내규", title: "v_node_source_document · DOC_07_KMARKET_CRM_POLICY", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_07_KMARKET_CRM_POLICY", title: "K마켙 초개인화 추천·장바구니 타겟팅 운영 내규", authority_level: "internal" }, verdictNote: "K마켙 CRM 본부 운영 내규 정본 PDF" },
      { id: "DOC::DOC_08", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_08_KMARKET_MD_POLICY\n08 K마켙 MD 상품마진·체화재고 내규", title: "v_node_source_document · DOC_08_KMARKET_MD_POLICY", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_08_KMARKET_MD_POLICY", title: "K마켙 MD 상품마진 및 체화재고 가격결정 내규", authority_level: "internal" }, verdictNote: "K마켙 MD본부 마진 가드레일 및 예외승인 내규 정본 PDF" }
    ],
    edges: [
      { from: "CTX::CRM_GROWTH", to: "PROV::CRM제3조", label: "INVOKES_PROVISION\n[term_key: hyper-personalized-reco]", color: "#b88a44", width: 2.0 },
      { from: "EVT::EVT-5002", to: "PRD::PRD-3001", label: "LOGGED_EVENT_ON_PRODUCT", color: "#6b88a8", width: 1.8 },
      { from: "PRD::PRD-3001", to: "INV::INV-1001", label: "STOCKED_AT_INVENTORY", color: "#6b88a8", width: 1.5 },
      { from: "PRD::PRD-3001", to: "PRD::PRD-3002", label: "complementary_product_id\n(코디 번들)", color: "#3b6ea5", width: 1.8 },
      { from: "PRD::PRD-3002", to: "INV::INV-1002", label: "STOCKED_AT_INVENTORY", color: "#6b88a8", width: 1.5 },
      { from: "PRD::PRD-3002", to: "EXC::EXC-KM-2026-01", label: "HAS_CAMPAIGN_EXCEPTION", color: "#3b735b", width: 1.8 },
      { from: "EVT::EVT-5002", to: "PROV::CRM제3조", label: "EVALUATED_UNDER_PROVISION", color: "#b88a44", width: 1.8 },
      { from: "PROV::CRM제3조", to: "PROV::MD제1~2조", label: "DELEGATES_TO_INTERNAL\n(마진 가드레일 연동)", color: "#5a8770", width: 1.7 },
      { from: "PROV::MD제1~2조", to: "PROV::MD제4조", label: "HAS_EXCEPTION_PROVISO", color: "#a85c56", width: 1.8 },
      { from: "EXC::EXC-KM-2026-01", to: "PROV::MD제4조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "PROV::CRM제3조", to: "DOC::DOC_07", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.6 },
      { from: "PROV::MD제1~2조", to: "DOC::DOC_08", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.5 },
      { from: "PROV::MD제4조", to: "DOC::DOC_08", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.5 }
    ]
  },
  {
    cqId: "CQ02",
    theme: "Theme B · 품절 감지 대체상품 전환 & 90일+ 체화재고 클리어런스 특례 (ObjectRef)",
    title: "CQ02 · 장바구니 품절 상품 대체 전환 및 장기 체화재고 특례 조회",
    question: "고객이 장바구니에 담아둔 린넨 와이드 팬츠가 지금 품절 상태인데 계속 추천 슬롯에 노출해도 돼? 내규에 따라 전환해야 할 대체상품은 무엇이고, 해당 대체상품의 체화재고 기준을 적용하면 최저 마진율을 몇 %까지 낮춰서 제안할 수 있어?",
    contextBadge: "BusinessContext: MD_MERCHANDISING · Glossary term_key: 'clearance-exception'",
    verdict: "[품절 자동 전환 · 체화 특례 발동] 주상품 PRD-3009(INV-1011 가용 0개 · OUT_OF_STOCK) 추천 차단 ➔ 대체상품 PRD-3002(INV-1002 가용 50개≥30 · 체화 125일≥90일) 전환 및 EXC-KM-2026-01 최저마진 10.0% 적용",
    answerDetail: "CRM 내규 제3조에 따라 주상품 PRD-3009의 가용재고가 0개(OUT_OF_STOCK)이므로 추천을 즉시 중단하고 substitute_product_id로 연결된 PRD-3002(아틀리에 메리노울 터틀넥 니트 아이보리)로 자동 전환합니다. MD_MERCHANDISING 맥락에서 'clearance-exception' 용어로 호출된 MD 내규 제3조(90일 이상 체화재고 10% 하한 특례)와 Spanner 결재 원장(EXC-KM-2026-01, ACTIVE)을 결합해 상시 25.0% 대신 10.0% 최저마진 하한을 적용하며, OBJ.GET_ACCESS_URL로 조문 원문 서명 URL을 인출합니다.",
    gql: `GRAPH kmarket_ontology.ecommerce_graph
MATCH (ctx:BusinessContext {context_id: 'MD_MERCHANDISING'})
      -[inv:INVOKES_PROVISION {term_key: 'clearance-exception'}]->(pr_md:Provision {article_no: '제3조'})
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (pr_dp:Provision {doc_id: 'DOC_04_FTC_DARK_PATTERN', article_no: '제3조'})
      -[:DELEGATES_TO_INTERNAL]->(pr_crm:Provision {doc_id: 'DOC_07_KMARKET_CRM_POLICY', article_no: '제3조'}),
      (ev:UserBehaviorEvent {event_id: 'EVT-5008'})-[:LOGGED_EVENT_ON_PRODUCT]->(p1:Product)-[:STOCKED_AT_INVENTORY]->(inv1:InventoryItem),
      (ev)-[:EVALUATED_UNDER_PROVISION]->(pr_crm),
      (p2:Product)-[:STOCKED_AT_INVENTORY]->(inv2:InventoryItem),
      (p2)-[:HAS_CAMPAIGN_EXCEPTION]->(ex:CampaignException)
WHERE p2.product_id = p1.substitute_product_id
  AND inv1.available_stock = 0
  AND inv2.stock_age_days >= 90
RETURN ctx.context_id AS context_id, inv.term_key AS term_key,
       ev.event_id AS event_id, p1.product_id AS stockout_product_id, inv1.available_stock AS stockout_qty,
       p2.product_id AS substitute_product_id, p2.product_name AS substitute_name,
       inv2.available_stock AS sub_avail_qty, inv2.stock_age_days AS sub_age_days,
       ex.exception_id AS approval_id, ex.approved_floor_margin_pct AS clearance_floor_pct,
       pr_crm.article_no AS crm_article, pr_md.article_no AS md_clearance_article,
       OBJ.GET_ACCESS_URL(pr_md.gcs_obj_ref, 'r') AS pr_md_obj_url`,
    nodes: [
      { id: "CTX::MD_MERCH", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nMD_MERCHANDISING (MD본부·가격전략실)", title: "v_node_business_context · MD_MERCHANDISING", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "MD_MERCHANDISING", dept_name: "MD본부·가격전략실", term_key: "clearance-exception" }, verdictNote: "체화재고(90일+) 클리어런스 및 마진 하한 완화 심사" },
      { id: "EVT::EVT-5008", classLabel: "UserBehaviorEvent", layer: "ONT", label: "[UserBehaviorEvent]\nEVT-5008 (SES-1007-A · cart)\nUSR-1007 품절 상품 장바구니 이탈", title: "v_node_user_behavior_event · EVT-5008", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_user_behavior_event", sourceStore: "Cloud Spanner Federated (ont_events)", record: { event_id: "EVT-5008", session_id: "SES-1007-A", user_id: "USR-1007", product_id: "PRD-3009", event_type: "cart" }, verdictNote: "주상품 PRD-3009 품절 상태에서 장바구니 이탈 감지" },
      { id: "PRD::PRD-3009", classLabel: "Product", layer: "ONT", label: "[Product · 품절 주상품]\nPRD-3009 린넨 와이드 팬츠\n(avail_qty = 0 · OUT_OF_STOCK)", title: "v_node_product · PRD-3009", color: "#a85c56", shape: "dot", size: 20, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3009", product_name: "아틀리에 린넨 블렌드 와이드 팬츠 베이지", retail_price_krw: 160000, cost_krw: 112000, substitute_product_id: "PRD-3002" }, verdictNote: "품절 감지 → substitute_product_id(PRD-3002)로 자동 전환" },
      { id: "INV::INV-1011", classLabel: "InventoryItem", layer: "ONT", label: "[InventoryItem · 품절]\nINV-1011 용인센터(DC-YIN)\n(가용재고 0개 · OUT_OF_STOCK)", title: "v_node_inventory_item · INV-1011", color: "#a85c56", shape: "dot", size: 16, viewName: "v_node_inventory_item", sourceStore: "Cloud Spanner Federated (ont_inventory_items)", record: { inventory_item_id: "INV-1011", product_id: "PRD-3009", warehouse_code: "DC-YIN", available_stock: 0, stock_status: "OUT_OF_STOCK" }, verdictNote: "가용재고 0개 품절 → 다크패턴 방지 가이드라인 제3조에 따라 노출 차단" },
      { id: "PRD::PRD-3002", classLabel: "Product", layer: "ONT", label: "[Product · 대체상품]\nPRD-3002 메리노울 터틀넥 니트\n(정가 200,000 · 원가 156,000)", title: "v_node_product · PRD-3002", color: "#3b735b", shape: "dot", size: 21, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3002", product_name: "아틀리에 메리노울 터틀넥 니트 아이보리", retail_price_krw: 200000, cost_krw: 156000 }, verdictNote: "체화재고 특례(하한 10.0%) 적용 시 최대 13.3% 클리어런스 할인 가능" },
      { id: "INV::INV-1002", classLabel: "InventoryItem", layer: "ONT", label: "[InventoryItem · 체화재고]\nINV-1002 김포센터(DC-ICN)\n(가용 50개 · 체화 125일 ≥ 90일)", title: "v_node_inventory_item · INV-1002", color: "#3b735b", shape: "dot", size: 18, viewName: "v_node_inventory_item", sourceStore: "Cloud Spanner Federated (ont_inventory_items)", record: { inventory_item_id: "INV-1002", product_id: "PRD-3002", warehouse_code: "DC-ICN", available_stock: 50, stock_age_days: 125, stock_status: "AVAILABLE" }, verdictNote: "stock_age_days=125 >= 90일 & avail_qty=50 >= 30개 체화재고 요건 충족" },
      { id: "EXC::EXC-KM-2026-01", classLabel: "CampaignException", layer: "ONT", label: "[CampaignException · ACTIVE]\nEXC-KM-2026-01 (하한 10.0% 완화)", title: "v_node_campaign_exception · EXC-KM-2026-01", color: "#3b735b", shape: "dot", size: 17, viewName: "v_node_campaign_exception", sourceStore: "Cloud Spanner Federated (ont_campaign_exceptions)", record: { exception_id: "EXC-KM-2026-01", product_id: "PRD-3002", exception_type: "CLEARANCE_MARGIN", approved_margin_floor: 10.0, status: "ACTIVE" }, verdictNote: "체화재고 클리어런스 마진 하한 10.0% ACTIVE 승인" },
      { id: "PROV::다크패턴제3조", classLabel: "Provision", layer: "LEX", label: "[Provision · 다크패턴 지침 제3조]\n실시간 재고·품절 표시 진실성\n(품절 상품 판매노출 금지)", title: "v_node_provision · 공정위 다크패턴 가이드라인 제3조", color: "#3b735b", shape: "box", matchSec: "regulations/04_ftc_dark_pattern_guideline/ch02_stock_and_countdown_truthfulness/dp_art_003_stock_truthfulness", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "regulations/04_ftc_dark_pattern_guideline/ch02_stock_and_countdown_truthfulness/dp_art_003_stock_truthfulness", doc_id: "DOC_04_FTC_DARK_PATTERN", article_no: "제3조", provision_role: "BASE_CRITERIA" }, verdictNote: "가용재고 0개 품절 상품의 허위 추천·노출 금지" },
      { id: "PROV::CRM제3조", classLabel: "Provision", layer: "LEX", label: "[Provision · CRM 내규 제3조]\n품절 상품 추천 중단 및\nsubstitute_product_id 자동 전환", title: "v_node_provision · CRM 내규 제3조", color: "#3b735b", shape: "box", matchSec: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle", doc_id: "DOC_07_KMARKET_CRM_POLICY", article_no: "제3조" }, verdictNote: "avail_qty=0 품절 시 대체상품 자동 전환 규칙" },
      { id: "PROV::MD제1~2조", classLabel: "Provision", layer: "LEX", label: "[Provision · MD 내규 제1~2조]\n상시 프로모션 최저마진율\n25.0% 가드레일 본칙", title: "v_node_provision · MD 내규 제1조~제2조", color: "#3b735b", shape: "box", matchSec: "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail", doc_id: "DOC_08_KMARKET_MD_POLICY", article_no: "제1조~제2조" }, verdictNote: "상시 25.0% 마진 가드레일 본칙" },
      { id: "PROV::MD제3조", classLabel: "Provision", layer: "LEX", label: "[Provision · MD 내규 제3조]\n90일 이상 체화재고 클리어런스\n최저마진 하한 10.0% 완화 특례", title: "v_node_provision · MD 내규 제3조", color: "#3b735b", shape: "box", matchSec: "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor", doc_id: "DOC_08_KMARKET_MD_POLICY", article_no: "제3조", provision_role: "EXCEPTION_PROVISO" }, verdictNote: "체화재고(age_days>=90, avail_qty>=30) 10% 마진 하한 특례" },
      { id: "DOC::DOC_07", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_07_KMARKET_CRM_POLICY\n07 K마켙 초개인화 추천 내규", title: "v_node_source_document · DOC_07_KMARKET_CRM_POLICY", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_07_KMARKET_CRM_POLICY", title: "K마켙 초개인화 추천·장바구니 타겟팅 운영 내규", authority_level: "internal" }, verdictNote: "CRM 품절 대체전환 운영 내규 정본 PDF" },
      { id: "DOC::DOC_08", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_08_KMARKET_MD_POLICY\n08 K마켙 MD 상품마진·체화재고 내규", title: "v_node_source_document · DOC_08_KMARKET_MD_POLICY", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_08_KMARKET_MD_POLICY", title: "K마켙 MD 상품마진 및 체화재고 가격결정 내규", authority_level: "internal" }, verdictNote: "MD본부 마진 가드레일 및 체화재고 특례 정본 PDF" }
    ],
    edges: [
      { from: "CTX::MD_MERCH", to: "PROV::MD제3조", label: "INVOKES_PROVISION\n[term_key: clearance-exception]", color: "#b88a44", width: 2.0 },
      { from: "EVT::EVT-5008", to: "PRD::PRD-3009", label: "LOGGED_EVENT_ON_PRODUCT", color: "#6b88a8", width: 1.8 },
      { from: "EVT::EVT-5008", to: "PROV::CRM제3조", label: "EVALUATED_UNDER_PROVISION", color: "#b88a44", width: 1.7 },
      { from: "PROV::다크패턴제3조", to: "PROV::CRM제3조", label: "DELEGATES_TO_INTERNAL", color: "#5a8770", width: 1.7 },
      { from: "PROV::CRM제3조", to: "DOC::DOC_07", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.5 },
      { from: "PRD::PRD-3009", to: "INV::INV-1011", label: "STOCKED_AT_INVENTORY\n(0개 품절)", color: "#a85c56", width: 1.7 },
      { from: "PRD::PRD-3009", to: "PRD::PRD-3002", label: "substitute_product_id\n(대체상품 전환)", color: "#3b735b", width: 1.9 },
      { from: "PRD::PRD-3002", to: "INV::INV-1002", label: "STOCKED_AT_INVENTORY\n(125일 체화 · 50개)", color: "#3b735b", width: 1.7 },
      { from: "PRD::PRD-3002", to: "EXC::EXC-KM-2026-01", label: "HAS_CAMPAIGN_EXCEPTION", color: "#3b735b", width: 1.7 },
      { from: "PRD::PRD-3002", to: "PROV::MD제1~2조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "EXC::EXC-KM-2026-01", to: "PROV::MD제3조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "PROV::MD제1~2조", to: "PROV::MD제3조", label: "HAS_EXCEPTION_PROVISO", color: "#a85c56", width: 1.8 },
      { from: "PROV::MD제1~2조", to: "DOC::DOC_08", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.5 },
      { from: "PROV::MD제3조", to: "DOC::DOC_08", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.6 }
    ]
  },
  {
    cqId: "CQ08",
    theme: "Theme C · 대규모유통업법 제11조 입점브랜드 판촉비 50% 상한 캡 정산 (ObjectRef)",
    title: "CQ08 · 입점브랜드 공동 프로모션 판촉비 분담 상한 및 정산 내역 조회",
    question: "이번 달 아틀리에누아르의 공동 프로모션 쿠폰 할인 건들을 정산하려고 해. 계약서상 분담률인 60%를 그대로 청구해도 법적으로 문제없어? 자발적 행사 예외신청 결재 결과까지 반영해서 브랜드에 청구할 정산 분담금과 우리 플랫폼이 흡수해야 할 금액을 계산해 줘.",
    contextBadge: "BusinessContext: PARTNER_SETTLEMENT · Glossary term_key: 'promo-cost-sharing'",
    verdict: "[50% 법정상한 강제 캡 발동] BRD-01 약정 60% 초과분 10%p 무효 + EXC-KM-2026-06 기각(REJECTED) ➔ 총 할인 300,000원 중 브랜드 분담 상한 150,000원(50%) · K마켙 초과 흡수액 30,000원",
    answerDetail: "PARTNER_SETTLEMENT 맥락에서 'promo-cost-sharing' 용어로 호출된 대규모유통업법 제11조제3항~제5항(50% 상한 캡)과 하위 위임 내규(파트너 정산기준 제3조)를 연결합니다. OIT-2026-0004에 연결된 자발적 분담 예외신청(EXC-KM-2026-06)이 Spanner 원장에서 REJECTED(기각) 상태이므로 제11조제5항 단서가 배제되고, 4건 전체(총 할인 300,000원)에 50% 상한(150,000원)이 강제 적용되어 약정 60%(180,000원)와의 차액 30,000원을 K마켙이 전액 흡수하며, OBJ.GET_ACCESS_URL로 법령·내규 원문 서명 URL을 인출합니다.",
    gql: `GRAPH kmarket_ontology.ecommerce_graph
MATCH (ctx:BusinessContext {context_id: 'PARTNER_SETTLEMENT'})
      -[inv:INVOKES_PROVISION {term_key: 'promo-cost-sharing'}]->(pr_law:Provision {article_no: '제11조제3항~제5항'})
      -[:DELEGATES_TO_INTERNAL]->(pr_int:Provision {article_no: '제3조'})
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(oi:OrderItem)-[:GOVERNED_BY_CRITERIA]->(pr_law),
      (oi)-[:OF_PRODUCT]->(p:Product)-[:SUPPLIED_BY_BRAND]->(b:BrandVendorContract {brand_id: 'BRD-01'})
OPTIONAL MATCH (p)-[:HAS_CAMPAIGN_EXCEPTION]->(ex:CampaignException {exception_type: 'VENDOR_VOLUNTARY_PROMO'})
WHERE oi.coupon_type = 'JOINT_PROMO'
RETURN ctx.context_id AS context_id, inv.term_key AS term_key,
       oi.order_item_id AS order_item_id, p.product_id AS product_id, b.brand_name AS brand_name,
       oi.coupon_discount_krw AS coupon_discount_krw, b.promo_cost_share_ratio AS contract_ratio,
       LEAST(b.promo_cost_share_ratio, 0.50) AS capped_ratio,
       CAST(oi.coupon_discount_krw * LEAST(b.promo_cost_share_ratio, 0.50) AS INT64) AS brand_share_krw,
       CAST(oi.coupon_discount_krw * (b.promo_cost_share_ratio - LEAST(b.promo_cost_share_ratio, 0.50)) AS INT64) AS kmarket_excess_absorbed_krw,
       ex.exception_id AS voluntary_filing_id, ex.status AS voluntary_filing_status,
       pr_law.article_no AS law_article, pr_int.article_no AS internal_article,
       OBJ.GET_ACCESS_URL(pr_law.gcs_obj_ref, 'r') AS pr_law_obj_url,
       OBJ.GET_ACCESS_URL(pr_int.gcs_obj_ref, 'r') AS pr_int_obj_url`,
    nodes: [
      { id: "CTX::PARTNER", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nPARTNER_SETTLEMENT (파트너상생·정산실)", title: "v_node_business_context · PARTNER_SETTLEMENT", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "PARTNER_SETTLEMENT", dept_name: "파트너상생·정산실", term_key: "promo-cost-sharing" }, verdictNote: "대규모유통업법 제11조 판촉비 50% 상한 캡 정산 맥락" },
      { id: "OI::OIT-2026-0001", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem]\nOIT-2026-0001 (쿠폰 60,000원)\n브랜드 30,000 · 초과흡수 6,000", title: "v_node_order_item · OIT-2026-0001", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0001", product_id: "PRD-3001", coupon_type: "JOINT_PROMO", coupon_discount_krw: 60000, brand_share_krw: 30000, kmarket_excess_absorbed_krw: 6000 }, verdictNote: "약정 60%(36,000원) → 법정 50%(30,000원) 캡 적용, K마켙 6,000원 초과 흡수" },
      { id: "OI::OIT-2026-0002", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem]\nOIT-2026-0002 (쿠폰 30,000원)\n브랜드 15,000 · 초과흡수 3,000", title: "v_node_order_item · OIT-2026-0002", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0002", product_id: "PRD-3002", coupon_type: "JOINT_PROMO", coupon_discount_krw: 30000, brand_share_krw: 15000, kmarket_excess_absorbed_krw: 3000 }, verdictNote: "약정 60%(18,000원) → 법정 50%(15,000원) 캡 적용, K마켙 3,000원 초과 흡수" },
      { id: "OI::OIT-2026-0003", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem]\nOIT-2026-0003 (쿠폰 60,000원)\n브랜드 30,000 · 초과흡수 6,000", title: "v_node_order_item · OIT-2026-0003", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0003", product_id: "PRD-3001", coupon_type: "JOINT_PROMO", coupon_discount_krw: 60000, brand_share_krw: 30000, kmarket_excess_absorbed_krw: 6000 }, verdictNote: "약정 60%(36,000원) → 법정 50%(30,000원) 캡 적용, K마켙 6,000원 초과 흡수" },
      { id: "OI::OIT-2026-0004", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem]\nOIT-2026-0004 (쿠폰 150,000원)\n브랜드 75,000 · 초과흡수 15,000", title: "v_node_order_item · OIT-2026-0004", color: "#3b6ea5", shape: "dot", size: 21, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0004", product_id: "PRD-3001", coupon_type: "JOINT_PROMO", coupon_discount_krw: 150000, brand_share_krw: 75000, kmarket_excess_absorbed_krw: 15000 }, verdictNote: "EXC-KM-2026-06 기각(REJECTED) → 법정 50%(75,000원) 캡 적용, K마켙 15,000원 초과 흡수" },
      { id: "PRD::PRD-3001", classLabel: "Product", layer: "ONT", label: "[Product]\nPRD-3001 핸드메이드 코트\n(BRD-01 공급)", title: "v_node_product · PRD-3001", color: "#527a9a", shape: "dot", size: 17, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3001", product_name: "아틀리에 울 캐시미어 핸드메이드 코트 블랙", brand_id: "BRD-01", retail_price_krw: 400000 }, verdictNote: "OIT-2026-0001, 0003, 0004가 참조하는 상품 마스터 노드" },
      { id: "PRD::PRD-3002", classLabel: "Product", layer: "ONT", label: "[Product]\nPRD-3002 메리노울 터틀넥 니트\n(BRD-01 공급)", title: "v_node_product · PRD-3002", color: "#527a9a", shape: "dot", size: 17, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3002", product_name: "아틀리에 메리노울 터틀넥 니트 아이보리", brand_id: "BRD-01", retail_price_krw: 200000 }, verdictNote: "OIT-2026-0002가 참조하는 상품 마스터 노드" },
      { id: "EXC::EXC-KM-2026-06", classLabel: "CampaignException", layer: "ONT", label: "[CampaignException · REJECTED]\nEXC-KM-2026-06 (자발성 불인정 기각)\n60% 예외분담 효력 부인", title: "v_node_campaign_exception · EXC-KM-2026-06", color: "#a85c56", shape: "dot", size: 18, viewName: "v_node_campaign_exception", sourceStore: "Cloud Spanner Federated (ont_campaign_exceptions)", record: { exception_id: "EXC-KM-2026-06", product_id: "PRD-3001", order_item_id: "OIT-2026-0004", exception_type: "VENDOR_VOLUNTARY_PROMO", vendor_voluntary_req_yn: "N", status: "REJECTED" }, verdictNote: "K마켙 MD 선제 기획 행사로 자발성 요건 미충족(REJECTED) → 50% 캡 강제" },
      { id: "BRD::BRD-01", classLabel: "BrandVendorContract", layer: "ONT", label: "[BrandVendorContract]\nBRD-01 아틀리에누아르\n(약정분담률 60% → 법정상한 50%)", title: "v_node_brand_vendor_contract · BRD-01", color: "#527a9a", shape: "dot", size: 19, viewName: "v_node_brand_vendor_contract", sourceStore: "BigQuery Master (brand_vendor_contracts)", record: { brand_id: "BRD-01", brand_name: "아틀리에누아르", trade_type: "특약매입", agreed_promo_share_pct: 60.0, promo_cost_share_ratio: 0.60, written_promo_agreement_yn: "Y" }, verdictNote: "계약서상 60% 약정이 있으나 강행규정에 의해 50%로 제한" },
      { id: "PROV::법제11조", classLabel: "Provision", layer: "LEX", label: "[Provision · 대규모유통업법 제11조]\n제4항 판매촉진비용 납품업자\n분담비율 50% 초과 금지", title: "v_node_provision · 대규모유통업법 제11조제3항~제5항", color: "#3b735b", shape: "box", matchSec: "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso", doc_id: "DOC_01_LAW_LARGE_RETAIL", article_no: "제11조제3항~제5항", provision_role: "BASE_CRITERIA" }, verdictNote: "납품업자 판촉비 분담비율 100분의 50 상한 강행규정" },
      { id: "PROV::정산제3조", classLabel: "Provision", layer: "LEX", label: "[Provision · 정산내규 제3조]\nMIN(agreed_promo_share_pct, 50%)\n초과분 K마켙 전액 의무 흡수", title: "v_node_provision · 정산내규 제3조", color: "#3b735b", shape: "box", matchSec: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula", doc_id: "DOC_09_KMARKET_PARTNER_POLICY", article_no: "제3조", provision_role: "INTERNAL_RULE" }, verdictNote: "대규모유통업법 제11조를 구체화한 정산 산식" },
      { id: "DOC::DOC_01", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_01_LAW_LARGE_RETAIL\n01 대규모유통업법 전문 (법률)", title: "v_node_source_document · DOC_01_LAW_LARGE_RETAIL", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_01_LAW_LARGE_RETAIL", title: "대규모유통업에서의 거래 공정화에 관한 법률", authority_level: "binding" }, verdictNote: "대규모유통업법 정본 PDF" },
      { id: "DOC::DOC_09", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_09_KMARKET_PARTNER_POLICY\n09 K마켙 파트너 판촉비 정산 내규", title: "v_node_source_document · DOC_09_KMARKET_PARTNER_POLICY", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_09_KMARKET_PARTNER_POLICY", title: "K마켙 파트너 판매촉진비용 분담 및 정산 운영 내규", authority_level: "internal" }, verdictNote: "K마켙 파트너 정산 운영 내규 정본 PDF" }
    ],
    edges: [
      { from: "CTX::PARTNER", to: "PROV::법제11조", label: "INVOKES_PROVISION\n[term_key: promo-cost-sharing]", color: "#b88a44", width: 2.0 },
      { from: "CTX::PARTNER", to: "OI::OIT-2026-0001", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "CTX::PARTNER", to: "OI::OIT-2026-0002", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "CTX::PARTNER", to: "OI::OIT-2026-0003", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "CTX::PARTNER", to: "OI::OIT-2026-0004", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "PROV::법제11조", to: "PROV::정산제3조", label: "DELEGATES_TO_INTERNAL", color: "#5a8770", width: 1.9 },
      { from: "PROV::법제11조", to: "DOC::DOC_01", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.6 },
      { from: "PROV::정산제3조", to: "DOC::DOC_09", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.6 },
      { from: "OI::OIT-2026-0001", to: "PROV::법제11조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "OI::OIT-2026-0002", to: "PROV::법제11조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "OI::OIT-2026-0003", to: "PROV::법제11조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "OI::OIT-2026-0004", to: "PROV::법제11조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "OI::OIT-2026-0001", to: "PRD::PRD-3001", label: "OF_PRODUCT", color: "#6b88a8", width: 1.5 },
      { from: "OI::OIT-2026-0002", to: "PRD::PRD-3002", label: "OF_PRODUCT", color: "#6b88a8", width: 1.5 },
      { from: "OI::OIT-2026-0003", to: "PRD::PRD-3001", label: "OF_PRODUCT", color: "#6b88a8", width: 1.5 },
      { from: "OI::OIT-2026-0004", to: "PRD::PRD-3001", label: "OF_PRODUCT", color: "#6b88a8", width: 1.5 },
      { from: "PRD::PRD-3001", to: "BRD::BRD-01", label: "SUPPLIED_BY_BRAND", color: "#6b88a8", width: 1.6 },
      { from: "PRD::PRD-3002", to: "BRD::BRD-01", label: "SUPPLIED_BY_BRAND", color: "#6b88a8", width: 1.6 },
      { from: "PRD::PRD-3001", to: "EXC::EXC-KM-2026-06", label: "HAS_CAMPAIGN_EXCEPTION\n(REJECTED 기각)", color: "#a85c56", width: 1.8, dashes: true }
    ]
  },
  {
    cqId: "CQ14",
    theme: "Theme D · 전자상거래법 청약철회 · 관세청 해외직구 대조군 방어 & ObjectRef",
    title: "CQ14 · 국내 물류센터 출고 반품 귀책사유별 배송비 및 환급액 심사",
    question: "용인과 김포 물류센터에서 출고된 반품 접수 건들 중에 실측 사이즈 상이, 봉제 불량, 단순변심 건이 섞여 있어. 여기 해외직구 반송수수료 기준을 적용하면 안 되는 이유가 뭐고, 각 주문별로 고객에게 얼마씩 환불해 줘야 해?",
    contextBadge: "BusinessContext: CX_CS_SUPPORT · Glossary term_key: 'return-withdrawal-eligibility'",
    verdict: "[타 업권 교란 고시 차단 · 정밀 환급] CONFLICTS_BY_SECTOR 엣지로 관세청 해외직구 고시(35,000원) 원천 배제 ➔ 판매자 귀책 2건(OIT-0018 10만·OIT-0011 15만) 전액 환급(배송비 0원) · 단순변심 1건(OIT-0007 20만) 6,000원 차감 후 194,000원 환급",
    answerDetail: "CX_CS_SUPPORT 맥락에서 'return-withdrawal-eligibility' 용어로 호출된 전자상거래법 제17조제1항과 CS 내규 제1~2조를 따르며, CONFLICTS_BY_SECTOR 엣지를 통해 관세청 해외직구 통관 고시 제3조(해외 반송수수료 35,000원)를 원천 차단합니다. 따라서 용인(DC-YIN)·김포(DC-ICN) 국내 물류센터 출고 건 중 실측 사이즈 상이(OIT-2026-0018, 100,000원)와 봉제 불량(OIT-2026-0011, 150,000원)은 판매자 귀책 무상반품(전액 환급), 단순변심(OIT-2026-0007, 200,000원)은 국내 왕복 배송비 6,000원만 차감한 194,000원을 환급하며, OBJ.GET_ACCESS_URL로 정본 및 교란 문서의 ObjectRef를 함께 검증합니다.",
    gql: `GRAPH kmarket_ontology.ecommerce_graph
MATCH (ctx:BusinessContext {context_id: 'CX_CS_SUPPORT'})
      -[inv:INVOKES_PROVISION {term_key: 'return-withdrawal-eligibility'}]->(pr:Provision {article_no: '제17조제1항'})
      -[:DELEGATES_TO_INTERNAL]->(pr_cs:Provision {article_no: '제1조~제2조'}),
      (pr)-[:CONFLICTS_BY_SECTOR]->(dist:Provision)-[:PART_OF_DOCUMENT]->(doc_dist:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(oi:OrderItem)-[:GOVERNED_BY_CRITERIA]->(pr),
      (oi)-[:OF_PRODUCT]->(p:Product)
WHERE oi.order_item_id IN ('OIT-2026-0007', 'OIT-2026-0011', 'OIT-2026-0018')
RETURN ctx.context_id AS context_id, inv.term_key AS term_key,
       oi.order_item_id AS order_item_id, p.distribution_center_id AS fulfillment_dc,
       oi.return_reason_code AS return_reason_code, oi.sale_price_krw AS sale_price_krw,
       IF(oi.return_reason_code = 'CHANGE_OF_MIND', 6000, 0) AS customer_return_fee_krw,
       oi.sale_price_krw - IF(oi.return_reason_code = 'CHANGE_OF_MIND', 6000, 0) AS net_refund_krw,
       pr.article_no AS governing_article, pr_cs.article_no AS cs_internal_article,
       dist.article_no AS blocked_distractor_article, doc_dist.doc_id AS distractor_doc_id,
       OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r') AS pr_obj_url,
       OBJ.GET_ACCESS_URL(dist.gcs_obj_ref, 'r') AS dist_obj_url`,
    nodes: [
      { id: "CTX::CS_SUPPORT", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nCX_CS_SUPPORT (고객경험·CS심사팀)", title: "v_node_business_context · CX_CS_SUPPORT", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "CX_CS_SUPPORT", dept_name: "고객경험·CS심사팀", term_key: "return-withdrawal-eligibility" }, verdictNote: "전자상거래법 제17조 청약철회 및 반품배송비 귀속 판정" },
      { id: "OI::OIT-2026-0018", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem · 실측사이즈 상이]\nOIT-2026-0018 (결제가 100,000원)\n무상반품 · 100,000원 전액 환급", title: "v_node_order_item · OIT-2026-0018", color: "#3b735b", shape: "dot", size: 21, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0018", order_id: "ORD-2026-0012", product_id: "PRD-3011", status: "Returned", return_reason_code: "SIZE_MISMATCH_SPEC_DIFF", sale_price_krw: 100000, customer_return_fee_krw: 0, net_refund_krw: 100000 }, verdictNote: "용인센터(DC-YIN) 국내 출고 + 실측 사이즈 상이(제17조제3항) → 배송비 0원, 100,000원 전액 환급" },
      { id: "OI::OIT-2026-0011", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem · 상품불량]\nOIT-2026-0011 (결제가 150,000원)\n무상반품 · 150,000원 전액 환급", title: "v_node_order_item · OIT-2026-0011", color: "#3b735b", shape: "dot", size: 20, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0011", order_id: "ORD-2026-0007", product_id: "PRD-3005", status: "Returned", return_reason_code: "DEFECTIVE", sale_price_krw: 150000, customer_return_fee_krw: 0, net_refund_krw: 150000 }, verdictNote: "표시·광고 상이 및 불량(3개월 이내) → 배송비 판매자 부담 무상반품(150,000원)" },
      { id: "OI::OIT-2026-0007", classLabel: "OrderItem", layer: "ONT", label: "[OrderItem · 단순변심]\nOIT-2026-0007 (결제가 200,000원)\n6,000원 차감 · 194,000원 환급", title: "v_node_order_item · OIT-2026-0007", color: "#3b6ea5", shape: "dot", size: 20, viewName: "v_node_order_item", sourceStore: "Cloud Spanner Federated (ont_order_items)", record: { order_item_id: "OIT-2026-0007", order_id: "ORD-2026-0005", product_id: "PRD-3003", status: "Returned", return_reason_code: "CHANGE_OF_MIND", sale_price_krw: 200000, customer_return_fee_krw: 6000, net_refund_krw: 194000 }, verdictNote: "수령 3일 후 단순변심 반품 → 국내 왕복배송비 6,000원 차감 후 194,000원 환급" },
      { id: "PRD::PRD-3011", classLabel: "Product", layer: "ONT", label: "[Product]\nPRD-3011 크롭 가디건\n(출고지: DC-YIN 용인센터)", title: "v_node_product · PRD-3011", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3011", distribution_center_id: "DC-YIN", return_policy_tag: "STANDARD" }, verdictNote: "국내 풀필먼트 용인센터(DC-YIN) 출고 상품" },
      { id: "PRD::PRD-3005", classLabel: "Product", layer: "ONT", label: "[Product]\nPRD-3005 캐시미어 머플러\n(출고지: DC-ICN 김포센터)", title: "v_node_product · PRD-3005", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3005", distribution_center_id: "DC-ICN", return_policy_tag: "STANDARD" }, verdictNote: "국내 풀필먼트 김포센터(DC-ICN) 출고 상품" },
      { id: "PRD::PRD-3003", classLabel: "Product", layer: "ONT", label: "[Product]\nPRD-3003 데님 트러커 자켓\n(출고지: DC-YIN 용인센터)", title: "v_node_product · PRD-3003", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_product", sourceStore: "BigQuery Master (products)", record: { product_id: "PRD-3003", distribution_center_id: "DC-YIN", return_policy_tag: "STANDARD" }, verdictNote: "국내 풀필먼트 용인센터(DC-YIN) 출고 상품" },
      { id: "PROV::전상법17조", classLabel: "Provision", layer: "LEX", label: "[Provision · 전자상거래법 제17조]\n단순변심 7일 vs 표시상이 3개월\n청약철회 기한 및 배송비 귀속", title: "v_node_provision · 전자상거래법 제17조제1항", color: "#3b735b", shape: "box", matchSec: "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods", doc_id: "DOC_03_LAW_ECOMMERCE", article_no: "제17조제1항", provision_role: "BASE_CRITERIA" }, verdictNote: "국내 전자상거래 청약철회 본칙" },
      { id: "PROV::CS제1~2조", classLabel: "Provision", layer: "LEX", label: "[Provision · CS 내규 제1~2조]\n판매자 귀책 무상반품(0원) vs\n단순변심 국내 왕복 6,000원", title: "v_node_provision · CS 내규 제1조~제2조", color: "#3b735b", shape: "box", matchSec: "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC (ecommerce-okf)", record: { provision_slot_id: "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules", doc_id: "DOC_10_KMARKET_CS_SLA_POLICY", article_no: "제1조~제2조", provision_role: "INTERNAL_RULE" }, verdictNote: "전자상거래법 제17조를 구체화한 K마켙 반품 배송비 내규" },
      { id: "PROV::관세청제3조", classLabel: "Provision", layer: "LEX", label: "[Provision · 교란차단]\n관세청 해외직구 반송비 35,000원\n(국내 물류센터 출고 적용금지)", title: "v_node_provision · 관세청 고시 제3조 (DISTRACTOR_RULE)", color: "#a85c56", shape: "box", matchSec: "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee", viewName: "v_node_provision", sourceStore: "LEX Layer (Blocked by CONFLICTS_BY_SECTOR)", record: { provision_slot_id: "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee", doc_id: "DOC_06_DISTRACTOR_CUSTOMS", article_no: "제3조", provision_role: "DISTRACTOR_RULE" }, verdictNote: "CONFLICTS_BY_SECTOR 엣지로 국내 출고 주문에 오적용 차단" },
      { id: "DOC::DOC_03", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_03_LAW_ECOMMERCE\n03 전자상거래 소비자보호법", title: "v_node_source_document · DOC_03_LAW_ECOMMERCE", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_03_LAW_ECOMMERCE", title: "전자상거래 등에서의 소비자보호에 관한 법률", authority_level: "binding" }, verdictNote: "전자상거래 소비자보호법 정본 PDF" },
      { id: "DOC::DOC_10", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_10_KMARKET_CS_SLA_POLICY\n10 K마켙 CS 반품·물류 SLA 내규", title: "v_node_source_document · DOC_10_KMARKET_CS_SLA_POLICY", color: "#477a63", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_10_KMARKET_CS_SLA_POLICY", title: "K마켙 CS 반품·청약철회 및 물류 출고 SLA 운영 내규", authority_level: "internal" }, verdictNote: "K마켙 CS·물류 운영 내규 정본 PDF" },
      { id: "DOC::DOC_06", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_06_DISTRACTOR_CUSTOMS\n06 관세청 해외직구 고시 (distractor)", title: "v_node_source_document · DOC_06_DISTRACTOR_CUSTOMS", color: "#a85c56", shape: "box", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_06_DISTRACTOR_CUSTOMS", title: "관세청 해외직구 목록통관 및 특송물품 반품 고시", authority_level: "distractor" }, verdictNote: "해외직구 특송물품 전용 대조군 문서 (국내 물류센터 출고 건 배제)" }
    ],
    edges: [
      { from: "CTX::CS_SUPPORT", to: "PROV::전상법17조", label: "INVOKES_PROVISION\n[term_key: return-withdrawal-eligibility]", color: "#b88a44", width: 2.0 },
      { from: "CTX::CS_SUPPORT", to: "OI::OIT-2026-0018", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "CTX::CS_SUPPORT", to: "OI::OIT-2026-0011", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "CTX::CS_SUPPORT", to: "OI::OIT-2026-0007", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.4, dashes: true },
      { from: "OI::OIT-2026-0018", to: "PRD::PRD-3011", label: "OF_PRODUCT\n(DC-YIN 용인출고)", color: "#6b88a8", width: 1.5 },
      { from: "OI::OIT-2026-0011", to: "PRD::PRD-3005", label: "OF_PRODUCT\n(DC-ICN 김포출고)", color: "#6b88a8", width: 1.5 },
      { from: "OI::OIT-2026-0007", to: "PRD::PRD-3003", label: "OF_PRODUCT\n(DC-YIN 용인출고)", color: "#6b88a8", width: 1.5 },
      { from: "OI::OIT-2026-0018", to: "PROV::전상법17조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "OI::OIT-2026-0011", to: "PROV::전상법17조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "OI::OIT-2026-0007", to: "PROV::전상법17조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "PROV::전상법17조", to: "PROV::CS제1~2조", label: "DELEGATES_TO_INTERNAL", color: "#5a8770", width: 1.8 },
      { from: "PROV::전상법17조", to: "DOC::DOC_03", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.5 },
      { from: "PROV::CS제1~2조", to: "DOC::DOC_10", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.5 },
      { from: "PROV::전상법17조", to: "PROV::관세청제3조", label: "CONFLICTS_BY_SECTOR\n(해외직구 35,000원 차단)", color: "#a85c56", width: 1.8, dashes: true },
      { from: "PROV::관세청제3조", to: "DOC::DOC_06", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.6 }
    ]
  }
];

const ECOMMERCE_AGENT_QUESTIONS = [
  {
    num: "01",
    title: "VIP 장바구니 이탈 코디 번들 · 15% 할인 제안액 산정",
    dept_id: "CRM_GROWTH",
    dept_name: "그로스마케팅·MD",
    question: "박준혁 고객의 장바구니 미결제 세션(SES-1002-A)에 담긴 주상품과 연관 코디상품을 묶어 VIP 등급 최대 할인율로 번들 쿠폰을 제안할 때, 실제로 허용되는 합산 할인액과 최종 결제 제안 금액은 얼마인가?"
  },
  {
    num: "02",
    title: "품절 감지 대체상품 전환 및 장기 체화재고 마진하한 특례",
    dept_id: "MD_MERCHANDISING",
    dept_name: "MD본부·가격전략",
    question: "장바구니 세션 SES-1007-A에서 고객이 담은 상품 PRD-3009는 현재 출고 가능한 재고가 있는가? 품절이라면 대체 추천해야 할 상품 코드와 그 대체상품에 프로모션 할인을 적용할 때 유지해야 하는 최저마진율 하한은 몇 %인가?"
  },
  {
    num: "03",
    title: "비체화 신상품 VIP_RETENTION 예외승인 마진하한 판정",
    dept_id: "MD_MERCHANDISING",
    dept_name: "MD본부·가격전략",
    question: "신상품 PRD-3012는 기본 마진율이 상시 가드레일(25%)에 미달하는데 이번 프로모션에서 할인이 차단되는지, 아니면 적용 가능한 최저마진율 하한이 몇 %인지 판정하라."
  },
  {
    num: "04",
    title: "본부별 반품 집계 분기 — MD본부 총반품 vs CS심사팀 판매자귀책",
    dept_id: "CX_CS_SUPPORT",
    dept_name: "MD본부·CS심사팀",
    question: "전체 주문품목 원장을 기준으로 MD본부가 관리하는 총반품 건수와 CS심사팀이 집계하는 판매자 귀책 무상반품 건수는 각각 몇 건이며, 두 부서 간 집계 차이는 몇 건인가?"
  },
  {
    num: "05",
    title: "대규모유통업법 제11조 · 아틀리에누아르 판촉비 상한 및 초과분 흡수",
    dept_id: "PARTNER_SETTLEMENT",
    dept_name: "파트너상생·정산실",
    question: "아틀리에누아르(BRD-01)의 공동판촉 쿠폰 적용 주문품목들을 정산할 때, 기본계약서상 분담률(60%)과 관련 법령상 상한 중 어느 기준이 적용되며 K마켙이 의무적으로 흡수해야 하는 초과 분담액 합계는 얼마인가?"
  },
  {
    num: "06",
    title: "자발적·차별화 단독 행사 예외 분담 인정 vs 기각 건 대조 판정",
    dept_id: "PARTNER_SETTLEMENT",
    dept_name: "파트너상생·정산실",
    question: "노르딕아웃도어(BRD-05)의 다운 파카 주문품목 OIT-2026-0017(공동판촉 쿠폰 할인 60,000원) 정산 시 계약서상 판촉비 분담률 70%를 브랜드에 그대로 청구할 수 있는지 판정하고, 브랜드와 K마켙의 최종 분담 금액을 각각 산출하라."
  },
  {
    num: "07",
    title: "국내 물류센터 출고 반품 시 관세청 해외직구 반송수수료 고시 차단",
    dept_id: "CX_CS_SUPPORT",
    dept_name: "CS심사·준법감시",
    question: "주문 ORD-2026-0012의 반품 건(OIT-2026-0018)에 대해 14일 반송기한 및 건당 35,000원 국제반송수수료 규정을 적용해 차감할 수 있는지 판정하고, 고객이 실제로 부담할 반품배송비와 최종 환급액을 산출하라."
  },
  {
    num: "08",
    title: "물류센터별 출고 SLA 위반 주문 및 전사 지연보상 적립금 집계",
    dept_id: "FULFILLMENT_OPS",
    dept_name: "풀필먼트운영실",
    question: "물류센터별 출고 목표 SLA를 위반한 지연 출고 주문들에 대해 K마켙이 지급해야 할 지연보상 적립금의 전사 합계 포인트와 물류센터별 지연 건수는 각각 얼마인가?"
  },
  {
    num: "09",
    title: "대규모유통업법 제6조 서면 미교부 약정 효력 및 제18조 서류 보존 기간",
    dept_id: "PARTNER_SETTLEMENT",
    dept_name: "파트너상생·계약",
    question: "대규모유통업법 제6조에서 서면을 교부하지 않고 진행한 판촉행사나 단가 인하 약정의 효력을 어떻게 규정하고 있으며, 제18조에 따른 계약서면 및 판매촉진비용 정산내역서의 보존 의무 기간은 거래 종료일로부터 몇 년인가?"
  },
  {
    num: "10",
    title: "공정위 판촉비 심사지침상 사전 서면약정 시점 및 포괄 문구 인정 여부",
    dept_id: "LEGAL_COMPLIANCE",
    dept_name: "준법감시·법무",
    question: "공정위 판매촉진비용 부담전가 심사지침(Ⅰ.3)에서 사전 서면약정의 완료 시점과, 연간 기본계약서에 포괄적인 비용 분담 문구만 둔 경우의 인정 여부를 어떻게 규정하는가?"
  },
  {
    num: "11",
    title: "전자상거래법 제21조의2 3대 다크패턴 유형 및 정상 판매가격 기준 기간",
    dept_id: "LEGAL_COMPLIANCE",
    dept_name: "준법감시·다크패턴",
    question: "전자상거래법 제21조의2에서 금지하는 온라인 다크패턴 3가지 행위 유형과 공정위 다크패턴 가이드라인 제2조에서 할인율 표시 시 요구하는 정상 판매가격의 기준 기간은 며칠인가?"
  },
  {
    num: "12",
    title: "개보위 행태정보 최대 보유기간 및 심야 광고성 푸시 제한 기준",
    dept_id: "LEGAL_COMPLIANCE",
    dept_name: "준법감시·개보보호",
    question: "개인정보보호위원회 맞춤형 광고 행태정보 가이드라인 제4조·제5조에서 규정하는 비식별 행태정보의 최대 보유·이용 기간과 심야 시간대 광고성 푸시 제한 원칙은 무엇인가?"
  },
  {
    num: "13",
    title: "전자상거래법 제18조 반품 회수 후 대금 환급 기한 및 지연배상금 이율",
    dept_id: "CX_CS_SUPPORT",
    dept_name: "고객경험·CS심사팀",
    question: "전자상거래법 제18조 및 K마켙 CS 내규 제3조에 따라 통신판매업자가 소비자로부터 재화등을 반환받은 날부터 대금을 환급해야 하는 법정 기한과 환급 지연 시 지급해야 하는 지연배상금 연 이율은 얼마인가?"
  },
  {
    num: "14",
    title: "대규모유통업법 제10조 직매입 부당 반품 금지 및 정당한 반품 예외 사유",
    dept_id: "PARTNER_SETTLEMENT",
    dept_name: "파트너상생·직매입",
    question: "대규모유통업법 제10조제1항에서 금지하는 부당 반품의 원칙과, 직매입 거래에서 예외적으로 납품업자에게 반품이 허용되는 정당한 사유는 무엇인가?"
  },
  {
    num: "15",
    title: "단건 주문품목 OIT-2026-0001 실현마진율 산출 및 가드레일 충족 여부",
    dept_id: "MD_MERCHANDISING",
    dept_name: "MD본부·가격전략",
    question: "주문품목 OIT-2026-0001에 쿠폰 할인이 적용된 후의 단건 실현마진율은 소수 첫째 자리 기준 몇 %이며, MD본부 상시 마진 가드레일을 충족하는가?"
  },
  {
    num: "16",
    title: "마케팅 미동의 VIP 회원 장바구니 리마인드 푸시 발송 차단 근거",
    dept_id: "LEGAL_COMPLIANCE",
    dept_name: "준법감시·개보보호",
    question: "장바구니 이탈 세션 SES-1004-A를 발생시킨 VIP 등급 최현우 고객에게 맞춤형 리마인드 푸시나 타겟팅 쿠폰을 발송할 수 없는 이유를 회원 마스터의 동의 컬럼 값과 개보위 가이드라인 제3조를 근거로 답하라."
  },
  {
    num: "17",
    title: "위생제한 상품 홀로그램 실링 택 훼손 시 청약철회 거절 판정",
    dept_id: "CX_CS_SUPPORT",
    dept_name: "고객경험·CS심사팀",
    question: "위생제한 상품인 실크 레이스 브라렛에 대한 반품 신청 건 OIT-2026-0014의 청약철회 승인 여부와 그 물리적 검수 근거는 무엇인가?"
  },
  {
    num: "18",
    title: "단순변심 기한 내 반품 건 왕복배송비 차감 및 최종 환급액 산정",
    dept_id: "CX_CS_SUPPORT",
    dept_name: "고객경험·CS심사팀",
    question: "배송완료 후 3일 만에 단순변심으로 반품 접수된 주문품목 OIT-2026-0007의 청약철회 적격 여부, 차감할 왕복 반품배송비, 그리고 고객에게 최종 환급할 금액은 얼마인가?"
  },
  {
    num: "19",
    title: "물류센터 재고 원장 재고상태별 항목 수 및 보유수량 합계 집계",
    dept_id: "FULFILLMENT_OPS",
    dept_name: "풀필먼트운영실",
    question: "물류센터 재고 원장 전체 32개 항목을 재고상태별로 집계할 때 각 상태의 항목 수와 수량 합계는 얼마인가?"
  },
  {
    num: "20",
    title: "장바구니 담기 후 동일 세션 내 결제완료 전환 회원 및 등급 조회",
    dept_id: "CRM_GROWTH",
    dept_name: "그로스마케팅·CRM",
    question: "실시간 행동로그에서 장바구니 담기 이후 이탈하지 않고 동일 세션 내에 결제완료까지 정상 전환된 세션 ID와 회원 ID, 구매 상품 ID 및 해당 회원의 멤버십 등급은 무엇인가?"
  },
  {
    num: "21",
    internal_key: "Q21_D5",
    title: "폐기된 구버전 MD 마진 가드레일(v0.1.0) 스냅샷 호출 차단 검증",
    dept_id: "MD_MERCHANDISING",
    dept_name: "MD본부·가격전략",
    question: "과거 폐기된 구버전 MD 마진 가드레일 내규 스냅샷(versions/md_art_002_margin_guardrail_v0.1.0, 구 하한 15%)을 기준으로 이번 프로모션 주문품목의 마진 적격 여부를 심사해줘."
  }
];

const ECOMMERCE_BENCH_EQ_TITLES = {
  EQ01: "VIP 장바구니 이탈 코디 번들 · 15% 할인 제안액 산정",
  EQ02: "품절 감지 대체상품 전환 및 장기 체화재고 마진하한 특례",
  EQ03: "비체화 신상품 VIP_RETENTION 예외승인 마진하한 판정",
  EQ04: "본부별 반품 집계 분기 — MD본부 총반품 vs CS심사팀 판매자귀책",
  EQ05: "대규모유통업법 제11조 · 아틀리에누아르 판촉비 상한 및 초과분 흡수",
  EQ06: "자발적·차별화 단독 행사 예외 분담 인정 vs 기각 건 대조 판정",
  EQ07: "국내 물류센터 출고 반품 시 관세청 해외직구 반송수수료 고시 차단",
  EQ08: "물류센터별 출고 SLA 위반 주문 및 전사 지연보상 적립금 집계",
  EQ09: "대규모유통업법 제6조 서면 미교부 약정 효력 및 제18조 서류 보존 기간",
  EQ10: "공정위 판촉비 심사지침상 사전 서면약정 시점 및 포괄 문구 인정 여부",
  EQ11: "전자상거래법 제21조의2 3대 다크패턴 유형 및 정상 판매가격 기준 기간",
  EQ12: "개보위 행태정보 최대 보유기간 및 심야 광고성 푸시 제한 기준",
  EQ13: "전자상거래법 제18조 반품 회수 후 대금 환급 기한 및 지연배상금 이율",
  EQ14: "대규모유통업법 제10조 직매입 부당 반품 금지 및 정당한 반품 예외 사유",
  EQ15: "단건 주문품목 OIT-2026-0001 실현마진율 산출 및 가드레일 충족 여부",
  EQ16: "마케팅 미동의 VIP 회원 장바구니 리마인드 푸시 발송 차단 근거",
  EQ17: "위생제한 상품 홀로그램 실링 택 훼손 시 청약철회 거절 판정",
  EQ18: "단순변심 기한 내 반품 건 왕복배송비 차감 및 최종 환급액 산정",
  EQ19: "물류센터 재고 원장 재고상태별 항목 수 및 보유수량 합계 집계",
  EQ20: "장바구니 담기 후 동일 세션 내 결제완료 전환 회원 및 등급 조회"
};

const ECOMMERCE_BENCH_DOC_NAMES = {
  "01": "대규모유통업법 제11조",
  "02": "공정위 특약매입 심사지침",
  "03": "전자상거래 소비자보호법",
  "04": "공정위 다크패턴 가이드라인",
  "05": "개보위 행태정보·망법 제50조",
  "06": "관세청 해외직구 고시(대조군)",
  "07": "K마켙 초개인화 추천 내규",
  "08": "K마켙 MD 마진·체화재고 내규",
  "09": "K마켙 파트너 판촉비 정산 내규",
  "10": "K마켙 CS 반품·물류 SLA 내규"
};

const ECOMMERCE_OKF_V02_DROPDOWN_OPTIONS = {
  type: ["Source Document", "Provision", "PolicyClause", "Table", "Concept", "Document"],
  status: ["stable", "verified", "draft", "deprecated"],
  content_class: ["authentic", "guidance", "internal_policy", "synthetic", "reference"],
  treatment: ["verbatim_ko", "normalized_ko", "structured_table"],
  license: [
    "공공누리 제1유형 (국가법령정보센터 · 대규모유통업법·전자상거래법 자유이용허락)",
    "공정거래위원회·개인정보보호위원회 표준 심사지침·안내서 (공공누리 출처표시)",
    "관세청 고시 공공저작물 (해외직구 목록통관 대조군 · 국내출고 적용제외)",
    "K마켙 사내 표준 운영 내규 (CRM·MD·파트너정산·CS · 사내한 대외비)"
  ],
  generated_by: [
    "process:build_okf/3.0",
    "process:okf_studio_editor/0.2",
    "agent:gemini-2.5-pro"
  ],
  verified_by: [
    "process:verify_provisions/1.0",
    "human:md_pricing_committee_lead",
    "human:fair_trade_cp_reviewer",
    "human:cx_privacy_governance_admin"
  ],
  verified_method: [
    "source_text_match",
    "owner_acceptance",
    "committee_signoff",
    "automated_lint_p1_p4"
  ],
  contacts: [
    "한지민(수석) - 데이터거버넌스·온톨로지팀 <no-hallucination@kmarket.co.kr>",
    "박서준(팀장) - MD본부 가격전략·마진관리실 <keep.margin25@kmarket.co.kr>",
    "최유진(리드) - 그로스마케팅·AI추천랩 <save.my.cart@kmarket.co.kr>",
    "정민호(책임) - 파트너상생·공정거래CP팀 <fifty.fifty@kmarket.co.kr>",
    "강하늘(매니저) - 고객경험(CX)·CS심사팀 <dont.cut.the.tag@kmarket.co.kr>"
  ]
};

const ECOMMERCE_CHANGE_NOTE_PRESETS = [
  "공정거래CP·데이터거버넌스 정기 검증 완료에 따른 verified.by 및 status 현행화",
  "MD 마진 가드레일(25%)·체화재고(90일+ 10%) 및 대규모유통업법 제11조(50% 상한) 개정에 따른 버전 승격",
  "장바구니 이탈 타겟팅 동의(marketing_opt_in) 및 청약철회(7일/90일·홀로그램 택) 단서·예외 수치 정밀 교정",
  "원문 대조(P1~P4) 재검증 및 K마켙 3-Plane(GCS·Knowledge Catalog·BQ Graph) 정합성 반영"
];

function applyProjectDomainData(projId) {
  const isEcom = projId === "ecommerce-ontology";

  // 1. Module 02 (OKF Validation Graph View)
  if (typeof FINANCE_SEMANTIC_ENTITIES !== "undefined") {
    SEMANTIC_ENTITIES = isEcom ? ECOMMERCE_SEMANTIC_ENTITIES : FINANCE_SEMANTIC_ENTITIES;
    SEMANTIC_EDGES = isEcom ? ECOMMERCE_SEMANTIC_EDGES : FINANCE_SEMANTIC_EDGES;
    CAVEAT_SECTIONS = isEcom ? ECOMMERCE_CAVEAT_SECTIONS : FINANCE_CAVEAT_SECTIONS;
  }
  if (typeof FINANCE_GRAPH_SCOPE_LABELS !== "undefined") {
    GRAPH_SCOPE_LABELS = isEcom ? ECOMMERCE_GRAPH_SCOPE_LABELS : FINANCE_GRAPH_SCOPE_LABELS;
  }

  const scopeMenu = document.getElementById("okf-graph-scope-select-menu");
  if (scopeMenu && typeof GRAPH_SCOPE_LABELS === "object") {
    scopeMenu.innerHTML = Object.entries(GRAPH_SCOPE_LABELS).map(([k, lbl], idx) => `
      <div class="gcp-custom-select-opt ${idx === 0 ? "selected" : ""}" data-value="${escapeHtml(k)}" onclick="selectGraphScopeCustomOption(event, '${escapeHtml(k)}')">
        <span>${escapeHtml(lbl)}</span>
        <span class="material-symbols-outlined gcp-opt-check" style="opacity:${idx === 0 ? "1" : "0"};">check</span>
      </div>
    `).join("");
    const scopeValEl = document.getElementById("okf-graph-scope-select-val");
    if (scopeValEl) scopeValEl.textContent = GRAPH_SCOPE_LABELS.ALL;
    const hiddenScope = document.getElementById("graph-scope-select");
    if (hiddenScope) hiddenScope.value = "ALL";
  }

  const gSearch = document.getElementById("graph-search-input");
  if (gSearch) {
    gSearch.placeholder = isEcom
      ? "노드·조문 검색 (제11조, 50%, 마진, 체화재고, 청약철회)..."
      : "노드·조문 검색 (제29조, 우선변제, 별표3)...";
  }

  // 2. Module 04 (BigQuery Property Graph)
  if (typeof FINANCE_BQ_CLASS_NODES !== "undefined") {
    BQ_CLASS_NODES = isEcom ? ECOMMERCE_BQ_CLASS_NODES : FINANCE_BQ_CLASS_NODES;
    BQ_CLASS_EDGES = isEcom ? ECOMMERCE_BQ_CLASS_EDGES : FINANCE_BQ_CLASS_EDGES;
    BQ_GQL_PRESETS = isEcom ? ECOMMERCE_BQ_GQL_PRESETS : FINANCE_BQ_GQL_PRESETS;
  }
  BQ_QUERY_IDX = 0;
  if (typeof bqCurrentInstNodes !== "undefined") {
    bqCurrentInstNodes = [];
    bqCurrentInstEdges = [];
  }

  const gqlMenu = document.getElementById("bq-gql-select-menu");
  if (gqlMenu && Array.isArray(BQ_GQL_PRESETS)) {
    gqlMenu.innerHTML = BQ_GQL_PRESETS.map((p, idx) => `
      <div class="gcp-custom-select-opt ${idx === 0 ? "selected" : ""}" data-idx="${idx}" onclick="selectBqGqlCustomOption(event, ${idx})">
        <span>${escapeHtml(p.title)}</span>
        <span class="material-symbols-outlined gcp-opt-check" style="opacity:${idx === 0 ? "1" : "0"};">check</span>
      </div>
    `).join("");
    const gqlValEl = document.getElementById("bq-gql-select-val");
    if (gqlValEl && BQ_GQL_PRESETS[0]) gqlValEl.textContent = BQ_GQL_PRESETS[0].title;
    const codeEl = document.getElementById("bq-gql-code");
    if (codeEl && BQ_GQL_PRESETS[0]) {
      if ("value" in codeEl) codeEl.value = BQ_GQL_PRESETS[0].gql;
      else codeEl.textContent = BQ_GQL_PRESETS[0].gql;
    }
  }

  // Update Module 04 Legend descriptions
  const legendDescs = document.querySelectorAll("#module-bq-graph .bq-legend-grid .legend-col-desc");
  if (legendDescs && legendDescs.length >= 2) {
    legendDescs[0].textContent = isEcom
      ? "· OrderItem 허브 + 원장 7종 + BusinessContext (SCOPES_PORTFOLIO)"
      : "· LoanContract 허브 + 원장 7종 + BusinessContext (SCOPES_PORTFOLIO)";
    legendDescs[1].textContent = isEcom
      ? "· SourceDocument(10) + Provision(36)"
      : "· SourceDocument(10) + Provision(174)";
  }

  // 3. Module 05 (Agent Studio)
  if (typeof FINANCE_AGENT_QUESTIONS !== "undefined") {
    AGENT_QUESTIONS = isEcom ? ECOMMERCE_AGENT_QUESTIONS : FINANCE_AGENT_QUESTIONS;
  }
  if (typeof AGENT_STUDIO_INITIALIZED !== "undefined") {
    AGENT_STUDIO_INITIALIZED = false;
    AGENT_SELECTED_IDX = 0;
    AGENT_SELECTED_NUM = "01";
    AGENT_TURN_HISTORY = [];
    AGENT_ACTIVE_TURN_IDX = -1;
  }

  // 4. Module 06 (RAG vs Graph Studio)
  if (typeof FINANCE_BENCH_EQ_TITLES !== "undefined") {
    BENCH_EQ_TITLES = isEcom ? ECOMMERCE_BENCH_EQ_TITLES : FINANCE_BENCH_EQ_TITLES;
    BENCH_DOC_NAMES = isEcom ? ECOMMERCE_BENCH_DOC_NAMES : FINANCE_BENCH_DOC_NAMES;
  }
  if (typeof BENCH_INITIALIZED !== "undefined") {
    BENCH_INITIALIZED = false;
    BENCH_DATA = null;
    BENCH_LOADING_ERROR = null;
    BENCH_SELECTED_IDX = 0;
    BENCH_LIVE_TURNS = [];
  }

  // 5. Module 01 (Intro)
  if (typeof INTRO_DATA !== "undefined") {
    INTRO_DATA = null;
    INTRO_DATA_ERR = "";
    if (typeof INTRO_SVG_CACHE === "object") {
      Object.keys(INTRO_SVG_CACHE).forEach(k => delete INTRO_SVG_CACHE[k]);
    }
  }

  // 6. Module 03 (OKF Management)
  if (typeof FINANCE_OKF_V02_DROPDOWN_OPTIONS !== "undefined") {
    OKF_V02_DROPDOWN_OPTIONS = isEcom ? ECOMMERCE_OKF_V02_DROPDOWN_OPTIONS : FINANCE_OKF_V02_DROPDOWN_OPTIONS;
  }
  if (typeof FINANCE_CHANGE_NOTE_PRESETS !== "undefined") {
    CHANGE_NOTE_PRESETS = isEcom ? ECOMMERCE_CHANGE_NOTE_PRESETS : FINANCE_CHANGE_NOTE_PRESETS;
  }
  if (typeof MODAL_PRESET_NOTE_VAL !== "undefined") {
    MODAL_PRESET_NOTE_VAL = CHANGE_NOTE_PRESETS[0] || "";
    MODAL_CHANGE_NOTE_TEXT = CHANGE_NOTE_PRESETS[0] || "";
  }
  if (typeof MGMT_ACTIVE_KEY !== "undefined") {
    MGMT_ACTIVE_KEY = 0;
    if (typeof MGMT_SELECTED_SET !== "undefined") MGMT_SELECTED_SET.clear();
    MGMT_DIRTY_MAP = {};
    KC_SELECTED_KEY = "ACTIVE:0";
  }
}
