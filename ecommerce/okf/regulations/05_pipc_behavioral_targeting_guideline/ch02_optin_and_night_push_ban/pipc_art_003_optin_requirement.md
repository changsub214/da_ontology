---
type: Provision
title: 제3조(식별 결합 행태정보 기반 타겟팅 마케팅 `marketing_opt_in = True` 필수 및 미동의자 차단)
description: '`marketing_opt_in = False` 회원은 장바구니 이탈 로그와 회원 원장을 결합한 타겟팅 쿠폰 발급·개인화
  추천 전면 금지.'
tags:
- regulations
- authentic
- 05_pipc_behavioral_targeting_guideline
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/05_PIPC_온라인_맞춤형광고_행태정보_가이드라인_2025.pdf
  kind: origin_document
  sha256: 012bff57c2179cabaf35173d32305a49d0937a35656b245c114b531945ae9075
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
part_of: /regulations/05_pipc_behavioral_targeting_guideline/doc.md
sequence: 2
treatment: verbatim_ko
license: 공공누리 제1유형 (개인정보보호위원회 공공저작물 자유이용허락)
content_class: authentic
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
---

# 제3조(식별 결합 행태정보 기반 타겟팅 마케팅 `marketing_opt_in = True` 필수 및 미동의자 차단)

* **상위 문서 (`Source Document`)**: [온라인 맞춤형 광고 개인정보보호 가이드라인 및 전자상거래 행태정보 처리 기준](/regulations/05_pipc_behavioral_targeting_guideline/doc.md)[^origin_pdf]
* **출처 페이지**: `05_PIPC_온라인_맞춤형광고_행태정보_가이드라인_2025.pdf` — **2쪽** (`section_number: 제3조`)

## 원문 발췌 (Verbatim Source Text)

제3조(식별 결합 행태정보 기반 타겟팅 마케팅의 동의 요건) ① 전자상거래 사업자가
특정 회원(`user_id`)의 실시간 이벤트 로그(`events` 테이블의
`view`, `cart`, `purchase` 등)를 회원 원장(`users`)과
결합하여 개인별 맞춤형 할인쿠폰을 발급하거나 타겟팅 메시지를 전송하려는 경우, 사전에
정보주체로부터 '개인정보의 마케팅 및 맞춤형 추천 활용
동의'(`marketing_opt_in = True`)를 명시적으로 받아야 한다.
② 정보주체가 마케팅 및 맞춤형 추천 활용에 동의하지 아니한
경우(`marketing_opt_in = False`), 사업자는 해당 회원의 장바구니
이탈 로그나 조회 로그를 회원 식별자(`user_id`)와 결합하여 타겟팅 쿠폰을
발급하거나 개인화 추천을 실행할 수 없다. 다만, 개인을 식별할 수 없도록 통계 처리된
연령대별·카테고리별 일반 인기상품 정보는 노출할 수 있다.
