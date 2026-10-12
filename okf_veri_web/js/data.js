/* ==========================================================================
   okf_veri_web/js/data.js
   Domain Dataset: Semantic Entities, Edges, 6 Demo Scenarios (01 · Intro figures live in data/intro_arch.json),
   and BigQuery Property Graph Class Schema & GQL Instance Presets.
   Palette: Google Cloud Enterprise 4-Color Chart Palette (#1a73e8, #1e8e3e, #f9ab00, #d93025)
   ========================================================================== */

let SEMANTIC_ENTITIES = [
  {
    id: "ENT_KSIC_FGHL",
    name: "표준산업분류 F·G·H·L (0.90%)",
    matchIds: ["regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029"],
    matchSec: ["제29조"]
  },
  {
    id: "ENT_PRIORITY_DIP",
    name: "우선변제자산 (회생법 제180조2항 · 10%)",
    matchIds: [
      "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
      "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_06_07_workout_special_rules",
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver"
    ],
    matchSec: ["제29조", "별표3 제6호~제7호", "내규 제18조"]
  },
  {
    id: "ENT_6M_REPAY",
    name: "채권재조정 6개월 연속상환",
    matchIds: [
      "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver"
    ],
    matchSec: ["별표3 제3호 라목", "내규 제18조"]
  },
  {
    id: "ENT_KODIT_85",
    name: "신용보증기금 85% 이상 보증서",
    matchIds: [
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule",
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver"
    ],
    matchSec: ["내규 제16조", "내규 제18조"]
  },
  {
    id: "ENT_PATENT_DISCRETION",
    name: "특허권 단독취득 (선택적 적용 재량)",
    matchIds: [
      "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion",
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion"
    ],
    matchSec: ["제Ⅱ장 1-나 ④항", "내규 제25조"]
  },
  {
    id: "ENT_RATE_ABC",
    name: "적용금리 A+B+C 분리공시",
    matchIds: [
      "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_c_abc_separation",
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc",
      "research_briefs/07_nars_rate_policy_issues/sec01_rate_components_and_dsr/nars_01_intro_and_rate_formula"
    ],
    matchSec: ["제Ⅱ장 1-다", "내규 제22조", "이슈와논점 1"]
  },
  {
    id: "ENT_EWS_10D",
    name: "조기경보(EWS) 10일+상각특수채권",
    matchIds: [
      "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
      "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency"
    ],
    matchSec: ["제27조", "내규 제14조"]
  },
  {
    id: "ENT_CONTRACT_DT",
    name: "대출계약 체결일 (contract_dt)",
    matchIds: ["internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates"],
    matchSec: ["내규 제21조"]
  }
];

let SEMANTIC_EDGES = [
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    toId: "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
    fromSec: "제27조",
    toSec: "별표3 제3호 라목",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "채권재조정 여신 중 6개월 이상 연속 정상상환 또는 유상증자 발생 및 판단근거 문서화 시 고정이하 분류에서 제외(요주의 유지) 특례"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
    toId: "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_06_07_workout_special_rules",
    fromSec: "제29조",
    toSec: "별표3 제6호~제7호",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "기촉법 제18조제2항 및 채무자회생법 제180조제2항 우선변제자산은 고정 10%·회수의문 25%·추정손실 50%로 적립률 1/2 감경 (요주의 7%는 감경 없음)"
  },
  {
    fromId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule",
    toId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
    fromSec: "내규 제16조",
    toSec: "내규 제18조",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "1월(30일) 초과 연체 시에도 (6개월 연속상환 OR 유상증자 OR 신보 85% 이상 보증서) + 우선변제자산 요건 충족 및 본부심사역 승인 시 자동 EOD 통지 유예"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_026",
    toId: "regulations/03_fsc_reg_impact_analysis/sec02_article_comparison_and_annex/impact_07_annex3_4_item54_exceptions",
    fromSec: "제26조",
    toSec: "별표3의4 제54호",
    rel: "HAS_EXCEPTION_PROVISO",
    color: "#a85c56",
    reason: "거액익스포져 기본자본 25% 한도(D-SIB 20%) 적용 시 [별표 3의4] 제54호 한도초과 예외 인정 사유 및 정책금융 특례"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    toId: "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_normal_precautionary",
    fromSec: "제27조",
    toSec: "별표3 제1호 가~나목",
    rel: "DELEGATES_CRITERIA_TO",
    color: "#3b6ea5",
    reason: "은행업감독규정 제27조제2항에 따라 자산건전성 5단계 중 정상(Normal)·요주의(1월 이상 3월 미만 연체) 세부 기준을 [별표 3] 제1호 가~나목에 위임"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    toId: "regulations/02_law_annex3_criteria/sec01_five_stage_definitions/annex3_item_01_substandard_doubtful_loss",
    fromSec: "제27조",
    toSec: "별표3 제1호 다~마목",
    rel: "DELEGATES_CRITERIA_TO",
    color: "#3b6ea5",
    reason: "은행업감독규정 제27조제2항에 따라 고정(3월 이상 연체)·회수의문·추정손실(12월 이상 연체) 세부 기준을 [별표 3] 제1호 다~마목에 위임"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    toId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
    fromSec: "제27조",
    toSec: "제29조",
    rel: "DELEGATES_CRITERIA_TO",
    color: "#3b6ea5",
    reason: "제27조에 따른 5단계 건전성 분류 결과를 제29조 단계별 대손충당금·대손준비금 최소적립률 산식의 입력 기준으로 연결"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    toId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
    fromSec: "제27조",
    toSec: "내규 제14조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "감독규정 제27조 건전성·연체 기준을 리스크위 보고용(고정이하 90일+)·금감원 공시용(30일+ 상각제외)·여신관리팀 EWS용(10일+ 상각포함) 3종 지표로 세분화"
  },
  {
    fromId: "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption",
    toId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
    fromSec: "별표3 제3호 라목",
    toSec: "내규 제18조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "[별표 3] 제3호 라목 채권재조정 6개월 연속상환 특례 및 보증부 여신 평가를 당행 내규 제18조 EOD 유예 요건(신보 85%+ 보증서·본부심사역 결재)으로 구체화"
  },
  {
    fromId: "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion",
    toId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion",
    fromSec: "제Ⅱ장 1-나 ④항",
    toSec: "내규 제25조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "금융위·은행연합회 개선방안 Ⅱ-1-나 ④항의 '특허취득 은행 선택적 적용 재량'을 행사하여 당행 내규 제25조②에서 '재무개선 미동반 단독 특허취득 필수 인하 제외'로 구체화"
  },
  {
    fromId: "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_c_abc_separation",
    toId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc",
    fromSec: "제Ⅱ장 1-다",
    toSec: "내규 제22조",
    rel: "DELEGATES_TO_INTERNAL",
    color: "#3b6ea5",
    reason: "대출금리 비교공시 개선방안 Ⅱ-1-다의 기준(A)·가산(B)·가감조정(C) 분리공시 원칙을 당행 내규 제22조 전산 산식 및 착시공시 금지 규칙으로 명문화"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
    toId: "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge",
    fromSec: "제29조",
    toSec: "저축은행감독규정 제38조",
    rel: "CONFLICTS_BY_SECTOR",
    color: "#b88a44",
    reason: "시중은행 기업여신 충당금(제29조: 정상 0.85%/0.90%, 고정 20%/10%)에 상호저축은행업감독규정 제38조(정상 0.5%, 다중채무자 가중)를 혼입 적용 금지"
  },
  {
    fromId: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
    toId: "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_02_overdue_criteria",
    fromSec: "제27조",
    toSec: "저축은행 연체기준 3~6쪽",
    rel: "CONFLICTS_BY_SECTOR",
    color: "#b88a44",
    reason: "시중은행 자산건전성 분류 기준(제27조)에 상호저축은행 전용 건전성 분류 및 연체 기준(79개 저축은행 대상)을 혼입 적용 금지"
  },
  {
    fromId: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
    toId: "research_briefs/07_nars_rate_policy_issues/sec01_rate_components_and_dsr/nars_02_dsr_and_delinquency_trend",
    fromSec: "내규 제14조",
    toSec: "이슈와논점 2",
    rel: "CONFLICTS_BY_SECTOR",
    color: "#b88a44",
    reason: "별빛은행 기업여신 연체율(공시 2.26% / EWS 4.00%) 산출 시 국회입법조사처 브리프에 인용된 거시 가계대출 연체율(0.24%) 수치를 혼입 인용 금지"
  }
];

let CAVEAT_SECTIONS = new Set([
  "제26조", "제27조", "제29조",
  "별표3 제1호 가~나목", "별표3 제1호 다~마목", "별표3 제3호 라목", "별표3 제6호~제7호",
  "별표3의4 제54호",
  "제Ⅱ장 1-나 ④항", "제Ⅱ장 1-다",
  "이슈와논점 1", "이슈와논점 2",
  "내규 제14조", "내규 제16조", "내규 제18조",
  "내규 제21조", "내규 제22조", "내규 제25조",
  "저축은행 연체기준 3~6쪽", "저축은행감독규정 제38조"
]);

