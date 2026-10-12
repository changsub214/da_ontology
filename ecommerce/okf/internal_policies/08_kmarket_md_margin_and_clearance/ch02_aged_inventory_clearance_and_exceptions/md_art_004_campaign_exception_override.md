---
type: Provision
title: 내규 제4조 — 캠페인 예외승인 원장(`campaign_exceptions`) `APPROVED` 검증 및 기각/만료 건 사용 금지
description: '`CLEARANCE_OVERRIDE` 또는 `VIP_RETENTION` 승인(`APPROVED`) 시 승인된 하한율(`approved_margin_floor`)까지
  가드레일 완화 허용.'
tags:
- internal_policies
- synthetic
- 08_kmarket_md_margin_and_clearance
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf
  kind: origin_document
  sha256: c9e2115f48d5db99dd1e82563930f0903534e81f96e73c40b784d98c8c98b72e
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
part_of: /internal_policies/08_kmarket_md_margin_and_clearance/doc.md
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
contacts: K마켙 가격전략실장 <md-pricing@kmarket.co.kr>
---

# 내규 제4조 — 캠페인 예외승인 원장(`campaign_exceptions`) `APPROVED` 검증 및 기각/만료 건 사용 금지

* **상위 문서 (`Source Document`)**: [K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 (제MD-2025-02호)](/internal_policies/08_kmarket_md_margin_and_clearance/doc.md)[^origin_pdf]
* **출처 페이지**: `08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf` — **2쪽** (`section_number: 제4조`)

## 원문 발췌 (Verbatim Source Text)

제4조(캠페인 예외승인 원장 검증 및 우회 기준) ① 체화재고 완화 요건이나 상시
마진율 25% 기준에 대한 예외를 적용하여 CRM 번들 쿠폰이나 클리어런스 특가를
실행하려는 경우, 실시간 캠페인 예외승인
원장(`campaign_exceptions`)에 승인 상태(`status =
'APPROVED'`)로 등록된 유효한 예외승인 코드(`exception_id`)가
존재하는지 확인하여야 한다.
② 적격 예외승인 유형(`exception_type`)은 다음 각 호와 같다.
1. `CLEARANCE_OVERRIDE`: 체화재고(`stock_age_days >=
90`) 또는 시즌오프 재고 소진을 위하여 MD본부장이 최저마진 하한을 승인된
하한율(`approved_margin_floor`, 최소 10% 이상)까지 완화 승인한
건
2. `VIP_RETENTION`: VVIP·VIP 핵심 고객의 이탈 방지를 위하여
그로스마케팅본부장 및 MD본부장이 합의하여 코디 번들 구성 상품의 마진 하한을
한시적으로 완화 승인한 건
③ 승인 상태가 기각(`REJECTED`)이거나 만료(`EXPIRED`)된 예외승인
건은 가격결정 및 쿠폰 발급의 근거로 사용할 수 없다.

K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 ― Page 2 / 2
