---
type: Source Document
title: K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 (제MD-2025-02호)
description: 실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`), 상시 프로모션 25%
  최저마진 가드레일, 90일 이상 체화재고(`stock_age_days >= 90`) 10% 마진 하한 완화 특례 및 예외승인(`campaign_exceptions`)
  내규(2쪽).
tags:
- internal_policies
- synthetic
- 08_kmarket_md_margin_and_clearance
- verbatim_ko
resource: https://internal.kmarket.co.kr/policies/MD-2025-02
sources:
- id: origin_pdf
  resource: okf://source/un_data/08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf
  kind: origin_document
  sha256: c9e2115f48d5db99dd1e82563930f0903534e81f96e73c40b784d98c8c98b72e
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
language: ko
treatment: verbatim_ko
license: K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)
content_class: synthetic
issuing_body: 주식회사 K마켙 MD본부 · 가격전략실
document_id: DOC_08_KMARKET_MD_POLICY
group: internal_policies
extraction_strategy: numbered_article_ko
source_pages: 2
provision_count: 3
contacts: K마켙 가격전략실장 <md-pricing@kmarket.co.kr>
---

# K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 (제MD-2025-02호)

실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`), 상시 프로모션 25% 최저마진 가드레일, 90일 이상 체화재고(`stock_age_days >= 90`) 10% 마진 하한 완화 특례 및 예외승인(`campaign_exceptions`) 내규(2쪽). (원본 PDF: `08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf`, 총 2쪽)[^origin_pdf]

## 하위 장·절 디렉터리 (`Parts`)

* [제1장 실현마진율 산식 및 상시 프로모션 25% 최저마진 가드레일 (제1조~제2조)](ch01_margin_formula_and_25pct_guardrail/index.md)
* [제2장 체화재고(`stock_age_days >= 90`) 10% 마진 완화 특례 및 캠페인 예외승인 검증 (제3조~제4조)](ch02_aged_inventory_clearance_and_exceptions/index.md)

## 수록 조문 (`Provisions`)

* [내규 제1조·제2조 — 실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`) 및 상시 25.0% 하한 가드레일](ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail.md) — 1쪽: 모든 상시 쿠폰·번들 할인 시 개별 상품 실현마진율 25.0% 이상 유지 의무 및 미달 저마진 상품 자동 차단.
* [내규 제3조 — 체화재고(`stock_age_days >= 90` & `available_stock >= 30`) 최저마진 10.0% 완화 및 최대 30% 클리어런스 할인 특례](ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor.md) — 2쪽: 입고 후 90일 이상 경과하고 가용재고 30개 이상인 체화재고는 최저마진 하한을 25%에서 10%로 완화.
* [내규 제4조 — 캠페인 예외승인 원장(`campaign_exceptions`) `APPROVED` 검증 및 기각/만료 건 사용 금지](ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override.md) — 2쪽: `CLEARANCE_OVERRIDE` 또는 `VIP_RETENTION` 승인(`APPROVED`) 시 승인된 하한율(`approved_margin_floor`)까지 가드레일 완화 허용.
