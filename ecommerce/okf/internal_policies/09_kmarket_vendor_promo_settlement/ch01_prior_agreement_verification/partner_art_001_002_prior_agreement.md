---
type: Provision
title: 내규 제1조·제2조 — 사전 서면약정(`signed_promo_agreement`) 검증 의무 및 미체결 시 K마켙 100% 부담
description: '`signed_promo_agreement = False`인 브랜드 상품의 쿠폰할인액은 브랜드 분담금 0원, K마켙이 100%
  부담.'
tags:
- internal_policies
- synthetic
- 09_kmarket_vendor_promo_settlement
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/09_INTERNAL_K마켙_입점브랜드_공동프로모션_정산내규_2025.pdf
  kind: origin_document
  sha256: e1248ac400cce4b5798f464f261536eced0c5271b0115c7c8f290a31eda2525d
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
part_of: /internal_policies/09_kmarket_vendor_promo_settlement/doc.md
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
contacts: K마켙 파트너상생본부장 <partner-cp@kmarket.co.kr>
---

# 내규 제1조·제2조 — 사전 서면약정(`signed_promo_agreement`) 검증 의무 및 미체결 시 K마켙 100% 부담

* **상위 문서 (`Source Document`)**: [K마켙 입점브랜드 공동프로모션 및 쿠폰분담금 정산내규 (제PARTNER-2025-03호)](/internal_policies/09_kmarket_vendor_promo_settlement/doc.md)[^origin_pdf]
* **출처 페이지**: `09_INTERNAL_K마켙_입점브랜드_공동프로모션_정산내규_2025.pdf` — **1쪽** (`section_number: 제1조~제2조`)

## 원문 발췌 (Verbatim Source Text)

제1조(목적) 이 내규는 K마켙과 입점브랜드(납품업자) 간에 실시하는 공동 프로모션,
CRM 타겟팅 쿠폰 및 코디 번들 할인행사에 소요되는 판매촉진비용(쿠폰할인액)을
정산함에 있어 「대규모유통업에서의 거래공정화에 관한 법률」 제11조 및 공정거래위원회
심사지침을 철저히 준수하기 위한 내부 통제 및 정산 산식을 규정함을 목적으로 한다.
제2조(사전 서면약정 유무 검증 의무) ① 정산시스템 및 에이전트는
주문상품(`order_items`)에 적용된
쿠폰할인액(`coupon_discount_krw`) 중 일부를
입점브랜드(`brand_vendor_contracts`)에 분담시키기 전에, 반드시
해당 브랜드 계약 원장의 사전 판촉약정 체결
여부(`signed_promo_agreement`)를 확인하여야 한다.
② 만약 `signed_promo_agreement = False`인 브랜드의 상품에
쿠폰이 적용된 경우, 입점브랜드 분담금은 0원으로 처리하고 쿠폰할인액의 100%를
K마켙 마케팅 예산에서 부담하여야 한다.

K마켙 입점브랜드 공동프로모션 및 쿠폰분담금 정산내규 ― Page 1 / 2
