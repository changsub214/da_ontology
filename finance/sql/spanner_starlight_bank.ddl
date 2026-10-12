-- ---------------------------------------------------------------------------
-- Spanner `finance-cs` / `starlight_bank` — 계정계 트랜잭션 원장 5종
--
-- ADR 0002 결정에 따라 트랜잭션성 테이블만 Spanner 에 둔다.
--   loan_contracts (루트)
--     └ collaterals / delinquency_events / rate_cut_requests / exception_approvals
--       (INTERLEAVE IN PARENT — 계약 단위 단일 split 조회)
--
-- 주의: 마스터 3종(customers / financial_products / workout_histories)은 BigQuery
--       `starlight_bank` 데이터셋에만 존재하므로, 여기의 customer_id / product_code 는
--       DB 제약(FK)이 아닌 스토어 간 논리 참조 키다. 무결성은 적재 게이트 G02 로 검증한다.
--
-- 주의: Spanner external dataset 은 기본(default) 스키마의 테이블만 BigQuery 에 노출하므로
--       named schema 를 사용하지 않는다.
-- ---------------------------------------------------------------------------

CREATE TABLE loan_contracts (
  contract_id             STRING(64) NOT NULL,
  customer_id             STRING(64) NOT NULL,        -- 논리 참조: bigquery starlight_bank.customers
  borrower_name           STRING(128),                -- 역정규화 (원장 조회 편의)
  ksic_section_code       STRING(8),                  -- 역정규화 (제29조 가목 F/G/H/L 단서 판정)
  product_code            STRING(64),                 -- 논리 참조: bigquery starlight_bank.financial_products
  reg_dt                  DATE,                       -- 데이터 등록일
  contract_dt             DATE,                       -- 계약 체결일
  disburse_dt             DATE,                       -- 대출 실행일
  base_rate               FLOAT64,                    -- 기준금리 (%)
  spread_rate             FLOAT64,                    -- 가산금리 (%)
  pref_rate               FLOAT64,                    -- 우대금리 (%)
  applied_rate            FLOAT64,                    -- 적용금리 (= base + spread - pref)
  contract_amt            INT64,                      -- 약정금액 (KRW)
  outstanding_amt         INT64,                      -- 대출잔액 (KRW)
  overdue_days            INT64,                      -- 연체일수
  asset_classification    STRING(32),                 -- NORMAL/PRECAUTIONARY/SUBSTANDARD/DOUBTFUL/ESTIMATED_LOSS
  rehab_priority_claim_yn STRING(1),                  -- 회생법 제180조제2항 공익채권 여부
  booked_provision_krw    INT64,                      -- 장부상 대손충당금 (KRW)
  account_status          STRING(32),
) PRIMARY KEY (contract_id);

CREATE TABLE collaterals (
  contract_id              STRING(64) NOT NULL,
  collateral_id            STRING(64) NOT NULL,
  customer_id              STRING(64),
  collateral_type_code     STRING(64),
  guarantee_agency_code    STRING(32),                -- KODIT / KIBO / SGI ...
  guarantee_ratio_pct      FLOAT64,                   -- 보증비율 (내규 제18조 85% 기준)
  appraised_collateral_krw INT64,
) PRIMARY KEY (contract_id, collateral_id),
  INTERLEAVE IN PARENT loan_contracts ON DELETE CASCADE;

CREATE TABLE delinquency_events (
  contract_id            STRING(64) NOT NULL,
  event_id               STRING(64) NOT NULL,
  customer_id            STRING(64),
  overdue_days           INT64,                       -- EWS 10d / 공시 30d / NPL 90d 분기 기준
  overdue_principal_krw  INT64,
  overdue_interest_krw   INT64,
  write_off_yn           STRING(1),                   -- 상각특수채권 여부
) PRIMARY KEY (contract_id, event_id),
  INTERLEAVE IN PARENT loan_contracts ON DELETE CASCADE;

CREATE TABLE rate_cut_requests (
  contract_id             STRING(64) NOT NULL,
  request_id              STRING(64) NOT NULL,
  customer_id             STRING(64),
  request_dt              DATE,
  application_reason_code STRING(64),                 -- PATENT_ACQUISITION 등
  patent_reg_no           STRING(64),
  credit_rating_before    STRING(16),
  credit_rating_after     STRING(16),
  yoy_revenue_growth_pct  FLOAT64,
  review_status_code      STRING(32),                 -- 접수→심사→APPROVED/REJECTED 상태 전이
  approved_cut_bp         INT64,
) PRIMARY KEY (contract_id, request_id),
  INTERLEAVE IN PARENT loan_contracts ON DELETE CASCADE;

CREATE TABLE exception_approvals (
  contract_id         STRING(64) NOT NULL,
  approval_id         STRING(64) NOT NULL,
  customer_id         STRING(64),
  approval_type_code  STRING(64),                     -- EOD_DEFERRAL_REVIEW 등
  approval_status     STRING(32),
  approver_role_code  STRING(64),
  approval_dt         DATE,
) PRIMARY KEY (contract_id, approval_id),
  INTERLEAVE IN PARENT loan_contracts ON DELETE CASCADE;
