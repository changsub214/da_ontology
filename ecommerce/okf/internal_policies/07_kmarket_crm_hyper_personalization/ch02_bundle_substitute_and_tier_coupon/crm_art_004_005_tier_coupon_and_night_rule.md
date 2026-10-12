---
type: Provision
title: 내규 제4조(VIP·VVIP 최대 15% 할인쿠폰 및 25% 마진 가드레일 연동)·제5조(야간 푸시 차단)
description: VVIP/VIP 최대 15%, GOLD 10%, SILVER 5% 쿠폰 한도 및 상품별 실현마진율 25% 하한(또는 체화재고/예외승인)
  사전 검증 의무.
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
sequence: 3
treatment: verbatim_ko
license: K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)
content_class: synthetic
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
contacts: K마켙 AI추천랩장 <ai-reco@kmarket.co.kr>
---

# 내규 제4조(VIP·VVIP 최대 15% 할인쿠폰 및 25% 마진 가드레일 연동)·제5조(야간 푸시 차단)

* **상위 문서 (`Source Document`)**: [K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 (제CRM-2025-01호)](/internal_policies/07_kmarket_crm_hyper_personalization/doc.md)[^origin_pdf]
* **출처 페이지**: `07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf` — **2쪽** (`section_number: 제4조~제5조`)

## 원문 발췌 (Verbatim Source Text)

제4조(회원 등급별 타겟팅 쿠폰 할인율 상한 및 마진 가드레일 연동) ① 마케팅
수신동의(`marketing_opt_in = True`)가 확인된 회원에 대하여 부여할
수 있는 CRM 타겟팅 쿠폰의 최대 할인율은 회원
등급(`membership_tier`)별로 다음과 같이 운영한다.
1. VVIP 및 VIP 등급 회원: 정상 판매가(`retail_price_krw`)
대비 최대 15% 할인쿠폰(단품 또는 코디 번들 전체 적용 가능)
2. GOLD 등급 회원: 정상 판매가 대비 최대 10% 할인쿠폰
3. SILVER 등급 회원: 정상 판매가 대비 최대 5% 할인쿠폰
② 제1항에 따른 쿠폰을 발급할 때에는 개별 상품별로 쿠폰 적용 후
실결제가격(`sale_price_krw`) 기준 매출총이익률이 「K마켙 MD 상품마진
가드레일 및 체화재고 가격결정 내규」 제2조의 상시 최저마진율(25%) 이상인지 반드시
사전 검증하여야 한다. 만약 번들 내 특정 상품의 쿠폰 적용 후 마진율이 25%
미만으로 하락하는 경우에는 해당 상품에 대한 체화재고 완화 특례(내규 제3조) 또는
MD본부 사전 예외승인(`campaign_exceptions`)이 존재하는 때에만 쿠폰
적용을 허용한다.
제5조(야간 발송 차단 및 추천 투명성 문구 표기) ① 모든 CRM 리마인드 푸시 및
알림톡은 오전 08:00부터 오후 21:00 사이에만 발송하며, 21:00 이후 발생한
장바구니 이탈 건은 익일 오전 08:30에 예약 발송한다.
② 코디 번들 및 대체상품 추천 카드 하단에는 '고객님의 최근 장바구니 및 관심 상품을
기반으로 추천되었습니다'라는 투명성 안내 문구를 필수 표기한다.

K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 ― Page 2 / 2
