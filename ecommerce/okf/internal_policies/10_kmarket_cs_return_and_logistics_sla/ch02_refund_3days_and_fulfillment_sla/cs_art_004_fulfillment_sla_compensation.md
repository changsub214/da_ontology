---
type: Provision
title: 내규 제4조 — 물류센터별(`GIMPO-FC` 24h·`YONGIN-FC` 36h·`YANGSAN-FC` 48h) 출고 SLA 위반 시
  3,000P 자동 보상
description: 주문결제 시각 대비 출고 시각이 물류센터별 `sla_hours` 초과 시 약속출고 지연 보상 적립금 3,000포인트 자동 지급.
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
contacts: K마켙 고객경험본부장 <cx-policy@kmarket.co.kr>
---

# 내규 제4조 — 물류센터별(`GIMPO-FC` 24h·`YONGIN-FC` 36h·`YANGSAN-FC` 48h) 출고 SLA 위반 시 3,000P 자동 보상

* **상위 문서 (`Source Document`)**: [K마켙 CS 반품·교환·환불 심사 및 물류 출고지연 SLA 보상내규 (제CX-2025-04호)](/internal_policies/10_kmarket_cs_return_and_logistics_sla/doc.md)[^origin_pdf]
* **출처 페이지**: `10_INTERNAL_K마켙_CS반품환불_및_물류SLA_보상내규_2025.pdf` — **2쪽** (`section_number: 제4조`)

## 원문 발췌 (Verbatim Source Text)

제4조(물류센터별 출고 SLA 기준 및 출고지연 자동 보상) ① 풀필먼트운영실은 물류
원장(`inventory_items`)에 지정된
물류센터(`distribution_center`)별 표준 출고
목표시간(`sla_hours`)을 다음과 같이 관리한다.
1. 김포 자동화 풀필먼트 센터(`GIMPO-FC`): 주문결제
시각(`orders.created_at`)으로부터 24시간 이내
출고(`sla_hours = 24`)
2. 용인 패션 허브 센터(`YONGIN-FC`): 주문결제 시각으로부터 36시간 이내
출고(`sla_hours = 36`)
3. 양산 남부권 광역 센터(`YANGSAN-FC`): 주문결제 시각으로부터 48시간
이내 출고(`sla_hours = 48`)
② 실제 출고 시각(`orders.shipped_at`)과 주문결제
시각(`orders.created_at`)의 차이(출고 소요시간)가 해당 상품 출고
물류센터의 `sla_hours`를 초과한 경우(출고 SLA 위반), 고객의 별도 클레임
제기가 없더라도 배송완료 즉시 고객에게 '약속출고 지연 보상 적립금
3,000포인트(3,000원 상당)'를 자동 지급한다.

K마켙 CS 반품·교환·환불 심사 및 물류 출고지연 SLA 보상내규 ― Page 2 / 2
