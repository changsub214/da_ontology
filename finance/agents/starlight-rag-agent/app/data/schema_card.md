# starlight_bank 스키마 카드 (빌드 시 INFORMATION_SCHEMA 에서 생성 · tools: scratch build_schema_card.py)

- 프로젝트: `finance-ontology-changseop` · 데이터셋: `starlight_bank` · 위치: us-central1
- `ont_*` 는 Cloud Spanner 원장을 보는 연합 뷰(읽기 전용). 금액 컬럼 `*_krw`, `*_amt` 는 원 단위.
- 쿼리는 반드시 `finance-ontology-changseop.starlight_bank.<table>` 로 완전 수식한다.

## customers (100행)
- `customer_id` STRING
- `borrower_name` STRING
- `corp_reg_no` STRING
- `ksic_section_code` STRING — 값: C, F, G, H, I, L
- `ksic_detail_code` STRING
- `industry_name` STRING
- `credit_rating` STRING — 값: A-, BB+, BBB, BBB+, BBB-, CCC, D
- `tcb_tech_grade` STRING — 값: T2, T3, T4, T5, T6
- `debt_ratio_pct` FLOAT64

## financial_products (4행)
- `product_code` STRING — 값: PROD_CONST_REALESTATE, PROD_CORP_PRIME_WC, PROD_RESTRUCTURED_DIP, PROD_TCB_WORKING
- `product_name` STRING — 값: 별빛 TCB 기술혁신 운전자금, 별빛 기업구조조정·회생운전자금, 별빛 프라임 중견기업 운전자금, 별빛 프로젝트·시설기업자금
- `loan_category` STRING — 값: CORPORATE_FACILITY_LOAN, CORPORATE_WORKING_CAPITAL, CORPORATE_WORKOUT_DIP
- `target_segment` STRING — 값: GENERAL_CORP, MID_CAP_GENERAL, SME_TECH_CERTIFIED, WORKOUT_AND_REHAB_CORP
- `base_rate_benchmark` STRING — 값: FINANCIAL_BOND_1Y, FINANCIAL_BOND_6M, KORIBOR_3M
- `repayment_method` STRING — 값: BULLET_AT_MATURITY, EQUAL_PRINCIPAL_INSTALLMENT
- `max_maturity_months` INT64

## ont_collaterals (3행)
- `contract_id` STRING — 값: LN_2026_0001, LN_2026_0002, LN_2026_KSIC_L1
- `collateral_id` STRING — 값: COL_LN_2026_0001, COL_LN_2026_0002, COL_LN_2026_KSIC_L1
- `customer_id` STRING — 값: CUST_0001, CUST_0002, CUST_0004
- `collateral_type_code` STRING — 값: CREDIT_GUARANTEE_CERT, REAL_ESTATE_MORTGAGE
- `guarantee_agency_code` STRING — 값: FIRST_LIEN_TRUST, KODIT
- `guarantee_ratio_pct` FLOAT64
- `appraised_collateral_krw` INT64

## ont_delinquency_events (7행)
- `contract_id` STRING — 값: LN_2025_WRITEOFF_01, LN_2026_0001, LN_2026_0002, LN_2026_0003, LN_2026_0021, LN_2026_0022, LN_2026_0023
- `event_id` STRING — 값: DEL_LN_2025_WRITEOFF_01, DEL_LN_2026_0001, DEL_LN_2026_0002, DEL_LN_2026_0003, DEL_LN_2026_0021, DEL_LN_2026_0022, DEL_LN_2026_0023
- `customer_id` STRING — 값: CUST_0001, CUST_0002, CUST_0003, CUST_0015, CUST_0021, CUST_0022, CUST_0023
- `overdue_days` INT64
- `overdue_principal_krw` INT64
- `overdue_interest_krw` INT64
- `write_off_yn` STRING — 값: N, Y

## ont_exception_approvals (3행)
- `contract_id` STRING — 값: LN_2026_0001, LN_2026_0002, LN_2026_0003
- `approval_id` STRING — 값: APR_LN_2026_0001, APR_LN_2026_0002, APR_LN_2026_0003
- `customer_id` STRING — 값: CUST_0001, CUST_0002, CUST_0003
- `approval_type_code` STRING — 값: EOD_DEFERRAL_REVIEW
- `approval_status` STRING — 값: APPROVED, REJECTED
- `approver_role_code` STRING — 값: HQ_SENIOR_CREDIT_OFFICER
- `approval_dt` DATE

## ont_loan_contracts (100행)
- `contract_id` STRING
- `customer_id` STRING
- `borrower_name` STRING
- `ksic_section_code` STRING — 값: C, F, G, H, I, L
- `product_code` STRING — 값: PROD_CONST_REALESTATE, PROD_CORP_PRIME_WC, PROD_RESTRUCTURED_DIP, PROD_TCB_WORKING
- `reg_dt` DATE
- `contract_dt` DATE
- `disburse_dt` DATE
- `base_rate` FLOAT64
- `spread_rate` FLOAT64
- `pref_rate` FLOAT64
- `applied_rate` FLOAT64
- `contract_amt` INT64
- `outstanding_amt` INT64
- `overdue_days` INT64
- `asset_classification` STRING — 값: ESTIMATED_LOSS, NORMAL, PRECAUTIONARY, SUBSTANDARD
- `rehab_priority_claim_yn` STRING — 값: N, Y
- `booked_provision_krw` INT64
- `account_status` STRING — 값: ACTIVE_OVERDUE, ACTIVE_PERFORMING, ACTIVE_RESTRUCTURED, WRITTEN_OFF_SPECIAL_CLAIM

## ont_rate_cut_requests (2행)
- `contract_id` STRING — 값: LN_2026_0213_01, LN_2026_0213_02
- `request_id` STRING — 값: RCR_2026_01, RCR_2026_02
- `customer_id` STRING — 값: CUST_0007, CUST_0008
- `request_dt` DATE
- `application_reason_code` STRING — 값: PATENT_ACQUISITION
- `patent_reg_no` STRING
- `credit_rating_before` STRING — 값: BBB
- `credit_rating_after` STRING — 값: BBB, BBB+
- `yoy_revenue_growth_pct` FLOAT64
- `review_status_code` STRING — 값: APPROVED, REJECTED
- `approved_cut_bp` INT64

## workout_histories (3행)
- `workout_id` STRING — 값: WKO_LN_2026_0001, WKO_LN_2026_0002, WKO_LN_2026_0003
- `contract_id` STRING — 값: LN_2026_0001, LN_2026_0002, LN_2026_0003
- `customer_id` STRING — 값: CUST_0001, CUST_0002, CUST_0003
- `workout_start_dt` DATE
- `consecutive_normal_repay_months` INT64
- `new_equity_paid_in_krw` INT64
- `legal_proceeding_code` STRING — 값: CORP_RESTRUCT_ACT_WORKOUT, NONE, REHAB_ACT_ART180_2_DIP
