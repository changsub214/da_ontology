#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K마켙(K-Market) 이커머스 정형 원장 생성기 (`ecommerce/data/generate_dummy_data.py` v1.0 — Zero Answer-Leakage)

기반 스키마: Google Cloud `bigquery-public-data.thelook_ecommerce` 호환 뼈대
            + K마켙 초개인화 추천·마진 가드레일·판촉정산·반품심사 온톨로지 브릿지 (총 8종 CSV)

핵심 설계 원칙:
1. 정형 데이터(`ecommerce/data/structured/*.csv`)에는 오직 커머스 계정계·물류·행태로그에 존재하는
   '기초 거래·재고·이벤트·승인 사실(Raw Operational Facts)'만 보관한다.
   - `max_coupon_pct`, `final_recommended_amt`, `legal_vendor_share_pct`, `refund_approved_yn` 등
     시나리오 정답 유출(Answer Leakage) 컬럼을 일절 두지 않는다.
2. 규범적 판단 기준(등급별 할인율 20%/15%/10%/5%, 최근 90일 반품률 30% 이상 시 5% 제한,
   기본 마진율 25% 미만 시 5% 제한 원칙 vs 입고 90일 초과 체화재고+특례승인 시 마진하한 10% 완화,
   대규모유통업법 제11조 판촉비 분담률 50% 상한 및 서면약정 필수, 전자상거래법 제17조 홀로그램 택 보존 시
   위생용품 청약철회 허용, 부서별 매출·반품률·가용재고 정의 차이)은 오직 비정형 PDF(`ecommerce/data/un_data/*.pdf`)와
   온톨로지(`ecommerce/ontology/l1.yaml`)에만 존재한다.
