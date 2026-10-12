/* ==========================================================================
   okf_veri_web/js/mod-pages.js
   Renderers for Modules 01 (intro — figures from data/intro_arch.json), 03 (okf-enrollment),
   05 (agent), and 06 (rag-vs-graphrag).
   Follows the 90-8-2 Google Cloud Console Neutral Design System.
   ========================================================================== */

/* --------------------------------------------------------------------------
   01 · Intro — design-document view (ADR 0015).
   Every figure, caption and number comes from data/intro_arch.json, written by
   tools/export_intro_arch.py from agents/design/*.yaml `diagrams` + ontology/l1.yaml
   + live measurement (the export refuses to write if any gate fails). Nothing here
   is hand-typed: this file only lays the figures out and renders the Mermaid text.
   -------------------------------------------------------------------------- */
const INTRO_MERMAID_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
let INTRO_DATA = null;
let INTRO_DATA_ERR = '';
let INTRO_MERMAID = null;
let INTRO_TOGGLE = {};            // tab id → selected toggle figure id
let INTRO_RENDER_TOKEN = 0;
let INTRO_RENDER_CHAIN = Promise.resolve();
let INTRO_SVG_SEQ = 0;
const INTRO_SVG_CACHE = {};       // `${theme}:${figure or panel id}` → svg markup
let INTRO_THEME_OBSERVER = null;

function introTheme() {
  return document.body.classList.contains('dark-mode') ? 'dark' : 'light';
}

function setIntroTab(tabId) {
  INTRO_TAB = tabId;
  saveUiState();
  renderIntroModule();
}

function setIntroToggle(tabId, figId) {
  INTRO_TOGGLE[tabId] = figId;
  const box = document.getElementById('module-intro');
  const scroller = box && box.querySelector('.intro-body-scroll');
  const wrap = box && box.querySelector(`.intro-toggle-wrap[data-toggle-tab="${tabId}"]`);
  if (box && scroller && wrap && INTRO_DATA && INTRO_DATA.figures && INTRO_DATA.figures[figId]) {
    const prevTop = scroller.scrollTop;
    wrap.querySelectorAll('.intro-seg button').forEach((b) => b.classList.toggle('on', b.dataset.figOpt === figId));
    const slot = wrap.querySelector('.intro-toggle-slot');
    if (slot) {
      const prevH = slot.offsetHeight;
      if (prevH > 0) slot.style.minHeight = `${prevH}px`;
      slot.innerHTML = introFigureHtml(INTRO_DATA.figures[figId]);
    }
    scroller.scrollTop = prevTop;
    renderIntroFigures(box).then(() => {
      if (slot) slot.style.minHeight = '';
      scroller.scrollTop = prevTop;
    });
    return;
  }
  renderIntroModule();
}

function jumpToCqEvalFromIntro(cqIdx, mode = 'report') {
  if (typeof BENCH_SELECTED_IDX !== 'undefined') BENCH_SELECTED_IDX = cqIdx;
  if (typeof SELECTED_SCEN_IDX !== 'undefined') SELECTED_SCEN_IDX = cqIdx;
  if (typeof BENCH_MODE !== 'undefined') BENCH_MODE = mode;
  if (typeof switchModule === 'function') {
    switchModule('rag-vs-graphrag');
  }
  setTimeout(() => {
    if (typeof selectBenchmarkQuestion === 'function') {
      selectBenchmarkQuestion(cqIdx, false);
    }
  }, 60);
}

function cqPillBtnHtml(cqNum) {
  const idx = Math.max(0, Number(cqNum) - 1);
  const label = `CQ${String(cqNum).padStart(2, '0')}`;
  return `<button type="button" class="agent-neutral-pill" style="cursor:pointer; font-family:var(--mono); font-size:11.5px; font-weight:600; color:var(--gcp-blue); border-color:rgba(26,115,232,0.35); margin:2px;" onclick="jumpToCqEvalFromIntro(${idx}, 'report')" title="${label} 평가 리포트로 이동">${label} ↗</button>`;
}

