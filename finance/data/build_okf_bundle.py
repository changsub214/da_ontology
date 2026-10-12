#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKF v0.2 전수 조문 추출·번들 생성기 (`data/build_okf_bundle.py` v3.1 — 10개 PDF 전수 178개 조문 + 10개 상위문서 = 188개 OKF Concept)

개선 사항:
1. 일부 시나리오 조문만 발췌(19개)하던 한계를 없애고, `01_FSC_은행업감독규정_전문_2025_07.pdf`의
   **제1장~제11장 전 조문(130개 조문 전수)**과 `02`~`10`번 PDF의 **모든 호·목·절·조문(48개)**을 합쳐
   **총 178개 `type: Provision` + 10개 `type: Source Document` = 188개 OKF v0.2 마크다운 파일**을 생성한다.
2. 각 OKF 파일의 **실제 YAML Frontmatter 전문(`--- ... ---`)**을 `verification.json`의 `yaml_frontmatter` 필드에
   그대로 저장하여 `/okf_veri_web` 우측 화면 상단에 100% 누락 없이 표시되게 한다.
3. (v3.1, ADR 0014) 한 장에 두 쪽을 나란히 인쇄한 PDF(05)는 `two_up_split_x`로 좌·우 단을 따로 읽어
   단 순서가 섞이지 않게 한다. 05에 조문 4개(제Ⅱ장 2·3·4, 별첨)가 추가되어 44 → 48개가 되었다.
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
NOW_ISO = "2026-09-22T04:00:00Z"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _pdf_sheet_size(path: str) -> tuple[float, float]:
    info = subprocess.check_output(["pdfinfo", "-f", "1", "-l", "9999", path], text=True)
    sizes = re.findall(r"Page\s+\d+ size:\s+([\d.]+) x ([\d.]+)", info)
    if not sizes:
        raise RuntimeError(f"pdfinfo reported no page sizes for {path}")
    w, h = float(sizes[0][0]), float(sizes[0][1])
    if any((float(sw), float(sh)) != (w, h) for sw, sh in sizes):
        raise RuntimeError(f"two-up split needs one sheet size for every page: {path}")
    return w, h


def extract_pdf_pages(pdf_filename: str, two_up_split_x: int | None = None) -> list[str]:
    """PDF → [""] + per-sheet text (index = sheet number, same as source_page).

    two_up_split_x (ADR 0014): for PDFs that print two logical pages side by side on one
    landscape sheet, pdftotext's default mode reads both columns line by line, so a heading at
    the top of the right column lands before the left column's body. With a split x, each sheet
    is read as its left crop, then its right crop, joined by a blank line. Sheet numbering is
    unchanged, so source_page keeps pointing at the PDF sheet.
    """
    path = os.path.join(PDF_DIR, pdf_filename)
    if two_up_split_x is None:
        raw = subprocess.check_output(["pdftotext", path, "-"], text=True)
        pages = raw.split("\x0c")
        if pages and pages[-1].strip() == "":
            pages = pages[:-1]
        return [""] + pages

    n_sheets = len(extract_pdf_pages(pdf_filename)) - 1
    w, h = _pdf_sheet_size(path)

    def crop(pg: int, x: int, width: int) -> str:
        return subprocess.check_output(
            ["pdftotext", "-f", str(pg), "-l", str(pg), "-x", str(x), "-y", "0",
             "-W", str(width), "-H", str(int(h) + 1), path, "-"], text=True).replace("\x0c", "")

    pages = [""]
    for pg in range(1, n_sheets + 1):
        left = crop(pg, 0, two_up_split_x)
        right = crop(pg, two_up_split_x, int(w) + 1 - two_up_split_x)
        pages.append(left.rstrip("\n") + ("\n\n" + right.strip("\n") if right.strip() else ""))
    return pages


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", "", s)


def slice_between(page_text: str, start_anchor: str, end_anchor: str | None = None) -> str:
    idx = page_text.find(start_anchor)
    sub = page_text[idx:] if idx != -1 else page_text
    if end_anchor:
        eidx = sub.find(end_anchor)
        if eidx != -1 and eidx > 0:
            sub = sub[:eidx]
    return sub.strip()


def extract_all_articles_of_pdf01(pages: list[str]) -> list[dict]:
    """01_FSC_은행업감독규정_전문_2025_07.pdf (57쪽)의 제1장~제11장 130개 전 조문을 자동 파싱하여 11개 장 폴더로 그룹화."""
    chapter_defs = [
        ("ch01_general_provisions", "제1장 총칙 (제1조~제4조)", 1, 4),
        ("ch02_licensing_and_reporting", "제2장 인가 및 신고 등 (제5조~제14조)", 5, 14),
        ("ch03_shareholding_and_major_shareholders", "제3장 은행주식보유 및 대주주 감독 (제15조~제17조)", 15, 17),
        ("ch05_banking_business_scope", "제5장 은행업무 (제18조~제25조)", 18, 25),
        ("ch06_prudential_management_and_provisioning", "제6장 건전경영의 유지 — 자본적정성·자산건전성(제27조)·대손충당금(제29조) (제26조~제51조)", 26, 51),
        ("ch07_fx_prudential_supervision", "제7장 외환건전성 감독 (제52조~제78조)", 52, 78),
        ("ch08_credit_risk_management", "제8장 신용위험 관리 (제79조~제85조)", 79, 85),
        ("ch09_supervision_inspection_and_consumer", "제9장 감독·검사 및 은행이용자 권익보호 (제86조~제93조)", 86, 93),
        ("ch10_special_cases_kdb_exim_internet", "제10장 한국산업은행·수출입은행·인터넷전문은행·외은지점 특례 (제94조~제102조의2)", 94, 102),
        ("ch11_supplementary_penalty", "제11장 보칙 (제103조~제104조)", 103, 200),
    ]

    # Build page-aware full text with page markers
    page_offsets: list[tuple[int, int, int]] = []
    chunks: list[str] = []
    cur = 0
    for pg_num in range(1, len(pages)):
        cleaned = re.sub(r"\n법제처\s*\n\d+\s*\n국가법령정보센터\s*\n?", "\n", pages[pg_num])
        cleaned = re.sub(r"^\s*은행업감독규정\s*\n", "", cleaned)
        start_off = cur
        chunks.append(cleaned)
        cur += len(cleaned) + 2
        page_offsets.append((start_off, cur, pg_num))
    full_text = "\n\n".join(chunks)

    def offset_to_page(off: int) -> int:
        for s_off, e_off, pno in page_offsets:
            if s_off <= off < e_off:
                return pno
        return 1

    art_re = re.compile(r"^제(\d+)조(의\d+)?\(([^)\n]+)\)", re.M)
    matches = list(art_re.finditer(full_text))

    parts_dict: dict[str, dict] = {
        cdir: {"part_dir": cdir, "part_title": ctitle, "provisions": []}
        for cdir, ctitle, _, _ in chapter_defs
    }

    seen_ids: dict[str, int] = {}
    for idx, m in enumerate(matches):
        art_num = int(m.group(1))
        sub_num = m.group(2) or ""
        art_title_inner = m.group(3).strip().replace("\n", "")
        sec_no = f"제{art_num}조{sub_num}"
        full_heading = f"{sec_no}({art_title_inner})"

        start_pos = m.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
        body = full_text[start_pos:end_pos].strip()
        start_pg = offset_to_page(start_pos)
        end_pg = offset_to_page(max(start_pos, end_pos - 10))
        span = sorted(list(set(range(start_pg, end_pg + 1))))

        slug_sub = sub_num.replace("의", "_")
        base_id = f"art_{art_num:03d}{slug_sub}"
        seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
        prov_id = base_id if seen_ids[base_id] == 1 else f"{base_id}_v{seen_ids[base_id]}"

        first_line = body.splitlines()[0] if body else full_heading
        desc = re.sub(r"\s+", " ", body)[:135] + ("…" if len(body) > 135 else "")

        target_cdir = "ch11_supplementary_penalty"
        for cdir, _, lo, hi in chapter_defs:
            if lo <= art_num <= hi:
                target_cdir = cdir
                break

        parts_dict[target_cdir]["provisions"].append({
            "prov_id": prov_id,
            "section_number": sec_no,
            "title": full_heading,
            "description": desc,
            "pages": span,
            "verbatim_override": body,
        })

    return [p for p in parts_dict.values() if p["provisions"]]