const DEMO_SCENARIOS = [
  {
    id: "S1",
    code: "SCEN_01_KSIC_PROVISION",
    title: "표준산업분류(KSIC) F·G·H·L 업종 정상여신 대손충당금 적립률 단서 (0.90% vs 0.85%)",
    dept: "리스크관리부 · 결산충당금 산출 (BusinessContext: RISK_PROV_CLOSING)",
    query: "그랜드하모니호텔(주)(CUST_0016, 숙박및음식점업 H, 정상 분류 여신 100억 원) 및 F·G·H·L 4대 민감업종 정상여신 포트폴리오(총 600억 원)의 최소 대손충당금 적립률과 적립액은?",
    targetSec: "제29조",
    ledgerTables: "customers.csv (ksic_sec_cd='H') ⋈ loan_contracts.csv (asset_quality_cd='NORMAL', balance_krw=60,000,000,000)",
    ragResult: {
      verdict: "0.85% 적용 · 대손충당금 5억 1,000만 원 적립 (3,000만 원 과소적립 위반)",
      chunks: "은행업감독규정 제29조제1항제1호가목 본문: '정상분류자산 : 100분의 0.85 이상'",
      failureReason: "Top-K 벡터 검색이 '기업여신 정상분류 적립률' 키워드와 가장 유사한 본칙 문장(0.85%)만 상위로 반환하고, 괄호 단서 조항('다만, 표준산업분류상 건설업(F), 도매 및 소매업(G), 숙박 및 음식점업(H), 부동산 및 임대업(L)은 100분의 0.9 이상')과 제8차/제10차 KSIC 문자체계 차이를 누락함."
    },
    graphRagResult: {
      verdict: "0.90% 단서 적용 · 대손충당금 5억 4,000만 원 적립 (법정 하한 100% 준수)",
      graphPath: "BusinessContext(RISK_PROV) ➔ DecisionCriteria(제29조1항1호가목 본칙 0.85%) ➔ ExceptionRule(OVERRULES_WITH_EXCEPTION: KSIC F·G·H·L 단서 0.90%) ➔ DataField(customers.ksic_sec_cd)",
      resolution: "Knowledge Catalog에 등록된 제29조(gs://okf/regulations/01_fsc_banking_reg/.../art_029.md)의 시맨틱 엔티티(ENT_KSIC_FGHL)를 통해 F·G·H·L 4대 업종 0.90% 단서를 강제 결합하여 3,000만 원 과소적립 리스크를 원천 차단."
    }
  },
  {
    id: "S2",
    code: "SCEN_02_PRIORITY_DIP",
    title: "채무자회생법 제180조제2항 우선변제권 인정 고정여신 적립률 1/2 감경 특례 (10% vs 20%)",
    dept: "기업구조조정실 · 회생기업 충당금 심사 (BusinessContext: WORKOUT_DIP_REVIEW)",
    query: "회생절차 개시결정 후 채무자회생법 제180조제2항에 따른 공익채권(우선변제권 인정)으로 확정된 고정(Substandard) 분류 여신 100억 원의 최소 대손충당금 적립률은?",
    targetSec: "제29조",
    ledgerTables: "loan_contracts.csv (asset_quality_cd='SUBSTANDARD') ⋈ workout_histories.csv (priority_repay_Right_yn='Y', legal_basis_cd='REHAB_ACT_180_2')",
    ragResult: {
      verdict: "20.0% 적용 · 대손충당금 20억 원 적립 (10억 원 과대적립 오류)",
      chunks: "은행업감독규정 제29조제1항제1호다목 본문: '고정분류자산 : 100분의 20 이상'",
      failureReason: "벡터 검색이 '고정분류자산 대손충당금' 질의에 대해 다목 본칙(20%)만 인출하고, 이어지는 단서('다만, 기업구조조정촉진법 또는 채무자 회생 및 파산에 관한 법률 제180조제2항에 따라 우선변제권이 인정되는 자산은 100분의 10 이상')와 workout_histories.csv의 공익채권 플래그를 연결하지 못함."
    },
    graphRagResult: {
      verdict: "10.0% 감경 특례 적용 · 대손충당금 10억 원 적립 (자본비율 훼손 방지)",
      graphPath: "DecisionCriteria(제29조1항1호다목 고정 20%) ➔ ExceptionRule(OVERRULES_WITH_EXCEPTION: 우선변제자산 10% 감경) ➔ DataField(workout_histories.priority_repay_right_yn='Y')",
      resolution: "제29조와 [별표 3] 제6호~제7호 사이에 연결된 OVERRULES_WITH_EXCEPTION 엣지를 추적하여 우선변제권 인정 자산 1/2 감경(20%→10%) 특례를 정확히 적용."
    }
  },
  {
    id: "S3",
    code: "SCEN_03_ANNEX3_6M_REPAY",
    title: "[별표 3] 제3호 라목 채권재조정 6개월 이상 연속 상환 시 고정이하 분류 제외 특례",
    dept: "여신감리부 · 자산건전성 재분류 심사 (BusinessContext: ASSET_QUALITY_AUDIT)",
    query: "워크아웃 채권재조정 이후 변경된 계약조건에 따라 7개월 연속 원리금을 정상 상환 중인 차주(LN_2026_WK_01)를 고정이하(Substandard)로 분류해야 하는가, 요주의(Precautionary)로 유지할 수 있는가?",
    targetSec: "별표3 제3호 라목",
    ledgerTables: "loan_contracts.csv ⋈ workout_histories.csv (consec_repay_months=7, debt_restruct_yn='Y')",
    ragResult: {
      verdict: "고정(Substandard) 분류 판정 (정상 상환 기업의 부당 등급 강등)",
      chunks: "은행업감독규정 제27조 및 별표3 제3호 가목: '채권재조정 여신은 원칙적으로 고정이하로 분류'",
      failureReason: "본문(제27조)과 별도 PDF 문서(02_LAW_별표3_자산건전성분류기준.pdf p.4~5)로 분리된 [별표 3] 제3호 라목('6개월 이상 연속하여 변경된 계약조건에 따라 채무를 이행하는 경우 고정이하 분류 대상에서 제외')을 다중 문서 간 위임 관계 없이 검색하여 놓침."
    },
    graphRagResult: {
      verdict: "고정이하 분류 제외 · 요주의(Precautionary) 유지 승인",
      graphPath: "제27조(건전성 분류) ➔ DELEGATES_CRITERIA_TO ➔ 별표3 제3호 가목(채권재조정 고정 원칙) ➔ OVERRULES_WITH_EXCEPTION ➔ 별표3 제3호 라목(6개월 연속상환 예외) ➔ workout_histories.consec_repay_months(7 >= 6)",
      resolution: "01번 감독규정 본문(제27조)에서 02번 별표3 PDF(제3호 라목)로 이어지는 문서 간 시맨틱 엣지를 탐색하여 6개월 연속 상환 특례 요건 충족을 입증."
    }
  },
  {
    id: "S4",
    code: "SCEN_04_PATENT_RATE_CUT",
    title: "기업대출 금리인하요구권 — 재무개선 미동반 '특허권 단독 취득'의 선택적 적용 재량",
    dept: "기업여신심사부 · 금리인하요구권 심사 (BusinessContext: CORP_RATE_CUT_REVIEW)",
    query: "재무상태나 신용등급 개선 없이 '국내 특허권 단독 취득'만을 사유로 금리인하요구권을 신청한 기업차주(REQ_2026_004)에 대해 은행이 의무적으로 금리를 인하해야 하는가?",
    targetSec: "제Ⅱ장 1-나 ④항",
    ledgerTables: "rate_cut_requests.csv (req_reason_cd='PATENT_ACQ_ONLY', credit_rating_delta=0, fin_improvement_yn='N')",
    ragResult: {
      verdict: "금리인하 의무 수용 판정 (내규 및 감독당국 재량 단서 위반)",
      chunks: "은행권 대출금리 산정체계 개선방안 제Ⅱ장 1-나: '기업대출 금리인하요구권 인정 사유에 특허권 취득, 담보제공 등을 명시'",
      failureReason: "개선방안 본문의 '특허권 취득 인정' 문구만 매칭하고, 같은 페이지 하단 ④항 단서('다만, 특허취득은 신용도 영향이 불명확하므로 은행이 내부 신용평가 반영 여부에 따라 선택적으로 적용 가능')와 이를 구체화한 당행 내규 제25조(재무개선 미동반 단독 특허취득은 필수 인하 제외)를 연결하지 못함."
    },
    graphRagResult: {
      verdict: "의무 인하 대상 아님 (내규 제25조에 의거 불수용 또는 재무개선 보완 요청)",
      graphPath: "개선방안 제Ⅱ장 1-나 ④항(선택적 적용 재량) ➔ SPECIFIES_INTERNAL_RULE ➔ 별빛은행 여신내규 제25조(단독 특허취득 인하 제외) ➔ rate_cut_requests.fin_improvement_yn='N'",
      resolution: "외부 감독당국 가이드라인(05번 PDF ④항)이 부여한 재량권과 당행 여신내규(10번 PDF 제25조)를 SPECIFIES_INTERNAL_RULE 엣지로 결합해 정확한 심사 판정 도출."
    }
  },
  {
    id: "S5",
    code: "SCEN_05_DELINQUENCY_TRIAD",
    title: "동일 용어('연체율')의 호출 부서·목적(BusinessContext)별 3중 산식 및 기준일수 분리",
    dept: "리스크위원회(90일+) vs 금감원 공시(1개월+) vs 여신관리팀 EWS(10일+상각포함)",
    query: "2026년 1분기 당행 기업여신 포트폴리오의 '연체율'은 몇 %인가? (호출 부서별 기준 분리)",
    targetSec: "내규 제14조",
    ledgerTables: "delinquency_events.csv (ovd_days, write_off_special_bond_krw) ⋈ loan_contracts.csv",
    ragResult: {
      verdict: "단일 수치(2.26%)만 반환하거나 문맥 없이 90일/30일/10일 기준을 혼동",
      chunks: "문서 내 산재한 '1개월 이상 연체', '90일 이상 고정이하', '10일 이상 조기경보' 구절 혼재",
      failureReason: "동일한 '연체율' 용어가 호출 주체(리스크위원회 vs 대외공시팀 vs 여신관리팀 EWS)에 따라 분자·분모와 연체일수(90일 / 30일 / 10일+상각특수채권)가 완전히 달라진다는 BusinessContext 분리 구조가 없음."
    },
    graphRagResult: {
      verdict: "부서별 3원화 산출 — 리스크 NPL 1.51% · 금감원 공시 2.26% · 여신관리 EWS 4.00%",
      graphPath: "Term('연체율') ➔ [Context 1: 리스크위 제27조(90일+ 1.51%)] / [Context 2: 감독원 공시(30일+ 2.26%)] / [Context 3: 내규 제14조 EWS(10일+상각채권 4.00%)]",
      resolution: "데이터·비즈니스 맥락·의사결정 기준 3각 연결 불변식에 따라 호출 부서(BusinessContext)별로 물리 컬럼 필터와 규정을 분리 매핑."
    }
  },
  {
    id: "S6",
    code: "SCEN_06_CROSS_SECTOR_CONTAGION",
    title: "타 업권 동명 조항(09 상호저축은행업감독규정 제38조) 혼입 및 거버넌스 오염 차단",
    dept: "준법감시인 · 시중은행 기업여신 규정 준수 감사 (BusinessContext: BANK_COMPLIANCE)",
    query: "시중은행(별빛은행) 기업여신 대손충당금 적립 시 '감독규정 제38조'의 상호저축은행 프로젝트파이낸싱(PF) 적립 기준을 적용해야 하는가?",
    targetSec: "저축은행감독규정 제38조",
    ledgerTables: "Knowledge Catalog Aspect: domain='savings_bank_distractor' vs 'commercial_bank'",
    ragResult: {
      verdict: "상호저축은행업감독규정 제38조를 시중은행 대손충당금 규정으로 오인·혼용",
      chunks: "09_FSC_상호저축은행업감독규정 제38조(대손충당금 등의 적립기준): '정상 0.5%, 고정 10%...'",
      failureReason: "벡터 임베딩 공간에서 '감독규정 대손충당금 적립기준'이라는 조문 제목이 동일하여, 시중은행(제29조)과 상호저축은행(제38조) 청크가 코사인 유사도 상위권에 동시 노출되며 LLM이 두 업권의 숫자를 뒤섞음."
    },
    graphRagResult: {
      verdict: "적용 차단 (CONFLICTS_CROSS_SECTOR 경고 및 은행업감독규정 제29조 강제 라우팅)",
      graphPath: "Knowledge Catalog Filter(tags!='distractors') + Edge(저축은행감독규정 제38조 ─[CONFLICTS_CROSS_SECTOR]─> 은행업감독규정 제29조)",
      resolution: "Dataplex Knowledge Catalog의 okf Aspect(tags: distractors)와 그래프의 CONFLICTS_CROSS_SECTOR 엣지가 타 업권 규정의 혼입을 사전 차단."
    }
  }
];