function injectCqAlignmentIntroTab(d) {
  if (!d || !Array.isArray(d.tabs)) return d;
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  d.figures = d.figures || {};

  const cqAlignTab = {
    id: 'cq_align',
    title: '사전 정의 · CQ 합의',
    figures: ['0-1'],
    lead: '',
    hero: {
      eyebrow: 'Step 0 · 비즈니스 사전 정의 (Pre-Definition) & 고객 CQ 합의 절차',
      title: isEcom
        ? '온톨로지는 코드가 아니라<br><em>고객(MD · 마케팅 · CS · 정산 · 준법)과의 사전 합의서</em>에서 출발합니다.'
        : '온톨로지는 코드가 아니라<br><em>고객(여신심사 · 리스크 · 준법 · 사후관리)과의 사전 합의서</em>에서 출발합니다.',
      sub: isEcom
        ? '현업에서는 동일한 용어(\'반품률\', \'할인쿠폰 마진\', \'판촉비 분담률\')라도 본부마다 바라보는 원장 모수와 본칙·단서 규정이 다릅니다. 데이터를 적재하거나 에이전트를 만들기 전에 고객과 사전 협의·합의하여 부서 맥락별 규칙을 명문화(l1.yaml)하고, 이를 검증 가능한 핵심 역량 질문(CQ, Competency Questions)으로 연결해야 온톨로지 구축과 평가의 의미가 명확해집니다.'
        : '현업에서는 동일한 용어(\'연체율\', \'대손충당금 적립률\', \'금리인하요구권\')라도 부서마다 바라보는 원장 모수와 본칙·단서 규정이 다릅니다. 데이터를 적재하거나 에이전트를 만들기 전에 고객과 사전 협의·합의하여 부서 맥락별 규칙을 명문화(l1.yaml)하고, 이를 검증 가능한 핵심 역량 질문(CQ, Competency Questions)으로 연결해야 온톨로지 구축과 평가의 의미가 명확해집니다.',
      reasons_title: '비즈니스에서 CQ로 연결되는 4단계 사전 정의 · 합의 · 단일 평가 절차',
      reasons: [
        {
          title: '1. 현업 해석 충돌(Silo) 발굴',
          text: isEcom
            ? '동일 주문품목 원장(21건)을 두고 MD본부는 쿠폰할인(6건), CS심사팀은 반품심사(3건), 파트너정산은 약정 70% vs 법정 50% 캡을 각각 주장하는 사일로 충돌을 발굴합니다.'
            : '동일 여신 원장(100계좌)을 두고 리스크위원회(1.51%), 금감원 공시(2.26%), 여신관리팀 EWS(4.00%)가 서로 다른 연체율 모수와 조문을 적용하는 사일로 충돌을 발굴합니다.'
        },
        {
          title: '2. 고객 사전 협의 · 합의서 (l1.yaml)',
          text: '누가(<span class="edge">BusinessContext</span>) × 어떤 표준 용어(<code>GlossaryTerm</code>)를 호출할 때 × 어느 원장 모수(<span class="edge">SCOPES_PORTFOLIO</span>)와 × 어떤 본칙·단서·위임 조문(<span class="edge">INVOKES_PROVISION</span> <span class="edge">HAS_EXCEPTION_PROVISO</span>)을 연결할지 사전 합의하여 <code>ontology/l1.yaml</code>로 고정합니다.'
        },
        {
          title: '3. CQ 도출 & CQ 단일 평가 체계',
          text: '사전 합의서의 실행 가능한 인수 기준(Acceptance Criteria)으로서 <b>CQ 20문항(CQ01~CQ20)</b>을 도출하고, 별도의 임의 평가셋(EQ)을 분리하지 않고 <b>사전 합의된 CQ 자체로 에이전트를 1:1 평가</b>합니다.'
        }
      ],
      foot: '아래 <b>그림 0-1</b>과 <b>고객 사전 협의·합의 매트릭스</b>는 현업 합의 항목(<code>AGR-01 ~ AGR-05</code>)이 어떻게 15개 그래프 엣지와 <b>CQ 20문항</b>으로 연결되는지 보여 줍니다. 우측 열의 <code>CQ</code> 버튼을 클릭하면 <b>06 · CQ 평가 스튜디오</b>의 해당 문항으로 즉시 이동합니다.'
    }
  };

  const financeRows = [
    {
      cells: [
        '<b>AGR-01</b><div class="intro-cell-sub"><code>CREDIT_REVIEW</code> (여신심사부)</div>',
        '<b>대손충당금적립률</b><div class="intro-cell-sub"><code>GT_PROVISION_RATIO</code> · 정상 여신 일괄 0.85% 적용 vs 경기민감업종 상향 단서 누락</div>',
        '• <b>본칙</b>: 은행업감독규정 제29조제1항 정상 0.85%, 고정 20%<br>• <b>단서 특례 합의</b>: 차주 업종(<code>ksic_code</code>)이 숙박·음식(H), 건설(F), 도소매(G), 부동산(L)일 때 단서(<code>PROV_1</code>) <b>0.9% 상향</b> 적용 및 우선변제 담보(<code>Collateral</code>) 차감 특례 연결',
        '<span class="edge">BORROWED_BY</span> <span class="edge">HAS_EXCEPTION_PROVISO</span> <span class="edge">HAS_COLLATERAL</span><div class="intro-cell-sub"><code>edge_has_exception_proviso</code> · <code>v_edge_has_collateral</code></div>',
        [1, 2, 8].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-02</b><div class="intro-cell-sub"><code>RISK_MGMT</code> · <code>COMPLIANCE</code> · <code>COLLECTION_EWS</code></div>',
        '<b>연체율 &amp; 연체기산일</b><div class="intro-cell-sub"><code>GT_DELINQUENCY_RATE</code> · 동일 여신원장에 대해 부서별 연체율 수치 불일치 (1.51% vs 2.26% vs 4.00%)</div>',
        '• <b>모수 분기 합의</b>: 호출 부서 맥락별로 <code>SCOPES_PORTFOLIO</code> 모수와 조문을 분리<br>&nbsp;&nbsp;- 리스크관리부: 30일 이상 연체 잔액 기준 (<b>1.51%</b>)<br>&nbsp;&nbsp;- 준법감시부 공시: 1일 이상 연체 원리금 기준 (<b>2.26%</b>)<br>&nbsp;&nbsp;- 여신관리팀 EWS: 5일 이상 연체 계좌수 기준 (<b>4.00%</b>)',
        '<span class="edge">SCOPES_PORTFOLIO</span> <span class="edge">INVOKES_PROVISION</span> <span class="edge">HAS_DELINQUENCY</span><div class="intro-cell-sub"><code>v_edge_scopes_portfolio</code> · <code>edge_invokes_provision</code></div>',
        [3, 4, 15, 16, 20].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-03</b><div class="intro-cell-sub"><code>CREDIT_REVIEW</code> · <code>COMPLIANCE</code></div>',
        '<b>금리인하요구권 &amp; 가산금리</b><div class="intro-cell-sub"><code>GT_RATE_CUT_RIGHT</code> · 신용등급 상승 차주의 금리인하 신청 시 우대금리 기적용 계좌 심사 기준 모호</div>',
        '• <b>위임·내규 연결 합의</b>: 대출금리 모범규준 본칙에서 별빛은행 여신내규(<span class="edge">DELEGATES_TO_INTERNAL</span>)로 위임된 심사 기준과 계좌별 기승인 특례(<code>ExceptionApproval</code>) 원장을 대조하여 인하 폭 산정',
        '<span class="edge">HAS_RATE_CUT_REQUEST</span> <span class="edge">DELEGATES_TO_INTERNAL</span> <span class="edge">HAS_EXCEPTION_APPROVAL</span><div class="intro-cell-sub"><code>edge_delegates_to_internal</code> · <code>v_node_rate_cut_request</code></div>',
        [5, 10, 14, 19].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-04</b><div class="intro-cell-sub"><code>RISK_MGMT</code> · <code>COMPLIANCE</code></div>',
        '<b>자산건전성 · 거액익스포져</b><div class="intro-cell-sub"><code>GT_ASSET_QUALITY</code> · 타 업권(저축은행 요주의 2% vs 은행 7%) 혼동 및 폐기 조문 인용 차단</div>',
        '• <b>업권 배제 합의</b>: 상호저축은행 감독규정은 <span class="edge">CONFLICTS_BY_SECTOR</span> 엣지로 명시적 배제<br>• <b>효력 게이트 합의</b>: Dataplex Knowledge Catalog <code>okf</code> Aspect 실시간 조회로 폐기(<code>deprecated</code>) 조문 차단 및 대체 조문 안내',
        '<span class="edge">CONFLICTS_BY_SECTOR</span> <span class="edge">EVALUATED_UNDER_PROVISION</span><div class="intro-cell-sub"><code>edge_conflicts_by_sector</code> · Knowledge Catalog Gate</div>',
        [6, 7, 11, 13, 17].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-05</b><div class="intro-cell-sub"><code>PORTFOLIO_ANALYTICS</code> · <code>GOVERNANCE</code></div>',
        '<b>순수 원장 집계 · 스키마 경계</b><div class="intro-cell-sub">규정 불필요 원장 집계(<code>LEDGER_ONLY</code>) · 거시 문헌 비교 · 도메인 외/미구현 컬럼 방어</div>',
        '• <b>모드 분기 합의</b>: 조문 불필요 잔액 합산은 <code>LEDGER_ONLY</code> 모드로 처리하고, 조문이 요구하나 물리 원장에 없는 컬럼(<code>missing_schema_columns</code>) 및 도메인 외 질의는 추측 없이 거절(<code>OUT_OF_DOMAIN</code>)',
        '<span class="edge">GOVERNED_BY_CRITERIA</span> <code>missing_schema_columns</code><div class="intro-cell-sub"><code>v_edge_governed_by_criteria</code> · <code>lex_provisions</code></div>',
        [9, 12, 18].map(cqPillBtnHtml).join(' ')
      ]
    }
  ];

  const ecommerceRows = [
    {
      cells: [
        '<b>AGR-01</b><div class="intro-cell-sub"><code>CRM_GROWTH</code> × <code>MD_MERCHANDISING</code></div>',
        '<b>프로모션할인쿠폰 마진율</b><div class="intro-cell-sub"><code>GT_PROMO_COUPON</code> · 상시 마진 25% 본칙만 적용하여 체화재고 소진 캠페인까지 오거절</div>',
        '• <b>본칙</b>: 프로모션 내규 제4조 실현마진율 <b>25% 하한</b> 가드레일<br>• <b>단서 특례 합의</b>: 입고 <b>90일 이상 체화재고</b>(<code>InventoryItem.stock_age_days ≥ 90</code>)이면서 <code>CampaignException(APPROVED)</code>이 존재하면 제4조 단서(<code>PROV_1</code>) <b>10% 하한</b> 적용',
        '<span class="edge">HAS_EXCEPTION_PROVISO</span> <span class="edge">STOCKED_AT_INVENTORY</span> <span class="edge">HAS_CAMPAIGN_EXCEPTION</span><div class="intro-cell-sub"><code>edge_has_exception_proviso</code> · <code>v_edge_has_campaign_exception</code></div>',
        [1, 3, 5, 14].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-02</b><div class="intro-cell-sub"><code>LEGAL_COMPLIANCE</code> × <code>CRM_GROWTH</code></div>',
        '<b>장바구니이탈타겟팅</b><div class="intro-cell-sub"><code>GT_CART_ABANDON</code> · 품절 대체상품 추천 시 마케팅 미동의(Opt-out) 고객 푸시 발송 리스크</div>',
        '• <b>법령 준수 합의</b>: 개인정보위 행태정보 가이드라인 제3조(<code>PIPC-BHV-001_ART_03</code>)와 회원 마스터(<code>marketing_opt_in</code>)를 결합하여 미동의 고객 개인화 쿠폰 푸시를 즉시 차단하고 품절 시 대체상품(<span class="edge">SUBSTITUTED_BY_PRODUCT</span>) 재고만 검증',
        '<span class="edge">PERFORMED_BY_CUSTOMER</span> <span class="edge">SUBSTITUTED_BY_PRODUCT</span> <span class="edge">INVOKES_PROVISION</span><div class="intro-cell-sub"><code>v_edge_performed_by_customer</code> · <code>v_edge_substituted_by_product</code></div>',
        [2, 11, 15].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-03</b><div class="intro-cell-sub"><code>MD_MERCHANDISING</code> vs <code>CX_CS_SUPPORT</code></div>',
        '<b>부서별 심사 모수 분기</b><div class="intro-cell-sub">동일 주문품목 원장(<code>OrderItem 21건</code>)에 대해 본부마다 반품/심사 모수 정의 충돌</div>',
        '• <b>모수 분기 합의</b>: <span class="edge">SCOPES_PORTFOLIO</span> 뷰를 통해 부서 맥락별 공식 심사 모수를 분리<br>&nbsp;&nbsp;- <b>MD본부</b>: 쿠폰할인 적용 품목 <b>6건</b> (<code>PROMO_MARGIN_AND_VENDOR_SHARE_SCOPE</code>)<br>&nbsp;&nbsp;- <b>CS심사팀</b>: 반품 접수/완료 품목 <b>3건</b> (<code>OI-6006~6008</code>, <code>CS_RETURN_AND_WITHDRAWAL_SCOPE</code>)',
        '<span class="edge">SCOPES_PORTFOLIO</span> <span class="edge">INVOKES_PROVISION</span><div class="intro-cell-sub"><code>v_edge_scopes_portfolio</code> · <code>edge_invokes_provision</code></div>',
        [4, 9, 18].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-04</b><div class="intro-cell-sub"><code>PARTNER_SETTLEMENT</code> × <code>LEGAL_COMPLIANCE</code></div>',
        '<b>판촉비분담률 (50% 캡 vs 70% 특례)</b><div class="intro-cell-sub"><code>GT_PROMO_SHARE_RATIO</code> · 계약서상 분담률(70%) 일괄 차감 시 대규모유통업법 위반 과징금</div>',
        '• <b>강행법규 우선 합의</b>: 계약서 분담률이 70%라도 대규모유통업법 제11조제4항 <b>50% 상한 캡</b> 우선 적용(벨로체 <code>OI-6004</code>: 50% 캡, 초과분 K마켙 흡수)<br>• <b>단서 특례 합의</b>: 제11조제5항 <b>자발적·차별화 단독행사</b>(메종드실크 <code>OI-6012</code>, <code>APR-7004 ACTIVE</code>)만 약정 70% 인정',
        '<span class="edge">SUPPLIED_BY_BRAND</span> <span class="edge">DELEGATES_TO_INTERNAL</span> <span class="edge">HAS_CAMPAIGN_EXCEPTION</span><div class="intro-cell-sub"><code>v_edge_supplied_by_brand</code> · <code>edge_delegates_to_internal</code></div>',
        [6, 8, 10, 16].map(cqPillBtnHtml).join(' ')
      ]
    },
    {
      cells: [
        '<b>AGR-05</b><div class="intro-cell-sub"><code>CX_CS_SUPPORT</code> × <code>FULFILLMENT_OPS</code></div>',
        '<b>청약철회기한 · 직구 대조군 · 스키마 진단</b><div class="intro-cell-sub"><code>GT_WITHDRAWAL_WINDOW</code> · 세탁훼손(불가) vs 치수오차(90일 무상) 및 해외직구 고시 오적용 방어</div>',
        '• <b>청약철회 &amp; 대조군 배제 합의</b>: 전자상거래법 제17조제1~3항을 반품사유코드와 매핑하고, 국내 풀필먼트 주문에 관세청 해외직구 고시(35,000원)는 <span class="edge">CONFLICTS_BY_SECTOR</span>로 배제하며, 미구현 컬럼(<code>missing_schema_columns</code>)은 추측 없이 진단',
        '<span class="edge">CONFLICTS_BY_SECTOR</span> <span class="edge">GOVERNED_BY_CRITERIA</span> <code>missing_schema_columns</code><div class="intro-cell-sub"><code>edge_conflicts_by_sector</code> · <code>lex_provisions</code></div>',
        [7, 12, 13, 17, 19, 20].map(cqPillBtnHtml).join(' ')
      ]
    }
  ];

  d.figures['0-1'] = {
    id: '0-1',
    kind: 'mermaid',
    title: '비즈니스 사전 정의(고객 합의) → CQ 도출 → L1 온톨로지 그래프 → CQ 단일 평가 파이프라인',
    caption: '현업 부서 간 용어·모수·규정 해석 충돌을 먼저 발굴한 뒤(1단계), 고객과의 사전 협의·합의를 통해 <code>ontology/l1.yaml</code> 위상 규칙으로 명문화하고(2단계), 이 합의가 제대로 작동하는지 검증하는 인수 기준으로서 <b>CQ(Competency Questions) 20문항</b>을 도출합니다(3단계). 최종 에이전트 평가는 별도 EQ 분리 없이 <b>사전 합의된 CQ 20문항 단일 체계</b>로 수행됩니다(4단계).',
    flowchart: true,
    mermaid: `---
config:
  flowchart:
    nodeSpacing: 18
    rankSpacing: 28
---
flowchart LR
  subgraph S1["1. 현업 문제 발굴"]
    P1["부서별 용어 · 모수 충돌<br/>(연체율/반품률 · 본칙/특례)"]
  end
  subgraph S2["2. 고객 사전 협의 · 합의"]
    A1["부서 맥락 × 표준 용어 합의<br/>BusinessContext × GlossaryTerm"]
    A2["원장 모수 · 단서 특례 합의<br/>ontology/l1.yaml 명문화"]
  end
  subgraph S3["3. CQ 인수 기준 도출"]
    C1["핵심 역량 질문 명세<br/>competency_questions.yaml"]
    C2["필수 순회 엣지 · 골드 판정<br/>CQ01 ~ CQ20 확정"]
  end
  subgraph S4["4. 그래프 구축 & CQ 단일 평가"]
    G1[("BigQuery Property Graph<br/>11 Nodes · 15 Edges")]
    E1["06 · CQ 평가 스튜디오<br/>사전 합의 CQ 20 단일 평가"]
  end
  P1 --> A1 --> A2 --> C1 --> C2 --> G1 --> E1
  class G1 store
  class C1,C2,E1 llm
`,
    table: {
      columns: [
        '합의 ID · 참여 부서 (BusinessContext)',
        '표준 용어 (GlossaryTerm) · 현업 충돌 이슈',
        '고객 사전 합의 규칙 (원장 모수 · 본칙 · 단서 특례)',
        '구현 그래프 위상 (L1 엣지 · 뷰)',
        '인수 평가 CQ (클릭 시 이동)'
      ],
      rows: isEcom ? ecommerceRows : financeRows
    }
  };

  if (!d.tabs.some((t) => t.id === 'cq_align')) {
    const sysIdx = d.tabs.findIndex((t) => t.id === 'sys');
    if (sysIdx >= 0) {
      d.tabs.splice(sysIdx + 1, 0, cqAlignTab);
    } else {
      d.tabs.unshift(cqAlignTab);
    }
  }
  return d;
}

