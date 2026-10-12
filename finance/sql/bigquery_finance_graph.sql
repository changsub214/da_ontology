-- ============================================================================
-- 1. 11 NODE VIEWS IN `starlight_bank_ontology` (모든 뷰·컬럼 직관적 한 줄 설명 포함)
-- ============================================================================

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_business_context` (
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
FROM `finance-ontology-changseop.starlight_bank_ontology.ctx_business_contexts`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_source_document` (
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
FROM `finance-ontology-changseop.starlight_bank_ontology.lex_source_documents`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (
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
FROM `finance-ontology-changseop.starlight_bank_ontology.lex_provisions`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_customer` (
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
FROM `finance-ontology-changseop.starlight_bank.customers`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_financial_product` (
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
FROM `finance-ontology-changseop.starlight_bank.financial_products`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_workout_history` (
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
FROM `finance-ontology-changseop.starlight_bank.workout_histories`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_collateral` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_collaterals`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_delinquency_event` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_delinquency_events`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_rate_cut_request` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_rate_cut_requests`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_node_exception_approval` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_exception_approvals`;


-- ============================================================================
-- 2. 15 EDGE VIEWS IN `starlight_bank_ontology` (모든 뷰·컬럼 직관적 한 줄 설명 포함)
-- ============================================================================

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_borrowed_by` (
  contract_id OPTIONS(description="여신계약 고유 번호 (Source FK -> LoanContract.contract_id)"),
  customer_id OPTIONS(description="차주 고객 고유 번호 (Destination FK -> Customer.customer_id)")
)
OPTIONS(description="[Edge: BORROWED_BY] 여신계약이 어느 기업 차주에게 실행되었는지 연결하는 엣지")
AS SELECT contract_id, customer_id FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_of_product` (
  contract_id OPTIONS(description="여신계약 고유 번호 (Source FK -> LoanContract.contract_id)"),
  product_code OPTIONS(description="가입 여신상품 코드 (Destination FK -> FinancialProduct.product_code)")
)
OPTIONS(description="[Edge: OF_PRODUCT] 여신계약이 어느 여신 금융상품으로 체결되었는지 연결하는 엣지")
AS SELECT contract_id, product_code FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_collateral` (
  contract_id OPTIONS(description="피담보 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  collateral_id OPTIONS(description="담보·보증서 고유 번호 (Destination FK -> Collateral.collateral_id)")
)
OPTIONS(description="[Edge: HAS_COLLATERAL] 여신계약에 설정된 담보 및 신용보증기금 보증서를 연결하는 엣지")
AS SELECT contract_id, collateral_id FROM `finance-ontology-changseop.starlight_bank.ont_collaterals`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_delinquency` (
  contract_id OPTIONS(description="연체 발생 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  event_id OPTIONS(description="연체·상각 이벤트 고유 번호 (Destination FK -> DelinquencyEvent.event_id)")
)
OPTIONS(description="[Edge: HAS_DELINQUENCY] 여신계약에서 발생한 연체 및 대손상각 특수채권 이벤트를 연결하는 엣지")
AS SELECT contract_id, event_id FROM `finance-ontology-changseop.starlight_bank.ont_delinquency_events`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_rate_cut_request` (
  contract_id OPTIONS(description="신청 대상 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  request_id OPTIONS(description="금리인하요구 신청 고유 번호 (Destination FK -> RateCutRequest.request_id)")
)
OPTIONS(description="[Edge: HAS_RATE_CUT_REQUEST] 여신계약에 대해 접수된 금리인하요구권 신청·심사 내역을 연결하는 엣지")
AS SELECT contract_id, request_id FROM `finance-ontology-changseop.starlight_bank.ont_rate_cut_requests`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_exception_approval` (
  contract_id OPTIONS(description="결재 대상 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  approval_id OPTIONS(description="예외승인 결재 고유 번호 (Destination FK -> ExceptionApproval.approval_id)")
)
OPTIONS(description="[Edge: HAS_EXCEPTION_APPROVAL] 여신계약의 기한이익상실 유예 등 본부 예외승인 결재 내역을 연결하는 엣지")
AS SELECT contract_id, approval_id FROM `finance-ontology-changseop.starlight_bank.ont_exception_approvals`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_workout_history` (
  contract_id OPTIONS(description="대상 여신계약 번호 (Source FK -> LoanContract.contract_id)"),
  workout_id OPTIONS(description="워크아웃·채권재조정 이력 고유 번호 (Destination FK -> WorkoutHistory.workout_id)")
)
OPTIONS(description="[Edge: HAS_WORKOUT_HISTORY] 여신계약의 채권재조정·워크아웃·회생절차 상환 및 증자 이력을 연결하는 엣지")
AS SELECT contract_id, workout_id FROM `finance-ontology-changseop.starlight_bank.workout_histories`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_scopes_portfolio` (
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
FROM `finance-ontology-changseop.starlight_bank_ontology.ctx_business_contexts` ctx
CROSS JOIN `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
   OR ctx.context_id IN ('CREDIT_MGMT', 'COMPLIANCE');

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_invokes_provision` (
  edge_id OPTIONS(description="부서맥락-용어-조문 호출 엣지 고유 식별자 (PK)"),
  context_id OPTIONS(description="호출 주체 부서·업무목적 맥락 식별자 (Source FK -> BusinessContext.context_id)"),
  term_key OPTIONS(description="Dataplex Business Glossary 표준 금융 용어 식별자 (예: delinquency-rate, provision-criteria, loan-rate)"),
  glossary_term_uri OPTIONS(description="Dataplex Knowledge Catalog Business Glossary 용어 리소스 경로"),
  provision_slot_id OPTIONS(description="호출 대상 법령·내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  invocation_reason OPTIONS(description="해당 부서 맥락과 금융 용어 조합에서 이 조문을 호출하는 비즈니스 이유 한 줄 설명")
)
OPTIONS(description="[Edge: INVOKES_PROVISION] 부서·업무목적 맥락(BusinessContext)과 KC Glossary 용어(term_key) 조합에 따라 호출할 법령·내규 조문을 분기하는 브리지 엣지")
AS SELECT edge_id, context_id, term_key, glossary_term_uri, provision_slot_id, invocation_reason
FROM `finance-ontology-changseop.starlight_bank_ontology.edge_invokes_provision`;

-- Pure Real-Time SQL View (Zero Ground-Truth Leakage): connects jurisdictional scope only
CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_governed_by_criteria` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_ACT_29_', l.contract_id) AS edge_id,
  l.contract_id,
  'regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029' AS provision_slot_id,
  '은행업감독규정 제29조 대손충당금 최소적립기준 심사 관할 여신 (단서 해당 여부는 원장 컬럼 실시간 대조 필요)' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_ACT_21_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_21_three_dates' AS provision_slot_id,
  '별빛은행 내규 제21조 대출 3대 기준일자(등록일·체결일·실행일) 구분 적용 대상 여신' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_ACT_22_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_22_rate_formula_abc' AS provision_slot_id,
  '별빛은행 내규 제22조 대출금리 산식(A+B-C) 및 비교공시 기준 적용 대상 여신' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_WO_27_', l.contract_id) AS edge_id,
  l.contract_id,
  'regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027' AS provision_slot_id,
  '은행업감독규정 제27조제4항 대손상각 특수채권 사후관리 관할 계좌' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status = 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_WO_14_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency' AS provision_slot_id,
  '별빛은행 내규 제14조 대손상각 특수채권의 부서별 연체율 산입 여부 심사 대상 계좌' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.account_status = 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_WK_RA_', w.contract_id) AS edge_id,
  w.contract_id,
  'regulations/02_law_annex3_criteria/sec03_restructured_loan_exceptions/annex3_item_03_ra_restructured_exemption' AS provision_slot_id,
  '채권재조정 이력 보유 여신 — 별표3 제3호 라목 고정이하 분류 제외 특례 심사 대상 (요건 충족 여부는 원장 대조 필요)' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.workout_histories` w
UNION ALL
SELECT
  CONCAT('GOV_OD_16_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule' AS provision_slot_id,
  '원리금 연체 발생 여신 — 내규 제16조 기한이익상실(EOD) 예정 통지 기준 심사 대상' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.overdue_days > 0 AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_OD_18_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver' AS provision_slot_id,
  '원리금 연체 발생 여신 — 내규 제18조 기한이익상실 유예 특례 심사 대상 (요건 충족 여부는 담보·워크아웃·결재 원장 대조 필요)' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.overdue_days > 0 AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
UNION ALL
SELECT
  CONCAT('GOV_TCB_25_', l.contract_id) AS edge_id,
  l.contract_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion' AS provision_slot_id,
  'TCB 기술혁신 운전자금 상품 — 내규 제25조제1항 우대금리 전결 상한 및 부채비율 상한 심사 대상' AS binding_reason
FROM `finance-ontology-changseop.starlight_bank.ont_loan_contracts` l
WHERE l.product_code = 'PROD_TCB_WORKING';

-- Pure Real-Time SQL View over Spanner `ont_rate_cut_requests`
CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_evaluated_under_provision` (
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
FROM `finance-ontology-changseop.starlight_bank.ont_rate_cut_requests` r
UNION ALL
SELECT
  CONCAT('EVAL_INT25_', r.request_id) AS edge_id,
  r.request_id,
  'internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion' AS provision_slot_id,
  '별빛은행 내규 제25조제2항 (특허권 취득 사유 금리인하요구 심사 기준) 심사 관할' AS evaluation_reason
FROM `finance-ontology-changseop.starlight_bank.ont_rate_cut_requests` r;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_part_of_document` (
  provision_slot_id OPTIONS(description="개별 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  doc_id OPTIONS(description="소속 원본 법령·내규 문서 식별자 (Destination FK -> SourceDocument.doc_id)")
)
OPTIONS(description="[Edge: PART_OF_DOCUMENT] 174개 개별 조문이 어느 원본 법령·내규 문서(10종)에 속하는지 연결하는 엣지")
AS SELECT provision_slot_id, doc_id FROM `finance-ontology-changseop.starlight_bank_ontology.lex_provisions`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_exception_proviso` (
  edge_id OPTIONS(description="본칙-단서/특례 조문 연결 엣지 고유 식별자 (PK)"),
  base_slot_id OPTIONS(description="원칙(본칙) 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  proviso_slot_id OPTIONS(description="단서·예외·특례 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  exception_condition OPTIONS(description="본칙에서 단서·특례로 분기되는 예외 성립 요건 한 줄 요약")
)
OPTIONS(description="[Edge: HAS_EXCEPTION_PROVISO] 원칙 조문(본칙)에서 단서·예외·특례 조문으로 분기하는 법령 내부 엣지")
AS SELECT edge_id, base_slot_id, proviso_slot_id, exception_condition FROM `finance-ontology-changseop.starlight_bank_ontology.edge_has_exception_proviso`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_delegates_to_internal` (
  edge_id OPTIONS(description="상위법령-당행내규 위임 엣지 고유 식별자 (PK)"),
  external_slot_id OPTIONS(description="상위 감독규정·모범규준 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  internal_slot_id OPTIONS(description="위임받아 구체화한 별빛은행 내규 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  delegation_scope OPTIONS(description="상위 규정이 당행 내규에 위임하거나 구체화한 세부 운영 기준 설명")
)
OPTIONS(description="[Edge: DELEGATES_TO_INTERNAL] 상위 감독규정·모범규준이 별빛은행 자체 내규 조문으로 세부 기준을 위임·구체화하는 엣지")
AS SELECT edge_id, external_slot_id, internal_slot_id, delegation_scope FROM `finance-ontology-changseop.starlight_bank_ontology.edge_delegates_to_internal`;

CREATE OR REPLACE VIEW `finance-ontology-changseop.starlight_bank_ontology.v_edge_conflicts_by_sector` (
  edge_id OPTIONS(description="업권·여신유형 충돌 대조 엣지 고유 식별자 (PK)"),
  bank_slot_id OPTIONS(description="시중은행 기업여신 정식 적용 조문 슬롯 식별자 (Source FK -> Provision.provision_slot_id)"),
  distractor_slot_id OPTIONS(description="혼입 차단 대상 타업권(저축은행)·타세그먼트 교란 조문 슬롯 식별자 (Destination FK -> Provision.provision_slot_id)"),
  conflict_warning OPTIONS(description="두 조문을 혼동하면 안 되는 업권·세그먼트 차이 경고 설명")
)
OPTIONS(description="[Edge: CONFLICTS_BY_SECTOR] 시중은행 기업여신 규정과 상호저축은행(타업권)·가계여신 규정 간의 오적용 방지 대조 엣지")
AS SELECT edge_id, bank_slot_id, distractor_slot_id, conflict_warning FROM `finance-ontology-changseop.starlight_bank_ontology.edge_conflicts_by_sector`;


-- ============================================================================
-- 3. CREATE OR REPLACE PROPERTY GRAPH `starlight_bank_ontology.finance_graph`
-- ============================================================================

CREATE OR REPLACE PROPERTY GRAPH `finance-ontology-changseop.starlight_bank_ontology.finance_graph`
  NODE TABLES (
    `finance-ontology-changseop.starlight_bank_ontology.v_node_business_context`
      KEY (context_id)
      LABEL BusinessContext,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_source_document`
      KEY (doc_id)
      LABEL SourceDocument,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_provision`
      KEY (provision_slot_id)
      LABEL Provision,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract`
      KEY (contract_id)
      LABEL LoanContract,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_customer`
      KEY (customer_id)
      LABEL Customer,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_financial_product`
      KEY (product_code)
      LABEL FinancialProduct,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_workout_history`
      KEY (workout_id)
      LABEL WorkoutHistory,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_collateral`
      KEY (collateral_id)
      LABEL Collateral,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_delinquency_event`
      KEY (event_id)
      LABEL DelinquencyEvent,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_rate_cut_request`
      KEY (request_id)
      LABEL RateCutRequest,
    `finance-ontology-changseop.starlight_bank_ontology.v_node_exception_approval`
      KEY (approval_id)
      LABEL ExceptionApproval
  )
  EDGE TABLES (
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_borrowed_by`
      KEY (contract_id, customer_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (customer_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_customer` (customer_id)
      LABEL BORROWED_BY,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_of_product`
      KEY (contract_id, product_code)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (product_code) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_financial_product` (product_code)
      LABEL OF_PRODUCT,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_collateral`
      KEY (contract_id, collateral_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (collateral_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_collateral` (collateral_id)
      LABEL HAS_COLLATERAL,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_delinquency`
      KEY (contract_id, event_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (event_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_delinquency_event` (event_id)
      LABEL HAS_DELINQUENCY,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_rate_cut_request`
      KEY (contract_id, request_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (request_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_rate_cut_request` (request_id)
      LABEL HAS_RATE_CUT_REQUEST,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_exception_approval`
      KEY (contract_id, approval_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (approval_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_exception_approval` (approval_id)
      LABEL HAS_EXCEPTION_APPROVAL,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_workout_history`
      KEY (contract_id, workout_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (workout_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_workout_history` (workout_id)
      LABEL HAS_WORKOUT_HISTORY,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_scopes_portfolio`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_business_context` (context_id)
      DESTINATION KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      LABEL SCOPES_PORTFOLIO,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_invokes_provision`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_business_context` (context_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      LABEL INVOKES_PROVISION,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_governed_by_criteria`
      KEY (edge_id)
      SOURCE KEY (contract_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_loan_contract` (contract_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      LABEL GOVERNED_BY_CRITERIA,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_evaluated_under_provision`
      KEY (edge_id)
      SOURCE KEY (request_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_rate_cut_request` (request_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      LABEL EVALUATED_UNDER_PROVISION,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_part_of_document`
      KEY (provision_slot_id, doc_id)
      SOURCE KEY (provision_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (doc_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_source_document` (doc_id)
      LABEL PART_OF_DOCUMENT,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_has_exception_proviso`
      KEY (edge_id)
      SOURCE KEY (base_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (proviso_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      LABEL HAS_EXCEPTION_PROVISO,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_delegates_to_internal`
      KEY (edge_id)
      SOURCE KEY (external_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (internal_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      LABEL DELEGATES_TO_INTERNAL,
    `finance-ontology-changseop.starlight_bank_ontology.v_edge_conflicts_by_sector`
      KEY (edge_id)
      SOURCE KEY (bank_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      DESTINATION KEY (distractor_slot_id) REFERENCES `finance-ontology-changseop.starlight_bank_ontology.v_node_provision` (provision_slot_id)
      LABEL CONFLICTS_BY_SECTOR
  );
