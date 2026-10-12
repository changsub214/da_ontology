---
type: Provision
title: 내규 제3조 — 체화재고(`stock_age_days >= 90` & `available_stock >= 30`) 최저마진 10.0%
  완화 및 최대 30% 클리어런스 할인 특례
description: 입고 후 90일 이상 경과하고 가용재고 30개 이상인 체화재고는 최저마진 하한을 25%에서 10%로 완화.
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
contacts: K마켙 가격전략실장 <md-pricing@kmarket.co.kr>
---

# 내규 제3조 — 체화재고(`stock_age_days >= 90` & `available_stock >= 30`) 최저마진 10.0% 완화 및 최대 30% 클리어런스 할인 특례

* **상위 문서 (`Source Document`)**: [K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 (제MD-2025-02호)](/internal_policies/08_kmarket_md_margin_and_clearance/doc.md)[^origin_pdf]
* **출처 페이지**: `08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf` — **2쪽** (`section_number: 제3조`)

## 원문 발췌 (Verbatim Source Text)

제3조(체화재고의 정의 및 클리어런스 마진 하한 완화 특례) ① 물류
원장(`inventory_items`)상 입고 후
경과일수(`stock_age_days`)가 90일 이상이고
가용재고(`available_stock`)가 30개 이상 누적된 상품은
'체화재고(Slow-moving / Aged Inventory)'로 분류한다.
② 제2조제2항에도 불구하고, 제1항의 체화재고(`stock_age_days >=
90`)에 해당하는 상품에 대하여는 창고 보관료 절감 및 현금흐름 회수를 위하여
최저마진 가드레일 하한선을 100분의 25(25.0%)에서 100분의
10(10.0%)으로 완화하며, 정상 판매가 대비 최대 30%까지 클리어런스 할인쿠폰
또는 번들 할인을 적용할 수 있다.
