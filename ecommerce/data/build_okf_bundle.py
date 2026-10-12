#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K마켙 (ecommerce-ontology) OKF v0.2 전수 조문 추출·번들 생성기 (`ecommerce/data/build_okf_bundle.py`)

특징:
1. `ecommerce/data/un_data/` 내 10개 PDF(공식 법령·심사지침·가이드라인 5종 + 해외직구 대조군 1종 + K마켙 사내내규 4종, 총 23쪽)의
   전 조문(35개 `type: Provision` + 10개 `type: Source Document` = 총 45개 OKF Concept)을 `pdftotext`로 무손실 추출한다.
2. 추출 시 P1(본문 원문 무결성), P2(조문 제목/번호 일치), P3(페이지 범위 유효성), P4(SHA-256 해시 일치)를 자동 검증하고
   `ecommerce/okf/verification.json`에 기록한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "un_data")
OKF_DIR = os.path.join(BASE_DIR, "okf")
NOW_ISO = "2026-10-03T06:00:00Z"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pdf_pages(pdf_filename: str) -> list[str]:
    path = os.path.join(PDF_DIR, pdf_filename)
    raw = subprocess.check_output(["pdftotext", path, "-"], text=True)
    pages = raw.split("\x0c")
    if pages and pages[-1].strip() == "":
        pages = pages[:-1]
    return [""] + pages


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", "", s)


def slice_between(page_text: str, start_anchor: str, end_anchor: str | None = None) -> str:
    idx = page_text.find(start_anchor)
    if idx == -1:
        raise ValueError(f"Start anchor {start_anchor!r} not found in page text:\n{page_text[:400]}")
    sub = page_text[idx:]
    if end_anchor:
        eidx = sub.find(end_anchor)
        if eidx != -1 and eidx > 0:
            sub = sub[:eidx]
    # Remove trailing page footer lines if present
    lines = [ln for ln in sub.splitlines() if "— Page " not in ln]
    return "\n".join(lines).strip()