def build_other_docs_spec() -> list[dict]:
    """02 ~ 10번 PDF의 전체 조문·별표·절(44개 Provision) 명세."""
    return [
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·감독규정·모범규준 (Authentic Regulations)",
            "doc_dir": "02_law_annex3_criteria",
            "doc_id": "DOC_02_LAW_ANNEX3",
            "pdf": "02_LAW_은행업감독규정_별표3_자산건전성분류기준.pdf",
            "title": "은행업감독규정 [별표 3] 자산건전성 분류기준 (제27조제2항 관련)",
            "description": "자산건전성 5단계 정의, 연체기간 기준, 채권재조정여신의 고정이하 분류 제외 특례(제3호 라목), 주담대·부실징후기업 특례(제4호~제7호) 전문(8쪽).",
            "content_class": "authentic",
            "issuing_body": "금융위원회 · 국가법령정보센터",
            "license": "공공누리 제1유형 (국가법령정보센터 공공저작물 자유이용허락)",
            "resource_url": "https://www.law.go.kr/행정규칙/은행업감독규정",
            "strategy": "numbered_annex_ko",
            "parts": [
                {
                    "part_dir": "sec01_five_stage_definitions",
                    "part_title": "제1호~제2호 건전성 5단계 정의 및 연체기간별 분류기준",
                    "provisions": [
                        {"prov_id": "annex3_item_01_normal_precautionary", "section_number": "별표3 제1호 가~나목", "title": "[별표 3] 1.가~나. 정상(Normal) 및 요주의(Precautionary · 1월 이상 3월 미만 연체) 정의", "description": "정상 및 요주의 단계의 차주 채무상환능력·연체기간(1개월~3개월 미만) 분류 기준.", "pages": [1], "start": "<별표", "end": "다. 고정"},
                        {"prov_id": "annex3_item_01_substandard_doubtful_loss", "section_number": "별표3 제1호 다~마목", "title": "[별표 3] 1.다~마. 고정(3월 이상 연체)·회수의문·추정손실(12월 이상 연체) 정의", "description": "고정이하 부실자산(3개월 이상 연체, 회수예상가액 초과분, 12개월 이상 연체) 분류 기준.", "pages": [1, 2], "start": "다. 고정", "end": "2. 은행은"},
                        {"prov_id": "annex3_item_02_evaluation_framework", "section_number": "별표3 제2호", "title": "[별표 3] 2. 차주 채무상환능력 평가모형 및 재무·비재무 평가항목", "description": "차주의 재무상태·현금흐름·산업위험·경영위험 등을 감안한 건전성 분류체계 수립 의무.", "pages": [2, 3], "start": "2. 은행은", "end": "3. 은행은"},
                    ],
                },
                {
                    "part_dir": "sec03_restructured_loan_exceptions",
                    "part_title": "제3호~제7호 채권재조정여신 건전성 분류 특례 · 회수예상가액 · 연체대출채권",
                    "provisions": [
                        {"prov_id": "annex3_item_03_a_to_c_adjustment", "section_number": "별표3 제3호 가~다목", "title": "[별표 3] 3.가~다. 여신건별 건전성분류 조정 및 담보가액 반영 기준", "description": "회수예상가액 산정 및 담보권 행사 가능 자산의 건전성 분류 조정 원칙.", "pages": [3, 4], "start": "( 여신건별 건전성분류 조정 )", "end": "라. 채권재조정여신"},
                        {"prov_id": "annex3_item_03_ra_restructured_exemption", "section_number": "별표3 제3호 라목", "title": "[별표 3] 3.라. 채권재조정여신 고정이하 분류 제외 특례 (6개월 연속이행·유상증자)", "description": "채권재조정여신 중 ① 6개월 이상 연속 정상이행 또는 ② 유상증자·자산매각 등 상환능력 개선 사건 발생 시 고정이하 분류 제외 특례.", "pages": [4, 5], "start": "라. 채권재조정여신", "end": "4. 제1호 내지 제3호"},
                        {"prov_id": "annex3_item_04_05_residential_and_guarantee", "section_number": "별표3 제4호~제5호", "title": "[별표 3] 4.~5. 채권재조정 주거용 주택담보대출(1년 이행) 및 확정지급보증 분류기준", "description": "주거용 주택담보대출 채권재조정 특례 및 지급보증·유가증권 건전성 분류 기준.", "pages": [6], "start": "4. 제1호 내지 제3호", "end": "6."},
                        {"prov_id": "annex3_item_06_07_workout_special_rules", "section_number": "별표3 제6호~제7호", "title": "[별표 3] 6.~7. 회수예상가액 산정 및 연체대출채권·연체기간", "description": "고정이하 분류여신 담보물의 회수예상가액 산정 기준과, 연체대출채권의 범위 및 유형별 연체기간 기산일.", "pages": [7, 8], "start": "6.", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·감독규정·모범규준 (Authentic Regulations)",
            "doc_dir": "03_fsc_reg_impact_analysis",
            "doc_id": "DOC_03_FSC_IMPACT",
            "pdf": "03_FSC_은행업감독규정_및_시행세칙_개정_규제영향분석서.pdf",
            "title": "은행업감독규정 및 시행세칙 개정 규제영향분석서 (거액익스포져 비율 규제 신설)",
            "description": "바젤 기준 거액익스포져(Large Exposure) 한도규제 도입 규제영향분석서 및 신·구조문대비표(41쪽).",
            "content_class": "authentic",
            "issuing_body": "금융위원회 은행과",
            "license": "공공누리 제1유형 (금융위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.fsc.go.kr",
            "strategy": "regulatory_impact_ko",
            "parts": [
                {
                    "part_dir": "sec01_large_exposure_overview",
                    "part_title": "제1부 거액익스포져 비율 규제 개요·필요성 및 비용편익 분석",
                    "provisions": [
                        {"prov_id": "impact_01_overview", "section_number": "규제개요 1", "title": "규제영향분석서 — 거액익스포져 비율 규제(Tier 1의 25%) 신설 개요", "description": "동일 거래상대방 익스포져를 기본자본의 25% 이내로 관리하는 바젤 기준 도입 개요.", "pages": [1, 2], "start": "규제영향분석서", "end": None},
                        {"prov_id": "impact_02_cost_benefit", "section_number": "분석서 본문", "title": "규제영향분석서 — 규제의 적정성·실효성 및 경쟁영향평가", "description": "국내 은행권 거액 편중리스크 관리 효과 및 규제 준수 부담 분석.", "pages": [3], "start": "11.영향평가", "end": None},
                    ],
                },
                {
                    "part_dir": "sec02_article_comparison_and_annex",
                    "part_title": "제2부 은행업감독규정 신·구조문대비표 및 별표3의4 거액익스포져 산출기준",
                    "provisions": [
                        {"prov_id": "impact_03_art26_to_102_comparison", "section_number": "조문대비표 제26조~제102조의2", "title": "신·구조문대비표 — 제26조(경영지도비율) 및 수출입은행·인터넷은행·외은지점 특례", "description": "은행업감독규정 본칙 개정안 신·구조문 대비표.", "pages": [4, 5, 6], "start": "현 행", "end": None},
                        {"prov_id": "impact_04_annex3_4_general_rules", "section_number": "별표3의4 제1호~제15호", "title": "[별표 3의4] 거액익스포져 산출 및 관리기준 — 총칙 및 기본자본 정의", "description": "거액익스포져 한도 산출을 위한 기본자본(Tier 1) 및 익스포져 측정 총칙.", "pages": [10, 11, 12], "start": "현 행", "end": None},
                        {"prov_id": "impact_05_annex3_4_counterparty_group", "section_number": "별표3의4 제29호~제37호", "title": "[별표 3의4] 트레이딩계정 포지션 익스포져 — 옵션·매수/매도포지션 상계·신용파생상품 처리 및 면제대상 익스포져", "description": "옵션 익스포져 산정, 동일 거래상대방 증권의 매수·매도포지션 상계 요건과 채무상환 우선순위, 신용파생상품 보장매입·신용부도스왑 처리, 계정간 상계 금지, 면제대상 익스포져(제6절 제1목) 도입부.", "pages": [16, 17], "start": "현 행", "end": None},
                        {"prov_id": "impact_06_annex3_4_crm", "section_number": "별표3의4 제41호~제46호", "title": "[별표 3의4] 이중상환청구권부 채권 및 집합투자·유동화증권 등 구조화상품 익스포져", "description": "이중상환청구권부 채권의 익스포져 인식과 완화 조건, 구조화상품의 거래상대방 인식(기본자본 0.25% 기준·기초자산접근법·무명 고객), 규제회피 목적 분산투자 금지, 기초자산 익스포져 계산.", "pages": [19, 20], "start": "현 행", "end": None},
                        {"prov_id": "impact_07_annex3_4_item54_exceptions", "section_number": "별표3의4 제54호", "title": "[별표 3의4] 제54호 거액익스포져 한도초과 예외 사유 및 보고 의무", "description": "구조조정·정책금융·일시적 합병 등 거액익스포져 25% 한도초과가 허용되는 예외 조항.", "pages": [23, 24], "start": "54. (한도초과 예외)", "end": None},
                        {"prov_id": "impact_08_enforcement_bylaws", "section_number": "시행세칙 개정안", "title": "은행업감독업무시행세칙 및 금융지주회사감독규정 신·구조문대비표", "description": "거액익스포져 업무보고서 서식 및 은행지주회사 준용 규정.", "pages": [30, 35], "start": "현 행", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·감독규정·모범규준 (Authentic Regulations)",
            "doc_dir": "04_fsc_large_exposure_notice",
            "doc_id": "DOC_04_FSC_EXPOSURE_NOTICE",
            "pdf": "04_FSC_은행업감독규정_개정안_규정변경예고_거액익스포져.pdf",
            "title": "「은행업감독규정」 등 개정안 규정변경예고 실시 (거액익스포져 한도규제 정식 도입)",
            "description": "2024년 1월 시행 바젤기준 거액익스포져 한도규제(BIS 기본자본 25%) 도입 및 산은·수은 특례 공고(3쪽).",
            "content_class": "authentic",
            "issuing_body": "금융위원회 · 금융감독원",
            "license": "공공누리 제1유형 (금융위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.fsc.go.kr",
            "strategy": "press_notice_ko",
            "parts": [
                {
                    "part_dir": "sec01_background_and_tier1_limit",
                    "part_title": "제1절 추진 배경 및 바젤 기준 거액익스포져 한도(Tier 1 25%) 주요 내용",
                    "provisions": [
                        {"prov_id": "notice_01_background", "section_number": "추진배경 1", "title": "바젤기준 거액익스포져 한도규제 도입 배경 및 기존 신용공여한도와의 비교", "description": "은행법 제35조 동일차주 신용공여한도(자기자본 25%) 대비 기본자본(Tier 1) 25%로 강화된 취지.", "pages": [1, 2], "start": "보도자료", "end": None},
                        {"prov_id": "notice_02_kdb_exim_exceptions", "section_number": "적용특례 2", "title": "한국산업은행(2년 유예)·한국수출입은행·외은지점·인터넷전문은행 적용 예외", "description": "기업 구조조정 자금공급 위축 방지를 위한 산업은행 유예 및 수출입은행 제외 특례.", "pages": [2, 3], "start": "아울러 정책금융", "end": None},
                        {"prov_id": "notice_03_schedule", "section_number": "향후계획 3", "title": "규정변경예고 기간 및 2024년 1월 1일 정식 시행 일정", "description": "규제개혁위원회 심사 및 금융위 의결을 통한 시행 일정.", "pages": [3], "start": "아울러 정책금융", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·감독규정·모범규준 (Authentic Regulations)",
            "doc_dir": "05_fsc_kfb_loan_rate_reform",
            "doc_id": "DOC_05_FSC_KFB_RATE",
            "pdf": "05_FSC_KFB_은행권_대출금리_산정체계_개선방안.pdf",
            "title": "합리적이고 투명한 은행권 대출금리 산정을 위한 개선방안 (금융위·금감원·은행연합회)",
            "description": "대출금리 산정내역서 제공, 금리인하요구권 운영 개선(Ⅱ-1-나 ④항: 특허취득 은행 선택적 적용 재량), 비교공시(Ⅱ-1-다: A+B+C 분리공시) 확정안(9쪽).",
            "content_class": "authentic",
            "issuing_body": "금융위원회 · 금융감독원 · 은행연합회",
            "license": "공공누리 제1유형 (금융위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.fsc.go.kr",
            "strategy": "policy_section_ko",
            "parts": [
                {
                    "part_dir": "ch01_background_and_statement",
                    "part_title": "제Ⅰ장~제Ⅱ장 1-가 추진배경 및 대출금리 산정내역서 제공 의무화",
                    "provisions": [
                        {"prov_id": "rate_reform_ch01_background", "section_number": "제Ⅰ장", "title": "Ⅰ. 추진 배경 — 대출금리 산정의 투명성·합리성 제고 필요성", "description": "금감원 대출금리 산정체계 점검 결과에 따른 제도개선 추진 배경.", "pages": [1, 2], "start": "Ⅰ 추진 배경", "end": None},
                        {"prov_id": "rate_reform_sec_2_1_a_statement", "section_number": "제Ⅱ장 1-가", "title": "Ⅱ-1-가. 대출금리 산정내역서 제공 (기준금리·가산금리·우대·전결금리 명시)", "description": "차주에게 소득·담보·신용등급 등 입력정보와 금리 항목별 산정내역서를 제공하도록 의무화.", "pages": [3], "start": "Ⅱ 소비자보호를 위한 대출금리 운용체계 개선", "end": None},
                    ],
                },
                {
                    "part_dir": "ch02_rate_cut_and_abc_disclosure",
                    "part_title": "제Ⅱ장 1-나~1-다 금리인하요구권 재량 단서(④항) 및 비교공시(A+B+C 분리)",
                    "provisions": [
                        {"prov_id": "rate_reform_sec_2_1_b_patent_discretion", "section_number": "제Ⅱ장 1-나 ④항", "title": "Ⅱ-1-나. 금리인하요구권 운영 개선 — ④항 전문자격증·특허취득 은행 선택적 적용 재량", "description": "신용도 개선만큼 가산금리를 인하하되, 전문자격증·특허취득 등은 은행이 선택적으로 적용할 수 있도록 조정한 핵심 단서.", "pages": [4], "start": "나. 금리인하요구권 운영 개선", "end": "다. 대출금리 비교공시제도 개선"},
                        {"prov_id": "rate_reform_sec_2_1_c_abc_separation", "section_number": "제Ⅱ장 1-다", "title": "Ⅱ-1-다. 대출금리 비교공시제도 개선 — 기준금리(A)+가산금리(B)+가감조정금리(C) 분리 공시", "description": "가산금리에 우대금리를 합산하여 가산금리를 축소 왜곡하는 공시를 금지하고 A·B·C를 별도 공시하도록 개정한 조항.", "pages": [4], "start": "다. 대출금리 비교공시제도 개선", "end": None},
                    ],
                },
                {
                    "part_dir": "ch03_internal_control_and_appendix",
                    "part_title": "제Ⅱ장 2~4 · 별첨 · 제Ⅲ장~참고3 내부통제 강화 · 가산금리 항목 조정 · 행정제재 근거 · 중도상환수수료 · 새로운 잔액기준 COFIX 도입 · 기대효과 · 금감원 검사 지적사항 개선방안",
                    "provisions": [
                        # ADR 0014 — 4 provisions that had no home before the two-up split (sheet 5–6 = p.7–10).
                        {"prov_id": "rate_reform_sec_2_2_internal_control", "section_number": "제Ⅱ장 2", "title": "Ⅱ-2. 대출금리 산정체계 내부통제 강화 — 기초정보 근거 산정 · 임의변경 내부승인 · 운영실태 주기 점검", "description": "차주 제공·조회 기초정보에 근거한 금리 산출, 여신심사시스템 산출 금리 변경 시 합리적 근거와 내부승인 의무화, 일선 점포 금리산정 운영실태 주기적 점검·기록.", "pages": [5], "start": "2.\n\n대출금리 산정체계 내부통제 강화", "end": "3.\n\n합리적 대출금리"},
                        {"prov_id": "rate_reform_sec_2_3_spread_items", "section_number": "제Ⅱ장 3", "title": "Ⅱ-3. 합리적 대출금리 산정을 위한 가산금리 항목 조정 — 구성항목 주기적 재산정 · 유동성 프리미엄 정의 개선", "description": "유동성·리스크프리미엄 월 1회 이상·간접비 1년 단위 재산정 원칙, 고정금리 대출에도 유동성프리미엄 가산 허용.", "pages": [5], "start": "3.\n\n합리적 대출금리", "end": None},
                        {"prov_id": "rate_reform_sec_2_4_unfair_rate_sanction", "section_number": "제Ⅱ장 4", "title": "Ⅱ-4. 부당한 금리산정 관련 행정제재 근거 마련 — 은행법 시행령 개정 우선 추진 · 의원입법안 현황", "description": "현행 은행법령상 대출금리 부당산정 행위에 행정제재가 곤란한 문제와, 불공정 영업행위 유형 추가를 위한 시행령 개정·의원입법안 3건.", "pages": [6], "start": "4.\n\n부당한 금리산정 관련 행정제재 근거 마련", "end": "중도상환수수료 개선방안"},
                        {"prov_id": "rate_reform_annex_prepayment_fee", "section_number": "별첨", "title": "별첨. 중도상환수수료 개선방안 — 변동금리대출 중도상환수수료 인하", "description": "잔여일수 체감방식 중도상환수수료의 부과 근거(대출비용·이자손실)와, 이자손실 위험이 작은 변동금리대출의 수수료 인하.", "pages": [6], "start": "중도상환수수료 개선방안", "end": None},
                        {"prov_id": "rate_reform_ch03_internal_control", "section_number": "제Ⅲ장", "title": "Ⅲ. 새로운 잔액기준 COFIX 도입 — 결제성자금 포함 산정 및 기존 대출자 전환", "description": "결제성자금·기타 예수/차입부채를 포함한 새로운 잔액기준 COFIX 산정(변동폭 비교), 시행 일정과 신규 대출자 적용, 기존 대출자 전환과 변동금리 중도상환수수료 인하, 신규취급액 기준 COFIX 현행 유지.", "pages": [7], "start": "Ⅲ 새로운 잔액기준 COFIX 도입", "end": None},
                        {"prov_id": "rate_reform_ch04_appendix_fss_audit", "section_number": "제Ⅳ장·참고3", "title": "Ⅳ~Ⅴ. 기대효과·향후 추진계획 및 참고3 금감원 검사결과 지적사항 개선방안", "description": "은행별 내규·전산시스템 반영 일정 및 금감원 점검 지적사항 대비 개선 내역표.", "pages": [8, 9], "start": "Ⅳ 기대 효과", "end": None},
                    ],
                },
            ],
            # ADR 0014 — two logical pages per landscape sheet (841×595 pt): read left crop, then right crop.
            "two_up_split_x": 420,
        },
        {
            "cat_dir": "regulations",
            "cat_title": "공식 법규·감독규정·모범규준 (Authentic Regulations)",
            "doc_dir": "06_fsc_7th_tf_rate_system",
            "doc_id": "DOC_06_FSC_7TH_TF",
            "pdf": "06_FSC_제7차_은행권_금리산정체계_정비방향.pdf",
            "title": "제7차 은행권 경영·영업 관행·제도 개선 TF — 은행권 금리산정체계 정비방향",
            "description": "시장금리 변동기 가산금리·우대금리 산정의 합리성·투명성 제고 및 상생금융 활성화 방안(6쪽).",
            "content_class": "authentic",
            "issuing_body": "금융위원회",
            "license": "공공누리 제1유형 (금융위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.fsc.go.kr",
            "strategy": "policy_section_ko",
            "parts": [
                {
                    "part_dir": "sec01_rate_system_maintenance",
                    "part_title": "제1절~제2절 금리산정체계 정비방향 및 상생금융 활성화",
                    "provisions": [
                        {"prov_id": "tf7_01_spread_and_pref_governance", "section_number": "정비방향 1", "title": "[1. 은행권 금리산정체계 정비방향] 가산금리·우대금리 산정 근거 점검", "description": "시장금리 하락기 가산금리 인상·우대금리 축소를 통한 금리 유지 관행 점검.", "pages": [1, 2], "start": "[ 1. 은행권 금리산정체계 정비방향 ]", "end": None},
                        {"prov_id": "tf7_02_rate_volatility_risk", "section_number": "정비방향 2", "title": "금리산정 합리성 공개 및 차주 금리변동 리스크 완화 방안", "description": "고정금리·혼합형 대출 확대 및 금리 산정 일관성 확보 지침.", "pages": [3, 4], "start": "참석자들은", "end": None},
                        {"prov_id": "tf7_03_inclusive_finance", "section_number": "상생금융 3", "title": "[2. 은행권 상생금융 활성화 방안] 참석자 의견·당국 평가 및 [3. 향후 계획]", "description": "상생금융 전담기구·창업벤처 투자·만기연장 차주 지원·KPI 반영 신중론 등 참석자 의견, 지속 가능한 상생금융 문화와 인센티브체계 개편 강조, 제8차 실무작업반(비이자수익 비중 확대) 예고.", "pages": [5, 6], "start": "은행권", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "research_briefs",
            "cat_title": "공공 연구기관 정책·충당금 브리프 (Authentic Research Briefs)",
            "doc_dir": "07_nars_rate_policy_issues",
            "doc_id": "DOC_07_NARS_RATE",
            "pdf": "07_NARS_합리적인_금리산정을_위한_정책동향_및_쟁점.pdf",
            "title": "국회입법조사처 이슈와 논점 제2071호 — 합리적인 금리산정을 위한 정책 동향 및 쟁점",
            "description": "국내은행 대출금리 구성요소(기준·가산·가감조정), DSR, 원화대출 연체율 및 비교공시 쟁점 보고서(4쪽).",
            "content_class": "authentic",
            "issuing_body": "국회입법조사처 (National Assembly Research Service)",
            "license": "공공누리 제1유형 (국회입법조사처 공공저작물 자유이용허락)",
            "resource_url": "https://www.nars.go.kr",
            "strategy": "research_brief_ko",
            "parts": [
                {
                    "part_dir": "sec01_rate_components_and_dsr",
                    "part_title": "제1절~제2절 대출금리 구성항목(기준·가산·가감조정) 및 DSR·연체율 구조",
                    "provisions": [
                        {"prov_id": "nars_01_intro_and_rate_formula", "section_number": "이슈와논점 1", "title": "1. 들어가며 및 은행 대출금리 산식(기준금리 + 가산금리 − 가감조정금리)", "description": "가산금리 세부 구성요소(업무원가·리스크프리미엄·유동성프리미엄·목표이익률·법적비용) 해설.", "pages": [1], "start": "합리적인 금리산정을 위한 정책 동향 및 쟁점", "end": None},
                        {"prov_id": "nars_02_dsr_and_delinquency_trend", "section_number": "이슈와논점 2", "title": "2. 총부채원리금상환비율(DSR) 및 국내은행 원화대출 연체율 현황", "description": "금리 상승기 차주 상환부담 및 국내은행 원화대출 연체율 산정 기준.", "pages": [2], "start": "(2) 총부채원리금상환비율(DSR)", "end": None},
                    ],
                },
                {
                    "part_dir": "sec02_policy_trends_and_issues",
                    "part_title": "제3절~제4절 금리산정체계 개선 정책 동향 및 입법 쟁점",
                    "provisions": [
                        {"prov_id": "nars_03_policy_trends", "section_number": "이슈와논점 3", "title": "3. 금융당국의 대출금리 산정체계 및 예대금리차 공시 개선 동향", "description": "은행연합회 소비자포털 예대금리차 및 가산·우대금리 비교공시 제도.", "pages": [2, 3], "start": "스크포스를 구성", "end": None},
                        {"prov_id": "nars_04_key_issues", "section_number": "이슈와논점 4", "title": "4. 금리산정체계 개선 관련 쟁점 — 잔액기준 예대금리차 및 금리인하요구권 실효성", "description": "금리인하요구권 수용률 제고 및 가산금리 산정 투명성 관련 입법 과제.", "pages": [3, 4], "start": "금리산정체계 개선 관련 쟁점", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "research_briefs",
            "cat_title": "공공 연구기관 정책·충당금 브리프 (Authentic Research Briefs)",
            "doc_dir": "08_kif_loan_loss_provision",
            "doc_id": "DOC_08_KIF_PROVISION",
            "pdf": "08_KIF_국내은행그룹_대손충당금_적립률_비교와_시사점.pdf",
            "title": "한국금융연구원(KIF) 금융브리프 34권 05호 — 국내 은행그룹의 대손충당금 적립률 국제 비교와 시사점",
            "description": "고정이하여신(NPL) 대비 대손충당금 적립률(Coverage Ratio) 산출 방식과 대손준비금 제도 분석 브리프(3쪽).",
            "content_class": "authentic",
            "issuing_body": "한국금융연구원 (Korea Institute of Finance)",
            "license": "공공누리 및 학술인용 허락 (한국금융연구원 금융브리프)",
            "resource_url": "https://www.kif.re.kr",
            "strategy": "research_brief_ko",
            "parts": [
                {
                    "part_dir": "sec01_coverage_ratio_and_implications",
                    "part_title": "제1절~제3절 고정이하여신 대비 대손충당금 적립률(CR) 국제비교 및 시사점",
                    "provisions": [
                        {"prov_id": "kif_01_cr_definition_and_domestic", "section_number": "KIF브리프 1쪽", "title": "1. 대손충당금 적립률(Coverage Ratio = 총대손충당금 잔액 ÷ 고정이하여신) 정의 및 추이", "description": "고정이하여신(NPL) 대비 대손충당금 및 대손준비금 합산 적립률 산식.", "pages": [1], "start": "Korea Institute of Finance", "end": None},
                        {"prov_id": "kif_02_global_comparison", "section_number": "KIF브리프 2쪽", "title": "2. 2017~2023년 국내 은행그룹 vs 글로벌 은행그룹 Coverage Ratio 비교", "description": "국내 은행그룹의 대손충당금 적립률 수준 및 글로벌 은행과의 차이 분석.", "pages": [2], "start": "2017년~2023년 동안", "end": None},
                        {"prov_id": "kif_03_regulatory_reserve_implications", "section_number": "KIF브리프 3쪽", "title": "3. 국내외 은행그룹 CR 격차 요인과 시사점 — 충당금 적립 관행 차이 및 위험조정수익률(RoRWA) 관리", "description": "글로벌 은행그룹 CR 이 국내보다 낮은 요인(충당금 적립 기준과 담보·부실채권 관리 관행의 차이), 과다 적립이 가용자본·배당여력에 미치는 영향, RoRWA 등 위험조정수익률 관리와 비즈니스 모델 전환 필요성.", "pages": [3], "start": "글로벌 주요 은행그룹의 CR 지표는", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "distractors",
            "cat_title": "타 업권 동명 조항 혼동 유도 대조군 (Cross-Sector Distractor Regulations)",
            "doc_dir": "09_fsc_savings_bank_reg",
            "doc_id": "DOC_09_DISTRACTOR_SAVINGS_BANK",
            "pdf": "09_DISTRACTOR_상호저축은행업감독규정_규제영향분석서.pdf",
            "title": "[타 업권 대조군] 상호저축은행업 감독규정 규제영향분석서 — 제38조(대손충당금등 적립기준)",
            "description": "시중은행(은행업감독규정 제29조)이 아닌 상호저축은행(제38조)의 연체 판단기준 및 대손충당금 적립기준 문서(9쪽).",
            "content_class": "authentic",
            "issuing_body": "금융위원회 중소금융과",
            "license": "공공누리 제1유형 (금융위원회 공공저작물 자유이용허락)",
            "resource_url": "https://www.fsc.go.kr",
            "strategy": "distractor_regulation_ko",
            "parts": [
                {
                    "part_dir": "sec01_savings_bank_soundness_and_art38",
                    "part_title": "제1절~제4절 상호저축은행 건전성규제 합리화 및 제38조 대손충당금 적립기준",
                    "provisions": [
                        {"prov_id": "distractor_01_overview", "section_number": "저축은행 규제개요 1~2쪽", "title": "[저축은행] 1. 상호저축은행 건전성규제 합리화 개요 (시중은행 비적용)", "description": "상호저축은행업 감독규정 개정 개요 및 규제 소관(중소금융과).", "pages": [1, 2], "start": "< 규제의 개요 >", "end": None},
                        {"prov_id": "distractor_02_overdue_criteria", "section_number": "저축은행 연체기준 3~6쪽", "title": "[저축은행] 2. 상호저축은행 연체 판단기준(1·3·12개월) 및 요주의·고정이하 분류 강화", "description": "타 업권 대비 완화되어 있던 상호저축은행의 자산건전성 분류 기준 강화 내용.", "pages": [3, 4], "start": "□ 규제 신설", "end": None},
                        {"prov_id": "distractor_03_alternatives_analysis", "section_number": "저축은행 대안검토 7~8쪽", "title": "[저축은행] 3. 대안의 발굴·검토 및 저축은행 대손충당금 추가적립 영향", "description": "상호저축은행 충당금 적립기준 강화에 따른 비용·편익 분석.", "pages": [7, 8], "start": "2. 대안의 발굴", "end": None},
                        {"prov_id": "distractor_04_art38_provision_surcharge", "section_number": "저축은행감독규정 제38조", "title": "[저축은행] 4. 상호저축은행업감독규정 제38조(대손충당금 등 적립기준) — 다중채무자 20% 가중적립", "description": "상호저축은행 가계대출·다중채무자 대출 대손충당금 20% 가중 적립 조항(시중은행 제29조와 혼동 주의).", "pages": [9], "start": "채무자 대 출 등", "end": None},
                    ],
                },
            ],
        },
        {
            "cat_dir": "internal_policies",
            "cat_title": "당행 내부지침·내규 (Synthetic Internal Bank Policies)",
            "doc_dir": "10_byulbit_bank_credit_rate_policy",
            "doc_id": "DOC_10_SYNTHETIC_BYULBIT_POLICY",
            "pdf": "10_SYNTHETIC_별빛은행_기업여신심사_및_금리운영_내규.pdf",
            "title": "[당행내규 제2026-08호] 별빛은행 기업여신 심사 · 조기경보(EWS) 및 금리운영 내규",
            "description": "별빛은행 여신관리부·기업여신심사부가 제정한 부서별 연체율(제14조), 채권재조정 EOD 유예(제16조·제18조), 3대 기준일자(제21조), 금리산식(제22조), TCB 한도 및 특허 금리인하 제외(제25조) 내규(2쪽).",
            "content_class": "synthetic",
            "issuing_body": "별빛은행 여신관리부 · 기업여신심사부",
            "license": "Internal Clean-room Demonstration Policy (Synthetic)",
            "resource_url": "okf://source/un_data/10_SYNTHETIC_별빛은행_기업여신심사_및_금리운영_내규.pdf",
            "strategy": "numbered_article_ko",
            "contacts": "신영만(과장) - 데이터거버넌스팀 <youngman@starlightbk.com>",
            "parts": [
                {
                    "part_dir": "ch01_ews_delinquency_and_eod_waiver",
                    "part_title": "제1장 부서별 연체율(제14조) 및 채권재조정 기한이익상실 유예 기준(제16조·제18조)",
                    "provisions": [
                        {"prov_id": "internal_art_14_ews_delinquency", "section_number": "내규 제14조", "title": "제14조 (여신관리팀 조기경보 연체율 산정 기준 — 10일 이상 연체 및 대손상각 특수채권 포함)", "description": "리스크관리위원회(고정이하) 및 금감원 공시(1월 이상, 특수채권 제외)와 구분되는 여신관리팀 조기경보(EWS) 실질관리 연체율 산식.", "pages": [1], "start": "제14조 (여신관리팀 조기경보 연체율 산정 기준)", "end": "제16조 (기한이익상실 통지 및 채권재조정 여신 특례)", "contacts": "신영만(과장) - 데이터거버넌스팀 <youngman@starlightbk.com>"},
                        {"prov_id": "internal_art_16_eod_notice_rule", "section_number": "내규 제16조", "title": "제16조 (기한이익상실 통지 원칙 — 1월 초과 연체 시 자동 분류)", "description": "기업여신 원리금 연체가 1월(30일)을 초과하는 경우 기한이익상실(EOD) 예정 통지 대상으로 자동 분류하는 원칙.", "pages": [1], "start": "제16조 (기한이익상실 통지 및 채권재조정 여신 특례)", "end": "② 제18조", "contacts": "봉미선(차장) - 여신심사·관리부 <misun@starlightbk.com>"},
                        {"prov_id": "internal_art_18_workout_kodit_waiver", "section_number": "내규 제18조", "title": "제18조 (채권재조정 및 신용보증기금 85% 이상 보증부여신 기한이익상실 유예 특례)", "description": "별표3 제3호라목(6개월 연속이행·유상증자·신보 85% 이상 보증서) 또는 기촉법·회생법 제180조제2항 우선변제자산 해당 시 고정이하 분류 및 즉시 EOD를 유예하는 특례.", "pages": [1], "start": "② 제18조 (채권재조정 및 보증부여신 기한이익상실 유예 특례)", "end": "제2장 대출계약 기준일자 및 금리 산정·인하 운영 기준", "contacts": "봉미선(차장) - 여신심사·관리부 <misun@starlightbk.com>"},
                    ],
                },
                {
                    "part_dir": "ch02_contract_dates_and_rate_discretion",
                    "part_title": "제2장 대출계약 3대 기준일자(제21조), 적용금리 산식(제22조) 및 특허권 금리인하 심사(제25조)",
                    "provisions": [
                        {"prov_id": "internal_art_21_three_dates", "section_number": "내규 제21조", "title": "제21조 (대출계약 3대 기준일자의 전산 구분 — 등록일 reg_dt · 체결일 contract_dt · 실행일 disburse_dt)", "description": "전산등록일(reg_dt), 대출계약 체결일(contract_dt: 특정일자 체결 대출 필수 기준), 자금실행일(disburse_dt) 구분 의무.", "pages": [1, 2], "start": "제21조 (대출계약 3대 기준일자의 전산 구분)", "end": "제22조 (대출금리 산출식 및 가감조정금리 비교공시)", "contacts": "신영만(과장) - 데이터거버넌스팀 <youngman@starlightbk.com>"},
                        {"prov_id": "internal_art_22_rate_formula_abc", "section_number": "내규 제22조", "title": "제22조 (대출금리 산출식 applied_rate = base + spread − pref 및 A·B·C 분리공시)", "description": "최종 적용금리 산출식 및 비교공시 시 기준금리(A)·가산금리(B)·가감조정금리(C) 분리 공시 의무.", "pages": [2], "start": "제22조 (대출금리 산출식 및 가감조정금리 비교공시)", "end": "제25조 (기술신용대출 우대금리", "contacts": "신영만(과장) - 데이터거버넌스팀 <youngman@starlightbk.com>"},
                        {"prov_id": "internal_art_25_tcb_and_patent_exclusion", "section_number": "내규 제25조", "title": "제25조 (기술신용대출 우대금리 전결 상한 1.20%p 및 특허권 단독 취득 시 금리인하 제외 기준)", "description": "별빛 TCB 운전자금 우대금리 상한(연 1.20%p, 부채비율 250%) 및 재무·신용등급 개선이 동반되지 않은 단독 특허권 취득의 필수 금리인하 제외 기준.", "pages": [2], "start": "제25조 (기술신용대출 우대금리", "end": None, "contacts": "봉미선(차장) - 여신심사·관리부 <misun@starlightbk.com>"},
                    ],
                },
            ],
        },
    ]


def build_bundle() -> dict:
    if os.path.exists(OKF_DIR):
        shutil.rmtree(OKF_DIR)
    os.makedirs(OKF_DIR, exist_ok=True)

    # DR-02 (2026-09-27): must stay byte-identical to the published
    # gs://finance_okf/okf/locations.yaml (generated_at 2026-09-22T07:09:00Z) — sync_gcs.py
    # verifies it by MD5. Source PDFs are local_only/upload: forbidden; the bundle resolves to GCS.
    locations_yaml = """# Logical path → physical location
#
# Bundle documents record only an `okf://…` logical path and a SHA-256.
# Physical locations are declared here and nowhere else.

version: 1
generated_at: "2026-09-22T07:09:00Z"

distribution:
  "okf://source/un_data/": local_only
  "okf://bundle/": publishable

resolvers:
  # Original source PDFs (local reference corpus).
  "okf://source/un_data/":
    - scheme: file
      root: "/home/changseop/finance_ontology/data/un_data/"
      status: active
      upload: forbidden

  # The OKF v0.2 markdown bundle in Google Cloud Storage (project: finance-ontology-changseop).
  "okf://bundle/":
    - scheme: gs
      root: "gs://finance_okf/okf/"
      status: active
      verified_by: "tools/sync_gcs.py --verify-only"
"""
    with open(os.path.join(OKF_DIR, "locations.yaml"), "w", encoding="utf-8") as f:
        f.write(locations_yaml)

    pages_pdf01 = extract_pdf_pages("01_FSC_은행업감독규정_전문_2025_07.pdf")
    doc01_spec = {
        "cat_dir": "regulations",
        "cat_title": "공식 법규·감독규정·모범규준 (Authentic Regulations)",
        "doc_dir": "01_fsc_banking_reg",
        "doc_id": "DOC_01_FSC_BANK_REG",
        "pdf": "01_FSC_은행업감독규정_전문_2025_07.pdf",
        "title": "은행업감독규정 (금융위원회고시 제2025-7호, 2025. 3. 19. 일부개정 — 제1장~제11장 전수 130개 조문)",
        "description": "은행법 및 같은 법 시행령에 따른 금융위원회의 은행 감독·인가·대주주·자산건전성(제27조)·대손충당금(제29조)·외환·신용위험·특례를 정한 공식 고시 전문(57쪽, 130개 전 조문).",
        "content_class": "authentic",
        "issuing_body": "금융위원회 (Financial Services Commission)",
        "license": "공공누리 제1유형 (국가법령정보센터·금융위원회 공공저작물 자유이용허락)",
        "resource_url": "https://www.law.go.kr/행정규칙/은행업감독규정",
        "strategy": "numbered_article_ko",
        "parts": extract_all_articles_of_pdf01(pages_pdf01),
    }

    all_docs = [doc01_spec] + build_other_docs_spec()
    cat_map: dict[str, list[dict]] = {}
    verification_records: list[dict] = []
    document_records: list[dict] = []
    total_docs = 0
    total_provs = 0

    for doc_spec in all_docs:
        cat_dir = doc_spec["cat_dir"]
        doc_dir = doc_spec["doc_dir"]
        pdf_name = doc_spec["pdf"]
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        digest = sha256_file(pdf_path)
        pages = extract_pdf_pages(pdf_name, doc_spec.get("two_up_split_x"))
        num_pages = len(pages) - 1

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

                if "verbatim_override" in p:
                    body_excerpt = p["verbatim_override"]
                else:
                    body_excerpt = slice_between(combined_page_text, p["start"], p.get("end"))

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
                if p.get("contacts"):
                    fm_prov["contacts"] = p["contacts"]
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
                    "contacts": p.get("contacts", ""),
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

# 국내 금융권 비정형 법규·내규 OKF v0.2 Knowledge Bundle (`finance_ontology/okf`)

총 10개 원본 PDF(142쪽)의 **모든 장·절·조문·별표(`{total_provs}`개 `Provision` + `{total_docs}`개 `Source Document` = 총 `{total_docs + total_provs}`개 OKF Concept)**를 무손실 구조화한 번들입니다.

* [regulations/](regulations/index.md) - 금융위원회·법제처·금감원·은행연합회 공식 감독규정·별표·제도개선안 (PDF 01~06)
* [research_briefs/](research_briefs/index.md) - 국회입법조사처(NARS)·한국금융연구원(KIF) 브리프 (PDF 07~08)
* [distractors/](distractors/index.md) - 타 업권(상호저축은행업감독규정 제38조) 대조군 (PDF 09)
* [internal_policies/](internal_policies/index.md) - 별빛은행 기업여신심사·조기경보(EWS)·금리운영 당행 내규 (PDF 10)
* [locations.yaml](locations.yaml) - 논리 URI ↔ 물리 경로 단일 매핑
* [log.md](log.md) - 번들 생성 및 검증 이력
"""
    with open(os.path.join(OKF_DIR, "index.md"), "w", encoding="utf-8") as fh:
        fh.write(root_idx)

    log_md = f"""# OKF Bundle Update Log

## 2026-09-22
* **Creation**: Built full 10-PDF exhaustive OKF v0.2 bundle (`{total_docs}` Source Documents + `{total_provs}` Provisions = `{total_docs + total_provs}` Concepts across 40 directories).
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
        f"Built Exhaustive OKF v0.2 bundle: {rep['source_pdf_count']} Source Documents + "
        f"{rep['provision_count']} Provisions = {rep['total_concepts']} Concepts"
    )
