# kmarket_ecommerce 스키마 카드 (INFORMATION_SCHEMA 기준 · 총 8개 테이블 184행)

- 프로젝트: `finance-ontology-changseop` · 데이터셋: `kmarket_ecommerce` · 위치: us-central1
- `ont_*` 는 Cloud Spanner 원장을 보는 연합 뷰(읽기 전용). 금액 컬럼 `*_krw` 는 원 단위.
- 쿼리는 반드시 `finance-ontology-changseop.kmarket_ecommerce.<table>` 로 완전 수식한다.

## users (60행)
- `user_id` STRING
- `user_name` STRING
- `age` INT64
- `gender` STRING — 값: F, M
- `membership_tier` STRING — 값: GOLD, SILVER, VIP, WELCOME
- `city` STRING
- `traffic_source` STRING — 값: Email, Instagram, Kakao, Organic, YouTube
- `marketing_opt_in_yn` STRING — 값: N, Y
- `preferred_style` STRING
- `created_at` DATE

## products (30행)
- `product_id` STRING
- `sku` STRING
- `product_name` STRING
- `brand_id` STRING — 값: BRD-01, BRD-02, BRD-03, BRD-04, BRD-05, BRD-06, BRD-07
- `brand_name` STRING
- `department` STRING
- `category` STRING
- `style_tag` STRING
- `cost_krw` INT64
- `retail_price_krw` INT64
- `coord_product_id` STRING
- `substitute_product_id` STRING
- `return_policy_tag` STRING — 값: HYGIENE_RESTRICTED, STANDARD
- `distribution_center_id` STRING — 값: DC-BUS, DC-ICN, DC-YIN

## brand_vendor_contracts (8행)
- `brand_id` STRING — 값: BRD-01, BRD-02, BRD-03, BRD-04, BRD-05, BRD-06, BRD-07, BRD-08
- `brand_name` STRING
- `trade_type` STRING — 값: 위수탁, 직매입, 특약매입
- `base_commission_pct` FLOAT64
- `agreed_promo_share_pct` FLOAT64
- `written_promo_agreement_yn` STRING — 값: N, Y
- `sla_ship_hours` INT64

## ont_orders (15행)
- `order_id` STRING
- `user_id` STRING
- `status` STRING — 값: Complete, Returned, Shipped
- `num_of_item` INT64
- `created_at` STRING (ISO-8601 시각 문자열, 시간 차 계산 시 `TIMESTAMP(created_at)` 변환 필요)
- `shipped_at` STRING (ISO-8601 시각 문자열, 시간 차 계산 시 `TIMESTAMP(shipped_at)` 변환 필요)
- `delivered_at` STRING (ISO-8601 시각 문자열)
- `returned_at` STRING (ISO-8601 시각 문자열)

## ont_order_items (21행)
- `item_id` STRING
- `order_id` STRING
- `user_id` STRING
- `product_id` STRING
- `inventory_item_id` STRING
- `status` STRING — 값: Complete, Returned, Shipped
- `retail_price_krw` INT64
- `sale_price_krw` INT64
- `coupon_discount_krw` INT64
- `coupon_type` STRING — 값: JOINT_PROMO, NONE, PLATFORM_TIER
- `return_reason_cd` STRING — 값: CHANGE_OF_MIND, DEFECTIVE, NONE, SIZE_MISMATCH_SPEC_DIFF, WEAR_AND_WASH_DAMAGE
- `created_at` STRING (ISO-8601 시각 문자열)
- `shipped_at` STRING (ISO-8601 시각 문자열)
- `delivered_at` STRING (ISO-8601 시각 문자열)
- `returned_at` STRING (ISO-8601 시각 문자열)

## ont_inventory_items (32행)
- `inventory_item_id` STRING
- `product_id` STRING
- `distribution_center_id` STRING — 값: DC-BUS, DC-ICN, DC-YIN
- `inbound_date` STRING (YYYY-MM-DD)
- `age_days` INT64
- `avail_qty` INT64
- `stock_status` STRING — 값: AVAILABLE, OUT_OF_STOCK, RESERVED, RETURN_INSPECTION

## ont_events (11행)
- `event_id` STRING
- `user_id` STRING
- `session_id` STRING
- `sequence_number` INT64
- `event_type` STRING — 값: cart, product, purchase
- `product_id` STRING
- `traffic_source` STRING
- `created_at` STRING (ISO-8601 시각 문자열)

## ont_campaign_exceptions (7행)
- `approval_id` STRING
- `target_kind` STRING — 값: CLEARANCE_MARGIN, RETURN_HYGIENE, VENDOR_VOLUNTARY_PROMO, VIP_RETENTION
- `product_id` STRING
- `item_id` STRING
- `approved_floor_margin_pct` FLOAT64
- `hologram_tag_intact_yn` STRING — 값: N, Y
- `vendor_voluntary_req_yn` STRING — 값: N, Y
- `approver_dept` STRING
- `approved_date` DATE
- `status` STRING — 값: ACTIVE, EXPIRED, REJECTED
