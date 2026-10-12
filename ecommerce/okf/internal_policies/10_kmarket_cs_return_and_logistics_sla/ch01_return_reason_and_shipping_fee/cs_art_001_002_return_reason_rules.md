---
type: Provision
title: 내규 제1조·제2조 — 반품 사유 코드별(`CHANGE_OF_MIND` 7일/6,000원 vs `SIZE_MISMATCH_SPEC_DIFF`
  90일/무상 vs `WEAR_AND_WASH_DAMAGE` 거절) 판정 기준
description: 단순변심 7일(고객 6,000원 부담), 실측 사이즈/표시·광고 상이 90일(판매자 부담 무상반품), 세탁/착용 흔적 청약철회
  거절 기준.
tags:
- internal_policies
- synthetic
- 10_kmarket_cs_return_and_logistics_sla
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/10_INTERNAL_K마켙_CS반품환불_및_물류SLA_보상내규_2025.pdf
  kind: origin_document
  sha256: 32d16d855827c4083d45139bc5e5b287b45c007bbc819d728a8712a55c038c92
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
part_of: /internal_policies/10_kmarket_cs_return_and_logistics_sla/doc.md
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
contacts: K마켙 고객경험본부장 <cx-policy@kmarket.co.kr>
---

# 내규 제1조·제2조 — 반품 사유 코드별(`CHANGE_OF_MIND` 7일/6,000원 vs `SIZE_MISMATCH_SPEC_DIFF` 90일/무상 vs `WEAR_AND_WASH_DAMAGE` 거절) 판정 기준

* **상위 문서 (`Source Document`)**: [K마켙 CS 반품·교환·환불 심사 및 물류 출고지연 SLA 보상내규 (제CX-2025-04호)](/internal_policies/10_kmarket_cs_return_and_logistics_sla/doc.md)[^origin_pdf]
* **출처 페이지**: `10_INTERNAL_K마켙_CS반품환불_및_물류SLA_보상내규_2025.pdf` — **1쪽** (`section_number: 제1조~제2조`)

## 원문 발췌 (Verbatim Source Text)

제1조(목적) 이 내규는 K마켙에서 발생한 고객 주문(`orders`,
`order_items`)의 반품·청약철회 심사와 환불 기한 관리, 그리고 국내
풀필먼트 물류센터의 출고 서비스수준협약(SLA) 위반 시 고객 보상 기준을 명확히 하여
「전자상거래 등에서의 소비자보호에 관한 법률」을 준수하고 고객 신뢰를 제고함을 목적으로
한다.
제2조(반품 사유 코드별 청약철회 가능 기한 및 반품배송비 귀속) ① CS 심사의원 및
자동화 에이전트는 주문 원장(`orders`)의 배송완료
시각(`delivered_at`), 반품요청
시각(`return_requested_at`) 및 주문상품
원장(`order_items`)의 반품 사유
코드(`return_reason_code`)를 대조하여 다음과 같이 청약철회 적격성 및
배송비 부담 주체를 판정한다.
1. 단순변심(`return_reason_code =
'CHANGE_OF_MIND'`): 전자상거래법 제17조제1항제1호에 따라
배송완료일(`delivered_at`)로부터 7일 이내에 반품이 요청된 경우 청약철회를
승인하되, 왕복 반품배송비 6,000원은 고객 부담(환불금액에서 차감 또는 별도
결제)으로 처리한다. 다만, 외부 착용 흔적·세탁·수선·택(Tag) 파손으로 재판매
가치가 현저히 감소한 경우(`WEAR_AND_WASH_DAMAGE`)에는 법
제17조제2항제2호에 따라 청약철회를 거절하고 상품을 고객에게 반송한다.
2. 표시·광고 내용 상이 또는 실측 사이즈 오기재(`return_reason_code
= 'SIZE_MISMATCH_SPEC_DIFF'`): 상품 상세페이지에 표기된 실측
치수·소재 정보가 실제 배송된 상품과 다른 경우에는 전자상거래법 제17조제1항제2호의
'표시·광고 내용과 다르게 이행된 경우'에 해당하므로, 단순변심 7일 기한이
경과하였더라도 배송완료일로부터 3개월(90일) 이내(안 날로부터 30일 이내)에는
청약철회를 무조건 승인하여야 하며, 반품배송비(6,000원)는 K마켙(또는 귀책
입점브랜드)이 전액 부담(무상반품)한다.
3. 상품 불량·파손·오배송(`return_reason_code =
'DEFECTIVE'`): 배송완료일로부터 3개월 이내 청약철회를 승인하며,
반품배송비는 판매자 측이 전액 부담하고 고객에게 사과 포인트 2,000P를 추가
지급한다.

K마켙 CS 반품·교환·환불 심사 및 물류 출고지연 SLA 보상내규 ― Page 1 / 2
