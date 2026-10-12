---
type: Provision
title: 제21조 (대출계약 3대 기준일자의 전산 구분 — 등록일 reg_dt · 체결일 contract_dt · 실행일 disburse_dt)
description: '전산등록일(reg_dt), 대출계약 체결일(contract_dt: 특정일자 체결 대출 필수 기준), 자금실행일(disburse_dt)
  구분 의무.'
tags:
- internal_policies
- synthetic
- 10_byulbit_bank_credit_rate_policy
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/10_SYNTHETIC_별빛은행_기업여신심사_및_금리운영_내규.pdf
  kind: origin_document
  sha256: 39396b77fc7ef4b547095c7bf3c2bb188ddb9c89b82e5b14451764525dc722dc
generated:
  by: process:build_okf/3.0
  at: '2026-09-22T04:00:00Z'
status: stable
part_of: /internal_policies/10_byulbit_bank_credit_rate_policy/doc.md
sequence: 4
treatment: verbatim_ko
license: Internal Clean-room Demonstration Policy (Synthetic)
content_class: synthetic
section_number: 내규 제21조
source_page: 1
source_pages_span:
- 1
- 2
verified:
- by: process:verify_provisions/1.0
  at: '2026-09-22T04:00:00Z'
  method: source_text_match
  checks:
  - P1_body
  - P2_heading
  - P3_page
  - P4_digest
contacts: 신영만(과장) - 데이터거버넌스팀 <youngman@starlightbk.com>
---

# 제21조 (대출계약 3대 기준일자의 전산 구분 — 등록일 reg_dt · 체결일 contract_dt · 실행일 disburse_dt)

* **상위 문서 (`Source Document`)**: [[당행내규 제2026-08호] 별빛은행 기업여신 심사 · 조기경보(EWS) 및 금리운영 내규](/internal_policies/10_byulbit_bank_credit_rate_policy/doc.md)[^origin_pdf]
* **출처 페이지**: `10_SYNTHETIC_별빛은행_기업여신심사_및_금리운영_내규.pdf` — **1, 2쪽** (`section_number: 내규 제21조`)

## 원문 발췌 (Verbatim Source Text)

제21조 (대출계약 3대 기준일자의 전산 구분)
① 코어뱅킹 여신원장(LoanContract)에서 실적을 집계할 때에는 다음 각 호의 일자를 엄격히 구분하여야 한
다.
1. 전산정보 등록일(reg_dt): 여신심사 신청 및 한도 산정이 전산에 최초 입력된 일자
2. 대출계약 체결일(contract_dt): 차주와 은행 간 여신거래약정서 서명·날인이 완료되어 법적 효력이 발생한



일자 ("특정일자 체결 대출" 조회 시 필수 기준 컬럼)
3. 자금 실행일(disburse_dt): 실제 대출금이 차주 계좌로 입금된 일자
