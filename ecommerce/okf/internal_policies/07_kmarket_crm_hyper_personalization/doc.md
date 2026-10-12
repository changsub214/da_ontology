---
type: Source Document
title: K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 (제CRM-2025-01호)
description: 장바구니 미결제 이탈(`event_type = 'cart'`) 탐지, 마케팅 동의(`marketing_opt_in`) 검증,
  가용재고 연동 대체상품(`substitute_product_id`)·코디 번들(`complementary_product_id`) 추천 및 등급별
  쿠폰 한도 내규(2쪽).
tags:
- internal_policies
- synthetic
- 07_kmarket_crm_hyper_personalization
- verbatim_ko
resource: https://internal.kmarket.co.kr/policies/CRM-2025-01
sources:
- id: origin_pdf
  resource: okf://source/un_data/07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf
  kind: origin_document
  sha256: 317d42e3328a520f9957261af8fe904f2cfe6330e74bb3a0bce3690df58940b7
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
language: ko
treatment: verbatim_ko
license: K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)
content_class: synthetic
issuing_body: 주식회사 K마켙 그로스마케팅본부 · AI추천랩
document_id: DOC_07_KMARKET_CRM_POLICY
group: internal_policies
extraction_strategy: numbered_article_ko
source_pages: 2
provision_count: 3
contacts: K마켙 AI추천랩장 <ai-reco@kmarket.co.kr>
---

# K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 (제CRM-2025-01호)

장바구니 미결제 이탈(`event_type = 'cart'`) 탐지, 마케팅 동의(`marketing_opt_in`) 검증, 가용재고 연동 대체상품(`substitute_product_id`)·코디 번들(`complementary_product_id`) 추천 및 등급별 쿠폰 한도 내규(2쪽). (원본 PDF: `07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf`, 총 2쪽)[^origin_pdf]

## 하위 장·절 디렉터리 (`Parts`)

* [제1장 장바구니 미결제 이탈 실시간 탐지 및 마케팅 수신동의(`marketing_opt_in`) 검증 (제1조~제2조)](ch01_cart_abandon_and_optin_gate/index.md)
* [제2장 가용재고 연동 대체상품·코디 번들 추천 및 회원 등급별 쿠폰 한도 (제3조~제5조)](ch02_bundle_substitute_and_tier_coupon/index.md)

## 수록 조문 (`Provisions`)

* [내규 제1조·제2조 — 장바구니 이탈(`event_type = 'cart'`) 탐지 및 `users.marketing_opt_in = True` 필수 검증](ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin.md) — 1쪽: 장바구니 미결제 이탈 고객에게 리마인드·타겟팅 쿠폰 발급 전 `marketing_opt_in = True` 확인 의무 및 미동의자 발급 차단.
* [내규 제3조 — 품절(`available_stock == 0`) 시 대체상품(`substitute_product_id`) 전환 및 정상재고 시 코디 번들(`complementary_product_id`) 추천](ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle.md) — 2쪽: 주상품 가용재고 0개 시 대체상품 우선 추천, 가용재고 1개 이상 시 연관 코디 상품 묶음 번들 추천 규칙.
* [내규 제4조(VIP·VVIP 최대 15% 할인쿠폰 및 25% 마진 가드레일 연동)·제5조(야간 푸시 차단)](ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule.md) — 2쪽: VVIP/VIP 최대 15%, GOLD 10%, SILVER 5% 쿠폰 한도 및 상품별 실현마진율 25% 하한(또는 체화재고/예외승인) 사전 검증 의무.