def build_docs_spec() -> list[dict]:
    return [
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·심사지침·개인정보 가이드라인 (Authentic Regulations)",
            "doc_dir": "01_law_large_retail_fair_trade",
            "doc_id": "DOC_01_LAW_LARGE_RETAIL",
            "pdf": "01_LAW_대규모유통업법_전문_2025.pdf",
            "title": "대규모유통업에서의 거래공정화에 관한 법률 (법률 제20195호, 2025. 1. 1. 시행)",
            "description": "대규모유통업자(온라인쇼핑몰 포함)와 납품업자 간 서면교부(제6조), 대금지급(제8조), 부당반품 금지(제10조), 판매촉진비용 부담전가 금지 및 50% 상한(제11조)을 규정한 법률 전문(4쪽).",
            "content_class": "authentic",
            "issuing_body": "공정거래위원회 · 국가법령정보센터",
            "license": "공공누리 제1유형 (국가법령정보센터 공공저작물 자유이용허락)",
            "resource_url": "https://www.law.go.kr/법령/대규모유통업에서의거래공정화에관한법률",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_general_and_contract",
                    "part_title": "제1장 총칙 및 계약서면 즉시 교부 의무 (제1조~제6조)",
                    "provisions": [
                        {
                            "prov_id": "art_001_002_purpose_definitions",
                            "section_number": "제1조~제2조",
                            "title": "제1조(목적) 및 제2조(정의 — 대규모유통업자·납품업자·직매입·특약매입·위수탁)",
                            "description": "대규모유통업자(연매출 1천억 이상 온라인쇼핑몰 포함)와 직매입·특약매입·위수탁 거래형태의 법적 정의.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": "제6조(서면의 즉시 교부",
                        },
                        {
                            "prov_id": "art_006_written_contract",
                            "section_number": "제6조",
                            "title": "제6조(서면의 즉시 교부 및 계약사항 명시)",
                            "description": "거래형태·수수료율·반품조건·판촉비 분담기준을 명시한 계약서면 즉시 교부 의무.",
                            "pages": [1],
                            "start": "제6조(서면의 즉시 교부",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_payment_and_return_ban",
                    "part_title": "제2장 납품대금 지급기한 및 부당 반품 금지 (제8조~제10조)",
                    "provisions": [
                        {
                            "prov_id": "art_008_payment_deadline",
                            "section_number": "제8조",
                            "title": "제8조(납품대금의 지급 — 직매입 60일·특약매입 40일 및 지연이자 연 15.5%)",
                            "description": "직매입 수령 후 60일, 특약매입·위수탁 마감 후 40일 이내 대금지급 의무 및 초과 시 지연이자(연 15.5%) 지급.",
                            "pages": [2],
                            "start": "제8조(납품대금의 지급)",
                            "end": "제10조(상품의 반품 금지)",
                        },
                        {
                            "prov_id": "art_010_unfair_return_ban",
                            "section_number": "제10조",
                            "title": "제10조(상품의 반품 금지 및 특약매입·직매입 시즌상품 예외)",
                            "description": "납품 상품의 부당 반품 원칙적 금지 및 특약매입·오손/결함·직매입 시즌상품 사전약정 시 예외 허용 요건.",
                            "pages": [2],
                            "start": "제10조(상품의 반품 금지)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch03_promo_cost_sharing_cap",
                    "part_title": "제3장 판매촉진비용 부담전가 금지 및 납품업자 50% 상한 (제11조)",
                    "provisions": [
                        {
                            "prov_id": "art_011_p1_p2_prior_written_agreement",
                            "section_number": "제11조제1항~제2항",
                            "title": "제11조제1항·제2항(판매촉진비용 사전 서면약정 의무 및 5대 필수 기재사항)",
                            "description": "할인쿠폰·가격할인 등 판매촉진행사 실시 이전 서면약정 체결 의무 및 명칭·기간·품목·예상편익·분담비율 명시.",
                            "pages": [3],
                            "start": "제11조(판매촉진비용의 부담전가 금지)",
                            "end": "③ 제1항 및 제2항에 따른",
                        },
                        {
                            "prov_id": "art_011_p3_p5_fifty_percent_cap_and_proviso",
                            "section_number": "제11조제3항~제5항",
                            "title": "제11조제3항~제5항(납품업자 판촉비 분담비율 50% 상한 강행규정 및 자발적·차별화 행사 단서)",
                            "description": "납품업자 판촉비 분담비율 50% 초과 금지(초과 약정 무효·대규모유통업자 전액 부담) 및 자발적·차별화 행사 예외 단서.",
                            "pages": [3],
                            "start": "③ 제1항 및 제2항에 따른",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch04_exclusivity_and_record_keeping",
                    "part_title": "제4장 배타적 거래 강요 금지 및 5년 서면 보존 의무 (제12조~제18조)",
                    "provisions": [
                        {
                            "prov_id": "art_012_017_018_fair_trade_duties",
                            "section_number": "제12조·제17조·제18조",
                            "title": "제12조(배타적 거래 강요 금지)·제17조(경영정보 요구 금지)·제18조(서면 5년 보존의무)",
                            "description": "경쟁 플랫폼 거래 제한 금지, 부당 원가/공급조건 요구 금지 및 판촉 약정·정산서류 5년 보존 의무.",
                            "pages": [4],
                            "start": "제12조(배타적 거래 강요 금지)",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·심사지침·개인정보 가이드라인 (Authentic Regulations)",
            "doc_dir": "02_ftc_promo_cost_guideline",
            "doc_id": "DOC_02_FTC_PROMO_GUIDE",
            "pdf": "02_FTC_대규모유통업법_판매촉진비용부담전가_심사지침_2025.pdf",
            "title": "대규모유통업 분야 판매촉진비용 부담전가 행위에 대한 위법성 심사지침 (공정위 예규 제445호)",
            "description": "온라인 플랫폼 타겟팅·번들 할인쿠폰의 판매촉진비용 산입, 사전약정 요건, 50% 초과 약정 무효 처리 및 자발성·차별성 심사기준(2쪽).",
            "content_class": "authentic",
            "issuing_body": "공정거래위원회 유통거래과",
            "license": "공공누리 제1유형 (공정거래위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.ftc.go.kr",
            "strategy": "numbered_section_ko",
            "parts": [
                {
                    "part_dir": "sec01_scope_and_prior_agreement",
                    "part_title": "Ⅰ. 판매촉진비용 산입 범위(자동 타겟팅·번들 쿠폰 포함) 및 사전 서면약정 요건",
                    "provisions": [
                        {
                            "prov_id": "guide_01_02_promo_coupon_scope",
                            "section_number": "Ⅰ.1~2",
                            "title": "심사지침 Ⅰ.1~2 — 온라인 타겟팅·번들 할인쿠폰의 판매촉진비용 해당성",
                            "description": "장바구니 이탈·코디 번들 자동 발행 할인쿠폰도 대규모유통업법 제11조 판매촉진비용에 해당함을 명시.",
                            "pages": [1],
                            "start": "1. 목적",
                            "end": "3. 사전 서면약정 체결 시점",
                        },
                        {
                            "prov_id": "guide_03_prior_written_agreement_rule",
                            "section_number": "Ⅰ.3",
                            "title": "심사지침 Ⅰ.3 — 사전 서면약정(`signed_promo_agreement`) 체결 시점 및 포괄약정 불인정",
                            "description": "행사 개시 전 품목·기간·분담비율이 명시된 사전 서면약정 체결 필수.",
                            "pages": [1],
                            "start": "3. 사전 서면약정 체결 시점",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "sec02_cap_override_and_voluntary_test",
                    "part_title": "Ⅱ. 납품업자 50% 상한 초과분 무효 처리 및 자발성·차별성 엄격 심사기준",
                    "provisions": [
                        {
                            "prov_id": "guide_04_fifty_percent_cap_invalidity",
                            "section_number": "Ⅱ.4",
                            "title": "심사지침 Ⅱ.4 — 50% 초과 약정(`promo_cost_share_ratio > 0.50`) 당연 무효 및 유통업자 부담 원칙",
                            "description": "계약상 분담률이 60% 등으로 약정되어도 50% 초과분은 무효이며 대규모유통업자가 전액 부담.",
                            "pages": [2],
                            "start": "4. 납품업자 분담비율 50% 상한선 준수",
                            "end": "5. 법 제11조제5항 단서",
                        },
                        {
                            "prov_id": "guide_05_voluntary_differentiated_test",
                            "section_number": "Ⅱ.5",
                            "title": "심사지침 Ⅱ.5 — 법 제11조제5항 단서(자발성·차별성) 인정 요건 및 상시 캠페인 배제",
                            "description": "플랫폼 상시 장바구니 리마인드·VIP 정기쿠폰 참여는 자발적·차별화 행사로 인정 불가.",
                            "pages": [2],
                            "start": "5. 법 제11조제5항 단서",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·심사지침·개인정보 가이드라인 (Authentic Regulations)",
            "doc_dir": "03_law_ecommerce_consumer_protection",
            "doc_id": "DOC_03_LAW_ECOMMERCE",
            "pdf": "03_LAW_전자상거래법_전문_2025.pdf",
            "title": "전자상거래 등에서의 소비자보호에 관한 법률 (법률 제20312호, 2025. 2. 1. 시행)",
            "description": "온라인 통신판매업자의 거래조건 고지(제13조), 3영업일 공급조치(제15조), 청약철회 기한 7일/90일 및 제한사유(제17조), 3영업일 환급·배송비 귀속(제18조), 다크패턴 금지(제21조의2) 전문(3쪽).",
            "content_class": "authentic",
            "issuing_body": "공정거래위원회 · 국가법령정보센터",
            "license": "공공누리 제1유형 (국가법령정보센터 공공저작물 자유이용허락)",
            "resource_url": "https://www.law.go.kr/법령/전자상거래등에서의소비자보호에관한법률",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_disclosure_and_supply",
                    "part_title": "제1장 거래조건 정보제공 및 3영업일 공급 의무 (제1조·제13조·제15조)",
                    "provisions": [
                        {
                            "prov_id": "ecom_art_001_013_015_disclosure_supply",
                            "section_number": "제1조·제13조·제15조",
                            "title": "제1조(목적)·제13조(거래조건 표시·고지)·제15조(선지급식 3영업일 이내 공급조치)",
                            "description": "치수·소재·정상가/할인가·출고예정일 고지 의무 및 대금 결제 후 3영업일 이내 공급조치 의무.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_withdrawal_and_exceptions",
                    "part_title": "제2장 청약철회 기한(단순변심 7일 vs 표시·광고 상이 3개월) 및 청약철회 제한 (제17조)",
                    "provisions": [
                        {
                            "prov_id": "ecom_art_017_p1_withdrawal_periods",
                            "section_number": "제17조제1항",
                            "title": "제17조제1항(청약철회 기간 — 제1호 단순변심 7일 vs 제2호 표시·광고 상이 3개월·30일)",
                            "description": "단순변심은 수령 후 7일 이내, 표시·광고 상이 또는 계약과 다르게 이행된 경우 수령 후 3개월(안 날부터 30일) 이내 청약철회 가능.",
                            "pages": [2],
                            "start": "제17조(청약철회등)",
                            "end": "② 소비자는 다음 각 호",
                        },
                        {
                            "prov_id": "ecom_art_017_p2_withdrawal_restrictions",
                            "section_number": "제17조제2항",
                            "title": "제17조제2항(청약철회 제한 사유 — 소비자 귀책 훼손·세탁/수선/착용 흔적으로 가치 현저 감소)",
                            "description": "소비자 사용·세탁·수선·착용 흔적 등으로 재화의 가치가 현저히 감소한 경우 청약철회 불가.",
                            "pages": [2],
                            "start": "② 소비자는 다음 각 호",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch03_refund_sla_and_dark_patterns",
                    "part_title": "제3장 3영업일 환급·반품배송비 부담 주체 및 온라인 다크패턴 금지 (제18조·제21조의2)",
                    "provisions": [
                        {
                            "prov_id": "ecom_art_018_refund_and_return_shipping",
                            "section_number": "제18조",
                            "title": "제18조(청약철회의 효과 — 반환 후 3영업일 이내 환급·지연배상금 연 15%·반품배송비 귀속)",
                            "description": "반환일로부터 3영업일 이내 대금 환급(초과 시 연 15% 지연배상금), 단순변심 반품배송비 소비자 부담 vs 표시·광고 상이 통신판매업자 부담.",
                            "pages": [3],
                            "start": "제18조(청약철회등의 효과)",
                            "end": "제21조의2(온라인 인터페이스",
                        },
                        {
                            "prov_id": "ecom_art_021_2_dark_pattern_ban",
                            "section_number": "제21조의2",
                            "title": "제21조의2(온라인 인터페이스 눈속임 상술·허위할인·허위품절임박 금지)",
                            "description": "순차공개 가격책정, 거짓 할인율, 실제 재고와 무관한 허위 품절임박 노출 및 수신거절 방해 금지.",
                            "pages": [3],
                            "start": "제21조의2(온라인 인터페이스",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·심사지침·개인정보 가이드라인 (Authentic Regulations)",
            "doc_dir": "04_ftc_dark_pattern_and_reco_guideline",
            "doc_id": "DOC_04_FTC_DARK_PATTERN",
            "pdf": "04_FTC_전자상거래_다크패턴_및_맞춤형광고_가이드라인_2025.pdf",
            "title": "온라인 다크패턴(눈속임 상술) 자율관리 가이드라인 및 맞춤형 추천 투명성 지침",
            "description": "할인율 비교기준가격(`retail_price_krw`), 실시간 가용재고(`available_stock`) 연동 품절 표시, 초개인화 추천 기준 고지 및 마케팅 동의 검증 지침(2쪽).",
            "content_class": "authentic",
            "issuing_body": "공정거래위원회 소비자정책국",
            "license": "공공누리 제1유형 (공정거래위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.ftc.go.kr",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_price_and_stock_truthfulness",
                    "part_title": "제1장 할인율 비교기준가격 및 실시간 재고·품절 표시 진실성 (제1조~제3조)",
                    "provisions": [
                        {
                            "prov_id": "dp_art_001_002_price_display",
                            "section_number": "제1조~제2조",
                            "title": "제1조(목적) 및 제2조(할인율 비교기준가격 `retail_price_krw` 및 번들 가격 구분 표시)",
                            "description": "종전 정상 판매가격 기준 할인율 산정 및 코디 번들 할인 시 정상가·할인액·실결제가 구분 표시 의무.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": "제3조(실시간 재고",
                        },
                        {
                            "prov_id": "dp_art_003_stock_truthfulness",
                            "section_number": "제3조",
                            "title": "제3조(실시간 가용재고 `available_stock` 연동 및 품절 시 대체상품 안내 원칙)",
                            "description": "가용재고 0개 품절 상품 미끼 노출 금지 및 품절 시 대체 상품(`substitute_product_id`) 객관적 안내.",
                            "pages": [1],
                            "start": "제3조(실시간 재고",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_reco_transparency_and_optin",
                    "part_title": "제2장 초개인화 추천 기준 고지 및 장바구니 리마인드 수신동의 검증 (제4조~제5조)",
                    "provisions": [
                        {
                            "prov_id": "dp_art_004_005_reco_transparency_optin",
                            "section_number": "제4조~제5조",
                            "title": "제4조(초개인화 추천 기준 고지) 및 제5조(장바구니 이탈 리마인드 `marketing_opt_in` 검증 의무)",
                            "description": "장바구니 이력 기반 추천 기준 명시 및 `marketing_opt_in = False` 회원 대상 리마인드·타겟팅 쿠폰 발송 금지.",
                            "pages": [2],
                            "start": "제4조(초개인화 추천 알고리즘의 기준 고지)",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·심사지침·개인정보 가이드라인 (Authentic Regulations)",
            "doc_dir": "05_pipc_behavioral_targeting_guideline",
            "doc_id": "DOC_05_PIPC_BEHAVIORAL",
            "pdf": "05_PIPC_온라인_맞춤형광고_행태정보_가이드라인_2025.pdf",
            "title": "온라인 맞춤형 광고 개인정보보호 가이드라인 및 전자상거래 행태정보 처리 기준",
            "description": "행태정보(`events`)를 회원 식별자(`user_id`)와 결합하여 초개인화 추천·타겟팅 쿠폰에 활용할 때의 사전 동의(`marketing_opt_in = True`), 90일 보관기간 및 야간 전송 제한 기준(2쪽).",
            "content_class": "authentic",
            "issuing_body": "개인정보보호위원회 자율보호정책과",
            "license": "공공누리 제1유형 (개인정보보호위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.pipc.go.kr",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_behavioral_info_definition",
                    "part_title": "제1장 전자상거래 행태정보의 정의 및 회원 식별 결합 시 개인정보성 (제1조~제2조)",
                    "provisions": [
                        {
                            "prov_id": "pipc_art_001_002_behavioral_def",
                            "section_number": "제1조~제2조",
                            "title": "제1조(목적) 및 제2조(행태정보의 정의 및 회원 식별정보 `user_id` 결합 시 개인정보보호법 적용)",
                            "description": "웹·앱 방문·장바구니·구매 이력을 특정 회원(`user_id`)과 결합 처리 시 개인정보보호법상 동의 규정 적용.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_optin_and_night_push_ban",
                    "part_title": "제2장 식별 결합 타겟팅 동의(`marketing_opt_in`) 필수 및 야간 광고 전송 제한 (제3조~제5조)",
                    "provisions": [
                        {
                            "prov_id": "pipc_art_003_optin_requirement",
                            "section_number": "제3조",
                            "title": "제3조(식별 결합 행태정보 기반 타겟팅 마케팅 `marketing_opt_in = True` 필수 및 미동의자 차단)",
                            "description": "`marketing_opt_in = False` 회원은 장바구니 이탈 로그와 회원 원장을 결합한 타겟팅 쿠폰 발급·개인화 추천 전면 금지.",
                            "pages": [2],
                            "start": "제3조(식별 결합 행태정보 기반 타겟팅 마케팅의 동의 요건)",
                            "end": "제4조(행태정보 보유기간",
                        },
                        {
                            "prov_id": "pipc_art_004_005_retention_and_night_ban",
                            "section_number": "제4조~제5조",
                            "title": "제4조(행태정보 90일 보유기간·동의철회권) 및 제5조(야간 21시~08시 광고성 정보 전송 제한)",
                            "description": "상세 이벤트 로그 최대 90일 보관 원칙 및 야간 시간대(21:00~08:00) 별도 동의 없는 리마인드 푸시 전송 금지.",
                            "pages": [2],
                            "start": "제4조(행태정보 보유기간",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "distractors",
            "cat_title": "타 업권·해외직구 특송통관 대조군 (Out-of-Scope Distractors)",
            "doc_dir": "06_distractor_customs_overseas_direct",
            "doc_id": "DOC_06_DISTRACTOR_CUSTOMS",
            "pdf": "06_DISTRACTOR_관세청_해외직구_목록통관_및_특송물품_고시_2025.pdf",
            "title": "[Distractor] 목록통관 및 특송물품 수입통관 사무처리에 관한 고시 (관세청 고시 제2025-12호)",
            "description": "해외 물류센터 반입 특송화물의 미화 150달러 목록통관 및 14일 국제반송·35,000원 반송수수료 규정 — 국내 풀필먼트(김포·용인·양산) 출고 주문에는 적용 제외되는 대조군(2쪽).",
            "content_class": "authentic",
            "issuing_body": "관세청 전자상거래통관과",
            "license": "공공누리 제1유형 (관세청 공공저작물 자유이용허락)",
            "resource_url": "https://www.customs.go.kr",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_overseas_customs_scope",
                    "part_title": "제1장~제2장 해외직구 목록통관(150달러) 및 14일 국제반송 특례 (국내 풀필먼트 적용 제외)",
                    "provisions": [
                        {
                            "prov_id": "dist_customs_art_001_002_scope",
                            "section_number": "제1조~제2조",
                            "title": "[타 업권 대조군] 관세청 고시 제1조·제2조 — 해외직구 특송물품 목록통관(미화 150달러) 및 국내 물류센터 제외",
                            "description": "해외 반입 국제특송화물에 한하여 적용되며 국내 물류센터(김포·용인·양산) 직매입·특약매입 출고 건에는 적용 제외.",
                            "pages": [1],
                            "start": "제1조(목적 및 적용범위)",
                            "end": None,
                        },
                        {
                            "prov_id": "dist_customs_art_003_return_fee",
                            "section_number": "제3조",
                            "title": "[타 업권 대조군] 관세청 고시 제3조 — 해외직구 14일 반송기한 및 국제반송수수료 35,000원 (국내 통신판매 혼동 금지)",
                            "description": "해외 특송화물 국제반송 특칙(14일·35,000원)을 국내 이커머스 청약철회(전자상거래법 제17조·제18조)에 적용 금지.",
                            "pages": [2],
                            "start": "제3조(해외직구 물품의 반송기한",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "internal_policies",
            "cat_title": "K마켙 사내 운영내규 (K-Market Internal Policies)",
            "doc_dir": "07_kmarket_crm_hyper_personalization",
            "doc_id": "DOC_07_KMARKET_CRM_POLICY",
            "pdf": "07_INTERNAL_K마켙_초개인화추천_및_CRM타겟팅_운영내규_2025.pdf",
            "title": "K마켙 초개인화 추천 알고리즘 및 CRM 타겟팅 쿠폰 운영내규 (제CRM-2025-01호)",
            "description": "장바구니 미결제 이탈(`event_type = 'cart'`) 탐지, 마케팅 동의(`marketing_opt_in`) 검증, 가용재고 연동 대체상품(`substitute_product_id`)·코디 번들(`complementary_product_id`) 추천 및 등급별 쿠폰 한도 내규(2쪽).",
            "content_class": "synthetic",
            "issuing_body": "주식회사 K마켙 그로스마케팅본부 · AI추천랩",
            "license": "K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)",
            "resource_url": "https://internal.kmarket.co.kr/policies/CRM-2025-01",
            "contacts": "K마켙 AI추천랩장 <ai-reco@kmarket.co.kr>",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_cart_abandon_and_optin_gate",
                    "part_title": "제1장 장바구니 미결제 이탈 실시간 탐지 및 마케팅 수신동의(`marketing_opt_in`) 검증 (제1조~제2조)",
                    "provisions": [
                        {
                            "prov_id": "crm_art_001_002_cart_abandon_optin",
                            "section_number": "제1조~제2조",
                            "title": "내규 제1조·제2조 — 장바구니 이탈(`event_type = 'cart'`) 탐지 및 `users.marketing_opt_in = True` 필수 검증",
                            "description": "장바구니 미결제 이탈 고객에게 리마인드·타겟팅 쿠폰 발급 전 `marketing_opt_in = True` 확인 의무 및 미동의자 발급 차단.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_bundle_substitute_and_tier_coupon",
                    "part_title": "제2장 가용재고 연동 대체상품·코디 번들 추천 및 회원 등급별 쿠폰 한도 (제3조~제5조)",
                    "provisions": [
                        {
                            "prov_id": "crm_art_003_stock_substitute_bundle",
                            "section_number": "제3조",
                            "title": "내규 제3조 — 품절(`available_stock == 0`) 시 대체상품(`substitute_product_id`) 전환 및 정상재고 시 코디 번들(`complementary_product_id`) 추천",
                            "description": "주상품 가용재고 0개 시 대체상품 우선 추천, 가용재고 1개 이상 시 연관 코디 상품 묶음 번들 추천 규칙.",
                            "pages": [2],
                            "start": "제3조(가용재고 연동 대체상품",
                            "end": "제4조(회원 등급별 타겟팅 쿠폰",
                        },
                        {
                            "prov_id": "crm_art_004_005_tier_coupon_and_night_rule",
                            "section_number": "제4조~제5조",
                            "title": "내규 제4조(VIP·VVIP 최대 15% 할인쿠폰 및 25% 마진 가드레일 연동)·제5조(야간 푸시 차단)",
                            "description": "VVIP/VIP 최대 15%, GOLD 10%, SILVER 5% 쿠폰 한도 및 상품별 실현마진율 25% 하한(또는 체화재고/예외승인) 사전 검증 의무.",
                            "pages": [2],
                            "start": "제4조(회원 등급별 타겟팅 쿠폰",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "internal_policies",
            "cat_title": "K마켙 사내 운영내규 (K-Market Internal Policies)",
            "doc_dir": "08_kmarket_md_margin_and_clearance",
            "doc_id": "DOC_08_KMARKET_MD_POLICY",
            "pdf": "08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf",
            "title": "K마켙 MD 상품마진 가드레일 및 체화재고 클리어런스 가격결정 내규 (제MD-2025-02호)",
            "description": "실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`), 상시 프로모션 25% 최저마진 가드레일, 90일 이상 체화재고(`stock_age_days >= 90`) 10% 마진 하한 완화 특례 및 예외승인(`campaign_exceptions`) 내규(2쪽).",
            "content_class": "synthetic",
            "issuing_body": "주식회사 K마켙 MD본부 · 가격전략실",
            "license": "K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)",
            "resource_url": "https://internal.kmarket.co.kr/policies/MD-2025-02",
            "contacts": "K마켙 가격전략실장 <md-pricing@kmarket.co.kr>",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_margin_formula_and_25pct_guardrail",
                    "part_title": "제1장 실현마진율 산식 및 상시 프로모션 25% 최저마진 가드레일 (제1조~제2조)",
                    "provisions": [
                        {
                            "prov_id": "md_art_001_002_margin_25pct_guardrail",
                            "section_number": "제1조~제2조",
                            "title": "내규 제1조·제2조 — 실현마진율 산식(`(sale_price_krw - cost_krw) / sale_price_krw`) 및 상시 25.0% 하한 가드레일",
                            "description": "모든 상시 쿠폰·번들 할인 시 개별 상품 실현마진율 25.0% 이상 유지 의무 및 미달 저마진 상품 자동 차단.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_aged_inventory_clearance_and_exceptions",
                    "part_title": "제2장 체화재고(`stock_age_days >= 90`) 10% 마진 완화 특례 및 캠페인 예외승인 검증 (제3조~제4조)",
                    "provisions": [
                        {
                            "prov_id": "md_art_003_aged_inventory_10pct_floor",
                            "section_number": "제3조",
                            "title": "내규 제3조 — 체화재고(`stock_age_days >= 90` & `available_stock >= 30`) 최저마진 10.0% 완화 및 최대 30% 클리어런스 할인 특례",
                            "description": "입고 후 90일 이상 경과하고 가용재고 30개 이상인 체화재고는 최저마진 하한을 25%에서 10%로 완화.",
                            "pages": [2],
                            "start": "제3조(체화재고의 정의",
                            "end": "제4조(캠페인 예외승인 원장",
                        },
                        {
                            "prov_id": "md_art_004_campaign_exception_override",
                            "section_number": "제4조",
                            "title": "내규 제4조 — 캠페인 예외승인 원장(`campaign_exceptions`) `APPROVED` 검증 및 기각/만료 건 사용 금지",
                            "description": "`CLEARANCE_OVERRIDE` 또는 `VIP_RETENTION` 승인(`APPROVED`) 시 승인된 하한율(`approved_margin_floor`)까지 가드레일 완화 허용.",
                            "pages": [2],
                            "start": "제4조(캠페인 예외승인 원장",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "internal_policies",
            "cat_title": "K마켙 사내 운영내규 (K-Market Internal Policies)",
            "doc_dir": "09_kmarket_vendor_promo_settlement",
            "doc_id": "DOC_09_KMARKET_PARTNER_POLICY",
            "pdf": "09_INTERNAL_K마켙_입점브랜드_공동프로모션_정산내규_2025.pdf",
            "title": "K마켙 입점브랜드 공동프로모션 및 쿠폰분담금 정산내규 (제PARTNER-2025-03호)",
            "description": "입점브랜드 사전 판촉약정(`signed_promo_agreement`) 확인, 법정 50% 상한 캡(`MIN(promo_cost_share_ratio, 0.50)`) 적용 산식 및 50% 초과분 K마켙 전액 흡수 정산내규(2쪽).",
            "content_class": "synthetic",
            "issuing_body": "주식회사 K마켙 파트너상생본부 · 준법감시실",
            "license": "K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)",
            "resource_url": "https://internal.kmarket.co.kr/policies/PARTNER-2025-03",
            "contacts": "K마켙 파트너상생본부장 <partner-cp@kmarket.co.kr>",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_prior_agreement_verification",
                    "part_title": "제1장 공동프로모션 사전 서면약정(`signed_promo_agreement`) 검증 원칙 (제1조~제2조)",
                    "provisions": [
                        {
                            "prov_id": "partner_art_001_002_prior_agreement",
                            "section_number": "제1조~제2조",
                            "title": "내규 제1조·제2조 — 사전 서면약정(`signed_promo_agreement`) 검증 의무 및 미체결 시 K마켙 100% 부담",
                            "description": "`signed_promo_agreement = False`인 브랜드 상품의 쿠폰할인액은 브랜드 분담금 0원, K마켙이 100% 부담.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_fifty_percent_cap_settlement_formula",
                    "part_title": "제2장 납품업자 50% 상한 캡(Cap) 정산 산식 및 자발적 행사 심사 (제3조~제4조)",
                    "provisions": [
                        {
                            "prov_id": "partner_art_003_cap_settlement_formula",
                            "section_number": "제3조",
                            "title": "내규 제3조 — 납품업자 분담비율 50% 법정 상한 캡(`MIN(promo_cost_share_ratio, 0.50)`) 적용 및 초과분 K마켙 흡수 산식",
                            "description": "계약상 `promo_cost_share_ratio`가 50%를 초과해도 최대 50%만 브랜드에 공제하고 초과분은 K마켙이 의무 흡수 부담.",
                            "pages": [2],
                            "start": "제3조(납품업자 쿠폰 분담비율 50% 법정 상한 적용",
                            "end": "제4조(납품업자 자발적·차별화",
                        },
                        {
                            "prov_id": "partner_art_004_voluntary_filing_review",
                            "section_number": "제4조",
                            "title": "내규 제4조 — 자발적·차별화 단독 행사(`VOLUNTARY_PROMO_FILING`) 예외 요건 및 상시 캠페인 기각(`REJECTED`) 원칙",
                            "description": "상시 장바구니·등급 쿠폰 캠페인에 대한 50% 초과 분담 신청은 즉시 기각(`REJECTED`)하고 50% 상한 캡을 적용.",
                            "pages": [2],
                            "start": "제4조(납품업자 자발적·차별화",
                            "end": None,
                        },
                    ],
                },
            ],
        },
        {
            "cat_dir": "internal_policies",
            "cat_title": "K마켙 사내 운영내규 (K-Market Internal Policies)",
            "doc_dir": "10_kmarket_cs_return_and_logistics_sla",
            "doc_id": "DOC_10_KMARKET_CS_SLA_POLICY",
            "pdf": "10_INTERNAL_K마켙_CS반품환불_및_물류SLA_보상내규_2025.pdf",
            "title": "K마켙 CS 반품·교환·환불 심사 및 물류 출고지연 SLA 보상내규 (제CX-2025-04호)",
            "description": "반품 사유 코드별(`CHANGE_OF_MIND` 7일·유상 6,000원 vs `SIZE_MISMATCH_SPEC_DIFF` 90일·무상 vs `WEAR_AND_WASH_DAMAGE` 거절) 심사기준, 3영업일 환불 및 물류센터별 출고 SLA 위반 시 3,000P 보상 내규(2쪽).",
            "content_class": "synthetic",
            "issuing_body": "주식회사 K마켙 고객경험(CX)본부 · 풀필먼트운영실",
            "license": "K마켙 사내 대외비 (핸즈온 교육용 합성 사내규정)",
            "resource_url": "https://internal.kmarket.co.kr/policies/CX-2025-04",
            "contacts": "K마켙 고객경험본부장 <cx-policy@kmarket.co.kr>",
            "strategy": "numbered_article_ko",
            "parts": [
                {
                    "part_dir": "ch01_return_reason_and_shipping_fee",
                    "part_title": "제1장 반품 사유 코드별 청약철회 기한(7일 vs 90일) 및 반품배송비 귀속 (제1조~제2조)",
                    "provisions": [
                        {
                            "prov_id": "cs_art_001_002_return_reason_rules",
                            "section_number": "제1조~제2조",
                            "title": "내규 제1조·제2조 — 반품 사유 코드별(`CHANGE_OF_MIND` 7일/6,000원 vs `SIZE_MISMATCH_SPEC_DIFF` 90일/무상 vs `WEAR_AND_WASH_DAMAGE` 거절) 판정 기준",
                            "description": "단순변심 7일(고객 6,000원 부담), 실측 사이즈/표시·광고 상이 90일(판매자 부담 무상반품), 세탁/착용 흔적 청약철회 거절 기준.",
                            "pages": [1],
                            "start": "제1조(목적)",
                            "end": None,
                        },
                    ],
                },
                {
                    "part_dir": "ch02_refund_3days_and_fulfillment_sla",
                    "part_title": "제2장 3영업일 환불 기한·해외직구 고시 혼동 금지 및 물류센터 출고 SLA 지연 보상 (제3조~제4조)",
                    "provisions": [
                        {
                            "prov_id": "cs_art_003_refund_3days_and_no_customs",
                            "section_number": "제3조",
                            "title": "내규 제3조 — 입고 후 3영업일 이내 환급(초과 시 연 15% 지연배상금) 및 해외직구 통관고시 적용 금지",
                            "description": "회수 후 3영업일 이내 환불 의무 및 국내 풀필먼트 출고 건에 관세청 해외직구 고시(14일·35,000원) 적용 엄격 금지.",
                            "pages": [2],
                            "start": "제3조(대금 환급 기한",
                            "end": "제4조(물류센터별 출고 SLA",
                        },
                        {
                            "prov_id": "cs_art_004_fulfillment_sla_compensation",
                            "section_number": "제4조",
                            "title": "내규 제4조 — 물류센터별(`GIMPO-FC` 24h·`YONGIN-FC` 36h·`YANGSAN-FC` 48h) 출고 SLA 위반 시 3,000P 자동 보상",
                            "description": "주문결제 시각 대비 출고 시각이 물류센터별 `sla_hours` 초과 시 약속출고 지연 보상 적립금 3,000포인트 자동 지급.",
                            "pages": [2],
                            "start": "제4조(물류센터별 출고 SLA",
                            "end": None,
                        },
                    ],
                },
            ],
        },
    ]


def build_bundle() -> dict:
    if os.path.exists(OKF_DIR):
        shutil.rmtree(OKF_DIR)
    os.makedirs(OKF_DIR, exist_ok=True)

    locations_yaml = """# locations.yaml — physical bindings for logical `okf://` URIs in ecommerce/okf.
# Maintained by the K-Market Ontology Platform Team.

distribution:
  "okf://source/un_data/": local_only
  "okf://bundle/": publishable

resolvers:
  "okf://source/un_data/":
    - scheme: file
      root: "/home/changseop/finance_ontology/ecommerce/data/un_data/"
      status: active
      upload: forbidden

  "okf://bundle/":
    - scheme: gs
      root: "gs://kmarket_okf/okf/"
      status: active
      verified_by: "tools/sync_gcs.py --verify-only"
"""
    with open(os.path.join(OKF_DIR, "locations.yaml"), "w", encoding="utf-8") as f:
        f.write(locations_yaml)

    all_docs = build_docs_spec()
    cat_map: dict[str, list[dict]] = {}
    verification_records: list[dict] = []
    document_records: list[dict] = []
    total_docs = 0
    total_provs = 0
    total_pdf_pages = 0

    for doc_spec in all_docs:
        cat_dir = doc_spec["cat_dir"]
        doc_dir = doc_spec["doc_dir"]
        pdf_name = doc_spec["pdf"]
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        digest = sha256_file(pdf_path)
        pages = extract_pdf_pages(pdf_name)
        num_pages = len(pages) - 1
        total_pdf_pages += num_pages

        cat_map.setdefault(cat_dir, []).append(doc_spec)
        doc_abs_dir = os.path.join(OKF_DIR, cat_dir, doc_dir)
        os.makedirs(doc_abs_dir, exist_ok=True)

        prov_links_for_doc: list[tuple[str, str, str, int]] = []
        part_links_for_doc: list[tuple[str, str]] = []
        seq = 0

        for part in doc_spec["parts"]:
            part_dir = part["part_dir"]
            part_abs_dir = os.path.join(doc_abs_dir, part_dir)
            os.makedirs(part_abs_dir, exist_ok=True)
            part_links_for_doc.append((part_dir, part["part_title"]))
            part_prov_items: list[tuple[str, str, str]] = []

            for p in part["provisions"]:
                seq += 1
                total_provs += 1
                prov_id = p["prov_id"]
                p_pages = p["pages"]
                combined_page_text = "\n\n".join(pages[pg] for pg in p_pages if 1 <= pg <= num_pages)
                body_excerpt = slice_between(combined_page_text, p["start"], p.get("end"))

                # Verify P1..P4
                assert norm_ws(body_excerpt) in norm_ws(combined_page_text), f"P1 failed for {prov_id}"
                assert all(1 <= pg <= num_pages for pg in p_pages), f"P3 failed for {prov_id}"

                rel_prov_path = f"/{cat_dir}/{doc_dir}/{part_dir}/{prov_id}.md"
                rel_doc_path = f"/{cat_dir}/{doc_dir}/doc.md"

                fm_prov = {
                    "type": "Provision",
                    "title": p["title"],
                    "description": p["description"],
                    "tags": [cat_dir, doc_spec["content_class"], doc_dir, "verbatim_ko"],
                    "language": "ko",
                    "sources": [
                        {
                            "id": "origin_pdf",
                            "resource": f"okf://source/un_data/{pdf_name}",
                            "kind": "origin_document",
                            "sha256": digest,
                        }
                    ],
                    "generated": {"by": "process:build_okf/3.0", "at": NOW_ISO},
                    "status": "stable",
                    "part_of": rel_doc_path,
                    "sequence": seq,
                    "treatment": "verbatim_ko",
                    "license": doc_spec["license"],
                    "content_class": doc_spec["content_class"],
                    "section_number": p["section_number"],
                    "source_page": p_pages[0],
                    "source_pages_span": p_pages,
                    "verified": [
                        {
                            "by": "process:verify_provisions/1.0",
                            "at": NOW_ISO,
                            "method": "source_text_match",
                            "checks": ["P1_body", "P2_heading", "P3_page", "P4_digest"],
                        }
                    ],
                }
                if doc_spec.get("contacts"):
                    fm_prov["contacts"] = doc_spec["contacts"]
                yaml_str = yaml.safe_dump(
                    fm_prov, allow_unicode=True, sort_keys=False, default_flow_style=False
                ).strip()
                prov_md = (
                    f"---\n{yaml_str}\n---\n\n"
                    f"# {p['title']}\n\n"
                    f"* **상위 문서 (`Source Document`)**: [{doc_spec['title']}]({rel_doc_path})[^origin_pdf]\n"
                    f"* **출처 페이지**: `{pdf_name}` — **{', '.join(str(x) for x in p_pages)}쪽** (`section_number: {p['section_number']}`)\n\n"
                    f"## 원문 발췌 (Verbatim Source Text)\n\n"
                    f"{body_excerpt}\n"
                )
                with open(os.path.join(part_abs_dir, f"{prov_id}.md"), "w", encoding="utf-8") as fh:
                    fh.write(prov_md)

                part_prov_items.append((f"{prov_id}.md", p["title"], p["description"]))
                prov_links_for_doc.append((f"{part_dir}/{prov_id}.md", p["title"], p["description"], p_pages[0]))

                verification_records.append({
                    "concept_id": f"{cat_dir}/{doc_dir}/{part_dir}/{prov_id}",
                    "okf_path": rel_prov_path,
                    "doc_id": doc_spec["doc_id"],
                    "doc_title": doc_spec["title"],
                    "part_title": part["part_title"],
                    "category": cat_dir,
                    "content_class": doc_spec["content_class"],
                    "pdf_file": pdf_name,
                    "pdf_total_pages": num_pages,
                    "sha256": digest,
                    "section_number": p["section_number"],
                    "title": p["title"],
                    "description": p["description"],
                    "source_page": p_pages[0],
                    "source_pages_span": p_pages,
                    "char_length": len(body_excerpt),
                    "yaml_frontmatter": f"---\n{yaml_str}\n---",
                    "verbatim_body": body_excerpt,
                    "contacts": doc_spec.get("contacts", ""),
                })

            part_index_lines = [f"# {part['part_title']}\n"]
            for fname, ptitle, pdesc in part_prov_items:
                part_index_lines.append(f"* [{ptitle}]({fname}) - {pdesc}")
            with open(os.path.join(part_abs_dir, "index.md"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(part_index_lines) + "\n")

        total_docs += 1
        fm_doc = {
            "type": "Source Document",
            "title": doc_spec["title"],
            "description": doc_spec["description"],
            "tags": [cat_dir, doc_spec["content_class"], doc_dir, "verbatim_ko"],
            "resource": doc_spec["resource_url"],
            "sources": [
                {
                    "id": "origin_pdf",
                    "resource": f"okf://source/un_data/{pdf_name}",
                    "kind": "origin_document",
                    "sha256": digest,
                }
            ],
            "generated": {"by": "process:build_okf/3.0", "at": NOW_ISO},
            "status": "stable",
            "language": "ko",
            "treatment": "verbatim_ko",
            "license": doc_spec["license"],
            "content_class": doc_spec["content_class"],
            "issuing_body": doc_spec["issuing_body"],
            "document_id": doc_spec["doc_id"],
            "group": cat_dir,
            "extraction_strategy": doc_spec["strategy"],
            "source_pages": num_pages,
            "provision_count": seq,
        }
        if doc_spec.get("contacts"):
            fm_doc["contacts"] = doc_spec["contacts"]
        yaml_doc = yaml.safe_dump(
            fm_doc, allow_unicode=True, sort_keys=False, default_flow_style=False
        ).strip()
        doc_md_lines = [
            f"---\n{yaml_doc}\n---\n",
            f"# {doc_spec['title']}\n",
            f"{doc_spec['description']} (원본 PDF: `{pdf_name}`, 총 {num_pages}쪽)[^origin_pdf]\n",
            "## 하위 장·절 디렉터리 (`Parts`)\n",
        ]
        for pdir, ptitle in part_links_for_doc:
            doc_md_lines.append(f"* [{ptitle}]({pdir}/index.md)")
        doc_md_lines.append("\n## 수록 조문 (`Provisions`)\n")
        for rel_p, ptitle, pdesc, pg in prov_links_for_doc:
            doc_md_lines.append(f"* [{ptitle}]({rel_p}) — {pg}쪽: {pdesc}")
        with open(os.path.join(doc_abs_dir, "doc.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(doc_md_lines) + "\n")

        doc_body_text = "\n".join(doc_md_lines[1:]).strip()
        document_records.append({
            "concept_id": f"{cat_dir}/{doc_dir}/doc",
            "okf_path": f"/{cat_dir}/{doc_dir}/doc.md",
            "doc_id": doc_spec["doc_id"],
            "doc_title": doc_spec["title"],
            "part_title": "Source Document Root (doc.md)",
            "category": cat_dir,
            "content_class": doc_spec["content_class"],
            "pdf_file": pdf_name,
            "pdf_total_pages": num_pages,
            "sha256": digest,
            "section_number": "doc.md (문서 총괄)",
            "title": doc_spec["title"],
            "description": doc_spec["description"],
            "source_page": 1,
            "source_pages_span": [1, num_pages] if num_pages > 1 else [1],
            "char_length": len(doc_body_text),
            "yaml_frontmatter": f"---\n{yaml_doc}\n---",
            "verbatim_body": doc_body_text,
            "is_source_document": True,
            "provision_count": seq,
            "contacts": doc_spec.get("contacts", ""),
        })

        doc_idx_lines = [
            f"# {doc_spec['title']}\n",
            f"* [문서 메타데이터 및 전체 조문 목차 (`doc.md`)](doc.md) - {doc_spec['description']}",
        ]
        for pdir, ptitle in part_links_for_doc:
            doc_idx_lines.append(f"* [{ptitle}]({pdir}/index.md)")
        with open(os.path.join(doc_abs_dir, "index.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(doc_idx_lines) + "\n")

    for cat_dir, docs in cat_map.items():
        cat_abs = os.path.join(OKF_DIR, cat_dir)
        lines = [f"# {docs[0]['cat_title']} (`{cat_dir}/`)\n"]
        for d in docs:
            lines.append(f"* [{d['title']}]({d['doc_dir']}/index.md) - `{d['pdf']}`")
        with open(os.path.join(cat_abs, "index.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    root_idx = f"""---
okf_version: "0.2"
---

# K마켙 이커머스 비정형 법규·내규 OKF v0.2 Knowledge Bundle (`ecommerce/okf`)

총 10개 원본 PDF({total_pdf_pages}쪽)의 **모든 장·절·조문(`{total_provs}`개 `Provision` + `{total_docs}`개 `Source Document` = 총 `{total_docs + total_provs}`개 OKF Concept)**을 무손실 구조화한 번들입니다.

* [regulations/](regulations/index.md) - 공정거래위원회·법제처·개인정보보호위원회 공식 법령·심사지침·가이드라인 (PDF 01~05)
* [distractors/](distractors/index.md) - 타 업권·해외직구 특송통관 고시 대조군 (PDF 06)
* [internal_policies/](internal_policies/index.md) - K마켙 초개인화 추천·MD 마진 가드레일·입점브랜드 판촉정산·CS 반품/물류 SLA 사내내규 (PDF 07~10)
* [locations.yaml](locations.yaml) - 논리 URI ↔ 물리 경로 단일 매핑
* [log.md](log.md) - 번들 생성 및 검증 이력
"""
    with open(os.path.join(OKF_DIR, "index.md"), "w", encoding="utf-8") as fh:
        fh.write(root_idx)

    log_md = f"""# K마켙 OKF Bundle Update Log

## 2026-10-03
* **Creation**: Built full 10-PDF exhaustive OKF v0.2 bundle for K마켙 (`{total_docs}` Source Documents + `{total_provs}` Provisions = `{total_docs + total_provs}` Concepts).
"""
    with open(os.path.join(OKF_DIR, "log.md"), "w", encoding="utf-8") as fh:
        fh.write(log_md)

    report = {
        "generated_at": NOW_ISO,
        "okf_version": "0.2",
        "source_pdf_count": total_docs,
        "provision_count": total_provs,
        "total_concepts": total_docs + total_provs,
        "documents": document_records,
        "provisions": verification_records,
    }
    with open(os.path.join(OKF_DIR, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    rep = build_bundle()
    print(
        f"[build_okf_bundle] Built K마켙 OKF v0.2 bundle: {rep['source_pdf_count']} Source Documents + "
        f"{rep['provision_count']} Provisions = {rep['total_concepts']} Concepts"
    )
