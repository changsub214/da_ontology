# da_ontology (Domain-Adaptive 3-Plane Ontology & BigQuery Property Graph Studio)

국내 엔터프라이즈(**금융권 여신심사·리스크·준법감시** 및 **이커머스 초개인화·마진·공정거래·CS심사**)의 **데이터(Data) · 비즈니스 맥락(Business Context) · 의사결정 기준(Decision Criteria)**을 **OKF v0.2 단일 진실 원천**으로부터 Google Cloud 3-Plane(Dataplex Knowledge Catalog 거버넌스 / BigQuery Property Graph + Spanner OLTP 위상 / Cloud Storage ObjectRef 원문)으로 연결하고, **고객 사전 합의 기반 CQ(Competency Questions) 단일 평가 체계**로 **Graph Agent vs Vector RAG + SQL 에이전트**의 의사결정 정확도를 실증하는 통합 레포지토리입니다.

```text
[Step 0: 비즈니스 사전 정의 & 고객 CQ 합의 (ontology/l1.yaml · competency_questions.yaml)]
                  │
                  ├──▶  Dataplex Knowledge Catalog   거버넌스 Plane — 조문 유효성(stable/deprecated) · 표준 용어집 · 클래스 앵커
                  ├──▶  BigQuery Property Graph      위상 Plane — 부서 맥락 분기(SCOPES_PORTFOLIO) · 본칙-단서-내규 다중 홉 GQL
                  │       ▲ (Spanner Data Boost 무복제 연합)
                  │       └── Cloud Spanner OLTP     실시간 원장 — 고객·계약/주문·담보/재고·연체/이벤트·예외승인
                  └──▶  Cloud Storage + ObjectRef    원문 Plane — 조항 단위 정본 마크다운 서명 URL 인출 및 SHA-256 무결성 검증
```

---

## 1. 핵심 구성 도메인 및 워크숍 패키지

| 구분 | 디렉터리 | BigQuery Property Graph | 핵심 내용 |
| :--- | :--- | :--- | :--- |
| **1. 통합 데모 스튜디오 웹** | `okf_veri_web/` · `tools/studio_server.py` | `finance_graph` & `ecommerce_graph` | 6개 모듈(`01 Intro & 사전 정의·CQ 합의` · `02 OKF 원문 대조` · `03 OKF 거버넌스 관리` · `04 3D/GQL 그래프 탐색` · `05 에이전트 대화` · `06 사전 합의 CQ 20 단일 평가 스튜디오`) |
| **2. 고객 Hands-on 워크숍** | `hands-on/` | `kmarket_ontology.ecommerce_graph` | 90분 고객 실습용 단독 웹 가이드(`/hands-on/index.html`) + 원클릭 BigQuery 시딩 SQL 3종 + Google ADK / BigQuery CAA 실습 코드 |
| **3. 금융 도메인 (별빛은행)** | `finance/` | `starlight_bank_ontology.finance_graph` | 은행업감독규정·별표3·사내내규 PDF 10종(188 Concept) · 여신 원장 8종(222행) · 11 Nodes / 15 Edges · `starlight-graphrag` & `starlight-rag-agent` |
| **4. 이커머스 도메인 (K마켙)** | `ecommerce/` | `kmarket_ontology.ecommerce_graph` | 대규모유통업법·전자상거래법·개보위·사내내규 PDF 10종(46 Concept) · 커머스 원장 8종(184행) · 11 Nodes / 15 Edges · `kmarket-graph-agent` & `kmarket-rag-agent` |

---

## 2. 디렉터리 구조 (`da_ontology/`)

```text
da_ontology/
├── Dockerfile                      # Cloud Run 통합 스튜디오 배포용 컨테이너 정의
├── README.md                       # 프로젝트 개요 및 실행 가이드
├── okf_veri_web/                   # 통합 데모 스튜디오 프론트엔드 (금융 ↔ 이커머스 프로젝트 전환 지원)
│   ├── index.html                  #   스튜디오 메인 엔트리포인트
│   ├── css/gcp-console.css         #   Google Cloud Console 디자인 시스템 스타일시트
│   ├── js/                         #   모듈 01~06 컨트롤러 (mod-pages.js, mod-benchmark.js 등)
│   └── data/                       #   아키텍처 다이어그램 및 사전 합의 CQ 20 평가 리포트 데이터
├── hands-on/                       # 고객 핸즈온 워크숍 패키지 (E-Commerce BigQuery Graph & Agent)
│   ├── index.html                  #   실습 가이드 웹 UI (Step 0 사전 정의 & CQ 합의 ~ Step 3 CQ 평가)
│   ├── ontology/                   #   Step 0 현업 사전 합의서(l1.yaml) 및 CQ 명세(competency_questions.yaml)
│   ├── data/                       #   K-Market 정형 원장 CSV 8종 (184 rows)
│   ├── sql/                        #   BigQuery Studio 원클릭 실행용 SQL 3종 (테이블 시딩 · Graph DDL · CQ GQL)
│   ├── agent/kmarket_graph_agent/  #   Google ADK 기반 Self-Repair Graph Agent 실습 코드
│   └── scripts/                    #   IAM/API 설정 및 Python 1-Click BigQuery 시딩 스크립트
├── finance/                        # [도메인 1] 별빛은행 (finance-ontology)
│   ├── data/                       #   원본 PDF 10종(un_data/) + 정형 원장 CSV 8종(structured/)
│   ├── okf/                        #   OKF v0.2 번들 및 무결성 검증 리포트(verification.json)
│   ├── ontology/                   #   L1 온톨로지(l1.yaml) 및 CQ 20문항 명세
│   ├── sql/                        #   Spanner DDL 및 BigQuery finance_graph SQL
│   └── agents/                     #   starlight-graphrag & starlight-rag-agent (ADK)
├── ecommerce/                      # [도메인 2] K마켙 (ecommerce-ontology)
│   ├── data/                       #   원본 PDF 10종(un_data/) + 정형 원장 CSV 8종(structured/)
│   ├── okf/                        #   OKF v0.2 번들 및 무결성 검증 리포트(verification.json)
│   ├── ontology/                   #   L1 온톨로지(l1.yaml) 및 CQ 20문항 명세
│   ├── sql/                        #   Spanner DDL 및 BigQuery ecommerce_graph SQL
│   └── agents/                     #   kmarket-graph-agent & kmarket-rag-agent (ADK)
└── tools/                          # 스튜디오 백엔드 서버 및 3-Plane 빌드·검증·배포 도구
    ├── studio_server.py            #   통합 스튜디오 웹 & REST API 서버 (기본 포트: 8090)
    ├── ecommerce_agent_handler.py  #   K마켙 Graph / RAG 에이전트 핸들러
    ├── build_ontology_graph.py     #   금융 3-Plane 그래프 빌더 및 정합성 게이트
    └── deploy_ecommerce_gcp.py     #   이커머스 3-Plane 그래프 빌더 및 정합성 게이트
```

---

## 3. 빠른 실행 가이드 (Quick Start)

### 3-1. 로컬 통합 데모 스튜디오 & 핸즈온 가이드 서버 실행
```bash
python3 tools/studio_server.py
```
- **통합 데모 스튜디오 (`finance-ontology` & `ecommerce-ontology`)**: `http://localhost:8090/okf_veri_web/index.html`
- **고객 Hands-on 실습 가이드 웹**: `http://localhost:8090/hands-on/index.html#tab-step0`

### 3-2. Cloud Run 배포
```bash
gcloud run deploy krda-ontology-studio \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```