let BQ_CLASS_NODES = [
  // =========================================================================
  // UPPER PLATE: ONTOLOGY LAYER (정형 원장 8종 + 비즈니스 맥락 1종 = 9 Classes)
  // =========================================================================
  {
    id: "CLS_CONTEXT",
    label: "BusinessContext",
    ko: "부서·업무목적 맥락 (6건)",
    subRole: "CTX · 해석 분기 앵커",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 15,
    x: -255,
    z: -85,
    pk: "context_id",
    view: "starlight_bank_ontology.v_node_business_context",
    table: "starlight_bank_ontology.ctx_business_contexts (BigQuery Native · 6 rows)",
    desc: "동일 금융 용어(연체율·금리·실적) 호출 시 부서와 업무목적에 따라 적용 조문과 물리 컬럼을 분기하는 맥락 노드",
    anchor: {
      anchor_type: "ALIAS_INTENT_MAP",
      alias_group: "BUSINESS_CONTEXT",
      match_bind_key: "context_id",
      gql_match_template: "(ctx:BusinessContext {context_id: '$CANONICAL_ID'})",
      planner_instruction: "질문의 발화 부서·목적(리스크관리위원회, 금감원 공시, 여신관리팀 EWS, 기업여신심사부, 영업점, 준법감시부)을 ont_entity_aliases에서 정규화하여 시작 노드로 MATCH 하세요."
    },
    props: [
      { name: "context_id", type: "STRING (PK)", desc: "부서·업무목적 맥락 고유 식별자 (RISK_MGMT, DISCLOSURE, CREDIT_MGMT, CREDIT_REVIEW, BRANCH, COMPLIANCE)" },
      { name: "dept_name", type: "STRING", desc: "업무를 주관하는 은행 내 부서명 (리스크관리부, 재무기획부, 여신관리팀 등)" },
      { name: "purpose_summary", type: "STRING", desc: "해당 부서의 핵심 의사결정 및 보고 목적 한 줄 요약" },
      { name: "primary_metric_scope", type: "STRING", desc: "해당 맥락에서 주로 산출·점검하는 핵심 지표 및 심사 범위" }
    ],
    ddl: `starlight_bank_ontology.v_node_business_context
  KEY (context_id)
  LABEL BusinessContext
  PROPERTIES (context_id, dept_name, purpose_summary, primary_metric_scope)`
  },
  {
    id: "CLS_LOAN",
    label: "LoanContract",
    ko: "기업여신 계약 원장 허브 (100건)",
    subRole: "LDM · 단일 중심 허브 (Spanner OLTP)",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 19,
    x: -10,
    z: 0,
    pk: "contract_id",
    view: "starlight_bank_ontology.v_node_loan_contract",
    table: "starlight_bank_ext.ont_loan_contracts (Cloud Spanner Data Boost Federated · 100 rows)",
    desc: "Cloud Spanner Data Boost를 통해 실시간 연합 조회되는 기업여신 계약 원장이자 7개 정형 엔티티와 규정이 만나는 단일 중심 허브 노드",
    anchor: {
      anchor_type: "CENTRAL_HUB_ANCHOR",
      alias_group: "CONTRACT_ID",
      match_bind_key: "contract_id",
      gql_match_template: "(l:LoanContract {contract_id: '$CANONICAL_ID'})",
      planner_instruction: "Spanner Data Boost 실시간 여신 원장이자 그래프의 단일 중심 허브입니다. 차주·상품·담보·연체·워크아웃·금리인하·예외승인 및 규정이 모두 1-hop으로 연결됩니다."
    },
    props: [
      { name: "contract_id", type: "STRING (PK)", desc: "여신계약 고유 번호 (예: LN_2026_0001, LN_2026_KSIC_L1)" },
      { name: "customer_id", type: "STRING (FK)", desc: "차주 고객 고유 번호 (-> Customer.customer_id)" },
      { name: "product_code", type: "STRING (FK)", desc: "가입 여신상품 코드 (-> FinancialProduct.product_code)" },
      { name: "ksic_section_code", type: "STRING", desc: "한국표준산업분류 대분류 코드 (F 건설, G 도소매, H 숙박음식, L 부동산 등)" },
      { name: "contract_dt", type: "DATE", desc: "여신거래약정 체결일 (내규 제21조상 신규 영업실적 필수 기준일)" },
      { name: "base_rate / spread_rate / pref_rate / applied_rate", type: "FLOAT64", desc: "기준금리(A) + 가산금리(B) - 우대금리(C) = 최종 적용금리 (연 %)" },
      { name: "outstanding_amt / booked_provision_krw", type: "INT64", desc: "현재 여신 대출 잔액 및 장부 적립 대손충당금 금액 (원)" },
      { name: "overdue_days", type: "INT64", desc: "현재 원리금 연체 일수 (일)" },
      { name: "asset_classification", type: "STRING", desc: "자산건전성 5단계 분류 (NORMAL, PRECAUTIONARY, SUBSTANDARD, DOUBTFUL, ESTIMATED_LOSS)" },
      { name: "rehab_priority_claim_yn", type: "STRING", desc: "회생법 제180조②·기촉법상 은행 우선변제권 인정 자산 여부 (Y/N)" },
      { name: "account_status", type: "STRING", desc: "계좌 원장 상태 (ACTIVE 정상운용 vs WRITTEN_OFF_SPECIAL_CLAIM 대손상각 특수채권)" }
    ],
    ddl: `starlight_bank_ontology.v_node_loan_contract
  KEY (contract_id)
  LABEL LoanContract
  PROPERTIES (
    contract_id, customer_id, product_code, borrower_name, ksic_section_code,
    reg_dt, contract_dt, disburse_dt, base_rate, spread_rate, pref_rate, applied_rate,
    contract_amt, outstanding_amt, overdue_days, asset_classification,
    rehab_priority_claim_yn, booked_provision_krw, account_status
  )`
  },
  {
    id: "CLS_CUSTOMER",
    label: "Customer",
    ko: "기업 차주 마스터 (100건)",
    subRole: "LDM · BigQuery Master",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: -175,
    z: 5,
    pk: "customer_id",
    view: "starlight_bank_ontology.v_node_customer",
    table: "starlight_bank.customers (BigQuery Native · 100 rows)",
    desc: "기업 차주의 산업분류(KSIC)·신용등급·기술등급·부채비율을 관리하는 BigQuery 마스터 노드",
    anchor: {
      anchor_type: "ALIAS_TABLE_LOOKUP",
      alias_group: "CUSTOMER_NAME",
      match_bind_key: "customer_id",
      gql_match_template: "(c:Customer {customer_id: '$CANONICAL_ID'})",
      planner_instruction: "질문 속 기업명 약칭('별빛정밀'->CUST_0001, '에이펙스세미콘'->CUST_0008 등)을 ont_entity_aliases에서 최장일치(Longest-Match-First)로 조회해 customer_id로 바인딩하세요."
    },
    props: [
      { name: "customer_id", type: "STRING (PK)", desc: "기업 차주 고유 식별자 (CUST_0001 ~ CUST_0100)" },
      { name: "borrower_name", type: "STRING", desc: "차주 공식 법인명 (예: 별빛정밀(주), 에이펙스세미콘(주))" },
      { name: "ksic_section_code", type: "STRING", desc: "한국표준산업분류 대분류 코드 (감독규정 제29조 단서 F·G·H·L 판정 기준)" },
      { name: "credit_rating / tcb_tech_grade", type: "STRING", desc: "내부 기업신용등급(BBB+ 등) 및 기술신용평가(TCB) 등급" },
      { name: "debt_ratio_pct", type: "FLOAT64", desc: "차주 최근 결산 부채비율 (%, 내규 제25조 신속심사 상한 250.0% 기준)" }
    ],
    ddl: `starlight_bank_ontology.v_node_customer
  KEY (customer_id)
  LABEL Customer
  PROPERTIES (
    customer_id, borrower_name, corp_reg_no, ksic_section_code,
    ksic_detail_code, industry_name, credit_rating, tcb_tech_grade, debt_ratio_pct
  )`
  },
  {
    id: "CLS_PRODUCT",
    label: "FinancialProduct",
    ko: "여신 금융상품 마스터 (4건)",
    subRole: "LDM · BigQuery Master",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: -155,
    z: 95,
    pk: "product_code",
    view: "starlight_bank_ontology.v_node_financial_product",
    table: "starlight_bank.financial_products (BigQuery Native · 4 rows)",
    desc: "대출 상품의 여신유형(기업여신 여부)·타깃 세그먼트·기준금리 벤치마크를 정의하는 상품 마스터 노드",
    anchor: {
      anchor_type: "ALIAS_TABLE_LOOKUP",
      alias_group: "PRODUCT_NAME",
      match_bind_key: "product_code",
      gql_match_template: "(p:FinancialProduct {product_code: '$CANONICAL_ID'})",
      planner_instruction: "상품 약칭('TCB 기술혁신 운전자금'->PROD_TCB_WORKING, '프라임 중견기업 운전자금'->PROD_CORP_PRIME_WC)을 ont_entity_aliases에서 조회해 바인딩하세요."
    },
    props: [
      { name: "product_code", type: "STRING (PK)", desc: "여신 금융상품 코드 (PROD_TCB_WORKING, PROD_CORP_PRIME_WC 등 4종)" },
      { name: "product_name", type: "STRING", desc: "여신 금융상품 한글 명칭" },
      { name: "loan_category", type: "STRING", desc: "여신 대분류 코드 (CORPORATE_* 기업여신 확인 및 가계여신 규정 배제 기준)" },
      { name: "base_rate_benchmark", type: "STRING", desc: "연동 기준금리 지표 (KORIBOR_3M, FINANCIAL_BOND_6M 등)" }
    ],
    ddl: `starlight_bank_ontology.v_node_financial_product
  KEY (product_code)
  LABEL FinancialProduct
  PROPERTIES (
    product_code, product_name, loan_category, target_segment,
    base_rate_benchmark, repayment_method, max_maturity_months
  )`
  },
  {
    id: "CLS_WORKOUT",
    label: "WorkoutHistory",
    ko: "채권재조정·워크아웃 이력 (3건)",
    subRole: "LDM · BigQuery History",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 115,
    z: -95,
    pk: "workout_id",
    view: "starlight_bank_ontology.v_node_workout_history",
    table: "starlight_bank.workout_histories (BigQuery Native · 3 rows)",
    desc: "채권재조정 여신의 연속 정상상환 개월 수·유상증자 금액·법적 구조조정 절차를 관리하는 이력 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "LEGAL_PROCEEDING_CODE",
      match_bind_key: "workout_id",
      gql_match_template: "(w:WorkoutHistory)",
      planner_instruction: "LoanContract에서 HAS_WORKOUT_HISTORY 엣지를 타고 탐색하여 6개월 연속 상환 및 유상증자 여부를 확인하세요."
    },
    props: [
      { name: "workout_id", type: "STRING (PK)", desc: "워크아웃·채권재조정 이력 고유 번호" },
      { name: "contract_id", type: "STRING (FK)", desc: "대상 여신계약 번호 (-> LoanContract.contract_id)" },
      { name: "consecutive_normal_repay_months", type: "INT64", desc: "채권재조정 후 연속 정상 상환 개월 수 (별표3 라목 6개월 이상 기준)" },
      { name: "new_equity_paid_in_krw", type: "INT64", desc: "유상증자·출자전환 납입 금액 (원, 별표3 라목 상환능력 개선 기준)" },
      { name: "legal_proceeding_code", type: "STRING", desc: "근거 법적 절차 코드 (CORP_RESTRUCT_ACT_WORKOUT, REHAB_ACT_ART180_2_DIP)" }
    ],
    ddl: `starlight_bank_ontology.v_node_workout_history
  KEY (workout_id)
  LABEL WorkoutHistory
  PROPERTIES (
    workout_id, contract_id, customer_id, workout_start_dt,
    consecutive_normal_repay_months, new_equity_paid_in_krw, legal_proceeding_code
  )`
  },
  {
    id: "CLS_COLLATERAL",
    label: "Collateral",
    ko: "담보·신보 보증서 원장 (3건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 235,
    z: -45,
    pk: "collateral_id",
    view: "starlight_bank_ontology.v_node_collateral",
    table: "starlight_bank_ext.ont_collaterals (Cloud Spanner Data Boost Federated · 3 rows)",
    desc: "여신계약에 설정된 신용보증기금(KODIT) 보증서·부동산 담보 유형과 보증비율(85% 기준 등)을 담는 Spanner Data Boost 원장 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "GUARANTEE_AGENCY_CODE",
      match_bind_key: "collateral_id",
      gql_match_template: "(col:Collateral)",
      planner_instruction: "LoanContract에서 HAS_COLLATERAL 엣지로 탐색하세요. '신보'는 guarantee_agency_code='KODIT'으로 매핑됩니다."
    },
    props: [
      { name: "collateral_id", type: "STRING (PK)", desc: "담보·보증서 고유 식별 번호" },
      { name: "contract_id", type: "STRING (FK)", desc: "피담보 여신계약 번호 (-> LoanContract.contract_id)" },
      { name: "collateral_type_code", type: "STRING", desc: "담보 유형 코드 (CREDIT_GUARANTEE_CERT 신용보증서 vs REAL_ESTATE_MORTGAGE 부동산담보)" },
      { name: "guarantee_agency_code", type: "STRING", desc: "보증서 발급 기관 코드 (KODIT 신용보증기금 등)" },
      { name: "guarantee_ratio_pct", type: "FLOAT64", desc: "보증기관 책임 보증비율 (%, 내규 제18조 85% 이상 요건 기준)" }
    ],
    ddl: `starlight_bank_ontology.v_node_collateral
  KEY (collateral_id)
  LABEL Collateral
  PROPERTIES (
    collateral_id, contract_id, customer_id, collateral_type_code,
    guarantee_agency_code, guarantee_ratio_pct, appraised_collateral_krw
  )`
  },
  {
    id: "CLS_DELINQ",
    label: "DelinquencyEvent",
    ko: "연체·상각특수채권 원장 (7건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 240,
    z: 45,
    pk: "event_id",
    view: "starlight_bank_ontology.v_node_delinquency_event",
    table: "starlight_bank_ext.ont_delinquency_events (Cloud Spanner Data Boost Federated · 7 rows)",
    desc: "여신계좌별 연체일수·연체원리금·대손상각 특수채권 편입 여부를 기록하는 Spanner Data Boost 이벤트 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "NONE",
      match_bind_key: "event_id",
      gql_match_template: "(del:DelinquencyEvent)",
      planner_instruction: "LoanContract에서 HAS_DELINQUENCY 엣지로 탐색하세요. 공시 연체율은 write_off_yn='N' & overdue_days>=30, EWS 실질연체율은 write_off_yn='Y' 포함 및 overdue_days>=10입니다."
    },
    props: [
      { name: "event_id", type: "STRING (PK)", desc: "연체·상각 이벤트 고유 번호" },
      { name: "contract_id", type: "STRING (FK)", desc: "연체 발생 여신계약 번호 (-> LoanContract.contract_id)" },
      { name: "overdue_days", type: "INT64", desc: "연체 경과 일수 (10일+ EWS, 30일+ 공시연체, 90일+ 고정이하)" },
      { name: "overdue_principal_krw", type: "INT64", desc: "연체 원금 또는 대손상각 특수채권 미회수 원금 잔액 (원)" },
      { name: "write_off_yn", type: "STRING", desc: "회계상 대손상각 특수채권 편입 여부 (Y: 공시 제외·EWS 포함 / N: on-BS)" }
    ],
    ddl: `starlight_bank_ontology.v_node_delinquency_event
  KEY (event_id)
  LABEL DelinquencyEvent
  PROPERTIES (
    event_id, contract_id, customer_id, overdue_days,
    overdue_principal_krw, overdue_interest_krw, write_off_yn
  )`
  },
  {
    id: "CLS_RATECUT",
    label: "RateCutRequest",
    ko: "금리인하요구 신청 원장 (2건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: 135,
    z: 95,
    pk: "request_id",
    view: "starlight_bank_ontology.v_node_rate_cut_request",
    table: "starlight_bank_ext.ont_rate_cut_requests (Cloud Spanner Data Boost Federated · 2 rows)",
    desc: "차주의 금리인하요구 신청 사유(특허 취득 등)·신용등급 변동·심사 결과(승인/거절)를 기록하는 Spanner Data Boost 노드",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "RATE_CUT_REASON",
      match_bind_key: "request_id",
      gql_match_template: "(rc:RateCutRequest)",
      planner_instruction: "LoanContract에서 HAS_RATE_CUT_REQUEST 엣지로 탐색하고 EVALUATED_UNDER_PROVISION으로 내규 제25조② 및 모범규준과 대조하세요."
    },
    props: [
      { name: "request_id", type: "STRING (PK)", desc: "금리인하요구권 신청 고유 번호 (RCR_2026_01, RCR_2026_02)" },
      { name: "contract_id", type: "STRING (FK)", desc: "신청 대상 여신계약 번호 (-> LoanContract.contract_id)" },
      { name: "application_reason_code", type: "STRING", desc: "신청 사유 코드 (PATENT_ACQUISITION 등)" },
      { name: "credit_rating_before / after", type: "STRING", desc: "신청 전·후 내부 신용등급 (BBB->BBB 불변 vs BBB->BBB+ 상승)" },
      { name: "review_status_code / approved_cut_bp", type: "STRING / INT64", desc: "심사 결과(APPROVED/REJECTED) 및 인하 폭(35bp vs 0bp)" }
    ],
    ddl: `starlight_bank_ontology.v_node_rate_cut_request
  KEY (request_id)
  LABEL RateCutRequest
  PROPERTIES (
    request_id, contract_id, customer_id, request_dt, application_reason_code,
    patent_reg_no, credit_rating_before, credit_rating_after,
    yoy_revenue_growth_pct, review_status_code, approved_cut_bp
  )`
  },
  {
    id: "CLS_APPROVAL",
    label: "ExceptionApproval",
    ko: "여신 예외승인 결재 원장 (3건)",
    subRole: "LDM · Spanner OLTP",
    layer: "ONT",
    color: 0x3b6ea5,
    radius: 14,
    x: -15,
    z: 100,
    pk: "approval_id",
    view: "starlight_bank_ontology.v_node_exception_approval",
    table: "starlight_bank_ext.ont_exception_approvals (Cloud Spanner Data Boost Federated · 3 rows)",
    desc: "기한이익상실(EOD) 유예 및 채권재조정 건전성 예외분류에 대한 본부 여신심사역 결재·문서화 증적 노드 (Spanner Data Boost)",
    anchor: {
      anchor_type: "TRAVERSAL_ONLY",
      alias_group: "NONE",
      match_bind_key: "approval_id",
      gql_match_template: "(ea:ExceptionApproval)",
      planner_instruction: "LoanContract에서 HAS_EXCEPTION_APPROVAL 엣지로 탐색하여 본부 여신심사역(HQ_SENIOR_CREDIT_OFFICER)의 승인(APPROVED) 및 문서화 여부를 확인하세요."
    },
    props: [
      { name: "approval_id", type: "STRING (PK)", desc: "예외승인 결재 건 고유 번호" },
      { name: "contract_id", type: "STRING (FK)", desc: "결재 대상 여신계약 번호 (-> LoanContract.contract_id)" },
      { name: "approval_type_code", type: "STRING", desc: "예외 결재 유형 코드 (EOD_DEFERRAL_REVIEW 등)" },
      { name: "approval_status", type: "STRING", desc: "결재 최종 상태 (APPROVED 승인완료 vs REJECTED 반려)" },
      { name: "approver_role_code / approval_dt", type: "STRING / DATE", desc: "승인권자 직책(HQ_SENIOR_CREDIT_OFFICER) 및 문서화 일자" }
    ],
    ddl: `starlight_bank_ontology.v_node_exception_approval
  KEY (approval_id)
  LABEL ExceptionApproval
  PROPERTIES (
    approval_id, contract_id, customer_id, approval_type_code,
    approval_status, approver_role_code, approval_dt
  )`
  },

  // =========================================================================
  // LOWER PLATE: LEX LAYER (비정형 OKF 문서 루트 1종 + 조문 1종 = 2 Classes)
  // =========================================================================
  {
    id: "CLS_SRCDOC",
    label: "SourceDocument",
    ko: "법령·감독규정·내규 문서 루트 (10건)",
    subRole: "LEX · OKF Document Root (ObjectRef)",
    layer: "LEX",
    color: 0x477a63,
    radius: 15,
    x: -175,
    z: 10,
    pk: "doc_id",
    view: "starlight_bank_ontology.v_node_source_document",
    table: "starlight_bank_ontology.lex_source_documents (10 OKF doc.md + BigQuery ObjectRef + KC 1:1)",
    desc: "은행업감독규정·모범규준·당행내규·타업권 규정 등 10종 원본 문서의 법적 구속력과 BigQuery 네이티브 ObjectRef(gcs_obj_ref)를 제공하는 루트 노드",
    anchor: {
      anchor_type: "KC_GOVERNED_LEX_ROOT",
      alias_group: "SOURCE_DOCUMENT",
      match_bind_key: "doc_id",
      gql_match_template: "(doc:SourceDocument {doc_id: '$CANONICAL_ID'})",
      planner_instruction: "10개 원본 문서 루트입니다. authority_level 및 applicable_sector로 타업권 규정을 필터링하고, gcs_obj_ref에 대해 OBJ.FETCH_METADATA / OBJ.GET_ACCESS_URL을 호출해 GCS 원문 doc.md를 직접 인출하세요."
    },
    props: [
      { name: "doc_id", type: "STRING (PK)", desc: "원본 법령·내규 문서 고유 식별자 (FSC_BANK_SUPERVISION_REG 등 10종)" },
      { name: "title", type: "STRING", desc: "법령·감독규정·브리프·내규 문서의 공식 명칭" },
      { name: "authority_level", type: "STRING", desc: "법적 구속력 구분 (binding 법규 / internal 당행내규 / advisory 자문 / distractor 교란)" },
      { name: "applicable_sector", type: "STRING", desc: "적용 대상 금융업권 (COMMERCIAL_BANK 시중은행 vs SAVINGS_BANK 상호저축은행)" },
      { name: "kc_entry_id / gcs_uri", type: "STRING", desc: "Dataplex Knowledge Catalog Entry ID 및 gs://okf/*/doc.md URI" },
      { name: "gcs_obj_ref", type: "STRUCT<uri, version, authorizer, details JSON> (ObjectRef)", desc: "OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn')로 생성된 BigQuery 네이티브 ObjectRef — OBJ.FETCH_METADATA 및 OBJ.GET_ACCESS_URL로 GCS 실시간 서명 읽기 수행" }
    ],
    ddl: `starlight_bank_ontology.v_node_source_document
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
    ko: "조문·별표·단서·내규 조항 (174건)",
    subRole: "LEX · 의사결정 기준 허브 (ObjectRef + KC Governed)",
    layer: "LEX",
    color: 0x3b735b,
    radius: 19,
    x: 45,
    z: 0,
    pk: "provision_slot_id",
    view: "starlight_bank_ontology.v_node_provision",
    table: "starlight_bank_ontology.lex_provisions (174 OKF Provisions + BigQuery ObjectRef + KC Aspect SSOT)",
    desc: "174개 개별 조문·별표·단서 조항 노드로, BigQuery 네이티브 ObjectRef(gcs_obj_ref)를 통해 GCS 마크다운 원문을 실시간 서명 URL로 인출하며 거버넌스 상태는 KC Aspect에서만 검증함",
    anchor: {
      anchor_type: "KC_GOVERNED_LEX_NODE",
      alias_group: "PROVISION_SYNONYM",
      match_bind_key: "provision_slot_id",
      gql_match_template: "(pr:Provision {provision_slot_id: '$CANONICAL_ID'})",
      planner_instruction: "도달 시 kc_entry_id로 Dataplex KC Aspect(status/superseded_by)를 검증하고, pr.gcs_obj_ref에 대해 OBJ.FETCH_METADATA(pr.gcs_obj_ref) 및 OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r')를 실행해 GCS OKF 마크다운 원문을 직접 읽으세요."
    },
    props: [
      { name: "provision_slot_id", type: "STRING (PK)", desc: "버전이 바뀌어도 유지되는 불변 조문 슬롯 식별자 (canonical_id)" },
      { name: "doc_id", type: "STRING (FK)", desc: "소속 원본 문서 식별자 (-> SourceDocument.doc_id)" },
      { name: "kc_entry_id", type: "STRING", desc: "Dataplex Knowledge Catalog에서 실시간 유효성(status) 및 대체문서(superseded_by)를 조회할 기준 Entry ID" },
      { name: "article_no / title", type: "STRING", desc: "조문 번호(예: 제29조, 별표3 제3호 라목, 내규 제25조) 및 제목" },
      { name: "provision_role", type: "STRING", desc: "기능적 역할 (BASE_CRITERIA 본칙 / EXCEPTION_PROVISO 단서·특례 / INTERNAL_RULE 당행내규 / DISTRACTOR_RULE 교란)" },
      { name: "target_columns", type: "STRING", desc: "조문 적용 시 조회해야 하는 정형 원장 테이블.컬럼 목록" },
      { name: "missing_schema_columns", type: "STRING", desc: "규정상 필요하나 현재 DW에 없는 데이터 공백 컬럼 (예: tier1_capital)" },
      { name: "gcs_uri", type: "STRING", desc: "GCS에 저장된 조문 마크다운 원문 URI (gs://okf/...)" },
      { name: "gcs_obj_ref", type: "STRUCT<uri, version, authorizer, details JSON> (ObjectRef)", desc: "OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn')로 생성된 BigQuery 네이티브 ObjectRef — OBJ.FETCH_METADATA 및 OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')로 GCS 마크다운 실시간 조회" }
    ],
    ddl: `starlight_bank_ontology.v_node_provision
  KEY (provision_slot_id)
  LABEL Provision
  PROPERTIES (
    provision_slot_id, doc_id, kc_entry_id, article_no, title,
    provision_role, target_columns, missing_schema_columns, gcs_uri,
    OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
  )`
  }
];

let BQ_CLASS_EDGES = [
  // 1. ONTOLOGY Layer Edges on Upper Plate (8종 — BusinessContext -> LoanContract 포트폴리오 스코프 1종 + LoanContract 중심 허브 방사 7종)
  { source: "CLS_CONTEXT", target: "CLS_LOAN", rel: "SCOPES_PORTFOLIO", isBridge: false, color: 0x6b88a8, view: "v_edge_scopes_portfolio", desc: "부서·업무목적 맥락(BusinessContext)이 관할하는 실시간 여신계약(LoanContract) 포트폴리오 스코프 연결 (on-BS 99계좌 vs EWS 상각포함 100계좌)" },
  { source: "CLS_LOAN", target: "CLS_CUSTOMER", rel: "BORROWED_BY", isBridge: false, color: 0x6b88a8, view: "v_edge_borrowed_by", desc: "여신계약이 어느 기업 차주에게 실행되었는지 연결 (N:1)" },
  { source: "CLS_LOAN", target: "CLS_PRODUCT", rel: "OF_PRODUCT", isBridge: false, color: 0x6b88a8, view: "v_edge_of_product", desc: "여신계약이 어느 여신 금융상품으로 체결되었는지 연결 (N:1)" },
  { source: "CLS_LOAN", target: "CLS_WORKOUT", rel: "HAS_WORKOUT_HISTORY", isBridge: false, color: 0x6b88a8, view: "v_edge_has_workout_history", desc: "여신계약의 채권재조정·워크아웃·회생 상환 및 증자 이력 연결 (1:N)" },
  { source: "CLS_LOAN", target: "CLS_COLLATERAL", rel: "HAS_COLLATERAL", isBridge: false, color: 0x6b88a8, view: "v_edge_has_collateral", desc: "여신계약에 설정된 담보 및 신용보증기금(KODIT) 보증서 연결 (1:N)" },
  { source: "CLS_LOAN", target: "CLS_DELINQ", rel: "HAS_DELINQUENCY", isBridge: false, color: 0x6b88a8, view: "v_edge_has_delinquency", desc: "여신계약에서 발생한 연체 및 대손상각 특수채권 이벤트 연결 (1:N)" },
  { source: "CLS_LOAN", target: "CLS_RATECUT", rel: "HAS_RATE_CUT_REQUEST", isBridge: false, color: 0x6b88a8, view: "v_edge_has_rate_cut_request", desc: "여신계약에 대해 접수된 금리인하요구권 신청·심사 내역 연결 (1:N)" },
  { source: "CLS_LOAN", target: "CLS_APPROVAL", rel: "HAS_EXCEPTION_APPROVAL", isBridge: false, color: 0x6b88a8, view: "v_edge_has_exception_approval", desc: "여신계약의 기한이익상실(EOD) 유예 등 본부 예외승인 결재 내역 연결 (1:N)" },

  // 2. Vertical Bridge Edges between ONTOLOGY Layer & LEX Layer (3종)
  { source: "CLS_CONTEXT", target: "CLS_PROVISION", rel: "INVOKES_PROVISION", isBridge: true, color: 0xb88a44, view: "v_edge_invokes_provision", desc: "부서 맥락(BusinessContext)과 Dataplex Glossary 용어(term_key) 조합에 따라 호출 조문을 분기하는 브리지 엣지 (M:N)" },
  { source: "CLS_LOAN", target: "CLS_PROVISION", rel: "GOVERNED_BY_CRITERIA", isBridge: true, color: 0xb88a44, view: "v_edge_governed_by_criteria", desc: "실시간 Spanner 여신계약의 구조적 범위(기업여신·연체·워크아웃)에 따라 심사 관할 조문을 동적 연결하는 순수 SQL View 엣지 (정답 미유출)" },
  { source: "CLS_RATECUT", target: "CLS_PROVISION", rel: "EVALUATED_UNDER_PROVISION", isBridge: true, color: 0xb88a44, view: "v_edge_evaluated_under_provision", desc: "실시간 Spanner 금리인하요구 신청 건을 심사 관할 모범규준 및 당행 내규 조문과 동적 연결하는 순수 SQL View 엣지" },

  // 3. LEX Layer Edges on Lower Plate (4종 — 문서 귀속 1종 + Provision 자기참조 루프 3종)
  { source: "CLS_PROVISION", target: "CLS_SRCDOC", rel: "PART_OF_DOCUMENT", isBridge: false, color: 0x5a8770, view: "v_edge_part_of_document", desc: "174개 개별 조문이 어느 원본 법령·내규 문서(10종)에 속하는지 연결 (N:1)" },
  { source: "CLS_PROVISION", target: "CLS_PROVISION", rel: "HAS_EXCEPTION_PROVISO", isBridge: false, isSelfLoop: true, loopIdx: 0, color: 0xa85c56, view: "v_edge_has_exception_proviso", desc: "원칙 조문(본칙)에서 단서·예외·특례 조문으로 분기하는 법령 내부 엣지 (M:N)" },
  { source: "CLS_PROVISION", target: "CLS_PROVISION", rel: "DELEGATES_TO_INTERNAL", isBridge: false, isSelfLoop: true, loopIdx: 1, color: 0x5a8770, view: "v_edge_delegates_to_internal", desc: "상위 감독규정·모범규준이 별빛은행 자체 내규 조문으로 세부 기준을 위임·구체화하는 엣지 (M:N)" },
  { source: "CLS_PROVISION", target: "CLS_PROVISION", rel: "CONFLICTS_BY_SECTOR", isBridge: false, isSelfLoop: true, loopIdx: 2, color: 0xb88a44, view: "v_edge_conflicts_by_sector", desc: "시중은행 기업여신 규정과 상호저축은행(타업권)·가계여신 규정 간의 오적용 방지 대조 엣지 (M:N)" }
];

const BQ_LEDGER_INSTANCES = [];

let BQ_GQL_PRESETS = [
  // =========================================================================
  // CASE 1: CQ01 (Theme A/E · Multi-Hop 단서 & 타업권 교란 차단)
  // =========================================================================
  {
    cqId: "CQ01",
    theme: "Theme A · 건전성 분류 · 대손충당금 최소적립 (Multi-Hop 단서)",
    title: "CQ01 · 대손충당금 적립기준 및 F·G·H·L 단서 조회",
    question: "이번 분기 결산에서 '정상' 여신에 대해 대손준비금을 추가로 쌓아야 해? 쌓아야 하면 얼마고, 어느 계좌 때문이야?",
    contextBadge: "BusinessContext: RISK_MGMT (리스크관리부) · Glossary term_key: 'provision-criteria'",
    verdict: "대손준비금 3,000만 원 추가 적립 필요 (F·G·H·L 경기민감 4계좌 장부 0.85% 적립 → 단서 0.90% 대비 부족)",
    answerDetail: "정상 여신 96건 중 92건은 본칙 0.85%로 충족하나, 제29조①1호가목 단서 대상인 한국표준산업분류 F(건설)·G(도소매)·H(숙박음식)·L(부동산) 4개 차주(대양피에프개발 L 200억, 삼호종합건설 F 150억, 한일유통상사 G 150억, 그랜드하모니호텔 H 100억)가 장부상 0.85%로만 적립돼 있어 0.90% 하한 대비 각 1,000만 / 750만 / 750만 / 500만 원(합계 3,000만 원) 부족합니다. 상호저축은행 제38조(0.5%)는 CONFLICTS_BY_SECTOR로 차단됩니다.",
    gql: `GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'RISK_MGMT'})
      -[inv:INVOKES_PROVISION {term_key: 'provision-criteria'}]->(pr:Provision {article_no: '제29조'})
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract {asset_classification: 'NORMAL'})
      -[:GOVERNED_BY_CRITERIA]->(pr),
      (l)-[:BORROWED_BY]->(c:Customer),
      (l)-[:OF_PRODUCT]->(fp:FinancialProduct)
