# K-Market E-Commerce Ontology & BigQuery Graph Agent Hands-on Workshop (`/hands-on`)

이 디렉터리는 **K마켙(K-Market) 이커머스 데이터로 BigQuery Property Graph(`ecommerce_graph`)를 구축하고, 그 위에 Graph Agent(BigQuery Conversational Analytics / Google ADK)를 만드는 고객 핸즈온 워크숍 패키지**입니다.

웹 가이드 디자인은 Google Cloud Enterprise Workshop Guide(`caa-guide-web`) UI/UX를 100% 계승하여 상단 **GCP 프로젝트 ID 동적 치환 배너**, **원클릭 SQL/코드 복사**, **질의 키워드 실시간 필터링**을 지원합니다.

---

## 📁 디렉터리 구조 (`hands-on/`)

```text
hands-on/
├── index.html                        # 실습 가이드 웹 UI (#tab-overview, #tab-step0, #tab-step1, #tab-step2, #tab-step3, #tab-faq, #tab-admin-script)
├── css/
│   └── styles.css                    # Pretendard + JetBrains Mono + GCP 스타일시트
├── js/
│   └── app.js                        # 탭 전환 · Project ID 동적 치환 · 클립보드 복사 · 질의 필터 컨트롤러
├── images/
│   └── gcp_logo.png                  # Google Cloud 로고
├── ontology/                         # Step 0 비즈니스 사전 정의(고객 합의) 및 CQ 단일 평가 명세
│   ├── l1.yaml                       # 현업 부서 맥락 · 표준 용어 · 본칙/단서 특례 · 물리 컬럼 사전 합의서
│   └── competency_questions.yaml     # 고객 합의 인수 기준 CQ (Competency Questions: CQ01 ~ CQ07)
├── data/                             # K마켙(K-Market) 정형 원장 CSV 8종 (총 184 rows)
│   ├── users.csv                     # 고객 마스터 (60건)
│   ├── products.csv                  # 상품 카탈로그 (30건, 코디/대체상품 관계 포함)
│   ├── brand_vendor_contracts.csv    # 입점 브랜드 계약 및 판촉비 분담 약정 (8건)
│   ├── orders.csv                    # 주문 원장 (15건)
│   ├── order_items.csv               # 주문 품목 허브 (21건)
│   ├── inventory_items.csv           # 물류센터별 재고 및 체화일수 (32건)
│   ├── events.csv                    # 장바구니/행동 이벤트 (11건)
│   └── campaign_exceptions.csv       # 캠페인/반품 예외승인 원장 (7건)
├── sql/                              # BigQuery Studio 복사·실행용 단독 SQL 스크립트 3종
│   ├── 01_seed_kmarket_tables.sql    # kmarket_ecommerce (8 테이블) & kmarket_ontology (8 메타/조문 테이블) 원클릭 시딩 SQL
│   ├── 02_create_ecommerce_graph.sql # 11 Node Views + 15 Edge Views + CREATE PROPERTY GRAPH DDL
│   └── 03_verify_gql_queries.sql     # CQ01 · CQ04 · CQ06 · CQ07 멀티홉 GQL 검증 쿼리 4선
├── agent/                            # Google ADK 기반 K-Market Graph Agent 실습 패키지
│   ├── kmarket_graph_agent/
│   │   ├── __init__.py
│   │   ├── agent.py                  # LlmAgent + Step 0 Entity Alias Callback + Step 1 GQL Tool (Dry-Run & Self-Repair) + Step 2 Provision Lookup Tool
│   │   └── prompts.py                # 3-Layer 그래프 스키마 · GQL 작성 수칙 프롬프트
│   ├── .env.example                  # GOOGLE_CLOUD_PROJECT / LOCATION / MODEL 환경변수 템플릿
│   └── requirements.txt              # google-adk, google-cloud-bigquery, google-genai
├── scripts/                          # 강사/관리자용 자동화 스크립트
│   ├── setup_iam_and_api.sh          # 실습 참여자 IAM 권한 & API 일괄 활성화
│   ├── seed_kmarket_bq.py            # Python으로 BigQuery 테이블 + Property Graph 원클릭 적재
│   └── cleanup_iam_roles.sh          # 워크숍 종료 후 임시 IAM 권한 회수
├── Dockerfile                        # Cloud Run 정적 웹 배포용 Nginx 컨테이너
└── nginx.conf                        # 포트 8080 Nginx 설정
```

---

## 🚀 실행 방법

### 1. 로컬 웹 서버로 가이드 열기
- 워크스페이스 루트에서 `studio_server.py` 실행 중일 때:
  - `http://localhost:8090/hands-on/index.html#tab-step1`
- 또는 `hands-on/` 단독 실행:
  ```bash
  cd hands-on
  python3 -m http.server 8085
  # 브라우저에서 http://localhost:8085/#tab-step1 접속
  ```

### 2. Cloud Run 단독 배포 (선택)
```bash
cd hands-on
gcloud run deploy kmarket-handson-guide \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```
