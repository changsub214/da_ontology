---
type: Provision
title: 내규 제3조 — 품절(`available_stock == 0`) 시 대체상품(`substitute_product_id`) 전환 및 정상재고
  시 코디 번들(`complementary_product_id`) 추천
description: 주상품 가용재고 0개 시 대체상품 우선 추천, 가용재고 1개 이상 시 연관 코디 상품 묶음 번들 추천 규칙.
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
contacts: K마켙 AI추천랩장 <ai-reco@kmarket.co.kr>
---

# 내규 제3조 — 품절(`available_stock == 0`) 시 대체상품(`substitute_product_id`) 전환 및 정상재고 시 코디 번들(`complementary_product_id`) 추천

* **상위 문서 (`Source Document`)**: [K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 (제CRM-2025-01호)](/internal_policies/07_kmarket_crm_hyper_personalization/doc.md)[^origin_pdf]
* **출처 페이지**: `07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf` — **2쪽** (`section_number: 제3조`)

## 원문 발췌 (Verbatim Source Text)

제3조(가용재고 연동 대체상품 및 크로스셀 코디 번들 추천 규칙) ① 장바구니 이탈
고객 또는 상품 상세 조회 고객에게 상품을 추천할 때에는 먼저 물류
원장(`inventory_items`)의 실시간
가용재고(`available_stock`)를 확인하여야 한다.
② 고객이 관심을 보인 주상품의 가용재고가 0개인 품절
상태(`available_stock == 0`)인 경우에는 해당 상품에 대한 쿠폰
발급을 즉시 중단하고, 상품 마스터(`products`)에 지정된 동일 카테고리·유사
가격대의 대체 추천 상품(`substitute_product_id`)을 우선 추천하여야
한다.
③ 주상품의 가용재고가 1개 이상 정상 확보(`available_stock >=
1`)되어 있는 경우에는 객단가(AOV) 증대를 위하여 상품
마스터(`products`)에 연결된 연관 코디·보완
상품(`complementary_product_id`)을 함께 묶은 '코디 세트
번들(Cross-sell Bundle)'로 추천할 수 있다.