OPTIONAL MATCH (pr)-[:CONFLICTS_BY_SECTOR]->(dist:Provision)
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
  AND c.ksic_section_code IN ('F', 'G', 'H', 'L')
RETURN ctx, inv.term_key, pr, OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r') AS pr_obj_url, dist, doc, l, c, fp`,
    nodes: [
      { id: "CTX::RISK_MGMT", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nRISK_MGMT (리스크관리부)", title: "starlight_bank_ontology.v_node_business_context · RISK_MGMT", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "RISK_MGMT", dept_name: "리스크관리부", term_key: "provision-criteria (대손충당금·대손준비금 적립기준)", purpose_summary: "자산건전성 5단계 분류 및 대손충당금·대손준비금 최소적립 점검" }, verdictNote: "Glossary term_key='provision-criteria'를 통해 은행업감독규정 제29조를 호출하고 SCOPES_PORTFOLIO로 대차대조표 내 기업여신을 스코핑합니다." },
      { id: "LOAN::LN_2026_KSIC_L1", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\nLN_2026_KSIC_L1\n(정상 200억 · 부족 1,000만)", title: "v_node_loan_contract · LN_2026_KSIC_L1 (대양피에프개발)", color: "#3b6ea5", shape: "dot", size: 21, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_KSIC_L1", customer_id: "CUST_0004", borrower_name: "대양피에프개발(주)", ksic_section_code: "L (부동산업)", asset_classification: "NORMAL", outstanding_amt: 20000000000, booked_provision_krw: 170000000, required_090_krw: 180000000, reserve_gap_krw: 10000000 }, verdictNote: "장부 0.85%(1.7억) 적립 → L업종 단서 0.90%(1.8억) 대비 1,000만 원 대손준비금 추가 적립 대상" },
      { id: "LOAN::LN_2026_KSIC_F1", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\nLN_2026_KSIC_F1\n(정상 150억 · 부족 750만)", title: "v_node_loan_contract · LN_2026_KSIC_F1 (삼호종합건설)", color: "#3b6ea5", shape: "dot", size: 20, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_KSIC_F1", customer_id: "CUST_0005", borrower_name: "삼호종합건설(주)", ksic_section_code: "F (건설업)", asset_classification: "NORMAL", outstanding_amt: 15000000000, booked_provision_krw: 127500000, required_090_krw: 135000000, reserve_gap_krw: 7500000 }, verdictNote: "장부 0.85%(1.275억) 적립 → F업종 단서 0.90%(1.35억) 대비 750만 원 부족" },
      { id: "LOAN::LN_2026_KSIC_G1", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\nLN_2026_KSIC_G1\n(정상 150억 · 부족 750만)", title: "v_node_loan_contract · LN_2026_KSIC_G1 (한일유통상사)", color: "#3b6ea5", shape: "dot", size: 20, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_KSIC_G1", customer_id: "CUST_0015", borrower_name: "한일유통상사(주)", ksic_section_code: "G (도소매업)", asset_classification: "NORMAL", outstanding_amt: 15000000000, booked_provision_krw: 127500000, required_090_krw: 135000000, reserve_gap_krw: 7500000 }, verdictNote: "장부 0.85%(1.275억) 적립 → G업종 단서 0.90%(1.35억) 대비 750만 원 부족" },
      { id: "LOAN::LN_2026_KSIC_H1", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\nLN_2026_KSIC_H1\n(정상 100억 · 부족 500만)", title: "v_node_loan_contract · LN_2026_KSIC_H1 (그랜드하모니호텔)", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_KSIC_H1", customer_id: "CUST_0016", borrower_name: "그랜드하모니호텔(주)", ksic_section_code: "H (숙박및음식점업)", asset_classification: "NORMAL", outstanding_amt: 10000000000, booked_provision_krw: 85000000, required_090_krw: 90000000, reserve_gap_krw: 5000000 }, verdictNote: "장부 0.85%(8,500만) 적립 → H업종 단서 0.90%(9,000만) 대비 500만 원 부족" },
      { id: "CUST::CUST_0004", classLabel: "Customer", layer: "ONT", label: "[Customer]\nCUST_0004 대양피에프개발\n(ksic='L' 부동산업)", title: "v_node_customer · CUST_0004", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_customer", sourceStore: "BigQuery Master (customers)", record: { customer_id: "CUST_0004", borrower_name: "대양피에프개발(주)", ksic_section_code: "L", industry_name: "부동산 및 임대업", credit_rating: "BBB+" }, verdictNote: "KSIC 대분류 'L' → 제29조①1호가목 0.90% 단서 발동" },
      { id: "CUST::CUST_0005", classLabel: "Customer", layer: "ONT", label: "[Customer]\nCUST_0005 삼호종합건설\n(ksic='F' 건설업)", title: "v_node_customer · CUST_0005", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_customer", sourceStore: "BigQuery Master (customers)", record: { customer_id: "CUST_0005", borrower_name: "삼호종합건설(주)", ksic_section_code: "F", industry_name: "종합 건설업", credit_rating: "A-" }, verdictNote: "KSIC 대분류 'F' → 제29조①1호가목 0.90% 단서 발동" },
      { id: "CUST::CUST_0015", classLabel: "Customer", layer: "ONT", label: "[Customer]\nCUST_0015 한일유통상사\n(ksic='G' 도소매업)", title: "v_node_customer · CUST_0015", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_customer", sourceStore: "BigQuery Master (customers)", record: { customer_id: "CUST_0015", borrower_name: "한일유통상사(주)", ksic_section_code: "G", industry_name: "도매 및 소매업", credit_rating: "BBB+" }, verdictNote: "KSIC 대분류 'G' → 제29조①1호가목 0.90% 단서 발동" },
      { id: "CUST::CUST_0016", classLabel: "Customer", layer: "ONT", label: "[Customer]\nCUST_0016 그랜드하모니호텔\n(ksic='H' 숙박음식업)", title: "v_node_customer · CUST_0016", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_customer", sourceStore: "BigQuery Master (customers)", record: { customer_id: "CUST_0016", borrower_name: "그랜드하모니호텔(주)", ksic_section_code: "H", industry_name: "숙박 및 음식점업", credit_rating: "BBB" }, verdictNote: "KSIC 대분류 'H' → 제29조①1호가목 0.90% 단서 발동" },
      { id: "PROD::PROD_CORP_PRIME_WC", classLabel: "FinancialProduct", layer: "ONT", label: "[FinancialProduct]\nPROD_CORP_PRIME_WC\n(loan_category: CORPORATE_*)", title: "v_node_financial_product · PROD_CORP_PRIME_WC", color: "#527a9a", shape: "dot", size: 15, viewName: "v_node_financial_product", sourceStore: "BigQuery Master (financial_products)", record: { product_code: "PROD_CORP_PRIME_WC", product_name: "별빛 프라임 중견기업 운전자금", loan_category: "CORPORATE_WORKING_CAPITAL", base_rate_benchmark: "FINANCIAL_BOND_6M" }, verdictNote: "기업여신(CORPORATE_*) 확인 → 가계자금대출(제29조①2호 정상 1.0%) 배제" },
      { id: "PROV::제29조", classLabel: "Provision", layer: "LEX", label: "[Provision · 제29조]\n대손충당금 등 적립기준\n(정상 0.85% / F·G·H·L 단서 0.90%)", title: "v_node_provision · 제29조 (은행업감독규정)", color: "#3b735b", shape: "box", matchSec: "제29조", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029", article_no: "제29조", provision_role: "BASE_CRITERIA", target_columns: "ont_loan_contracts.asset_classification,ont_loan_contracts.outstanding_amt,ont_loan_contracts.booked_provision_krw,customers.ksic_section_code,financial_products.loan_category", gcs_uri: "gs://okf/regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029.md" }, verdictNote: "제29조① 본문(결산 시 부족분 대손준비금 적립) + 제1호가목 단서(F·G·H·L 0.90% 이상)" },
      { id: "PROV::저축은행제38조", classLabel: "Provision", layer: "LEX", label: "[Provision · 교란차단]\n저축은행감독규정 제38조\n(타업권 정상 0.5% · 적용차단)", title: "v_node_provision · 저축은행감독규정 제38조 (DISTRACTOR_RULE)", color: "#a85c56", shape: "box", matchSec: "저축은행감독규정 제38조", viewName: "v_node_provision", sourceStore: "LEX Layer (Blocked by CONFLICTS_BY_SECTOR & KC authority='distractor')", record: { provision_slot_id: "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge", article_no: "저축은행감독규정 제38조", provision_role: "DISTRACTOR_RULE", applicable_sector: "SAVINGS_BANK" }, verdictNote: "상호저축은행(79개사) 대상 규정으로 CONFLICTS_BY_SECTOR 엣지 및 SourceDocument.applicable_sector로 혼입 차단" },
      { id: "DOC::DOC_01", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_01_FSC_BANK_REG\n01 은행업감독규정 전문\n(binding · COMMERCIAL_BANK)", title: "v_node_source_document · DOC_01_FSC_BANK_REG", color: "#477a63", shape: "box", matchDocId: "DOC_01_FSC_BANK_REG", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_01_FSC_BANK_REG", title: "은행업감독규정 전문 (금융위고시 제2025-7호)", authority_level: "binding", applicable_sector: "COMMERCIAL_BANK", gcs_uri: "gs://okf/regulations/01_fsc_banking_reg/doc.md" }, verdictNote: "시중은행 구속력 있는 법규(binding)" },
      { id: "DOC::DOC_09", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_09_DISTRACTOR_SAVINGS_BANK\n09 상호저축은행업감독규정\n(distractor · SAVINGS_BANK)", title: "v_node_source_document · DOC_09_DISTRACTOR_SAVINGS_BANK", color: "#a85c56", shape: "box", matchDocId: "DOC_09_DISTRACTOR_SAVINGS_BANK", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_09_DISTRACTOR_SAVINGS_BANK", title: "상호저축은행업감독규정", authority_level: "distractor", applicable_sector: "SAVINGS_BANK", gcs_uri: "gs://okf/distractors/09_fsc_savings_bank_reg/doc.md" }, verdictNote: "타업권(상호저축은행) 교란 원본 문서" }
    ],
    edges: [
      { from: "CTX::RISK_MGMT", to: "PROV::제29조", label: "INVOKES_PROVISION\n[term_key: provision-criteria]", color: "#b88a44", width: 2.0 },
      { from: "CTX::RISK_MGMT", to: "LOAN::LN_2026_KSIC_L1", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::RISK_MGMT", to: "LOAN::LN_2026_KSIC_F1", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::RISK_MGMT", to: "LOAN::LN_2026_KSIC_G1", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::RISK_MGMT", to: "LOAN::LN_2026_KSIC_H1", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "PROV::제29조", to: "DOC::DOC_01", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.7 },
      { from: "PROV::저축은행제38조", to: "DOC::DOC_09", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.6 },
      { from: "PROV::제29조", to: "PROV::저축은행제38조", label: "CONFLICTS_BY_SECTOR\n(저축은행 0.5% 차단)", color: "#a85c56", width: 1.8, dashes: true },
      { from: "LOAN::LN_2026_KSIC_L1", to: "PROV::제29조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "LOAN::LN_2026_KSIC_F1", to: "PROV::제29조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "LOAN::LN_2026_KSIC_G1", to: "PROV::제29조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "LOAN::LN_2026_KSIC_H1", to: "PROV::제29조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "LOAN::LN_2026_KSIC_L1", to: "CUST::CUST_0004", label: "BORROWED_BY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_2026_KSIC_F1", to: "CUST::CUST_0005", label: "BORROWED_BY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_2026_KSIC_G1", to: "CUST::CUST_0015", label: "BORROWED_BY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_2026_KSIC_H1", to: "CUST::CUST_0016", label: "BORROWED_BY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_2026_KSIC_L1", to: "PROD::PROD_CORP_PRIME_WC", label: "OF_PRODUCT", color: "#6b88a8", width: 1.3 },
      { from: "LOAN::LN_2026_KSIC_H1", to: "PROD::PROD_CORP_PRIME_WC", label: "OF_PRODUCT", color: "#6b88a8", width: 1.3 }
    ]
  },

  // =========================================================================
  // CASE 2: CQ07 (Theme B · Glossary term_key & 부서별 연체율 3중 분기)
  // =========================================================================
  {
    cqId: "CQ07",
    theme: "Theme B · 부서별 연체율 정의 분기 (Context Branching via Glossary term_key)",
    title: "CQ07 · 부서 맥락별 연체율 정의 분기 및 상각채권 조회",
    question: "여신관리팀 조기경보 기준으로 산출한 실질 연체율은 몇 %야? 금감원 대외공시 연체율이나 리스크관리위원회 고정이하여신비율과 비교하면 왜 이렇게 높게 나오는 거야?",
    contextBadge: "BusinessContext: CREDIT_MGMT vs DISCLOSURE vs RISK_MGMT · Glossary term_key: 'delinquency-rate'",
    verdict: "여신관리팀 EWS 실질연체율 = 4.00% (공시 2.26% · 리스크위 NPL 1.51% 대비 단기연체 150억 + 상각특수채권 85억 추가 반영)",
    answerDetail: "동일한 Dataplex Glossary 용어 'delinquency-rate(연체율·부실비율)'라도 호출 부서(BusinessContext)에 따라 산식과 관할 포트폴리오 스코프(SCOPES_PORTFOLIO)가 분기됩니다. ① 리스크위(RISK_MGMT)는 고정이하 분류 기준 1.51%(200억/1조3,275억, 별빛정밀 100억 요주의 제외), ② 금감원 공시(DISCLOSURE)는 30일 이상 연체 기준 2.26%(300억/1조3,275억, 상각특수채권 제외), ③ 여신관리팀(CREDIT_MGMT)은 내규 제14조②에 따라 10일 이상 연체(450억)와 대손상각 특수채권(성진해운물류 85억)을 분자·분모 모두에 합산하여 4.00%(535억/1조3,360억)가 됩니다.",
    gql: `GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext)
      -[inv:INVOKES_PROVISION {term_key: 'delinquency-rate'}]->(pr:Provision)
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[sp:SCOPES_PORTFOLIO]->(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(pr),
      (l)-[:HAS_DELINQUENCY]->(del:DelinquencyEvent)
WHERE ctx.context_id IN ('CREDIT_MGMT', 'DISCLOSURE', 'RISK_MGMT')
  AND (del.overdue_days >= 10 OR del.write_off_yn = 'Y')
RETURN ctx, sp.portfolio_scope_rule, inv.term_key, pr, OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r') AS pr_obj_url, l, del`,
    nodes: [
      { id: "CTX::CREDIT_MGMT", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nCREDIT_MGMT 여신관리팀\n(EWS 실질연체율 4.00%)", title: "v_node_business_context · CREDIT_MGMT", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "CREDIT_MGMT", dept_name: "여신관리팀", term_key: "delinquency-rate", formula: "(10일+ 연체 450억 + 상각특수채권 85억) ÷ (on-BS 1조3,275억 + 상각특수채권 85억) = 4.00%" }, verdictNote: "내규 제14조② 호출 + SCOPES_PORTFOLIO로 상각특수채권 포함 100계좌 스코핑" },
      { id: "CTX::DISCLOSURE", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nDISCLOSURE 재무기획부\n(금감원 공시 연체율 2.26%)", title: "v_node_business_context · DISCLOSURE", color: "#527a9a", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "DISCLOSURE", dept_name: "재무기획부(대외공시)", term_key: "delinquency-rate", formula: "30일+ 연체 300억 ÷ on-BS 1조3,275억 = 2.26% (상각특수채권 제외)" }, verdictNote: "내규 제14조① 호출: 1개월(30일) 이상 연체 기준, 상각특수채권(write_off_yn='Y') 제외" },
      { id: "CTX::RISK_MGMT_B", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nRISK_MGMT 리스크관리부\n(고정이하여신비율 1.51%)", title: "v_node_business_context · RISK_MGMT", color: "#527a9a", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "RISK_MGMT", dept_name: "리스크관리부", term_key: "delinquency-rate", formula: "고정이하 200억 ÷ on-BS 1조3,275억 = 1.51% (별빛정밀 100억 요주의 제외)" }, verdictNote: "감독규정 제27조 및 내규 제14조① 호출: 건전성 분류상 고정이하(SUBSTANDARD 이하)만 산입" },
      { id: "LOAN::LN_2025_WRITEOFF_01", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\nLN_2025_WRITEOFF_01 성진해운물류\n(상각특수채권 85억 · 추정손실)", title: "v_node_loan_contract · LN_2025_WRITEOFF_01", color: "#a85c56", shape: "dot", size: 21, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2025_WRITEOFF_01", borrower_name: "성진해운물류(주)", asset_classification: "ESTIMATED_LOSS", account_status: "WRITTEN_OFF_SPECIAL_CLAIM", outstanding_amt: 8500000000, overdue_days: 210 }, verdictNote: "대차대조표 외 상각특수채권(85억) → 공시·NPL에서는 제외되나 여신관리팀 EWS(4.00%)에는 분자·분모 모두 산입" },
      { id: "DEL::DLQ_WRITEOFF", classLabel: "DelinquencyEvent", layer: "ONT", label: "[DelinquencyEvent]\nDLQ_2025_99 (210일 연체)\nwrite_off_yn='Y' · 85억", title: "v_node_delinquency_event · DLQ_2025_99", color: "#a85c56", shape: "dot", size: 16, viewName: "v_node_delinquency_event", sourceStore: "Cloud Spanner Federated (ont_delinquency_events)", record: { event_id: "DLQ_2025_99", contract_id: "LN_2025_WRITEOFF_01", overdue_days: 210, overdue_principal_krw: 8500000000, write_off_yn: "Y" }, verdictNote: "write_off_yn='Y' → EWS 실질연체율에만 포함" },
      { id: "LOAN::LN_EWS_18D", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\n단기연체 3계좌 (18일 연체)\n합계 150억 (정상 분류)", title: "v_node_loan_contract · 18일 연체 계좌군 (3건 합계 150억)", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_group: "10일 이상 30일 미만 단기연체 3건", overdue_days: 18, total_outstanding_krw: 15000000000, asset_classification: "NORMAL" }, verdictNote: "18일 연체(≥10일, <30일) → 공시(2.26%)에는 빠지고 EWS(4.00%)에만 150억 산입" },
      { id: "DEL::DLQ_18D", classLabel: "DelinquencyEvent", layer: "ONT", label: "[DelinquencyEvent]\nDLQ_18D (18일 연체 · 150억)\nwrite_off_yn='N'", title: "v_node_delinquency_event · 18일 연체 이벤트 (3건)", color: "#527a9a", shape: "dot", size: 15, viewName: "v_node_delinquency_event", sourceStore: "Cloud Spanner Federated (ont_delinquency_events)", record: { overdue_days: 18, overdue_principal_krw: 15000000000, write_off_yn: "N", included_in: "CREDIT_MGMT (EWS 4.00%) only" }, verdictNote: "overdue_days=18 ≥ 10 → EWS 분자에만 포함" },
      { id: "LOAN::LN_30D_PLUS", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\n30일+ 연체 3계좌 (합계 300억)\n별빛정밀(요주의 100억)+태성·극동(고정 200억)", title: "v_node_loan_contract · LN_2026_0001~0003 (300억)", color: "#3b6ea5", shape: "dot", size: 20, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contracts: ["LN_2026_0001 (별빛정밀 45일·요주의 100억)", "LN_2026_0002 (태성금속 95일·고정 100억)", "LN_2026_0003 (극동철강 95일·고정 100억)"], npl_subset_krw: 20000000000, official_30d_krw: 30000000000 }, verdictNote: "별빛정밀 100억은 45일 연체라 공시(2.26%)·EWS(4.00%)에 포함되나, 별표3 라목 특례로 요주의이므로 리스크위 NPL(1.51%)에서는 제외" },
      { id: "PROV::내규제14조", classLabel: "Provision", layer: "LEX", label: "[Provision · 내규 제14조]\n목적별 연체율 3중 정의·산식\n(NPL 1.51% / 공시 2.26% / EWS 4.00%)", title: "v_node_provision · 내규 제14조 (별빛은행 여신내규)", color: "#3b735b", shape: "box", matchSec: "내규 제14조", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency", article_no: "내규 제14조", provision_role: "INTERNAL_RULE", target_columns: "ont_loan_contracts.outstanding_amt,ont_loan_contracts.asset_classification,ont_loan_contracts.account_status,ont_delinquency_events.overdue_days,ont_delinquency_events.write_off_yn", gcs_uri: "gs://okf/internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency.md" }, verdictNote: "제14조① 리스크위 고정이하비율 vs 금감원 공시 연체율(상각 제외) / 제14조② 여신관리팀 EWS 실질연체율(10일+ & 상각 포함)" },
      { id: "PROV::제27조", classLabel: "Provision", layer: "LEX", label: "[Provision · 제27조]\n자산건전성 5단계 분류 및\n제4항 추정손실 조기상각", title: "v_node_provision · 제27조 (은행업감독규정)", color: "#3b735b", shape: "box", matchSec: "제27조", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027", article_no: "제27조", provision_role: "BASE_CRITERIA", gcs_uri: "gs://okf/regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027.md" }, verdictNote: "5단계 분류 기준 및 부실자산 조기 대손상각 근거" },
      { id: "PROV::NARS가계연체", classLabel: "Provision", layer: "LEX", label: "[Provision · 교란차단]\nNARS 브리프 가계연체율 0.24%\n(타 세그먼트 인용 차단)", title: "v_node_provision · 이슈와논점 2 (DISTRACTOR_RULE)", color: "#a85c56", shape: "box", matchSec: "이슈와논점 2", viewName: "v_node_provision", sourceStore: "LEX Layer (Blocked by CONFLICTS_BY_SECTOR)", record: { provision_slot_id: "research_briefs/07_nars_rate_policy_issues/sec01_rate_components_and_dsr/nars_02_dsr_and_delinquency_trend", article_no: "이슈와논점 2", provision_role: "DISTRACTOR_RULE" }, verdictNote: "가계대출 연체율(0.24%)을 기업여신 공시 연체율(2.26%)에 혼입 인용 금지" },
      { id: "DOC::DOC_10", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_10_SYNTHETIC_BYULBIT_POLICY\n10 별빛은행 기업여신 내규\n(internal · COMMERCIAL_BANK)", title: "v_node_source_document · DOC_10_SYNTHETIC_BYULBIT_POLICY", color: "#477a63", shape: "box", matchDocId: "DOC_10_SYNTHETIC_BYULBIT_POLICY", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_10_SYNTHETIC_BYULBIT_POLICY", title: "별빛은행 기업여신 심사·금리·사후관리 내규", authority_level: "internal", applicable_sector: "COMMERCIAL_BANK" }, verdictNote: "당행 내부 규정(internal)" }
    ],
    edges: [
      { from: "CTX::CREDIT_MGMT", to: "PROV::내규제14조", label: "INVOKES_PROVISION\n[term_key: delinquency-rate · EWS]", color: "#b88a44", width: 2.0 },
      { from: "CTX::DISCLOSURE", to: "PROV::내규제14조", label: "INVOKES_PROVISION\n[term_key: delinquency-rate · 공시]", color: "#b88a44", width: 1.8 },
      { from: "CTX::RISK_MGMT_B", to: "PROV::제27조", label: "INVOKES_PROVISION\n[term_key: delinquency-rate · NPL]", color: "#b88a44", width: 1.8 },
      { from: "CTX::CREDIT_MGMT", to: "LOAN::LN_2025_WRITEOFF_01", label: "SCOPES_PORTFOLIO\n(EWS 상각포함)", color: "#6b88a8", width: 1.6 },
      { from: "CTX::CREDIT_MGMT", to: "LOAN::LN_EWS_18D", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::CREDIT_MGMT", to: "LOAN::LN_30D_PLUS", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::DISCLOSURE", to: "LOAN::LN_30D_PLUS", label: "SCOPES_PORTFOLIO\n(on-BS만)", color: "#6b88a8", width: 1.5 },
      { from: "CTX::RISK_MGMT_B", to: "LOAN::LN_30D_PLUS", label: "SCOPES_PORTFOLIO\n(on-BS만)", color: "#6b88a8", width: 1.5 },
      { from: "PROV::제27조", to: "PROV::내규제14조", label: "DELEGATES_TO_INTERNAL", color: "#5a8770", width: 1.8 },
      { from: "PROV::내규제14조", to: "DOC::DOC_10", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.7 },
      { from: "PROV::내규제14조", to: "PROV::NARS가계연체", label: "CONFLICTS_BY_SECTOR\n(가계 0.24% 차단)", color: "#a85c56", width: 1.7, dashes: true },
      { from: "LOAN::LN_2025_WRITEOFF_01", to: "PROV::내규제14조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "LOAN::LN_EWS_18D", to: "PROV::내규제14조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_30D_PLUS", to: "PROV::내규제14조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_30D_PLUS", to: "PROV::제27조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_2025_WRITEOFF_01", to: "DEL::DLQ_WRITEOFF", label: "HAS_DELINQUENCY", color: "#a85c56", width: 1.5 },
      { from: "LOAN::LN_EWS_18D", to: "DEL::DLQ_18D", label: "HAS_DELINQUENCY", color: "#6b88a8", width: 1.4 }
    ]
  },

  // =========================================================================
  // CASE 3: CQ09 (Theme C · Star Schema 원장 허브 & 복합 특례 EOD 유예)
  // =========================================================================
  {
    cqId: "CQ09",
    theme: "Theme C · 예외·특례 복합 판정 (Star Schema Hub + Multi-Hop Rule Chain)",
    title: "CQ09 · 30일 초과 연체 여신 및 기한이익상실(EOD) 유예 조회",
    question: "연체 30일 넘은 기업여신 중에 기한이익상실(EOD) 바로 처리해야 하는 차주랑 유예할 수 있는 차주 나눠줘. 지금 결재 결과가 내규랑 맞아?",
    contextBadge: "BusinessContext: CREDIT_MGMT (여신관리팀) · Glossary term_key: 'eod-deferral'",
    verdict: "EOD 유예 = 별빛정밀 1건(APPROVED) / 즉시 EOD 예정 통지 = 태성금속·극동철강 2건(REJECTED) — 결재 결과 내규 100% 부합",
    answerDetail: "내규 제16조①(30일 초과 연체 → EOD 예정 통지 원칙)에 대해 제18조 유예 특례는 ①(6개월 연속상환 OR 유상증자 OR 신보 85% 이상 보증서) AND ②우선변제자산(rehab_priority_claim_yn='Y') + 본부심사역 승인(APPROVED)을 모두 요구합니다. 별빛정밀(LN_2026_0001)은 7개월 연속상환·50억 증자·신보 90% 보증서·우선변제 Y·본부승인을 모두 갖춰 유예 적법. 반면 태성금속(LN_2026_0002)은 우선변제 Y이나 2개월 상환·신보 70%(<85%)로 요건① 미달, 극동철강(LN_2026_0003)은 요건①·② 모두 미달이므로 EOD 통지가 맞습니다.",
    gql: `GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'CREDIT_MGMT'})
      -[inv:INVOKES_PROVISION {term_key: 'eod-deferral'}]->(p16:Provision {article_no: '내규 제16조'})
      -[:HAS_EXCEPTION_PROVISO]->(p18:Provision {article_no: '내규 제18조'})
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:GOVERNED_BY_CRITERIA]->(p16),
      (l)-[:BORROWED_BY]->(c:Customer)
OPTIONAL MATCH (l)-[:HAS_WORKOUT_HISTORY]->(w:WorkoutHistory)
OPTIONAL MATCH (l)-[:HAS_COLLATERAL]->(col:Collateral)
OPTIONAL MATCH (l)-[:HAS_EXCEPTION_APPROVAL]->(ea:ExceptionApproval)
WHERE l.overdue_days > 30 AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
RETURN ctx, p16, OBJ.GET_ACCESS_URL(p18.gcs_obj_ref, 'r') AS p18_obj_url, doc, l, c, w, col, ea`,
    nodes: [
      { id: "CTX::CREDIT_MGMT_C", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nCREDIT_MGMT 여신관리팀", title: "v_node_business_context · CREDIT_MGMT", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "CREDIT_MGMT", dept_name: "여신관리팀", term_key: "eod-deferral (기한이익상실 통지 및 유예 특례)" }, verdictNote: "term_key='eod-deferral'로 내규 제16조(원칙) 및 제18조(유예 특례) 호출 + SCOPES_PORTFOLIO로 연체 계좌 스코핑" },
      { id: "LOAN::LN_2026_0001", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract · EOD 유예]\nLN_2026_0001 별빛정밀(주)\n(45일 연체 · 요주의 · 우선변제 Y)", title: "v_node_loan_contract · LN_2026_0001 (별빛정밀)", color: "#3b735b", shape: "dot", size: 22, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_0001", borrower_name: "별빛정밀(주)", overdue_days: 45, asset_classification: "PRECAUTIONARY", rehab_priority_claim_yn: "Y", outstanding_amt: 10000000000, eod_action: "EOD_DEFERRED (유예 적법)" }, verdictNote: "요건①(7개월 상환·50억 증자·신보 90%) + 요건②(우선변제 Y) + 본부심사역 APPROVED 모두 충족 → EOD 유예" },
      { id: "WK::WK_0001", classLabel: "WorkoutHistory", layer: "ONT", label: "[WorkoutHistory]\nWK_0001 (7개월 연속상환 ≥ 6M\n· 유상증자 50억)", title: "v_node_workout_history · WK_0001 (별빛정밀)", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_workout_history", sourceStore: "BigQuery Native (workout_histories)", record: { workout_id: "WK_2026_001", contract_id: "LN_2026_0001", consecutive_normal_repay_months: 7, new_equity_paid_in_krw: 5000000000, legal_proceeding_code: "CORP_RESTRUCT_ACT_WORKOUT" }, verdictNote: "별표3 제3호 라목 및 내규 제18조1호 충족" },
      { id: "COL::COL_0001", classLabel: "Collateral", layer: "ONT", label: "[Collateral]\nCOL_0001 (신보 KODIT 보증서\n90.0% ≥ 85% 충족)", title: "v_node_collateral · COL_0001 (별빛정밀)", color: "#527a9a", shape: "dot", size: 16, viewName: "v_node_collateral", sourceStore: "Cloud Spanner Federated (ont_collaterals)", record: { collateral_id: "COL_2026_001", contract_id: "LN_2026_0001", collateral_type_code: "CREDIT_GUARANTEE_CERT", guarantee_agency_code: "KODIT", guarantee_ratio_pct: 90.0, appraised_collateral_krw: 9000000000 }, verdictNote: "신용보증기금(KODIT) 90.0% 보증서 → 내규 제18조1호(85% 이상) 충족" },
      { id: "EA::EA_0001", classLabel: "ExceptionApproval", layer: "ONT", label: "[ExceptionApproval]\nEA_0001 (APPROVED · 2026-02-25\n본부 여신심사역 문서화)", title: "v_node_exception_approval · EA_0001 (별빛정밀)", color: "#3b735b", shape: "dot", size: 16, viewName: "v_node_exception_approval", sourceStore: "Cloud Spanner Federated (ont_exception_approvals)", record: { approval_id: "EA_2026_001", contract_id: "LN_2026_0001", approval_type_code: "EOD_DEFERRAL_REVIEW", approval_status: "APPROVED", approver_role_code: "HQ_SENIOR_CREDIT_OFFICER", approval_dt: "2026-02-25" }, verdictNote: "본부 여신심사역 승인 및 판단근거 문서화 완료" },
      { id: "LOAN::LN_2026_0002", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract · EOD 통지]\nLN_2026_0002 태성금속공업(주)\n(95일 연체 · 고정 · 우선변제 Y)", title: "v_node_loan_contract · LN_2026_0002 (태성금속공업)", color: "#a85c56", shape: "dot", size: 21, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_0002", borrower_name: "태성금속공업(주)", overdue_days: 95, asset_classification: "SUBSTANDARD", rehab_priority_claim_yn: "Y", outstanding_amt: 10000000000, eod_action: "EOD_NOTICE (즉시 EOD 통지)" }, verdictNote: "우선변제자산(Y)이나 2개월 상환(<6M)·증자 0원·신보 보증비율 70%(<85%)로 제18조1호 미충족 → EOD 예정 통지" },
      { id: "WK::WK_0002", classLabel: "WorkoutHistory", layer: "ONT", label: "[WorkoutHistory]\nWK_0002 (2개월 상환 < 6M 미달\n· 증자 0원)", title: "v_node_workout_history · WK_0002 (태성금속)", color: "#a85c56", shape: "dot", size: 15, viewName: "v_node_workout_history", sourceStore: "BigQuery Native (workout_histories)", record: { workout_id: "WK_2026_002", contract_id: "LN_2026_0002", consecutive_normal_repay_months: 2, new_equity_paid_in_krw: 0, legal_proceeding_code: "REHAB_ACT_ART180_2_DIP" }, verdictNote: "연속 상환 2개월(<6개월) 및 증자 0원으로 요건 미달" },
      { id: "COL::COL_0002", classLabel: "Collateral", layer: "ONT", label: "[Collateral]\nCOL_0002 (신보 KODIT 70.0%\n< 85% 기준 미달)", title: "v_node_collateral · COL_0002 (태성금속)", color: "#a85c56", shape: "dot", size: 15, viewName: "v_node_collateral", sourceStore: "Cloud Spanner Federated (ont_collaterals)", record: { collateral_id: "COL_2026_002", contract_id: "LN_2026_0002", collateral_type_code: "CREDIT_GUARANTEE_CERT", guarantee_agency_code: "KODIT", guarantee_ratio_pct: 70.0, appraised_collateral_krw: 7000000000 }, verdictNote: "보증비율 70.0%로 내규 제18조1호(85% 이상) 미달" },
      { id: "LOAN::LN_2026_0003", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract · EOD 통지]\nLN_2026_0003 극동철강산업(주)\n(95일 연체 · 고정 · 우선변제 N)", title: "v_node_loan_contract · LN_2026_0003 (극동철강산업)", color: "#a85c56", shape: "dot", size: 20, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_0003", borrower_name: "극동철강산업(주)", overdue_days: 95, asset_classification: "SUBSTANDARD", rehab_priority_claim_yn: "N", outstanding_amt: 10000000000, approval_status: "REJECTED", eod_action: "EOD_NOTICE (즉시 EOD 통지)" }, verdictNote: "요건①·② 모두 불충족 및 결재 REJECTED → 즉시 EOD 예정 통지" },
      { id: "PROV::내규제16조", classLabel: "Provision", layer: "LEX", label: "[Provision · 내규 제16조]\n30일(1월) 초과 연체 시\n기한이익상실(EOD) 예정 통지 원칙", title: "v_node_provision · 내규 제16조", color: "#3b735b", shape: "box", matchSec: "내규 제16조", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule", article_no: "내규 제16조", provision_role: "INTERNAL_RULE", target_columns: "ont_loan_contracts.overdue_days,ont_loan_contracts.account_status" }, verdictNote: "원리금 연체 30일 초과 시 EOD 예정 통지 원칙" },
      { id: "PROV::내규제18조", classLabel: "Provision", layer: "LEX", label: "[Provision · 내규 제18조]\n채권재조정·신보85%+ & 우선변제\n본부승인 시 EOD 유예 특례", title: "v_node_provision · 내규 제18조", color: "#3b735b", shape: "box", matchSec: "내규 제18조", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver", article_no: "내규 제18조", provision_role: "EXCEPTION_PROVISO", target_columns: "ont_loan_contracts.rehab_priority_claim_yn,workout_histories.consecutive_normal_repay_months,workout_histories.new_equity_paid_in_krw,ont_collaterals.guarantee_ratio_pct,ont_exception_approvals.approval_status" }, verdictNote: "내규 제16조의 예외 특례: 각 호 요건(① AND ②) + 본부 여신심사역 APPROVED 필요" },
      { id: "PROV::별표3라목", classLabel: "Provision", layer: "LEX", label: "[Provision · 별표3 제3호 라목]\n채권재조정 6개월 연속상환·증자 시\n고정이하 분류 제외(요주의) 특례", title: "v_node_provision · 별표3 제3호 라목", color: "#3b735b", shape: "box", matchSec: "별표3 제3호 라목", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption", article_no: "별표3 제3호 라목", provision_role: "EXCEPTION_PROVISO" }, verdictNote: "감독규정 별표3 제3호 라목 → 당행 내규 제18조로 위임·구체화" },
      { id: "DOC::DOC_10_C", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_10_SYNTHETIC_BYULBIT_POLICY\n10 별빛은행 기업여신 내규\n(internal · COMMERCIAL_BANK)", title: "v_node_source_document · DOC_10_SYNTHETIC_BYULBIT_POLICY", color: "#477a63", shape: "box", matchDocId: "DOC_10_SYNTHETIC_BYULBIT_POLICY", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_10_SYNTHETIC_BYULBIT_POLICY", title: "별빛은행 기업여신 심사·금리·사후관리 내규", authority_level: "internal", applicable_sector: "COMMERCIAL_BANK" }, verdictNote: "내규 제16조·제18조가 소속된 상위 문서 루트 (PART_OF_DOCUMENT)" }
    ],
    edges: [
      { from: "CTX::CREDIT_MGMT_C", to: "PROV::내규제16조", label: "INVOKES_PROVISION\n[term_key: eod-deferral]", color: "#b88a44", width: 2.0 },
      { from: "CTX::CREDIT_MGMT_C", to: "LOAN::LN_2026_0001", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::CREDIT_MGMT_C", to: "LOAN::LN_2026_0002", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::CREDIT_MGMT_C", to: "LOAN::LN_2026_0003", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "PROV::내규제16조", to: "PROV::내규제18조", label: "HAS_EXCEPTION_PROVISO", color: "#a85c56", width: 1.8 },
      { from: "PROV::별표3라목", to: "PROV::내규제18조", label: "DELEGATES_TO_INTERNAL", color: "#5a8770", width: 1.8 },
      { from: "PROV::내규제16조", to: "DOC::DOC_10_C", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.7 },
      { from: "PROV::내규제18조", to: "DOC::DOC_10_C", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.7 },
      { from: "LOAN::LN_2026_0001", to: "PROV::내규제16조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_2026_0001", to: "PROV::내규제18조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.7 },
      { from: "LOAN::LN_2026_0002", to: "PROV::내규제16조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_2026_0003", to: "PROV::내규제16조", label: "GOVERNED_BY_CRITERIA", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_2026_0001", to: "WK::WK_0001", label: "HAS_WORKOUT_HISTORY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_2026_0001", to: "COL::COL_0001", label: "HAS_COLLATERAL", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_2026_0001", to: "EA::EA_0001", label: "HAS_EXCEPTION_APPROVAL", color: "#3b735b", width: 1.5 },
      { from: "LOAN::LN_2026_0002", to: "WK::WK_0002", label: "HAS_WORKOUT_HISTORY", color: "#a85c56", width: 1.4 },
      { from: "LOAN::LN_2026_0002", to: "COL::COL_0002", label: "HAS_COLLATERAL", color: "#a85c56", width: 1.4 }
    ]
  },

  // =========================================================================
  // CASE 4: CQ12 (Theme D · 상위 모범규준→내규 위임 & 단독 특허 금리인하 거절)
  // =========================================================================
  {
    cqId: "CQ12",
    theme: "Theme D · 금리인하요구권 재량 위임 & 엔티티 별칭 해석 (Delegation & Discretion)",
    title: "CQ12 · 금리인하요구권 재량 위임 및 심사 내역 조회",
    question: "에이펙스세미콘이 특허 땄다고 금리인하요구 했는데 우리가 거절했잖아. 고객이 '특허 취득은 금리인하 사유로 정해져 있다'고 항의하는데, 거절이 맞아? 뭐라고 통보해야 해?",
    contextBadge: "BusinessContext: BRANCH (영업점 RM) · Glossary term_key: 'loan-rate' · Alias: '에이펙스세미콘' ➔ CUST_0008",
    verdict: "거절 적법 (0bp) — 개선방안 ④항 선택적 적용 재량 + 내규 제25조② 단독 특허 제외 (단, 개선방안 ②항에 따라 구체적 거절사유 통보 필수)",
    answerDetail: "금융위·은행연합회 개선방안 표에는 '특허권 신규취득'이 예시되어 있으나, 같은 쪽 ④항 단서가 '특허 취득 등은 은행이 선택적으로 적용할 수 있도록 조정'했고, 이를 위임받은 당행 내규 제25조②가 '단독 특허 취득(재무상태·신용등급 개선 미동반)'을 필수 인하 대상에서 제외했습니다. 에이펙스세미콘(CUST_0008)은 등급 BBB→BBB 불변(매출 +1.2%)이라 거절(REJECTED, 0bp)이 적법하며, 같은 날 특허+등급 상승(BBB→BBB+, 매출 +35%)을 입증한 네오바이오텍은 35bp 인하 승인(APPROVED)되어 일관됩니다. 개선방안 ②항에 따라 '단독 특허만으로는 내부 신용등급·현금흐름 개선이 확인되지 않는다'는 구체적 사유를 반드시 통보해야 합니다.",
    gql: `GRAPH starlight_bank_ontology.finance_graph
MATCH (ctx:BusinessContext {context_id: 'BRANCH'})
      -[inv:INVOKES_PROVISION {term_key: 'loan-rate'}]->(p_ext:Provision {article_no: '제Ⅱ장 1-나 ④항'})
      -[:DELEGATES_TO_INTERNAL]->(p_int:Provision {article_no: '내규 제25조'})
      -[:PART_OF_DOCUMENT]->(doc:SourceDocument),
      (ctx)-[:SCOPES_PORTFOLIO]->(l:LoanContract)-[:BORROWED_BY]->(c:Customer),
      (l)-[:HAS_RATE_CUT_REQUEST]->(rc:RateCutRequest)
      -[:EVALUATED_UNDER_PROVISION]->(p_int)
RETURN ctx, p_ext, p_int, OBJ.GET_ACCESS_URL(p_int.gcs_obj_ref, 'r') AS p_int_obj_url, doc, c, l, rc`,
    nodes: [
      { id: "CTX::BRANCH", classLabel: "BusinessContext", layer: "ONT", label: "[BusinessContext]\nBRANCH 영업점(RM)", title: "v_node_business_context · BRANCH", color: "#3b6ea5", shape: "box", viewName: "v_node_business_context", sourceStore: "BigQuery Native (ctx_business_contexts)", record: { context_id: "BRANCH", dept_name: "영업점(RM)", term_key: "loan-rate (대출금리 산정체계 및 금리인하요구권)" }, verdictNote: "term_key='loan-rate'로 개선방안 제Ⅱ장 1-나 ④항 및 당행 내규 제25조 호출 + SCOPES_PORTFOLIO로 영업점 관할 여신 스코핑" },
      { id: "CUST::CUST_0008", classLabel: "Customer", layer: "ONT", label: "[Customer · 별칭 바인딩]\nCUST_0008 에이펙스세미콘(주)\n(신용등급 BBB 불변)", title: "v_node_customer · CUST_0008 (에이펙스세미콘)", color: "#527a9a", shape: "dot", size: 17, viewName: "v_node_customer", sourceStore: "BigQuery Master (customers + ont_entity_aliases)", record: { customer_id: "CUST_0008", borrower_name: "에이펙스세미콘(주)", alias_matched: "에이펙스세미콘 -> CUST_0008 (Longest-Match-First)", credit_rating: "BBB", industry_name: "반도체 제조업" }, verdictNote: "ont_entity_aliases에서 '에이펙스세미콘' → CUST_0008로 정확히 바인딩" },
      { id: "LOAN::LN_APEX", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\nLN_2026_0008\n(에이펙스세미콘 기업운전자금)", title: "v_node_loan_contract · LN_2026_0008", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { contract_id: "LN_2026_0008", customer_id: "CUST_0008", borrower_name: "에이펙스세미콘(주)", product_code: "PROD_CORP_PRIME_WC", asset_classification: "NORMAL" }, verdictNote: "차주 CUST_0008과 금리인하 신청 RCR_2026_01을 연결하는 원장 허브" },
      { id: "RC::RCR_2026_01", classLabel: "RateCutRequest", layer: "ONT", label: "[RateCutRequest · REJECTED]\nRCR_2026_01 단독 특허 취득\n(BBB→BBB 불변 · 매출 +1.2% · 0bp)", title: "v_node_rate_cut_request · RCR_2026_01 (에이펙스세미콘)", color: "#a85c56", shape: "dot", size: 21, viewName: "v_node_rate_cut_request", sourceStore: "Cloud Spanner Federated (ont_rate_cut_requests)", record: { request_id: "RCR_2026_01", customer_id: "CUST_0008", borrower_name: "에이펙스세미콘(주)", application_reason_code: "PATENT_ACQUISITION", credit_rating_before: "BBB", credit_rating_after: "BBB", yoy_revenue_growth_pct: 1.2, review_status_code: "REJECTED", approved_cut_bp: 0 }, verdictNote: "신용등급 상승 없음(BBB→BBB) → 내규 제25조②에 따라 거절 적법 + 구체적 거절사유 통보 대상" },
      { id: "CUST::CUST_0009", classLabel: "Customer", layer: "ONT", label: "[Customer · 승인 대조군]\n네오바이오텍(주)\n(신용등급 BBB → BBB+ 상승)", title: "v_node_customer · 네오바이오텍(주)", color: "#527a9a", shape: "dot", size: 17, viewName: "v_node_customer", sourceStore: "BigQuery Master (customers)", record: { borrower_name: "네오바이오텍(주)", credit_rating_change: "BBB -> BBB+", yoy_revenue_growth_pct: 35.0 }, verdictNote: "특허 취득 + 재무·신용등급 개선 동반 차주 (대조군)" },
      { id: "LOAN::LN_NEO", classLabel: "LoanContract", layer: "ONT", label: "[LoanContract]\n네오바이오텍 기업운전자금", title: "v_node_loan_contract · 네오바이오텍 여신계약", color: "#3b6ea5", shape: "dot", size: 19, viewName: "v_node_loan_contract", sourceStore: "Cloud Spanner Federated (ont_loan_contracts)", record: { borrower_name: "네오바이오텍(주)", product_code: "PROD_TCB_WORKING", asset_classification: "NORMAL" }, verdictNote: "네오바이오텍 여신계약 허브" },
      { id: "RC::RCR_2026_02", classLabel: "RateCutRequest", layer: "ONT", label: "[RateCutRequest · APPROVED]\nRCR_2026_02 특허 + 등급 상승\n(BBB→BBB+ · 매출 +35% · -35bp 인하)", title: "v_node_rate_cut_request · RCR_2026_02 (네오바이오텍)", color: "#3b735b", shape: "dot", size: 21, viewName: "v_node_rate_cut_request", sourceStore: "Cloud Spanner Federated (ont_rate_cut_requests)", record: { request_id: "RCR_2026_02", borrower_name: "네오바이오텍(주)", application_reason_code: "PATENT_ACQUISITION", credit_rating_before: "BBB", credit_rating_after: "BBB+", yoy_revenue_growth_pct: 35.0, review_status_code: "APPROVED", approved_cut_bp: 35 }, verdictNote: "특허 취득 + 신용등급 상승(BBB→BBB+) 동반 → 35bp 금리인하 승인" },
      { id: "PROV::개선방안4항", classLabel: "Provision", layer: "LEX", label: "[Provision · 제Ⅱ장 1-나 ④항]\n특허 취득 은행 선택적 적용 재량\n& ②항 구체적 거절사유 통보 의무", title: "v_node_provision · 제Ⅱ장 1-나 ④항 (대출금리 산정체계 개선방안)", color: "#3b735b", shape: "box", matchSec: "제Ⅱ장 1-나 ④항", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion", article_no: "제Ⅱ장 1-나 ④항", provision_role: "EXCEPTION_PROVISO", target_columns: "ont_rate_cut_requests.application_reason_code,ont_rate_cut_requests.review_status_code", gcs_uri: "gs://okf/regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion.md" }, verdictNote: "④항: 특허 취득은 은행이 선택적으로 적용 가능 / ②항: 처리결과 및 구체적 사유 통보 의무" },
      { id: "PROV::내규제25조", classLabel: "Provision", layer: "LEX", label: "[Provision · 내규 제25조]\n제25조② 단독 특허 필수인하 제외\n(신용등급·재무 개선 동반 시에만 인하)", title: "v_node_provision · 내규 제25조 (별빛은행 여신내규)", color: "#3b735b", shape: "box", matchSec: "내규 제25조", viewName: "v_node_provision", sourceStore: "LEX Layer + Dataplex KC Aspect (verified)", record: { provision_slot_id: "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion", article_no: "내규 제25조", provision_role: "INTERNAL_RULE", target_columns: "ont_rate_cut_requests.application_reason_code,ont_rate_cut_requests.credit_rating_before,ont_rate_cut_requests.credit_rating_after,ont_rate_cut_requests.review_status_code", gcs_uri: "gs://okf/internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion.md" }, verdictNote: "상위 개선방안 ④항의 재량을 위임받아 단독 특허를 필수 인하 사유에서 제외" },
      { id: "DOC::DOC_05", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_05_FSC_KFB_RATE\n05 대출금리 산정체계 개선방안\n(advisory · 금융위·은행연합회)", title: "v_node_source_document · DOC_05_FSC_KFB_RATE", color: "#477a63", shape: "box", matchDocId: "DOC_05_FSC_KFB_RATE", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_05_FSC_KFB_RATE", title: "은행권 대출금리 산정체계 개선방안", authority_level: "advisory", applicable_sector: "COMMERCIAL_BANK" }, verdictNote: "금융위원회·금감원·은행연합회 공동 개선방안" },
      { id: "DOC::DOC_10_D", classLabel: "SourceDocument", layer: "LEX", label: "[SourceDocument]\nDOC_10_SYNTHETIC_BYULBIT_POLICY\n10 별빛은행 기업여신 내규\n(internal · COMMERCIAL_BANK)", title: "v_node_source_document · DOC_10_SYNTHETIC_BYULBIT_POLICY", color: "#477a63", shape: "box", matchDocId: "DOC_10_SYNTHETIC_BYULBIT_POLICY", viewName: "v_node_source_document", sourceStore: "LEX Layer (lex_source_documents)", record: { doc_id: "DOC_10_SYNTHETIC_BYULBIT_POLICY", title: "별빛은행 기업여신 심사·금리·사후관리 내규", authority_level: "internal", applicable_sector: "COMMERCIAL_BANK" }, verdictNote: "내규 제25조가 소속된 상위 문서 루트 (PART_OF_DOCUMENT)" }
    ],
    edges: [
      { from: "CTX::BRANCH", to: "PROV::개선방안4항", label: "INVOKES_PROVISION\n[term_key: loan-rate]", color: "#b88a44", width: 2.0 },
      { from: "CTX::BRANCH", to: "LOAN::LN_APEX", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "CTX::BRANCH", to: "LOAN::LN_NEO", label: "SCOPES_PORTFOLIO", color: "#6b88a8", width: 1.5 },
      { from: "PROV::개선방안4항", to: "PROV::내규제25조", label: "DELEGATES_TO_INTERNAL", color: "#5a8770", width: 1.9 },
      { from: "PROV::개선방안4항", to: "DOC::DOC_05", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.7 },
      { from: "PROV::내규제25조", to: "DOC::DOC_10_D", label: "PART_OF_DOCUMENT", color: "#5a8770", width: 1.7 },
      { from: "LOAN::LN_APEX", to: "CUST::CUST_0008", label: "BORROWED_BY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_APEX", to: "RC::RCR_2026_01", label: "HAS_RATE_CUT_REQUEST", color: "#a85c56", width: 1.6 },
      { from: "RC::RCR_2026_01", to: "PROV::내규제25조", label: "EVALUATED_UNDER_PROVISION", color: "#b88a44", width: 1.8 },
      { from: "RC::RCR_2026_01", to: "PROV::개선방안4항", label: "EVALUATED_UNDER_PROVISION", color: "#b88a44", width: 1.6 },
      { from: "LOAN::LN_NEO", to: "CUST::CUST_0009", label: "BORROWED_BY", color: "#6b88a8", width: 1.4 },
      { from: "LOAN::LN_NEO", to: "RC::RCR_2026_02", label: "HAS_RATE_CUT_REQUEST", color: "#3b735b", width: 1.6 },
      { from: "RC::RCR_2026_02", to: "PROV::내규제25조", label: "EVALUATED_UNDER_PROVISION", color: "#b88a44", width: 1.8 }
    ]
  }
];

const FINANCE_SEMANTIC_ENTITIES = SEMANTIC_ENTITIES;
const FINANCE_SEMANTIC_EDGES = SEMANTIC_EDGES;
const FINANCE_CAVEAT_SECTIONS = CAVEAT_SECTIONS;
const FINANCE_BQ_CLASS_NODES = BQ_CLASS_NODES;
const FINANCE_BQ_CLASS_EDGES = BQ_CLASS_EDGES;
const FINANCE_BQ_GQL_PRESETS = BQ_GQL_PRESETS;



