---
type: Provision
title: 제14조 (여신관리팀 조기경보 연체율 산정 기준 — 10일 이상 연체 및 대손상각 특수채권 포함)
description: 리스크관리위원회(고정이하) 및 금감원 공시(1월 이상, 특수채권 제외)와 구분되는 여신관리팀 조기경보(EWS) 실질관리 연체율
  산식.
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
sequence: 1
treatment: verbatim_ko
license: Internal Clean-room Demonstration Policy (Synthetic)
content_class: synthetic
section_number: 내규 제14조
source_page: 1
source_pages_span:
- 1
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

# 제14조 (여신관리팀 조기경보 연체율 산정 기준 — 10일 이상 연체 및 대손상각 특수채권 포함)

* **상위 문서 (`Source Document`)**: [[당행내규 제2026-08호] 별빛은행 기업여신 심사 · 조기경보(EWS) 및 금리운영 내규](/internal_policies/10_byulbit_bank_credit_rate_policy/doc.md)[^origin_pdf]
* **출처 페이지**: `10_SYNTHETIC_별빛은행_기업여신심사_및_금리운영_내규.pdf` — **1쪽** (`section_number: 내규 제14조`)

## 원문 발췌 (Verbatim Source Text)

제14조 (여신관리팀 조기경보 연체율 산정 기준)
① 리스크관리위원회 보고용 고정이하여신비율(은행업감독규정 제27조 및 별표3에 따른 3월 이상 연체 등
고정·회수의문·추정손실 합계 비율) 및 금융감독원 대외공시용 원화대출 연체율(1월 이상 원리금 연체 기준,
대손상각 특수채권 제외)과는 별도로, 여신관리팀은 조기경보(EWS) 목적의 실질관리 연체율
(ews_30d_special_ratio)을 산출·관리한다.
② 제1항의 여신관리팀 조기경보 실질관리 연체율은 다음 산식에 의한다.
1. 분자: 10일 이상 원리금 연체 기업여신 잔액 + 30일 이상 관리연체 잔액 + 회계상 대손상각 처리되어 특수
채권(written_oﬀ_special_claim)으로 편입된 미회수 원금 잔액
2. 분모: 대차대조표상 원화 기업여신 총잔액 + 대손상각 특수채권 미회수 원금 잔액