function loadIntroData() {
  const projMeta = (typeof PROJECT_REGISTRY !== 'undefined' && typeof ACTIVE_PROJECT !== 'undefined')
    ? PROJECT_REGISTRY[ACTIVE_PROJECT]
    : null;
  const url = (projMeta && projMeta.introArchUrl) || 'data/intro_arch.json';
  return fetch(url + '?t=' + Date.now())
    .then((res) => {
      if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
      return res.json();
    })
    .then((d) => {
      INTRO_DATA = injectCqAlignmentIntroTab(d);
      INTRO_DATA_ERR = null;
      Object.keys(INTRO_SVG_CACHE).forEach((k) => delete INTRO_SVG_CACHE[k]);
    })
    .catch((err) => { INTRO_DATA_ERR = String(err && err.message || err); });
}

function introFigureTitle(fig) {
  return `<b>그림 ${escapeHtml(fig.id)} · ${fig.title}</b>`;   // title is trusted HTML from the design YAML
}

function introTableHtml(table) {
  const head = table.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join('');
  const body = table.rows.map((r) => {
    if (Array.isArray(r.cells)) {
      return `<tr>${r.cells.map((cell) => `<td>${cell}</td>`).join('')}</tr>`;
    }
    return `
    <tr>
      <td><b>${escapeHtml(r.class)}</b><div class="intro-cell-sub">${escapeHtml(r.korean)}</div></td>
      <td>${escapeHtml(r.store)}</td>
      <td><code>${escapeHtml(r.physical_table)}</code> → <code>${escapeHtml(r.graph_view)}</code></td>
      <td class="intro-num">${Number(r.rows_source).toLocaleString('en-US')} · ${Number(r.nodes_graph).toLocaleString('en-US')}</td>
    </tr>`;
  }).join('');
  return `<div class="intro-table-wrap"><table class="intro-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function introFigureHtml(fig) {
  if (!fig) return '';
  if (fig.kind === 'trap_paths') {
    const panels = (fig.panels || []).map((p) => `
      <div class="intro-sub">
        <div class="intro-sub-h">${escapeHtml(p.title)}</div>
        <div class="intro-fig-canvas" data-mm-fig="${escapeHtml(fig.id)}" data-mm-panel="${escapeHtml(p.id)}"></div>
        <div class="intro-sub-c">${p.text}</div>
        <pre class="intro-gql">${escapeHtml(p.gql)}</pre>
      </div>`).join('');
    return `
      <figure class="intro-fig" data-fig="${escapeHtml(fig.id)}">
        <div class="intro-grid3">${panels}</div>
        <figcaption>${introFigureTitle(fig)} — ${fig.caption}</figcaption>
      </figure>`;
  }
  return `
    <figure class="intro-fig" data-fig="${escapeHtml(fig.id)}">
      <div class="intro-fig-canvas" data-mm-fig="${escapeHtml(fig.id)}"></div>
      ${fig.table ? introTableHtml(fig.table) : ''}
      <figcaption>${introFigureTitle(fig)} — ${fig.caption}</figcaption>
    </figure>`;
}

/* First-screen hero (design intro_tabs[].hero · 2026-09-30). Text is trusted design HTML (like lead / captions);
   the example is gated == the stored 06 report by export_intro_arch.py G9. */
function introHeroHtml(h) {
  if (!h) return '';
  const ex = h.example || {};
  const verdictKo = (v) => (v === 'correct' ? '정답' : v === 'incorrect' ? '오답' : escapeHtml(v || ''));
  const arms = (ex.arms || []).map((a) => `
      <div class="intro-hero-arm ${a.verdict === 'incorrect' ? 'bad' : ''}">
        <div class="intro-hero-arm-k"><span>${a.label || ''}</span><span class="intro-hero-verdict">${verdictKo(a.verdict)}</span></div>
        <div class="intro-hero-ans">${a.answer || ''}</div>
        <ol>${(a.steps || []).map((s) => `<li>${s}</li>`).join('')}</ol>
      </div>`).join('');
  const reasons = (h.reasons || []).map((r) => `<div><b>${r.title || ''}</b>${r.text || ''}</div>`).join('');
  return `
    <section class="intro-hero">
      ${h.eyebrow ? `<p class="intro-hero-eyebrow">${h.eyebrow}</p>` : ''}
      <h1 class="intro-hero-title">${h.title || ''}</h1>
      ${h.sub ? `<p class="intro-hero-sub">${h.sub}</p>` : ''}
      ${ex.question ? `<div class="intro-hero-q"><span class="material-symbols-outlined">chat</span><span>"${ex.question}"</span></div>` : ''}
      ${arms ? `<div class="intro-hero-ba">${arms}</div>` : ''}
      ${h.reasons_title ? `<h2 class="intro-hero-h2">${h.reasons_title}</h2>` : ''}
      ${reasons ? `<div class="intro-hero-reasons">${reasons}</div>` : ''}
      ${h.foot ? `<p class="intro-hero-foot">${h.foot}</p>` : ''}
    </section>`;
}

function introTabHtml(tab, D) {
  const parts = [];
  if (tab.hero) parts.push(introHeroHtml(tab.hero));
  if (tab.id === 'sys') {
    parts.push(`
      <div class="mod-card" style="margin:0 0 18px 0; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; border-left:3px solid var(--gcp-blue);">
        <div style="font-size:12.5px; line-height:1.55; color:var(--text);">
          <strong>비즈니스 사전 정의 &amp; 고객 CQ 합의 프로세스:</strong>
          현업 부서 간 용어·모수·특례 충돌을 먼저 협의·합의(<code>l1.yaml</code>)하고, 이를 검증하는 인수 기준으로서 <strong>CQ(Competency Questions) 20문항</strong>을 도출하여 단일 체계로 평가합니다.
        </div>
        <button type="button" class="gcp-action-btn" style="height:30px; padding:0 12px; font-size:12px; font-weight:600; flex-shrink:0;" onclick="setIntroTab('cq_align')">
          사전 정의 · CQ 합의 매트릭스 보기 ➔
        </button>
      </div>
    `);
  }
  if (tab.lead) parts.push(`<p class="intro-lead">${tab.lead}</p>`);
  if (tab.legend && D.conventions && D.conventions.legend) {
    parts.push(`<p class="intro-legend">${escapeHtml(D.conventions.legend)}</p>`);
  }
  (tab.figures || []).forEach((id) => parts.push(introFigureHtml(D.figures[id])));
  if (tab.toggle && (tab.toggle.options || []).length) {
    const opts = tab.toggle.options;
    const sel = opts.some((o) => o.figure === INTRO_TOGGLE[tab.id]) ? INTRO_TOGGLE[tab.id] : opts[0].figure;
    parts.push(`
      <div class="intro-toggle-wrap" data-toggle-tab="${escapeHtml(tab.id)}">
        <div class="intro-seg" role="group" aria-label="${escapeHtml(tab.toggle.label)}">
          <span>${escapeHtml(tab.toggle.label)}</span>
          ${opts.map((o) => `<button type="button" class="${o.figure === sel ? 'on' : ''}" data-fig-opt="${escapeHtml(o.figure)}" onclick="setIntroToggle('${escapeHtml(tab.id)}', '${escapeHtml(o.figure)}')">${escapeHtml(o.label)}</button>`).join('')}
        </div>
        <div class="intro-toggle-slot">${introFigureHtml(D.figures[sel])}</div>
      </div>`);
  }
  return parts.join('');
}

function ensureIntroThemeObserver() {
  if (INTRO_THEME_OBSERVER) return;
  let last = introTheme();
  INTRO_THEME_OBSERVER = new MutationObserver(() => {
    const now = introTheme();
    if (now === last) return;
    last = now;
    const box = document.getElementById('module-intro');
    if (box && INTRO_DATA && box.querySelector('[data-mm-fig]')) renderIntroFigures(box);
  });
  INTRO_THEME_OBSERVER.observe(document.body, { attributes: true, attributeFilter: ['class'] });
}

function renderIntroFigures(box) {
  const token = ++INTRO_RENDER_TOKEN;
  // Serialise renders: mermaid.initialize() is global, so a theme switch must not overlap a running render.
  INTRO_RENDER_CHAIN = INTRO_RENDER_CHAIN.then(() => renderIntroFiguresNow(box, token)).catch((err) => {
    console.error('intro render failed', err);
  });
  return INTRO_RENDER_CHAIN;
}

async function renderIntroFiguresNow(box, token) {
  if (token !== INTRO_RENDER_TOKEN) return;
  const D = INTRO_DATA;
  const theme = introTheme();
  const targets = Array.from(box.querySelectorAll('[data-mm-fig]'));
  let mermaid;
  try {
    if (!INTRO_MERMAID) INTRO_MERMAID = import(INTRO_MERMAID_URL).then((mod) => mod.default);
    mermaid = await INTRO_MERMAID;
  } catch (err) {
    INTRO_MERMAID = null;
    targets.forEach((el) => {
      el.innerHTML = `<pre class="intro-err">Mermaid 로드 실패: ${escapeHtml(err && err.message || err)}</pre>`;
      el.dataset.state = 'error';
    });
    box.dataset.introStatus = `error:mermaid-load`;
    return;
  }
  const M = D.conventions.mermaid;
  mermaid.initialize({
    startOnLoad: false, securityLevel: 'strict', theme: 'base', fontFamily: M.font,
    themeVariables: { ...M.theme_variables[theme], fontFamily: M.font },
    flowchart: M.flowchart, sequence: M.sequence,
  });
  let ok = 0;
  const failed = [];
  for (const el of targets) {
    if (token !== INTRO_RENDER_TOKEN) return;
    const fig = D.figures[el.dataset.mmFig];
    const unit = el.dataset.mmPanel ? (fig.panels || []).find((p) => p.id === el.dataset.mmPanel) : fig;
    const unitId = el.dataset.mmPanel || el.dataset.mmFig;
    const projId = typeof ACTIVE_PROJECT !== 'undefined' ? ACTIVE_PROJECT : 'default';
    const key = `${projId}:${theme}:${unitId}`;
    if (!INTRO_SVG_CACHE[key]) {
      const code = unit.flowchart ? `${unit.mermaid.trimEnd()}\n  ${M.class_defs[theme].join('\n  ')}` : unit.mermaid;
      try {
        const { svg } = await mermaid.render(`intro-mm-${++INTRO_SVG_SEQ}`, code);
        INTRO_SVG_CACHE[key] = svg;
      } catch (err) {
        failed.push(unitId);
        el.innerHTML = `<pre class="intro-err">그림 ${escapeHtml(unitId)} 렌더 실패: ${escapeHtml(err && err.message || err)}</pre>`;
        el.dataset.state = 'error';
        console.error('mermaid render failed', unitId, err);
        continue;
      }
    }
    if (token !== INTRO_RENDER_TOKEN) return;
    el.innerHTML = INTRO_SVG_CACHE[key];
    const svgEl = el.querySelector('svg');
    const natural = svgEl && svgEl.viewBox && svgEl.viewBox.baseVal ? svgEl.viewBox.baseVal.width : 0;
    // Shrink to fit, but never below min_scale of the natural width — wider figures scroll horizontally.
    if (natural) svgEl.style.minWidth = `${Math.round(natural * (D.conventions.min_scale || 0.8))}px`;
    el.dataset.state = 'ok';
    ok += 1;
  }
  box.dataset.introStatus = `${failed.length ? 'error' : 'ok'}:${ok}/${targets.length}:${theme}${failed.length ? ':' + failed.join(',') : ''}`;
}

function renderIntroModule() {
  const box = document.getElementById('module-intro');
  if (!box) return;
  ensureIntroThemeObserver();
  if (!INTRO_DATA && !INTRO_DATA_ERR) {
    box.innerHTML = `<div class="intro-body-scroll"><p class="intro-foot">Intro 그림 데이터를 불러오는 중…</p></div>`;
    loadIntroData().then(renderIntroModule);
    return;
  }
  if (!INTRO_DATA) {
    box.innerHTML = `<div class="intro-body-scroll"><pre class="intro-err">${escapeHtml(INTRO_DATA_ERR)} — tools/export_intro_arch.py 를 실행해 okf_veri_web/data/intro_arch.json 을 만드세요.</pre></div>`;
    box.dataset.introStatus = 'error:data';
    return;
  }
  const D = INTRO_DATA;
  const tabs = D.tabs || [];
  if (!tabs.some((t) => t.id === INTRO_TAB)) INTRO_TAB = tabs.length ? tabs[0].id : '';
  const tab = tabs.find((t) => t.id === INTRO_TAB);

  box.innerHTML = `
    <div class="pane-subbar" style="height:46px; padding:0 18px; width:100%; flex-shrink:0;">
      <div style="display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden;">
        <span class="material-symbols-outlined" style="color:var(--gcp-blue); font-size:19px; line-height:1; flex-shrink:0;">space_dashboard</span>
        <span style="font-size:13.5px; font-weight:600; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Intro</span>
      </div>
      <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
        <div class="mgmt-subtab-group">
          ${tabs.map((t) => `
            <button type="button" class="mgmt-subtab-btn ${t.id === INTRO_TAB ? 'active' : ''}" onclick="setIntroTab('${escapeHtml(t.id)}')">${escapeHtml(t.title)}</button>`).join('')}
        </div>
      </div>
    </div>
    <div class="intro-body-scroll">
      <div class="intro-doc" data-tab="${escapeHtml(INTRO_TAB)}">
        ${tab ? introTabHtml(tab, D) : ''}
      </div>
    </div>
  `;
  renderIntroFigures(box);
}

function renderEnrollmentModule(idx) {
  const box = document.getElementById('module-enrollment');
  if (!box || !PROVS.length) return;
  const p = PROVS[idx] || PROVS[0];
  const relPath = p.okf_path.replace(/^\//, '');
  const entryId = relPath.replace(/\.md$/, '');
  const gcsUri = `gs://okf/${relPath}`;

  const aspectPreview = {
    "finance-ontology.us-central1.okf": {
      "data": {
        "okf_type": "Provision",
        "status": "stable",
        "generated": { "by": "process:build_okf/3.0", "at": "2026-09-22T04:00:00Z" },
        "verified": [{ "by": "process:verify_provisions/1.0", "at": "2026-09-22T04:00:00Z" }],
        "sources": [{ "id": "origin_pdf", "resource": `okf://source/un_data/${p.pdf_file}` }],
        "extra": JSON.stringify([
          [["verified", "0", "method"], "source_text_match"],
          [["verified", "0", "checks"], ["P1_body", "P2_heading", "P3_page", "P4_digest"]],
          [["sources", "0", "sha256"], p.pdf_sha256],
          [["content_class"], "authentic"],
          [["section_number"], p.section_number],
          [["source_page"], p.source_page],
          [["source_pages_span"], p.source_pages_span]
        ])
      }
    },
    "dataplex-types.global.overview": {
      "data": {
        "content": p.verbatim_body.slice(0, 280) + (p.verbatim_body.length > 280 ? " ..." : ""),
        "contentType": "MARKDOWN"
      }
    }
  };

  const cliPreview = `gcloud dataplex entries create ${entryId} \\
  --entry-group=okf-catalog \\
  --location=us-central1 \\
  --project=finance-ontology \\
  --entry-type=okf-bundle \\
  --entry-type-location=us-central1 \\
  --entry-type-project=finance-ontology \\
  --entry-source-resource=${gcsUri} \\
  --entry-source-system="Open Knowledge Format" \\
  --entry-source-platform=OKF \\
  --entry-source-display-name="${p.title.replace(/"/g, '\\"')}" \\
  --aspects=/tmp/aspects_${p.concept_id}.json`;

  box.innerHTML = `
    <div class="module-container">
      <div class="mod-hero">
        <div>
          <div class="mod-tag">03 · OKF Enrollment · GCS & Dataplex Knowledge Catalog Pipeline</div>
          <div class="mod-title">OKF v0.2 번들 GCS(<code>gs://okf/</code>) 적재 및 Dataplex Knowledge Catalog 엔트리 등록</div>
          <div class="mod-desc">
            Dataplex의 기본 스토리지 자동 스캔(DATA_DISCOVERY)은 정형 테이블(CSV/Parquet)만 그룹화하므로, 개별 마크다운(<code>.md</code>) 조문 단위의 거버넌스를 위해
            <strong>1 파일 = 1 Catalog Entry (<code>okf-bundle</code>) + <code>okf</code> Aspect(신호층 13개 필드 + 무손실 <code>extra</code>) + <code>overview</code> Aspect(마크다운 본문)</strong> 구조로 명시적 Upsert 등록을 수행합니다.
          </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px; align-items:flex-end; flex-shrink:0;">
          <span class="mod-badge green">GCS Sync: 226 / 226 MD5 Verified</span>
          <span class="mod-badge blue">Catalog Entries: 225 / 225 Active</span>
        </div>
      </div>

      <div class="mod-grid-4">
        <div class="mod-card">
          <div class="mod-card-header"><span class="mod-badge blue">Step 1</span><span class="material-symbols-outlined" style="color:var(--gcp-blue);">inventory_2</span></div>
          <div class="mod-card-title">카탈로그 그릇 3종 생성</div>
          <div style="font-size:12px; color:var(--text-sub); line-height:1.6;">
            • <strong>EntryGroup</strong>: <code>okf-catalog</code><br>
            • <strong>AspectType</strong>: <code>okf</code> (업스트림 <code>okf-aspect.json</code> 13개 필드)<br>
            • <strong>EntryType</strong>: <code>okf-bundle</code> (OKF Document)
          </div>
        </div>
        <div class="mod-card">
          <div class="mod-card-header"><span class="mod-badge blue">Step 2</span><span class="material-symbols-outlined" style="color:var(--gcp-blue);">cloud_sync</span></div>
          <div class="mod-card-title">GCS 마크다운 동기화</div>
          <div style="font-size:12px; color:var(--text-sub); line-height:1.6;">
            • <code>locations.yaml</code>의 <code>okf://bundle/</code>을 <code>gs://okf/</code>로 연결<br>
            • <code>sync_gcs.py</code>로 226개 파일 업로드 후 로컬↔원격 MD5 해시 100% 대조 검증
          </div>
        </div>
        <div class="mod-card">
          <div class="mod-card-header"><span class="mod-badge blue">Step 3</span><span class="material-symbols-outlined" style="color:var(--gcp-blue);">schema</span></div>
          <div class="mod-card-title">Frontmatter 신호층 분리 매핑</div>
          <div style="font-size:12px; color:var(--text-sub); line-height:1.6;">
            • <code>title, description</code> ➔ 엔트리 본체<br>
            • <code>generated, verified, status, sources</code> ➔ <code>okf</code> Aspect<br>
            • <code>sha256, section_number, source_page</code> ➔ <code>okf.extra</code> 무손실 직렬화
          </div>
        </div>
        <div class="mod-card">
          <div class="mod-card-header"><span class="mod-badge green">Step 4</span><span class="material-symbols-outlined" style="color:var(--gcp-green);">published_with_changes</span></div>
          <div class="mod-card-title">225개 엔트리 병렬 Upsert</div>
          <div style="font-size:12px; color:var(--text-sub); line-height:1.6;">
            • <code>push_catalog.py</code>로 최초 생성 시 <code>entries create</code> 실행<br>
            • 재적재(<code>ALREADY_EXISTS</code>) 시 <code>entries update --update-aspects</code>로 무중단 갱신
          </div>
        </div>
      </div>

      <div class="mod-card">
        <div class="mod-card-header">
          <div class="mod-card-title">
            <span class="material-symbols-outlined" style="color:var(--gcp-blue);">terminal</span>
            조문별 Dataplex Knowledge Catalog 등록 명령어 및 <code>--aspects</code> 페이로드 인스펙터
          </div>
          <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-size:12px; color:var(--text-sub);">검토할 OKF 조문 선택:</span>
            <select class="gcp-select" style="width:360px;" onchange="CURRENT_IDX=Number(this.value); renderEnrollmentModule(CURRENT_IDX); saveUiState();">
              ${PROVS.map((item, i) => `<option value="${i}" ${i === idx ? 'selected' : ''}>[${escapeHtml(item.section_number)}] ${escapeHtml(item.title.slice(0, 38))}</option>`).join('')}
            </select>
            <button class="gcp-action-btn" style="padding:6px 12px;" onclick="switchModule('okf-validation'); selectItem(CURRENT_IDX);">
              <span class="material-symbols-outlined">open_in_new</span> 02 · 원문 대조뷰에서 보기
            </button>
          </div>
        </div>

        <div class="mod-grid-2" style="margin-top:6px;">
          <div>
            <div class="section-label"><span>1. Dataplex CLI Command (push_catalog.py)</span><span>Upsert Ready</span></div>
            <div class="frontmatter-block" style="border:1px solid var(--border); border-radius:6px;">${escapeHtml(cliPreview)}</div>
          </div>
          <div>
            <div class="section-label"><span>2. Generated --aspects JSON Payload (okf + overview)</span><span>Lossless Round-Trip</span></div>
            <div class="frontmatter-block" style="border:1px solid var(--border); border-radius:6px; max-height:310px; overflow-y:auto;">${escapeHtml(JSON.stringify(aspectPreview, null, 2))}</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// Module 05 (05 · agent) is implemented in okf_veri_web/js/mod-agent.js (renderAgentModule).

// Module 06 (06 · rag-vs-graphrag) is implemented in okf_veri_web/js/mod-benchmark.js (renderBenchmarkModule).
