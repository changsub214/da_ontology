---
type: Provision
title: 제4조(초개인화 추천 기준 고지) 및 제5조(장바구니 이탈 리마인드 `marketing_opt_in` 검증 의무)
description: 장바구니 이력 기반 추천 기준 명시 및 `marketing_opt_in = False` 회원 대상 리마인드·타겟팅 쿠폰 발송
  금지.
tags:
- regulations
- authentic
- 04_ftc_dark_pattern_and_reco_guideline
- verbatim_ko
language: ko
sources:
- id: origin_pdf
  resource: okf://source/un_data/04_FTC_전자상거래_다크패턴_및_맞춤형광고_가이드라인_2025.pdf
  kind: origin_document
  sha256: 83a3b347d03418a23544b29b38f2842e62d33f2995b39584c015f491e29f2708
generated:
  by: process:build_okf/3.0
  at: '2026-10-03T06:00:00Z'
status: stable
part_of: /regulations/04_ftc_dark_pattern_and_reco_guideline/doc.md
sequence: 3
treatment: verbatim_ko
license: 공공누리 제1유형 (공정거래위원회 공공저작물 자유이용허락)
content_class: authentic
section_number: 제4조~제5조
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

# 제4조(초개인화 추천 기준 고지) 및 제5조(장바구니 이탈 리마인드 `marketing_opt_in` 검증 의무)

* **상위 문서 (`Source Document`)**: [온라인 다크패턴(눈속임 상술) 자율관리 가이드라인 및 맞춤형 추천 투명성 지침](/regulations/04_ftc_dark_pattern_and_reco_guideline/doc.md)[^origin_pdf]
* **출처 페이지**: `04_FTC_전자상거래_다크패턴_및_맞춤형광고_가이드라인_2025.pdf` — **2쪽** (`section_number: 제4조~제5조`)

## 원문 발췌 (Verbatim Source Text)

제4조(초개인화 추천 알고리즘의 기준 고지) ① 사업자가 소비자의 구매이력, 장바구니
담기 이력(`event_type = 'cart'`), 카테고리 선호도를 분석하여
초개인화 상품 추천이나 맞춤형 코디
번들(`complementary_product_id`)을 노출하는 경우, 추천 영역
상단 또는 안내 아이콘을 통해 '고객님의 최근 관심 상품 및 장바구니 이력을 기반으로
추천된 상품입니다'와 같이 주요 추천 기준을 소비자가 알기 쉽게 표시하여야 한다.
② 입점브랜드로부터 별도의 광고비를 지급받아 상단에 노출하는 광고 상품은 개인화 추천
상품과 명확히 구분하여 '광고' 표시를 부착하여야 한다.
제5조(장바구니 이탈 리마인드 및 타겟팅 쿠폰 발송 준수사항) ① 소비자가 상품을
장바구니에 담은 후 결제하지 않고 이탈한 경우, 사업자가 앱 푸시(App Push),
알림톡, 문자메시지 등을 통해 리마인드 알림이나 시크릿 할인쿠폰을 발송하려면 반드시
해당 소비자의 사전 마케팅·맞춤형 추천 수신동의(`marketing_opt_in =
True`) 여부를 실시간으로 검증하여야 한다.
② 마케팅 수신에 동의하지 아니한 소비자(`marketing_opt_in =
False`)에 대하여는 장바구니 이탈 감지 쿠폰이나 개인화된 리마인드 메시지를
발송하여서는 아니 되며, 오직 앱 내 일반 베스트셀러 영역이나 비식별 전체 공개
배너만을 노출하여야 한다.

온라인 다크패턴(눈속임 상술) 자율관리 가이드라인 및 맞춤형 추천 투명성 지침 ― Page 2 / 2
