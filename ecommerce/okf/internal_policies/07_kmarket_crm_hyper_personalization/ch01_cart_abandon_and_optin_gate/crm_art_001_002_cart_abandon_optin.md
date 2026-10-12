---
type: Provision
title: 내규 제1조·제2조 — 장바구니 이탈(`event_type = 'cart'`) 탐지 및 `users.marketing_opt_in =
  True` 필수 검증
description: 장바구니 미결제 이탈 고객에게 리마인드·타겟팅 쿠폰 발급 전 `marketing_opt_in = True` 확인 의무 및 미동의자
  발급 차단.
tags:
- internal_policies
- synthetic
- 07_kmarket_crm_hyper_personalization
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf
  kind: origin_document
  sha256: 317d42e3328a520f9957261af8fe904f2cfe6330e74bb3a0bce3690df58940b7
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
part_of: /internal_policies/07_kmarket_crm_hyper_personalization/doc.md
sequence: 1
treatment: verbatim_ko
license: K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)
content_class: synthetic
section_number: 제1조~제2조
source_page: 1
source_pages_span:
- 1
verified:
- by: process:verify_provisions/1.0
  at: '2026-10-03T06:00:00Z'
  method: source_text_match
  checks:
  - P1_body
  - P2_heading
  - P3_page
  - P4_digest
contacts: K마켙 AI추천랩장 <ai-reco@kmarket.co.kr>
---

# 내규 제1조·제2조 — 장바구니 이탈(`event_type = 'cart'`) 탐지 및 `users.marketing_opt_in = True` 필수 검증

* **상위 문서 (`Source Document`)**: [K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 (제CRM-2025-01호)](/internal_policies/07_kmarket_crm_hyper_personalization/doc.md)[^origin_pdf]
* **출처 페이지**: `07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf` — **1쪽** (`section_number: 제1조~제2조`)

## 원문 발췌 (Verbatim Source Text)

제1조(목적) 이 내규는 주식회사 K마켙(이하 "당사"라 한다)이 운영하는 온라인
패션·라이프스타일 플랫폼에서 고객 행동로그와 상품·재고 원장을 결합하여 초개인화 상품
추천 및 타겟팅 할인쿠폰을 발급할 때 준수하여야 할 비즈니스 의사결정 기준과
개인정보·공정거래 가드레일을 정함을 목적으로 한다.
제2조(장바구니 미결제 이탈 고객 실시간 탐지 및 동의 검증 의무) ① AI추천랩 및
CRM 시스템은 실시간 행동로그 원장(`events`)에서 이벤트 유형이 장바구니
담기(`event_type = 'cart'`)로 기록된 후 동일
세션(`session_id`) 내에 결제완료(`purchase`) 이벤트가 발생하지
아니한 미결제 이탈 고객을 실시간 탐지한다.
② 제1항에 따라 탐지된 고객에게 장바구니 리마인드 알림이나 개인화 타겟팅 쿠폰을
발급하기 전에, 반드시 회원 원장(`users`)의 마케팅 및 맞춤형 추천 동의
여부(`marketing_opt_in`)를 조회하여야 한다.
③ `users.marketing_opt_in = True`인 회원에 한하여 개인화
추천 및 타겟팅 쿠폰을 발급할 수 있으며, `users.marketing_opt_in
= False`인 회원에 대하여는 어떠한 경우에도 개인 식별 기반 리마인드 푸시나
타겟팅 쿠폰을 발급하여서는 아니 된다(개인정보보호위원회 행태정보 가이드라인 제3조
준수).

K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 ― Page 1 / 2