"""

from __future__ import annotations

import csv
import json
import os
import random

SEED = 20261003
random.seed(SEED)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "structured")
os.makedirs(OUT_DIR, exist_ok=True)


def write_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> str:
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_brand_vendor_contracts() -> list[dict]:
    """입점 브랜드 파트너 계약 마스터 (BigQuery `kmarket.brand_vendor_contracts`)."""
    return [
        {
            "brand_id": "BRD-01",
            "brand_name": "아틀리에누아르",
            "trade_type": "특약매입",
            "base_commission_pct": 28.0,
            "agreed_promo_share_pct": 60.0,  # 계약서상 60% 약정이나 대규모유통업법 제11조상 50% 상한 캡 작동 대상
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 24,
        },
        {
            "brand_id": "BRD-02",
            "brand_name": "어반트랙",
            "trade_type": "위수탁",
            "base_commission_pct": 25.0,
            "agreed_promo_share_pct": 40.0,  # 50% 이하 적법 약정
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 24,
        },
        {
            "brand_id": "BRD-03",
            "brand_name": "마린블루",
            "trade_type": "특약매입",
            "base_commission_pct": 30.0,
            "agreed_promo_share_pct": 50.0,
            "written_promo_agreement_yn": "N",  # 사전 서면약정 미비 -> K마켙 100% 부담 대상
            "sla_ship_hours": 48,
        },
        {
            "brand_id": "BRD-04",
            "brand_name": "메종드실크",
            "trade_type": "특약매입",
            "base_commission_pct": 32.0,
            "agreed_promo_share_pct": 50.0,
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 24,
        },
        {
            "brand_id": "BRD-05",
            "brand_name": "노르딕아웃도어",
            "trade_type": "직매입",
            "base_commission_pct": 0.0,
            "agreed_promo_share_pct": 70.0,  # 입점사 자발적 단독 프로모션 요청건(EXC-KM-2026-05)이 있을 때만 예외 허용
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 24,
        },
        {
            "brand_id": "BRD-06",
            "brand_name": "소울데님",
            "trade_type": "위수탁",
            "base_commission_pct": 24.0,
            "agreed_promo_share_pct": 45.0,
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 48,
        },
        {
            "brand_id": "BRD-07",
            "brand_name": "퓨어코튼랩",
            "trade_type": "위수탁",
            "base_commission_pct": 22.0,
            "agreed_promo_share_pct": 35.0,
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 24,
        },
        {
            "brand_id": "BRD-08",
            "brand_name": "케이마켙PB",
            "trade_type": "직매입",
            "base_commission_pct": 0.0,
            "agreed_promo_share_pct": 0.0,
            "written_promo_agreement_yn": "Y",
            "sla_ship_hours": 24,
        },
    ]


def build_products() -> list[dict]:
    """상품 및 코디·대체 관계 마스터 (BigQuery `kmarket.products`, 총 30개 SKU)."""
    core_products = [
        # 1. USR-1001(VIP)이 장바구니에 담은 메인 아우터 (정상 마진 40.0%)
        {
            "product_id": "PRD-3001", "sku": "KM-OUT-3001",
            "product_name": "아틀리에 캐시미어 발마칸 코트 블랙",
            "brand_id": "BRD-01", "brand_name": "아틀리에누아르",
            "department": "Women", "category": "Outerwear", "style_tag": "Minimal",
            "cost_krw": 240000, "retail_price_krw": 400000,  # 마진율 40.0% (>= 25%)
            "coord_product_id": "PRD-3002", "substitute_product_id": "PRD-3009",
            "return_policy_tag": "STANDARD", "distribution_center_id": "DC-ICN",
        },
        # 2. PRD-3001의 코디 호환 상품 — 저마진(22.0% < 25%)이지만 입고 125일 체화재고 + 클리어런스 특례승인(EXC-KM-2026-01, 마진하한 10.0%) 보유!
        #    -> 원칙상 저마진은 5% 할인 제한이지만, 체화재고 특례(마진하한 10%)로 22% - 10% = 12.0% 할인 가능!
        {
            "product_id": "PRD-3002", "sku": "KM-TOP-3002",
            "product_name": "아틀리에 메리노울 터틀넥 니트 아이보리",
            "brand_id": "BRD-01", "brand_name": "아틀리에누아르",
            "department": "Women", "category": "Tops & Tees", "style_tag": "Minimal",
            "cost_krw": 156000, "retail_price_krw": 200000,  # 마진율 22.0% (< 25% 저마진!)
            "coord_product_id": "PRD-3001", "substitute_product_id": "PRD-3010",
            "return_policy_tag": "STANDARD", "distribution_center_id": "DC-ICN",
        },
        # 3. USR-1002(VIP, 단 90일 반품률 50% >= 30% 과다반품자!)가 장바구니에 담은 데님 자켓
        {
            "product_id": "PRD-3003", "sku": "KM-JNS-3003",
            "product_name": "소울데님 셀비지 트러커 자켓 인디고",
            "brand_id": "BRD-06", "brand_name": "소울데님",
            "department": "Men", "category": "Jeans", "style_tag": "Street",
            "cost_krw": 120000, "retail_price_krw": 200000,  # 마진율 40.0%
            "coord_product_id": "PRD-3004", "substitute_product_id": "PRD-3011",
            "return_policy_tag": "STANDARD", "distribution_center_id": "DC-YIN",
        },
        # 4. PRD-3003의 코디 호환 상품 — 정상 마진(35.0%)
        {
            "product_id": "PRD-3004", "sku": "KM-TOP-3004",
            "product_name": "어반트랙 헤비웨이트 스웻 후디 그레이",
            "brand_id": "BRD-02", "brand_name": "어반트랙",
            "department": "Men", "category": "Tops & Tees", "style_tag": "Street",
            "cost_krw": 65000, "retail_price_krw": 100000,  # 마진율 35.0%
            "coord_product_id": "PRD-3003", "substitute_product_id": "PRD-3012",
            "return_policy_tag": "STANDARD", "distribution_center_id": "DC-YIN",
        },
        # 5. 저마진(20.0% < 25%) + 입고 40일(비체화) + 특례승인 없음 -> 5% 할인 상한 엄격 적용 대상
        {
            "product_id": "PRD-3005", "sku": "KM-ACC-3005",
            "product_name": "메종드실크 시그니처 실크 스카프",
            "brand_id": "BRD-04", "brand_name": "메종드실크",
            "department": "Women", "category": "Accessories", "style_tag": "Classic",
            "cost_krw": 120000, "retail_price_krw": 150000,  # 마진율 20.0% (< 25%)
            "coord_product_id": "PRD-3001", "substitute_product_id": "PRD-3013",
            "return_policy_tag": "STANDARD", "distribution_center_id": "DC-ICN",
        },
        # 6. 위생제한 태그(HYGIENE_RESTRICTED) 부여된 수영복 — 홀로그램 택 보존 시 전자상거래법 제17조로 반품 허용 대상
        {
            "product_id": "PRD-3006", "sku": "KM-SWM-3006",
            "product_name": "마린블루 프로페셔널 인도어 스윔수트 네이비",
            "brand_id": "BRD-03", "brand_name": "마린블루",
            "department": "Women", "category": "Swim", "style_tag": "Resort",
            "cost_krw": 72000, "retail_price_krw": 120000,  # 마진율 40.0%
            "coord_product_id": "PRD-3014", "substitute_product_id": "PRD-3015",
            "return_policy_tag": "HYGIENE_RESTRICTED", "distribution_center_id": "DC-BUS",
        },
        # 7. 위생제한 태그(HYGIENE_RESTRICTED) 부여된 이너웨어 — 홀로그램 택 훼손(N)으로 반품 거절 대상
        {
            "product_id": "PRD-3007", "sku": "KM-INT-3007",
            "product_name": "메종드실크 심리스 실크 브라렛 세트",
            "brand_id": "BRD-04", "brand_name": "메종드실크",
            "department": "Women", "category": "Intimates", "style_tag": "Minimal",
            "cost_krw": 54000, "retail_price_krw": 90000,  # 마진율 40.0%
            "coord_product_id": "PRD-3002", "substitute_product_id": "PRD-3016",
            "return_policy_tag": "HYGIENE_RESTRICTED", "distribution_center_id": "DC-ICN",
        },
        # 8. 아웃도어 고어텍스 자켓 — 입점사 자발적 단독 판촉행사(EXC-KM-2026-03) 대상
        {
            "product_id": "PRD-3008", "sku": "KM-ACT-3008",
            "product_name": "노르딕 3L 프로쉘 알파인 자켓",
            "brand_id": "BRD-05", "brand_name": "노르딕아웃도어",
            "department": "Unisex", "category": "Active", "style_tag": "Athleisure",
            "cost_krw": 180000, "retail_price_krw": 300000,  # 마진율 40.0%
            "coord_product_id": "PRD-3017", "substitute_product_id": "PRD-3018",
            "return_policy_tag": "STANDARD", "distribution_center_id": "DC-YIN",
        },
    ]

    # 배경 상품 PRD-3009 ~ PRD-3030 (22개 추가하여 총 30개 SKU)
    categories = [
        ("Outerwear", "Minimal", "BRD-01", "아틀리에누아르", "DC-ICN"),
        ("Tops & Tees", "Street", "BRD-02", "어반트랙", "DC-YIN"),
        ("Jeans", "Street", "BRD-06", "소울데님", "DC-YIN"),
        ("Accessories", "Classic", "BRD-04", "메종드실크", "DC-ICN"),
        ("Active", "Athleisure", "BRD-05", "노르딕아웃도어", "DC-YIN"),
        ("Tops & Tees", "Minimal", "BRD-07", "퓨어코튼랩", "DC-ICN"),
    ]
    for i in range(9, 31):
        cat, sty, bid, bname, dc = categories[(i - 9) % len(categories)]
        retail = (6 + (i % 10)) * 10000
        cost = int(retail * 0.60)  # 기본 40% 마진
        coord_id = f"PRD-{3001 + (i % 8)}"
        sub_id = f"PRD-{3001 + ((i + 1) % 8)}"
        if i == 9:
            # PRD-3009: 품절(avail_qty=0) 상태이며 대체 상품이 PRD-3002(체화재고 125일 + 특례 EXC-KM-2026-01)
            sub_id = "PRD-3002"
        elif i == 10:
            # PRD-3010: 품절(avail_qty=0) 상태이며 대체 상품이 PRD-3011(체화재고 105일, 특례 미승인)
            sub_id = "PRD-3011"
        elif i == 12:
            # PRD-3012: 저마진(22.0% < 25%) + 비체화(35일)이나 VIP_RETENTION 특례(EXC-KM-2026-07, 하한 12%) 보유
            retail = 150000
            cost = 117000
        core_products.append({
            "product_id": f"PRD-{3000 + i}",
            "sku": f"KM-GEN-{3000 + i}",
            "product_name": f"{bname} 에센셜 {cat.split()[0]} 아이템 {i}호",
            "brand_id": bid,
            "brand_name": bname,
            "department": "Women" if i % 2 == 0 else "Men",
            "category": cat,
            "style_tag": sty,
            "cost_krw": cost,
            "retail_price_krw": retail,
            "coord_product_id": coord_id,
            "substitute_product_id": sub_id,
            "return_policy_tag": "STANDARD",
            "distribution_center_id": dc,
        })
    return core_products


def build_users() -> list[dict]:
    """고객 마스터 (BigQuery `kmarket.users`, 총 60명)."""
    featured_users = [
        # USR-1001: VIP 고객, 마케팅 동의 Y, 최근 90일 반품률 0% (정상 우량 VIP)
        {
            "user_id": "USR-1001", "user_name": "김서연", "age": 32, "gender": "F",
            "membership_tier": "VIP", "city": "서울 강남구", "traffic_source": "Instagram",
            "marketing_opt_in_yn": "Y", "preferred_style": "Minimal", "created_at": "2024-03-15",
        },
        # USR-1002: VIP 고객, 마케팅 동의 Y, 최근 90일 단순변심 반품률 50.0% (>= 30% 과다반품 주의고객 -> 쿠폰 5% 제한 단서 작동!)
        {
            "user_id": "USR-1002", "user_name": "박준혁", "age": 29, "gender": "M",
            "membership_tier": "VIP", "city": "서울 성동구", "traffic_source": "YouTube",
            "marketing_opt_in_yn": "Y", "preferred_style": "Street", "created_at": "2024-05-20",
        },
        # USR-1003: GOLD 고객, 마케팅 동의 Y, 반품 건이 있으나 전부 '상품불량(DEFECTIVE)' 귀책이라 반품률 모수에서 제외되어 정상 GOLD(15%) 유지!
        {
            "user_id": "USR-1003", "user_name": "이수빈", "age": 35, "gender": "F",
            "membership_tier": "GOLD", "city": "경기 분당구", "traffic_source": "Organic",
            "marketing_opt_in_yn": "Y", "preferred_style": "Classic", "created_at": "2024-08-10",
        },
        # USR-1004: VIP 고객이나 마케팅 수신동의 거부(marketing_opt_in_yn = N) -> 개인정보보호법 지침상 외부 알림톡 시크릿 쿠폰 발송 차단 대상!
        {
            "user_id": "USR-1004", "user_name": "최현우", "age": 41, "gender": "M",
            "membership_tier": "VIP", "city": "서울 서초구", "traffic_source": "Email",
            "marketing_opt_in_yn": "N", "preferred_style": "Athleisure", "created_at": "2023-11-02",
        },
        # USR-1005: SILVER 고객, 수영복(PRD-3006) 반품 신청자 (홀로그램 택 보존 Y -> 전자상거래법 제17조 환불 승인)
        {
            "user_id": "USR-1005", "user_name": "정하윤", "age": 27, "gender": "F",
            "membership_tier": "SILVER", "city": "부산 해운대구", "traffic_source": "Instagram",
            "marketing_opt_in_yn": "Y", "preferred_style": "Resort", "created_at": "2025-01-12",
        },
        # USR-1006: GOLD 고객, 이너웨어(PRD-3007) 반품 신청자 (홀로그램 택 제거 N -> 반품 거절)
        {
            "user_id": "USR-1006", "user_name": "한지민", "age": 31, "gender": "F",
            "membership_tier": "GOLD", "city": "서울 마포구", "traffic_source": "Kakao",
            "marketing_opt_in_yn": "Y", "preferred_style": "Minimal", "created_at": "2025-02-18",
        },
    ]

    last_names = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
    first_names = ["민준", "서준", "도윤", "예준", "시우", "서연", "서윤", "지우", "하은", "민서"]
    cities = ["서울 강남구", "서울 송파구", "서울 마포구", "경기 성남시", "경기 수원시", "인천 연수구", "부산 해운대구", "대구 수성구"]
    sources = ["Organic", "Instagram", "YouTube", "Kakao", "Email"]
    styles = ["Minimal", "Street", "Athleisure", "Classic", "Resort"]
    tiers = ["VIP", "GOLD", "SILVER", "WELCOME"]

    for i in range(7, 61):
        uid = f"USR-{1000 + i}"
        name = last_names[i % len(last_names)] + first_names[(i * 3) % len(first_names)]
        featured_users.append({
            "user_id": uid,
            "user_name": name,
            "age": 22 + (i % 30),
            "gender": "F" if i % 2 == 0 else "M",
            "membership_tier": tiers[i % len(tiers)],
            "city": cities[i % len(cities)],
            "traffic_source": sources[i % len(sources)],
            "marketing_opt_in_yn": "Y" if i % 5 != 0 else "N",
            "preferred_style": styles[i % len(styles)],
            "created_at": f"2025-{(i % 9) + 1:02d}-{(i % 27) + 1:02d}",
        })
    return featured_users


def build_inventory_items(products: list[dict]) -> list[dict]:
    """물류센터 배치별 재고 원장 (Spanner `kmarket.inventory_items`)."""
    rows = [
        # PRD-3001 (발마칸 코트): 정상 가용재고 (입고 30일)
        {
            "inventory_item_id": "INV-1001", "product_id": "PRD-3001",
            "distribution_center_id": "DC-ICN", "inbound_date": "2026-08-30",
            "age_days": 30, "avail_qty": 40, "stock_status": "AVAILABLE",
        },
        # PRD-3002 (터틀넥 니트): 입고 125일 경과 체화재고 (> 90일, <= 180일) -> 클리어런스 특례 대상이면서 당일출고 가능!
        {
            "inventory_item_id": "INV-1002", "product_id": "PRD-3002",
            "distribution_center_id": "DC-ICN", "inbound_date": "2026-05-27",
            "age_days": 125, "avail_qty": 50, "stock_status": "AVAILABLE",
        },
        # PRD-3003 (데님 자켓): 정상 가용재고 (입고 45일)
        {
            "inventory_item_id": "INV-1003", "product_id": "PRD-3003",
            "distribution_center_id": "DC-YIN", "inbound_date": "2026-08-15",
            "age_days": 45, "avail_qty": 30, "stock_status": "AVAILABLE",
        },
        # PRD-3004 (스웻 후디): 정상 가용재고 (입고 25일)
        {
            "inventory_item_id": "INV-1004", "product_id": "PRD-3004",
            "distribution_center_id": "DC-YIN", "inbound_date": "2026-09-04",
            "age_days": 25, "avail_qty": 60, "stock_status": "AVAILABLE",
        },
        # PRD-3005 (실크 스카프): 저마진(20%)이나 입고 40일(비체화) -> 체화재고 요건(90일 초과) 미충족!
        {
            "inventory_item_id": "INV-1005", "product_id": "PRD-3005",
            "distribution_center_id": "DC-ICN", "inbound_date": "2026-08-20",
            "age_days": 40, "avail_qty": 20, "stock_status": "AVAILABLE",
        },
        # PRD-3006 (스윔수트): 가용재고 + 반품검수대기(RETURN_INSPECTION) 배치 분리 (부서별 재고 정의 차이 검증용)
        {
            "inventory_item_id": "INV-1006", "product_id": "PRD-3006",
            "distribution_center_id": "DC-BUS", "inbound_date": "2026-07-20",
            "age_days": 71, "avail_qty": 25, "stock_status": "AVAILABLE",
        },
        {
            "inventory_item_id": "INV-1007", "product_id": "PRD-3006",
            "distribution_center_id": "DC-BUS", "inbound_date": "2026-09-20",
            "age_days": 9, "avail_qty": 15, "stock_status": "RETURN_INSPECTION",
        },
        # PRD-3007 (실크 브라렛): 입고 210일 초과 장기 체화재고 (> 180일 -> 물류팀 당일출고 가용재고에서 제외, 재무팀 재고자산에는 포함!)
        {
            "inventory_item_id": "INV-1008", "product_id": "PRD-3007",
            "distribution_center_id": "DC-ICN", "inbound_date": "2026-03-01",
            "age_days": 212, "avail_qty": 35, "stock_status": "AVAILABLE",
        },
        # PRD-3008 (알파인 자켓): 결제예약(RESERVED) 배치 vs 가용(AVAILABLE) 배치
        {
            "inventory_item_id": "INV-1009", "product_id": "PRD-3008",
            "distribution_center_id": "DC-YIN", "inbound_date": "2026-08-01",
            "age_days": 59, "avail_qty": 20, "stock_status": "AVAILABLE",
        },
        {
            "inventory_item_id": "INV-1010", "product_id": "PRD-3008",
            "distribution_center_id": "DC-YIN", "inbound_date": "2026-08-01",
            "age_days": 59, "avail_qty": 10, "stock_status": "RESERVED",
        },
    ]

    for idx, p in enumerate(products[8:], start=11):
        pid = p["product_id"]
        if pid == "PRD-3009":
            # 일시품절(OUT_OF_STOCK, avail_qty=0) -> 대체 상품 PRD-3002(체화재고 125일, 50개) 유도
            rows.append({
                "inventory_item_id": f"INV-{1000 + idx}",
                "product_id": pid,
                "distribution_center_id": p["distribution_center_id"],
                "inbound_date": "2026-08-10",
                "age_days": 50,
                "avail_qty": 0,
                "stock_status": "OUT_OF_STOCK",
            })
        elif pid == "PRD-3010":
            # 일시품절(OUT_OF_STOCK, avail_qty=0) -> 대체 상품 PRD-3011(체화재고 105일, 45개) 유도
            rows.append({
                "inventory_item_id": f"INV-{1000 + idx}",
                "product_id": pid,
                "distribution_center_id": p["distribution_center_id"],
                "inbound_date": "2026-08-10",
                "age_days": 50,
                "avail_qty": 0,
                "stock_status": "OUT_OF_STOCK",
            })
        elif pid == "PRD-3011":
            # 입고 105일 경과 체화재고(age_days >= 90, avail_qty=45 >= 30, 특례 미승인 상태)
            rows.append({
                "inventory_item_id": f"INV-{1000 + idx}",
                "product_id": pid,
                "distribution_center_id": p["distribution_center_id"],
                "inbound_date": "2026-06-16",
                "age_days": 105,
                "avail_qty": 45,
                "stock_status": "AVAILABLE",
            })
        elif pid == "PRD-3012":
            # 저마진(22%) + 입고 35일(비체화) 배치 (VIP_RETENTION 특례 EXC-KM-2026-07 대상)
            rows.append({
                "inventory_item_id": f"INV-{1000 + idx}",
                "product_id": pid,
                "distribution_center_id": p["distribution_center_id"],
                "inbound_date": "2026-08-25",
                "age_days": 35,
                "avail_qty": 30,
                "stock_status": "AVAILABLE",
            })
        else:
            rows.append({
                "inventory_item_id": f"INV-{1000 + idx}",
                "product_id": pid,
                "distribution_center_id": p["distribution_center_id"],
                "inbound_date": "2026-08-10",
                "age_days": 50,
                "avail_qty": 20,
                "stock_status": "AVAILABLE",
            })
    return rows


def build_orders_and_items() -> tuple[list[dict], list[dict]]:
    """주문 헤더(`orders.csv`) 및 주문상품 상세(`order_items.csv`) 원장 (Spanner OLTP).

    기준일(2026-09-29) 기준으로 부서별 매출·반품률·판촉비 분담·SLA 지연 보상 수치가 정확히 떨어지도록 설계:
      - USR-1001: 최근 90일 주문 4건 모두 Complete (반품률 0.0%)
      - USR-1002: 최근 90일 주문 4건 중 2건이 단순변심(CHANGE_OF_MIND) Returned (반품률 50.0% >= 30.0%)
      - USR-1003: 최근 90일 주문 4건 중 2건이 상품불량(DEFECTIVE) Returned (CRM 내규 제9조 단서상 불량 반품은 모수 제외 -> 단순변심 반품률 0.0%!)
      - BRD-01 공동판촉(JOINT_PROMO) 할인 합계: 정가 합계 2,000,000원, 쿠폰할인 합계 300,000원
        (계약서상 분담률 60% = 180,000원이나, 대규모유통업법 제11조 50% 상한 적용 시 150,000원, 과다청구 위험액 30,000원!)
      - BRD-03 공동판촉(JOINT_PROMO) 할인 합계: 쿠폰할인 20,000원 (서면약정 N -> 브랜드 부담 0원, K마켙 100% 부담!)
      - BRD-05 자발적 단독판촉(JOINT_PROMO + EXC-KM-2026-03) 할인 합계: 쿠폰할인 60,000원 (대규모유통업법 제11조제5항 단서 충족 -> 70% = 42,000원 적법 분담!)
    """
    orders: list[dict] = []
    items: list[dict] = []

    def add_order(
        oid: str, uid: str, status: str, created_at: str, shipped_at: str, delivered_at: str, returned_at: str,
        item_specs: list[dict]
    ) -> None:
        orders.append({
            "order_id": oid,
            "user_id": uid,
            "status": status,
            "num_of_item": len(item_specs),
            "created_at": created_at,
            "shipped_at": shipped_at,
            "delivered_at": delivered_at,
            "returned_at": returned_at,
        })
        for sp in item_specs:
            items.append({
                "item_id": sp["item_id"],
                "order_id": oid,
                "user_id": uid,
                "product_id": sp["product_id"],
                "inventory_item_id": sp["inventory_item_id"],
                "status": sp.get("status", status),
                "retail_price_krw": sp["retail_price_krw"],
                "sale_price_krw": sp["retail_price_krw"] - sp["coupon_discount_krw"],
                "coupon_discount_krw": sp["coupon_discount_krw"],
                "coupon_type": sp["coupon_type"],
                "return_reason_cd": sp.get("return_reason_cd", "NONE"),
                "created_at": created_at,
                "shipped_at": shipped_at,
                "delivered_at": delivered_at,
                "returned_at": sp.get("returned_at", returned_at),
            })

    # 1) USR-1001 (김서연, VIP): 4건 모두 Complete, 배송완료 후 7일 이상 경과 (확정매출)
    #    BRD-01 JOINT_PROMO 쿠폰 할인액 총 300,000원 발생
    add_order(
        "ORD-2026-0001", "USR-1001", "Complete",
        "2026-08-05T10:00:00Z", "2026-08-05T18:00:00Z", "2026-08-07T14:00:00Z", "",
        [
            {"item_id": "OIT-2026-0001", "product_id": "PRD-3001", "inventory_item_id": "INV-1001", "retail_price_krw": 400000, "coupon_discount_krw": 60000, "coupon_type": "JOINT_PROMO"},
            {"item_id": "OIT-2026-0002", "product_id": "PRD-3002", "inventory_item_id": "INV-1002", "retail_price_krw": 200000, "coupon_discount_krw": 30000, "coupon_type": "JOINT_PROMO"},
        ],
    )
    add_order(
        "ORD-2026-0002", "USR-1001", "Complete",
        "2026-08-18T11:00:00Z", "2026-08-18T19:00:00Z", "2026-08-20T15:00:00Z", "",
        [
            {"item_id": "OIT-2026-0003", "product_id": "PRD-3001", "inventory_item_id": "INV-1001", "retail_price_krw": 400000, "coupon_discount_krw": 60000, "coupon_type": "JOINT_PROMO"},
            {"item_id": "OIT-2026-0004", "product_id": "PRD-3001", "inventory_item_id": "INV-1001", "retail_price_krw": 1000000, "coupon_discount_krw": 150000, "coupon_type": "JOINT_PROMO"},
        ],
    )

    # 2) USR-1002 (박준혁, VIP): 최근 90일 품목 4건 중 2건 단순변심(CHANGE_OF_MIND) 반품 -> 반품률 50.0% (>= 30%)
    add_order(
        "ORD-2026-0003", "USR-1002", "Complete",
        "2026-08-10T09:00:00Z", "2026-08-10T17:00:00Z", "2026-08-12T12:00:00Z", "",
        [
            {"item_id": "OIT-2026-0005", "product_id": "PRD-3003", "inventory_item_id": "INV-1003", "retail_price_krw": 200000, "coupon_discount_krw": 20000, "coupon_type": "PLATFORM_TIER"},
            {"item_id": "OIT-2026-0006", "product_id": "PRD-3004", "inventory_item_id": "INV-1004", "retail_price_krw": 100000, "coupon_discount_krw": 10000, "coupon_type": "PLATFORM_TIER"},
        ],
    )
    add_order(
        "ORD-2026-0004", "USR-1002", "Returned",
        "2026-08-25T10:00:00Z", "2026-08-25T18:00:00Z", "2026-08-27T14:00:00Z", "2026-08-30T11:00:00Z",
        [
            {"item_id": "OIT-2026-0007", "product_id": "PRD-3003", "inventory_item_id": "INV-1003", "retail_price_krw": 200000, "coupon_discount_krw": 0, "coupon_type": "NONE", "return_reason_cd": "CHANGE_OF_MIND"},
            {"item_id": "OIT-2026-0008", "product_id": "PRD-3004", "inventory_item_id": "INV-1004", "retail_price_krw": 100000, "coupon_discount_krw": 0, "coupon_type": "NONE", "return_reason_cd": "CHANGE_OF_MIND"},
        ],
    )

    # 3) USR-1003 (이수빈, GOLD): 품목 4건 중 2건 반품이나 사유가 'DEFECTIVE'(상품불량) -> CRM 반품률 모수 제외 대상 (단순변심 반품률 0.0%!)
    add_order(
        "ORD-2026-0005", "USR-1003", "Complete",
        "2026-08-12T10:00:00Z", "2026-08-12T16:00:00Z", "2026-08-14T13:00:00Z", "",
        [
            {"item_id": "OIT-2026-0009", "product_id": "PRD-3005", "inventory_item_id": "INV-1005", "retail_price_krw": 150000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
            {"item_id": "OIT-2026-0010", "product_id": "PRD-3004", "inventory_item_id": "INV-1004", "retail_price_krw": 100000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
        ],
    )
    add_order(
        "ORD-2026-0006", "USR-1003", "Returned",
        "2026-08-28T10:00:00Z", "2026-08-28T18:00:00Z", "2026-08-30T14:00:00Z", "2026-09-02T15:00:00Z",
        [
            {"item_id": "OIT-2026-0011", "product_id": "PRD-3005", "inventory_item_id": "INV-1005", "retail_price_krw": 150000, "coupon_discount_krw": 0, "coupon_type": "NONE", "return_reason_cd": "DEFECTIVE"},
            {"item_id": "OIT-2026-0012", "product_id": "PRD-3004", "inventory_item_id": "INV-1004", "retail_price_krw": 100000, "coupon_discount_krw": 0, "coupon_type": "NONE", "return_reason_cd": "DEFECTIVE"},
        ],
    )

    # 4) USR-1005 (정하윤, SILVER): 수영복(PRD-3006) 배송완료 후 3일 만에 반품 신청 (홀로그램 택 보존 Y -> EXC-KM-2026-04)
    #    + BRD-03 서면약정 미비(N) 상태에서 발행된 JOINT_PROMO 쿠폰 20,000원
    add_order(
        "ORD-2026-0007", "USR-1005", "Complete",
        "2026-09-24T10:00:00Z", "2026-09-24T18:00:00Z", "2026-09-26T14:00:00Z", "",
        [
            {"item_id": "OIT-2026-0013", "product_id": "PRD-3006", "inventory_item_id": "INV-1006", "retail_price_krw": 120000, "coupon_discount_krw": 20000, "coupon_type": "JOINT_PROMO"},
        ],
    )

    # 5) USR-1006 (한지민, GOLD): 이너웨어(PRD-3007) 배송완료 후 4일 만에 반품 신청 (홀로그램 택 제거 N -> EXC-KM-2026-05 반품 거절)
    add_order(
        "ORD-2026-0008", "USR-1006", "Complete",
        "2026-09-23T10:00:00Z", "2026-09-23T17:00:00Z", "2026-09-25T15:00:00Z", "",
        [
            {"item_id": "OIT-2026-0014", "product_id": "PRD-3007", "inventory_item_id": "INV-1008", "retail_price_krw": 90000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
        ],
    )

    # 6) ORD-2026-0009 (USR-1004): 출고 SLA(24h) 대비 60시간 만에 출고된 지연 주문 (+36h 초과 >= 24h) -> 결제액 300,000원의 5% = 15,000원이나 상한 10,000원 보상 대상!
    add_order(
        "ORD-2026-0009", "USR-1004", "Shipped",
        "2026-09-25T09:00:00Z", "2026-09-27T21:00:00Z", "", "",
        [
            {"item_id": "OIT-2026-0015", "product_id": "PRD-3008", "inventory_item_id": "INV-1009", "retail_price_krw": 300000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
        ],
    )

    # 7) ORD-2026-0010 (USR-1001): 배송완료 후 아직 3일밖에 안 지난 주문 (CRM 구매액에는 포함되나, 재무정산팀 '배송완료 7일 경과 확정매출'에서는 제외!)
    add_order(
        "ORD-2026-0010", "USR-1001", "Complete",
        "2026-09-24T12:00:00Z", "2026-09-25T09:00:00Z", "2026-09-26T16:00:00Z", "",
        [
            {"item_id": "OIT-2026-0016", "product_id": "PRD-3004", "inventory_item_id": "INV-1004", "retail_price_krw": 100000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
        ],
    )

    # 8) ORD-2026-0011 (USR-1007): BRD-05(노르딕아웃도어, 약정 분담률 70%)의 PRD-3008 주문 — 입점사 자발적 단독 프로모션 승인(EXC-KM-2026-03)으로 70% 분담(42,000원) 적법 인정!
    add_order(
        "ORD-2026-0011", "USR-1007", "Complete",
        "2026-09-12T10:00:00Z", "2026-09-12T18:00:00Z", "2026-09-14T14:00:00Z", "",
        [
            {"item_id": "OIT-2026-0017", "product_id": "PRD-3008", "inventory_item_id": "INV-1009", "retail_price_krw": 300000, "coupon_discount_krw": 60000, "coupon_type": "JOINT_PROMO"},
        ],
    )

    # 9) ORD-2026-0012 (USR-1008): 배송완료 후 20일 경과 시점에 신청된 표시·광고 상이/사이즈 오배송(SIZE_MISMATCH_SPEC_DIFF) 반품 — 단순변심 7일 도과이나 전자상거래법 제17조제3항(3개월/90일 이내)으로 무료반품 승인!
    add_order(
        "ORD-2026-0012", "USR-1008", "Returned",
        "2026-08-20T10:00:00Z", "2026-08-20T18:00:00Z", "2026-08-22T14:00:00Z", "2026-09-11T15:00:00Z",
        [
            {"item_id": "OIT-2026-0018", "product_id": "PRD-3004", "inventory_item_id": "INV-1004", "retail_price_krw": 100000, "coupon_discount_krw": 0, "coupon_type": "NONE", "return_reason_cd": "SIZE_MISMATCH_SPEC_DIFF"},
        ],
    )

    # 10) ORD-2026-0013 (USR-1009): 배송완료 후 4일 이내이나 고객 착용·세탁 훼손(WEAR_AND_WASH_DAMAGE) 사유로 청약철회 거절(Complete 유지)된 건
    add_order(
        "ORD-2026-0013", "USR-1009", "Complete",
        "2026-09-18T10:00:00Z", "2026-09-18T18:00:00Z", "2026-09-20T14:00:00Z", "",
        [
            {"item_id": "OIT-2026-0019", "product_id": "PRD-3003", "inventory_item_id": "INV-1003", "retail_price_krw": 200000, "coupon_discount_krw": 0, "coupon_type": "NONE", "return_reason_cd": "WEAR_AND_WASH_DAMAGE"},
        ],
    )

    # 11) ORD-2026-0014 (USR-1010): 용인 물류센터(DC-YIN, 센터 SLA 36h / 브랜드 BRD-06 계약 SLA 48h)에서 42시간 만에 출고된 주문 -> 센터 SLA(36h) 초과로 CS 3,000P 보상 대상이나 파트너 페널티(48h)는 면제!
    add_order(
        "ORD-2026-0014", "USR-1010", "Shipped",
        "2026-09-25T10:00:00Z", "2026-09-27T04:00:00Z", "", "",
        [
            {"item_id": "OIT-2026-0020", "product_id": "PRD-3003", "inventory_item_id": "INV-1003", "retail_price_krw": 200000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
        ],
    )

    # 12) ORD-2026-0015 (USR-1011): 부산/양산 물류센터(DC-BUS, 센터 SLA 48h / 브랜드 BRD-03 계약 SLA 48h)에서 60시간 만에 출고된 주문 -> 센터 SLA(48h) 및 계약 SLA(48h) 모두 초과!
    add_order(
        "ORD-2026-0015", "USR-1011", "Shipped",
        "2026-09-24T08:00:00Z", "2026-09-26T20:00:00Z", "", "",
        [
            {"item_id": "OIT-2026-0021", "product_id": "PRD-3006", "inventory_item_id": "INV-1006", "retail_price_krw": 120000, "coupon_discount_krw": 0, "coupon_type": "NONE"},
        ],
    )

    return orders, items


def build_events() -> list[dict]:
    """고객 행동·장바구니 세션 로그 (Spanner `kmarket.events`).
    TheLook 원본과 달리 모든 장바구니 미결제(cart without purchase) 세션에 회원 `user_id`가 보존됨.
    """
    return [
        # USR-1001 (VIP, 반품률 0%): PRD-3001(발마칸 코트 400,000원)을 장바구니(cart)에 담고 미결제 이탈!
        # -> PRD-3001(정상마진 40%, VIP 20% 할인 = 80,000원) + 코디 상품 PRD-3002(정가 200,000원, 저마진 22%이나 체화재고 특례 마진하한 10% 적용으로 최대 12% 할인 = 24,000원)
        # -> 합산 초개인화 번들 최대 쿠폰 할인액 = 104,000원! (Vector RAG는 두 상품 모두 VIP 20%를 적용해 120,000원 오답 도출)
        {"event_id": "EVT-5001", "user_id": "USR-1001", "session_id": "SES-1001-A", "sequence_number": 1, "event_type": "product", "product_id": "PRD-3001", "traffic_source": "Instagram", "created_at": "2026-09-28T20:10:00Z"},
        {"event_id": "EVT-5002", "user_id": "USR-1001", "session_id": "SES-1001-A", "sequence_number": 2, "event_type": "cart", "product_id": "PRD-3001", "traffic_source": "Instagram", "created_at": "2026-09-28T20:12:00Z"},

        # USR-1002 (VIP, 단 단순변심 반품률 50% >= 30%): PRD-3003(데님 자켓 200,000원)을 장바구니(cart)에 담고 미결제 이탈!
        # -> 과다반품 제한 단서(제9조) 작동으로 VIP 20%가 아닌 5% 상한 적용! (200,000 + 코디 PRD-3004 100,000 = 300,000원의 5% = 15,000원)
        {"event_id": "EVT-5003", "user_id": "USR-1002", "session_id": "SES-1002-A", "sequence_number": 1, "event_type": "product", "product_id": "PRD-3003", "traffic_source": "YouTube", "created_at": "2026-09-28T21:00:00Z"},
        {"event_id": "EVT-5004", "user_id": "USR-1002", "session_id": "SES-1002-A", "sequence_number": 2, "event_type": "cart", "product_id": "PRD-3003", "traffic_source": "YouTube", "created_at": "2026-09-28T21:05:00Z"},

        # USR-1003 (GOLD, 불량반품 제외 시 반품률 0%): PRD-3005(실크 스카프 150,000원, 마진율 20% 저마진·비체화)를 장바구니에 담음
        # -> PRD-3005는 저마진(20% < 25%)이고 체화재고 특례가 없으므로 GOLD 15%가 아닌 5% 상한(7,500원) 적용!
        {"event_id": "EVT-5005", "user_id": "USR-1003", "session_id": "SES-1003-A", "sequence_number": 1, "event_type": "product", "product_id": "PRD-3005", "traffic_source": "Organic", "created_at": "2026-09-28T22:00:00Z"},
        {"event_id": "EVT-5006", "user_id": "USR-1003", "session_id": "SES-1003-A", "sequence_number": 2, "event_type": "cart", "product_id": "PRD-3005", "traffic_source": "Organic", "created_at": "2026-09-28T22:03:00Z"},

        # USR-1004 (VIP, 마케팅 수신동의 N): PRD-3008(알파인 자켓 300,000원) 장바구니 이탈 -> 외부 푸시/알림톡 발송 불가(인앱 배너만 허용)
        {"event_id": "EVT-5007", "user_id": "USR-1004", "session_id": "SES-1004-A", "sequence_number": 1, "event_type": "cart", "product_id": "PRD-3008", "traffic_source": "Email", "created_at": "2026-09-28T23:10:00Z"},

        # USR-1007 (SILVER, 마케팅 동의 Y): 일시품절 상품 PRD-3009(avail_qty=0)를 장바구니에 담고 미결제 이탈 -> 대체 상품 PRD-3002(체화재고 125일) 추천 대상!
        {"event_id": "EVT-5008", "user_id": "USR-1007", "session_id": "SES-1007-A", "sequence_number": 1, "event_type": "cart", "product_id": "PRD-3009", "traffic_source": "Instagram", "created_at": "2026-09-28T23:30:00Z"},

        # USR-1008 (GOLD): 장바구니(cart) 담은 후 결제 완료(purchase)까지 이어진 정상 전환 세션 (미결제 이탈 모수에서 제외 대조군!)
        {"event_id": "EVT-5009", "user_id": "USR-1008", "session_id": "SES-1008-A", "sequence_number": 1, "event_type": "product", "product_id": "PRD-3004", "traffic_source": "Organic", "created_at": "2026-08-20T09:50:00Z"},
        {"event_id": "EVT-5010", "user_id": "USR-1008", "session_id": "SES-1008-A", "sequence_number": 2, "event_type": "cart", "product_id": "PRD-3004", "traffic_source": "Organic", "created_at": "2026-08-20T09:55:00Z"},
        {"event_id": "EVT-5011", "user_id": "USR-1008", "session_id": "SES-1008-A", "sequence_number": 3, "event_type": "purchase", "product_id": "PRD-3004", "traffic_source": "Organic", "created_at": "2026-08-20T10:00:00Z"},
    ]


def build_campaign_exceptions() -> list[dict]:
    """캠페인 마진완화·위생반품 검수·입점사 자발적 행사 특례 승인 원장 (Spanner `kmarket.campaign_exceptions`)."""
    return [
        # 1. PRD-3002 (입고 125일 체화재고): 최저 마진율 하한을 25.0% -> 10.0%로 완화 승인 (할인율 최대 22% - 10% = 12% 허용)
        {
            "approval_id": "EXC-KM-2026-01",
            "target_kind": "CLEARANCE_MARGIN",
            "product_id": "PRD-3002",
            "item_id": "",
            "approved_floor_margin_pct": 10.0,
            "hologram_tag_intact_yn": "",
            "vendor_voluntary_req_yn": "N",
            "approver_dept": "MD상품본부장",
            "approved_date": "2026-09-01",
            "status": "ACTIVE",
        },
        # 2. PRD-3005 (실크 스카프): 만료된 구 특례승인(EXPIRED) -> 적용 불가!
        {
            "approval_id": "EXC-KM-2026-02",
            "target_kind": "CLEARANCE_MARGIN",
            "product_id": "PRD-3005",
            "item_id": "",
            "approved_floor_margin_pct": 10.0,
            "hologram_tag_intact_yn": "",
            "vendor_voluntary_req_yn": "N",
            "approver_dept": "MD상품본부장",
            "approved_date": "2026-05-01",
            "status": "EXPIRED",
        },
        # 3. PRD-3008 (노르딕아웃도어 BRD-05): 대규모유통업법 제11조제5항 입점사 자발적 단독 프로모션 공문 접수 승인 (70% 분담 적법)
        {
            "approval_id": "EXC-KM-2026-03",
            "target_kind": "VENDOR_VOLUNTARY_PROMO",
            "product_id": "PRD-3008",
            "item_id": "",
            "approved_floor_margin_pct": 15.0,
            "hologram_tag_intact_yn": "",
            "vendor_voluntary_req_yn": "Y",
            "approver_dept": "준법감시팀장",
            "approved_date": "2026-09-10",
            "status": "ACTIVE",
        },
        # 4. OIT-2026-0013 (USR-1005 수영복 PRD-3006 반품 건): 반품 검수 결과 홀로그램 택 보존 확인(Y) -> 전자상거래법 제17조제2항 단서로 환불 승인 대상
        {
            "approval_id": "EXC-KM-2026-04",
            "target_kind": "RETURN_HYGIENE",
            "product_id": "PRD-3006",
            "item_id": "OIT-2026-0013",
            "approved_floor_margin_pct": 0.0,
            "hologram_tag_intact_yn": "Y",
            "vendor_voluntary_req_yn": "N",
            "approver_dept": "CS총괄실장",
            "approved_date": "2026-09-28",
            "status": "ACTIVE",
        },
        # 5. OIT-2026-0014 (USR-1006 이너웨어 PRD-3007 반품 건): 홀로그램 택 제거/훼손(N) -> 청약철회 제한 작동(반품 거절)
        {
            "approval_id": "EXC-KM-2026-05",
            "target_kind": "RETURN_HYGIENE",
            "product_id": "PRD-3007",
            "item_id": "OIT-2026-0014",
            "approved_floor_margin_pct": 0.0,
            "hologram_tag_intact_yn": "N",
            "vendor_voluntary_req_yn": "N",
            "approver_dept": "CS총괄실장",
            "approved_date": "2026-09-28",
            "status": "ACTIVE",
        },
        # 6. OIT-2026-0004 (BRD-01 아틀리에누아르 PRD-3001 주문건): 입점사 자발적 행사 신청서 미제출(vendor_voluntary_req_yn=N)로 특례 기각(REJECTED) -> 50% 법정 캡 강제!
        {
            "approval_id": "EXC-KM-2026-06",
            "target_kind": "VENDOR_VOLUNTARY_PROMO",
            "product_id": "PRD-3001",
            "item_id": "OIT-2026-0004",
            "approved_floor_margin_pct": 25.0,
            "hologram_tag_intact_yn": "",
            "vendor_voluntary_req_yn": "N",
            "approver_dept": "준법감시팀장",
            "approved_date": "2026-08-18",
            "status": "REJECTED",
        },
        # 7. PRD-3012 (메종드실크 저마진 22% 비체화 아이템): VIP_RETENTION 목적 마진 하한 12.0% 완화 특례 승인(ACTIVE)
        {
            "approval_id": "EXC-KM-2026-07",
            "target_kind": "VIP_RETENTION",
            "product_id": "PRD-3012",
            "item_id": "",
            "approved_floor_margin_pct": 12.0,
            "hologram_tag_intact_yn": "",
            "vendor_voluntary_req_yn": "N",
            "approver_dept": "마케팅총괄실장",
            "approved_date": "2026-09-15",
            "status": "ACTIVE",
        },
    ]


def generate_all() -> None:
    brands = build_brand_vendor_contracts()
    products = build_products()
    users = build_users()
    inv_items = build_inventory_items(products)
    orders, order_items = build_orders_and_items()
    events = build_events()
    exceptions = build_campaign_exceptions()

    write_csv("brand_vendor_contracts.csv", list(brands[0].keys()), brands)
    write_csv("products.csv", list(products[0].keys()), products)
    write_csv("users.csv", list(users[0].keys()), users)
    write_csv("inventory_items.csv", list(inv_items[0].keys()), inv_items)
    write_csv("orders.csv", list(orders[0].keys()), orders)
    write_csv("order_items.csv", list(order_items[0].keys()), order_items)
    write_csv("events.csv", list(events[0].keys()), events)
    write_csv("campaign_exceptions.csv", list(exceptions[0].keys()), exceptions)

    summary = {
        "company": "K마켙 (K-Market)",
        "seed": SEED,
        "reference_date": "2026-09-29",
        "table_counts": {
            "brand_vendor_contracts": len(brands),
            "products": len(products),
            "users": len(users),
            "inventory_items": len(inv_items),
            "orders": len(orders),
            "order_items": len(order_items),
            "events": len(events),
            "campaign_exceptions": len(exceptions),
        },
        "golden_verification_numbers": {
            "usr_1001_bundle_naive_rag_discount_krw": 120000,
            "usr_1001_bundle_ontology_discount_krw": 104000,
            "usr_1002_cherrypicker_bundle_discount_krw": 15000,
            "brd_01_joint_promo_total_discount_krw": 300000,
            "brd_01_contract_60pct_share_krw": 180000,
            "brd_01_legal_50pct_cap_share_krw": 150000,
            "brd_01_illegal_overcharge_krw": 30000,
            "brd_03_no_written_agreement_vendor_share_krw": 0,
            "ord_0009_sla_delay_hours": 60,
            "ord_0009_sla_compensation_krw": 10000,
        },
    }
    with open(os.path.join(OUT_DIR, "summary_stats.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[generate_dummy_data] Generated 8 CSV tables in {OUT_DIR}: {summary['table_counts']}")


if __name__ == "__main__":
    generate_all()
