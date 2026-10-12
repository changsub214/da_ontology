---
type: Provision
title: 내규 제1조·제2조 — 실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`) 및 상시
  25.0% 하한 가드레일
description: 모든 상시 쿠폰·번들 할인 시 개별 상품 실현마진율 25.0% 이상 유지 의무 및 미달 저마진 상품 자동 차단.
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
contacts: K마켙 가격전략실장 <md-pricing@kmarket.co.kr>
---

# 내규 제1조·제2조 — 실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`) 및 상시 25.0% 하한 가드레일

* **상위 문서 (`Source Document`)**: [K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 (제MD-2025-02호)](/internal_policies/08_kmarket_md_margin_and_clearance/doc.md)[^origin_pdf]
* **출처 페이지**: `08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf` — **1쪽** (`section_number: 제1조~제2조`)

## 원문 발췌 (Verbatim Source Text)

제1조(목적) 이 내규는 K마켙에서 판매되는 직매입·특약매입·위수탁 상품의 수익성을
방어하고 무분별한 할인쿠폰 남발로 인한 역마진을 방지하기 위하여, 상품 마진율 산정
산식과 상시 최저마진 가드레일 및 체화재고(악성재고) 클리어런스 특례 기준을 정함을
목적으로 한다.
제2조(매출총이익률 산식 및 상시 프로모션 최저마진 25% 가드레일) ① 개별 상품의
프로모션 적용 후 매출총이익률(Gross Margin Ratio, 이하
"실현마진율"이라 한다)은 다음 산식에 의하여 계산한다.
* 실현마진율 = (`sale_price_krw` - `cost_krw`) /
`sale_price_krw`
(여기서 `sale_price_krw`는 정상 판매가
`retail_price_krw`에서 쿠폰할인액
`coupon_discount_krw`를 차감한 고객 실결제가격이며,
`cost_krw`는 상품 매입원가이다.)
② 모든 상시 프로모션, CRM 타겟팅 쿠폰 및 코디 번들 할인 적용 시 개별 상품의
실현마진율은 100분의 25(25.0%) 이상을 유지하여야 한다(상시 최저마진
가드레일).
③ 기본 마진율(`(retail_price_krw - cost_krw) /
retail_price_krw`)이 낮아 할인쿠폰 적용 시 실현마진율이 25.0%
미만으로 하락하는 저마진 상품은 원칙적으로 자동 할인쿠폰 적용 대상에서
제외(Block)하여야 한다.

K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 ― Page 1 / 2
