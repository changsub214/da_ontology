---
type: Provision
title: 내규 제3조 — 납품업자 분담비율 50% 법정 상한 캡(`MIN(promo_cost_share_ratio, 0.50)`) 적용 및 초과분
  K마켙 흡수 산식
description: 계약상 `promo_cost_share_ratio`가 50%를 초과해도 최대 50%만 브랜드에 공제하고 초과분은 K마켙이 의무
  흡수 부담.
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
sequence: 2
treatment: verbatim_ko
license: K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)
content_class: synthetic
section_number: 제3조
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

# 내규 제3조 — 납품업자 분담비율 50% 법정 상한 캡(`MIN(promo_cost_share_ratio, 0.50)`) 적용 및 초과분 K마켙 흡수 산식

* **상위 문서 (`Source Document`)**: [K마켙 입점브랜드 공동프로모션 및 쿠폰분담금 정산내규 (제PARTNER-2025-03호)](/internal_policies/09_kmarket_vendor_promo_settlement/doc.md)[^origin_pdf]
* **출처 페이지**: `09_INTERNAL_K마켙_입점브랜드_공동프로모션_정산내규_2025.pdf` — **2쪽** (`section_number: 제3조`)

## 원문 발췌 (Verbatim Source Text)

제3조(납품업자 쿠폰 분담비율 50% 법정 상한 적용 및 초과분 K마켙 흡수 원칙) ①
사전 서면약정(`signed_promo_agreement = True`)이 체결된
입점브랜드라 하더라도, 대규모유통업법 제11조제4항에 따라 입점브랜드가 실제로 부담하는
판매촉진비용 분담비율은 총 쿠폰할인액(`coupon_discount_krw`)의
100분의 50(50.0%)을 초과할 수 없다.
② 입점브랜드 계약 원장(`brand_vendor_contracts`)에 기재된 약정
판촉비 분담률(`promo_cost_share_ratio`)이 0.50(50%)을
초과하는 경우(예: `promo_cost_share_ratio = 0.60` 즉 60%
약정), 정산 시에는 법정 상한인 0.50(50%)으로 자동 캡(Cap)을 씌워
산정하며, 약정 분담률과 법정 상한(50%)의 차액에 해당하는 초과분은 전액 K마켙이
흡수하여 부담한다.
③ 구체적인 주문건별·브랜드별 쿠폰 분담금 정산 산식은 다음과 같다.
1. 약정 기준 브랜드 분담액(캡 적용 전) =
`coupon_discount_krw` × `promo_cost_share_ratio`
2. 법정 유효 브랜드 분담률 =
`MIN(promo_cost_share_ratio, 0.50)` (단, 제4조의 자발적
차별화 행사 예외 승인 건은 제외)
3. 최종 브랜드 정산 공제액(납품업자 실부담액) =
`coupon_discount_krw` ×
`MIN(promo_cost_share_ratio, 0.50)`
4. K마켙 최종 부담액 = `coupon_discount_krw` - 최종 브랜드
정산 공제액 (여기에는 법 제11조제4항에 따라 K마켙이 의무 흡수한 50% 초과분
`coupon_discount_krw × MAX(0,
promo_cost_share_ratio - 0.50)`이 포함된다.)
