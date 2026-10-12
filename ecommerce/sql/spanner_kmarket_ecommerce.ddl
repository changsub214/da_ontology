-- ---------------------------------------------------------------------------
-- Spanner `finance-cs` / `kmarket_ecommerce` — K마켙 실시간 커머스 트랜잭션 원장 5종
--
-- ADR 0002 / ADR 0018 결정에 따라 실시간 트랜잭션성 5개 테이블만 Spanner 에 둔다:
--   1. orders (고객 주문 및 출고·배송완료·반품 타임스탬프 원장)
--   2. order_items (품목별 정상가·쿠폰할인액·실결제가·반품사유 원장)
--   3. inventory_items (물류센터별 실시간 가용재고·체화일수·재고상태 원장)
--   4. events (실시간 웹·앱 조회/장바구니/결제 행동로그 원장)
--   5. campaign_exceptions (체화재고 마진완화·위생반품 검수·자발적 판촉 예외승인 결재 원장)
--
-- 마스터 3종(users, products, brand_vendor_contracts)은 BigQuery `kmarket_ecommerce`에 위치한다.
-- ---------------------------------------------------------------------------

CREATE TABLE orders (
  order_id     STRING(64) NOT NULL,
  user_id      STRING(64) NOT NULL,
  status       STRING(32),
  num_of_item  INT64,
  created_at   STRING(64),
  shipped_at   STRING(64),
  delivered_at STRING(64),
  returned_at  STRING(64),
) PRIMARY KEY (order_id);

CREATE TABLE order_items (
  item_id             STRING(64) NOT NULL,
  order_id            STRING(64) NOT NULL,
  user_id             STRING(64) NOT NULL,
  product_id          STRING(64) NOT NULL,
  inventory_item_id   STRING(64) NOT NULL,
  status              STRING(32),
  retail_price_krw    INT64,
  sale_price_krw      INT64,
  coupon_discount_krw INT64,
  coupon_type         STRING(64),
  return_reason_cd    STRING(64),
  created_at          STRING(64),
  shipped_at          STRING(64),
  delivered_at        STRING(64),
  returned_at         STRING(64),
) PRIMARY KEY (item_id);

CREATE TABLE inventory_items (
  inventory_item_id      STRING(64) NOT NULL,
  product_id             STRING(64) NOT NULL,
  distribution_center_id STRING(64),
  inbound_date           STRING(32),
  age_days               INT64,
  avail_qty              INT64,
  stock_status           STRING(32),
) PRIMARY KEY (inventory_item_id);

CREATE TABLE events (
  event_id        STRING(64) NOT NULL,
  user_id         STRING(64) NOT NULL,
  session_id      STRING(64),
  sequence_number INT64,
  event_type      STRING(32),
  product_id      STRING(64) NOT NULL,
  traffic_source  STRING(64),
  created_at      STRING(64),
) PRIMARY KEY (event_id);

CREATE TABLE campaign_exceptions (
  approval_id               STRING(64) NOT NULL,
  target_kind               STRING(64),
  product_id                STRING(64) NOT NULL,
  item_id                   STRING(64),
  approved_floor_margin_pct FLOAT64,
  hologram_tag_intact_yn    STRING(16),
  vendor_voluntary_req_yn   STRING(16),
  approver_dept             STRING(64),
  approved_date             DATE,
  status                    STRING(32),
) PRIMARY KEY (approval_id);
