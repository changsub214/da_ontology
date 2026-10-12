---
type: Provision
title: 내규 제4조 — 자발적·차별화 단독 행사(`VOLUNTARY_PROMO_FILING`) 예외 요건 및 상시 캠페인 기각(`REJECTED`)
  원칙
description: 상시 장바구니·등급 쿠폰 캠페인에 대한 50% 초과 분담 신청은 즉시 기각(`REJECTED`)하고 50% 상한 캡을 적용.
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
sequence: 3
treatment: verbatim_ko
license: K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)
content_class: synthetic
section_number: 제4조
source_page: 2
source_pages_span:
- 2
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

# 내규 제4조 — 자발적·차별화 단독 행사(`VOLUNTARY_PROMO_FILING`) 예외 요건 및 상시 캠페인 기각(`REJECTED`) 원칙

* **상위 문서 (`Source Document`)**: [K마켙 입점브랜드 공동프로모션 및 쿠폰분담금 정산내규 (제PARTNER-2025-03호)](/internal_policies/09_kmarket_vendor_promo_settlement/doc.md)[^origin_pdf]
* **출처 페이지**: `09_INTERNAL_K마켙_입점브랜드_공동프로모션_정산내규_2025.pdf` — **2쪽** (`section_number: 제4조`)

## 원문 발췌 (Verbatim Source Text)

제4조(납품업자 자발적·차별화 단독 행사 예외의 엄격한 요건) ① 대규모유통업법
제11조제5항 단서에 따라 입점브랜드에 50%를 초과하는 판촉비 분담률을 예외적으로
적용하려면, 캠페인 예외승인 원장(`campaign_exceptions`)에 예외
유형이 `VOLUNTARY_PROMO_FILING`으로 등재되어 있고 승인 상태가
`APPROVED`여야 한다.
② 준법감시실은 입점브랜드가 K마켙의 상시 등급쿠폰·장바구니 리마인드 행사에 단순
참여한 건에 대하여 브랜드가 50% 초과 분담을 신청하더라도 자발성·차별성 요건
미충족을 사유로 즉시 기각(`status = 'REJECTED'`)하여야 하며, 기각된
건은 제3조제2항에 따라 반드시 50% 상한 캡을 적용하여 정산한다.

K마켙 입점브랜드 공동프로모션 및 쿠폰분담금 정산내규 ― Page 2 / 2
