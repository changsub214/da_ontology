// ============================================================================
// Module 06 (06 · rag-vs-graphrag): Live 2-Agent Split View & Static EQ Report
//   - Default mode ('live'): Left EQ 20 sidebar + 50/50 split live chat
//     (Vector RAG Agent on left, GraphRAG Agent on right) + shared bottom
//     composer calling /api/rag/chat/stream and /api/agent/chat/stream in parallel.
//   - Report mode ('report', top-right toggle): Static 20-EQ evaluation report
//     loaded from okf_veri_web/data/eq_compare.json (verdicts, wrong-span
//     highlights, OOD rule badges, protocol/ADR disclosure).
// ============================================================================

let BENCH_INITIALIZED = false;
let BENCH_DATA = null;
let BENCH_LOADING_ERROR = null;
let BENCH_MODE = "live"; // 'live' | 'report'
let BENCH_SELECTED_IDX = 0;
let BENCH_REPORT_FILTER = "all"; // 'all' | 'diff' | 'ood'
let BENCH_IS_SENDING = false;
let BENCH_LIVE_TURNS = [];

let BENCH_EQ_TITLES = {
  EQ01: "숙박업(H) 증액 여신 최소 충당금 산정",
  EQ02: "우선변제자산 인정 시 고정 여신 충당금 경감",
  EQ03: "18일 연체 계좌 건전성 분류 및 조기경보 대상",
  EQ04: "여신관리팀 EWS 연체율과 금감원 공시 연체율 비교",
  EQ05: "신용등급 상승 동반 금리인하요구 승인 적정성",
  EQ06: "요주의 여신 충당금 2% 적용 가부 (업권 구분)",
  EQ07: "보증비율 85% 상향 시 기한이익상실 유예 요건",
  EQ08: "건설업(F) 기업여신 PF 충당금 기준 적용 가부",
  EQ09: "국내 은행그룹 대손충당금 적립률이 해외보다 높은 이유",
  EQ10: "제7차 은행권 TF 금리산정체계 주요 논의 사항",
  EQ11: "거액익스포져 한도 규제 유예·제외 대상 은행",
  EQ12: "국회입법조사처 보고서상 4대 은행 이자순수익 증가폭",
  EQ13: "저축은행 건전성 규제 강화 시 업계 자율방안 기각 사유",
  EQ14: "금리인하요구권 개선방안 도입 전 소비자 측면 문제점",
  EQ15: "자산건전성 분류상 '요주의' 연체기간 기준",
  EQ16: "기한이익 상실 대출의 연체기간 기산일",
  EQ17: "시스템적 중요 은행(D-SIB) 거액익스포져 한도",
  EQ18: "부동산업(L) 차주 대출 잔액 합계",
  EQ19: "대출금리 모범규준 개선방안상 대출금리 구성 항목",
  EQ20: "기업여신 기한이익상실 예정 통지 연체일수 기준"
};
const FINANCE_BENCH_EQ_TITLES = BENCH_EQ_TITLES;

let BENCH_DOC_NAMES = {
  "01": "은행업감독규정",
  "02": "감독규정 별표3",
  "03": "감독규정 규제영향분석서",
  "04": "거액익스포져 개정예고",
  "05": "대출금리 산정체계 개선방안",
  "06": "제7차 금리산정체계 정비방향",
  "07": "NARS 금리산정 정책동향",
  "08": "KIF 대손충당금 적립률 비교",
  "09": "상호저축은행 감독규정(대조군)",
  "10": "별빛은행 여신·금리 내규"
};
const FINANCE_BENCH_DOC_NAMES = BENCH_DOC_NAMES;

function formatBenchCqId(rawId) {
  return String(rawId || "").replace(/^EQ/i, "CQ");
}

function openIntroCqAlignmentTab() {
  if (typeof INTRO_TAB !== "undefined") INTRO_TAB = "cq_align";
  if (typeof switchModule === "function") {
    switchModule("intro");
  }
  if (typeof setIntroTab === "function") {
    setIntroTab("cq_align");
  }
}

function getBenchmarkPreAgreementMeta(rawId) {
  const num = parseInt(String(rawId || "").replace(/\D+/g, ""), 10) || 1;
  const isEcom = typeof ACTIVE_PROJECT !== "undefined" && ACTIVE_PROJECT === "ecommerce-ontology";
  if (isEcom) {
    if ([1, 3, 5, 14].includes(num)) {
      return {
        agrId: "AGR-01",
        context: "CRM_GROWTH × MD_MERCHANDISING",
        rule: "프로모션 내규 제4조 본칙(마진 25% 하한) vs 단서 특례(입고 90일+ 체화재고 & CampaignException=APPROVED 시 10% 하한 완화)",
        edges: "HAS_EXCEPTION_PROVISO · STOCKED_AT_INVENTORY · HAS_CAMPAIGN_EXCEPTION"
      };
    }
    if ([2, 11, 15].includes(num)) {
      return {
        agrId: "AGR-02",
        context: "LEGAL_COMPLIANCE × CRM_GROWTH",
        rule: "개인정보위 행태정보 가이드라인 제3조 마케팅 수신 미동의(marketing_opt_in=FALSE) 타겟팅 즉시 차단 및 품절 대체상품 재고 검증",
        edges: "PERFORMED_BY_CUSTOMER · SUBSTITUTED_BY_PRODUCT · INVOKES_PROVISION"
      };
    }
    if ([4, 9, 18].includes(num)) {
      return {
        agrId: "AGR-03",
        context: "MD_MERCHANDISING vs CX_CS_SUPPORT",
        rule: "동일 주문품목 원장(21건)에 대해 부서 맥락별 심사 모수 분리 합의 (MD 쿠폰할인 6건 vs CS 반품심사 3건)",
        edges: "SCOPES_PORTFOLIO · INVOKES_PROVISION"
      };
    }
    if ([6, 8, 10, 16].includes(num)) {
      return {
        agrId: "AGR-04",
        context: "PARTNER_SETTLEMENT × LEGAL_COMPLIANCE",
        rule: "대규모유통업법 제11조제4항 50% 판촉비 분담 상한 캡 우선 적용 vs 제11조제5항 자발적·차별화 단독행사(APR-7004 ACTIVE) 70% 특례 인정",
        edges: "SUPPLIED_BY_BRAND · DELEGATES_TO_INTERNAL · HAS_CAMPAIGN_EXCEPTION"
      };
    }
    return {
      agrId: "AGR-05",
      context: "CX_CS_SUPPORT × FULFILLMENT_OPS",
      rule: "전자상거래법 제17조 청약철회(세탁훼손 거절 vs 표시불일치 90일 무상반품), 관세청 해외직구 대조군 배제 및 미구현 스키마(missing_schema_columns) 진단",
      edges: "CONFLICTS_BY_SECTOR · GOVERNED_BY_CRITERIA · missing_schema_columns"
    };
  }

  // Finance (별빛은행)
  if ([1, 2, 8].includes(num)) {
    return {
      agrId: "AGR-01",
      context: "CREDIT_REVIEW (여신심사부)",
      rule: "은행업감독규정 제29조제1항 본칙(정상 0.85%) vs 단서 특례(숙박·음식·건설·도소매·부동산 0.9% 상향) 및 우선변제 담보(Collateral) 차감 특례 연결",
      edges: "BORROWED_BY · HAS_EXCEPTION_PROVISO · HAS_COLLATERAL"
    };
  }
  if ([3, 4, 15, 16, 20].includes(num)) {
    return {
      agrId: "AGR-02",
      context: "RISK_MGMT · COMPLIANCE · COLLECTION_EWS",
      rule: "동일 여신원장(100계좌)에 대해 호출 부서 맥락별 연체율 모수 및 조문 분리 합의 (리스크위원회 1.51% · 금감원 공시 2.26% · EWS 4.00%)",
      edges: "SCOPES_PORTFOLIO · INVOKES_PROVISION · HAS_DELINQUENCY"
    };
  }
  if ([5, 10, 14, 19].includes(num)) {
    return {
      agrId: "AGR-03",
      context: "CREDIT_REVIEW · COMPLIANCE",
      rule: "대출금리 모범규준 본칙과 별빛은행 사내내규(DELEGATES_TO_INTERNAL) 및 기승인 우대금리 특례(ExceptionApproval) 원장 대조 심사",
      edges: "HAS_RATE_CUT_REQUEST · DELEGATES_TO_INTERNAL · HAS_EXCEPTION_APPROVAL"
    };
  }
  if ([6, 7, 11, 13, 17].includes(num)) {
    return {
      agrId: "AGR-04",
      context: "RISK_MGMT · COMPLIANCE",
      rule: "상호저축은행 대조군 규정(요주의 2% ≠ 은행 7%) 배제(CONFLICTS_BY_SECTOR) 및 Knowledge Catalog 유효성 게이트로 폐기 조문 차단",
      edges: "CONFLICTS_BY_SECTOR · EVALUATED_UNDER_PROVISION · KC Gate"
    };
  }
  return {
    agrId: "AGR-05",
    context: "PORTFOLIO_ANALYTICS · GOVERNANCE",
    rule: "조문 불필요 순수 원장 집계(LEDGER_ONLY), 거시 정책 문헌 비교 및 미구현 스키마(missing_schema_columns)/도메인 외 질의 방어",
    edges: "GOVERNED_BY_CRITERIA · missing_schema_columns"
  };
}

function getBenchmarkEqTitle(q) {
  if (!q) return "";
  return BENCH_EQ_TITLES[q.id] || q.title || q.question || "";
}

async function ensureBenchmarkDataLoaded() {
  if (BENCH_DATA) return BENCH_DATA;
  try {
    const projMeta = (typeof PROJECT_REGISTRY !== "undefined" && typeof ACTIVE_PROJECT !== "undefined")
      ? PROJECT_REGISTRY[ACTIVE_PROJECT]
      : null;
    const url = (projMeta && projMeta.eqCompareUrl) || "data/eq_compare.json";
    const resp = await fetch(`${url}?v=${Date.now()}`, { cache: "no-store" });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status} (${resp.statusText})`);
    }
    BENCH_DATA = await resp.json();
    BENCH_LOADING_ERROR = null;
    return BENCH_DATA;
  } catch (err) {
    BENCH_LOADING_ERROR = err ? String(err.message || err) : "eq_compare.json 로드 실패";
    return null;
  }
}

function isEqDiff(q) {
  if (!q) return false;
  const gv = ((q.graphrag || {}).judge || {}).verdict;
  const rv = ((q.rag || {}).judge || {}).verdict;
  return gv !== rv;
}

function isEqOodRule(q) {
  if (!q) return false;
  return ((q.graphrag || {}).judge || {}).rule === "out_of_domain" ||
    ((q.rag || {}).judge || {}).rule === "out_of_domain";
}

function renderBenchmarkModule(scenIdx = 0) {
  const box = document.getElementById("module-benchmark");
  if (!box) return;
  const isEcom = typeof ACTIVE_PROJECT !== "undefined" && ACTIVE_PROJECT === "ecommerce-ontology";

  if (typeof scenIdx === "number" && scenIdx >= 0 && (!BENCH_DATA || scenIdx < (BENCH_DATA.questions || []).length)) {
    BENCH_SELECTED_IDX = scenIdx;
  }

  if (!BENCH_INITIALIZED || !document.getElementById("bench-main-pane")) {
    box.innerHTML = `
      <!-- Top Full-Width Subbar (Zero shift when toggling Live vs Report) -->
      <div class="pane-subbar" style="height:46px; padding:0 18px; flex-shrink:0;">
        <div style="display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden;">
          <span class="material-symbols-outlined" style="color:var(--gcp-blue); font-size:19px; line-height:1; flex-shrink:0;">compare_arrows</span>
          <span style="font-size:13.5px; font-weight:600; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            CQ 평가 스튜디오 (RAG vs Graph)
          </span>
          <button
            type="button"
            class="agent-neutral-pill"
            style="cursor:pointer; font-size:11px; color:var(--gcp-blue); border-color:rgba(26,115,232,0.35); flex-shrink:0;"
            onclick="openIntroCqAlignmentTab()"
            title="01 · Intro 사전 정의 · 고객 CQ 합의 매트릭스 보기"
          >
            사전 정의 · CQ 합의 매트릭스 ↗
          </button>
        </div>
        <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
          <div class="mgmt-subtab-group">
            <button
              type="button"
              class="mgmt-subtab-btn active"
              id="bench-mode-btn-live"
              onclick="switchBenchmarkMode('live')"
            >
              라이브 질의
            </button>
            <button
              type="button"
              class="mgmt-subtab-btn"
              id="bench-mode-btn-report"
              onclick="switchBenchmarkMode('report')"
            >
              CQ 평가 리포트
            </button>
          </div>
        </div>
      </div>

      <!-- Body Row: Left Sidebar (Live mode only) + Main Pane -->
      <div class="bench-body-row">
        <aside class="agent-nav-sidebar" id="bench-sidebar">
          <div class="agent-sidebar-header">
            <div class="graph-sidebar-title" id="bench-sidebar-title">${isEcom ? "CQ 20 커머스 사전 합의 질의 목록" : "CQ 20 사전 합의 역량 질의 목록"}</div>
            <div class="graph-sidebar-sub" id="bench-sidebar-sub">
              고객과 사전 합의한 비즈니스 규칙(l1.yaml)에서 도출된 핵심 역량 질문(CQ)입니다. 클릭 후 Enter 시 두 에이전트를 동시 평가합니다.
            </div>
          </div>
          <div class="search-wrap">
            <input
              type="text"
              id="bench-q-search"
              class="search-input"
              placeholder="${isEcom ? "CQ 검색 (CQ01, AGR-01, 마진, 품절, 분담금)..." : "CQ 검색 (CQ01, AGR-01, 충당금, 연체율, 금리인하)..."}"
              oninput="renderBenchmarkSidebarList()"
            />
          </div>
          <div class="nav-list" id="bench-q-list"></div>
        </aside>

        <section class="bench-main-pane" id="bench-main-pane">
          <!-- Mode A: Live 2-Agent Split View (Default) -->
          <div id="bench-live-wrap" style="flex:1; display:flex; flex-direction:column; min-height:0; min-width:0; overflow:hidden;">
            <div class="bench-split-grid">
              <!-- Left Arm: Vector RAG Agent -->
              <div class="bench-arm-col">
                <div class="bench-arm-header">
                  <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Vector RAG Agent</span>
                </div>
                <div class="bench-arm-messages" id="bench-rag-messages"></div>
              </div>

              <!-- Right Arm: Graph Agent -->
              <div class="bench-arm-col">
                <div class="bench-arm-header">
                  <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Graph Agent</span>
                </div>
                <div class="bench-arm-messages" id="bench-graphrag-messages"></div>
              </div>
            </div>

            <div class="agent-chat-input-bar">
              <div class="agent-composer-card">
                <textarea
                  id="bench-chat-input"
                  class="agent-chat-textarea"
                  rows="2"
                  placeholder="${isEcom ? "좌측 목록(CQ01 ~ CQ20)에서 질문을 클릭하거나 평가 질의를 입력하세요..." : "좌측 목록(CQ01 ~ CQ20)에서 질문을 클릭하거나 평가 질의를 입력하세요 (Enter: 두 에이전트 동시 호출, Shift+Enter: 줄바꿈)..."}"
                  onkeydown="handleBenchmarkInputKeydown(event)"
                  oninput="autoResizeAgentTextarea(this)"
                ></textarea>
                <div class="agent-composer-footer" style="justify-content:space-between; gap:10px;">
                  <span style="font-size:11.5px; color:var(--text-sub);">
                    동일 질문을 좌측 <code>Vector RAG Agent</code>와 우측 <code>Graph Agent</code>에 동시 전송합니다.
                  </span>
                  <div style="display:inline-flex; align-items:center; gap:8px; flex-shrink:0;">
                    <button
                      type="button"
                      id="bench-reset-btn"
                      class="agent-reset-icon-btn"
                      onclick="resetBenchmarkLiveChat()"
                      aria-label="초기화"
                    >
                      <span class="material-symbols-outlined">restart_alt</span>
                      <span class="composer-icon-tooltip">초기화</span>
                    </button>
                    <button id="bench-send-btn" class="agent-send-btn" onclick="sendBenchmarkLiveChat()" title="두 에이전트에 동시 전송 (Enter)">
                      <span class="material-symbols-outlined">arrow_upward</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Mode B: Full-Width Static EQ Comparison Report -->
          <div id="bench-report-wrap" class="bench-report-scroll" style="display:none;"></div>
        </section>
      </div>
    `;

    BENCH_INITIALIZED = true;
    renderBenchmarkWelcomeMessages();
  } else {
    const sbTitle = document.getElementById("bench-sidebar-title");
    if (sbTitle) sbTitle.textContent = isEcom ? "CQ 20 커머스 사전 합의 질의 목록" : "CQ 20 사전 합의 역량 질의 목록";
  }

  const sidebar = document.getElementById("bench-sidebar");
  const btnLive = document.getElementById("bench-mode-btn-live");
  const btnReport = document.getElementById("bench-mode-btn-report");
  const liveWrap = document.getElementById("bench-live-wrap");
  const reportWrap = document.getElementById("bench-report-wrap");
  if (sidebar) sidebar.style.display = BENCH_MODE === "live" ? "flex" : "none";
  if (btnLive) btnLive.classList.toggle("active", BENCH_MODE === "live");
  if (btnReport) btnReport.classList.toggle("active", BENCH_MODE === "report");
  if (liveWrap) liveWrap.style.display = BENCH_MODE === "live" ? "flex" : "none";
  if (reportWrap) reportWrap.style.display = BENCH_MODE === "report" ? "flex" : "none";

  ensureBenchmarkDataLoaded().then(() => {
    renderBenchmarkSidebarList();
    if (BENCH_DATA && BENCH_DATA.questions && BENCH_DATA.questions[BENCH_SELECTED_IDX]) {
      const inputEl = document.getElementById("bench-chat-input");
      if (inputEl && !inputEl.value.trim() && BENCH_LIVE_TURNS.length === 0) {
        inputEl.value = BENCH_DATA.questions[BENCH_SELECTED_IDX].question;
        autoResizeAgentTextarea(inputEl);
      }
    }
    if (BENCH_MODE === "report") {
      renderBenchmarkReportView();
    }
  });
}

function switchBenchmarkMode(mode) {
  BENCH_MODE = mode === "report" ? "report" : "live";
  const sidebar = document.getElementById("bench-sidebar");
  const btnLive = document.getElementById("bench-mode-btn-live");
  const btnReport = document.getElementById("bench-mode-btn-report");
  const liveWrap = document.getElementById("bench-live-wrap");
  const reportWrap = document.getElementById("bench-report-wrap");

  if (sidebar) sidebar.style.display = BENCH_MODE === "live" ? "flex" : "none";
  if (btnLive) btnLive.classList.toggle("active", BENCH_MODE === "live");
  if (btnReport) btnReport.classList.toggle("active", BENCH_MODE === "report");
  if (liveWrap) liveWrap.style.display = BENCH_MODE === "live" ? "flex" : "none";
  if (reportWrap) reportWrap.style.display = BENCH_MODE === "report" ? "flex" : "none";

  renderBenchmarkSidebarList();
  if (BENCH_MODE === "report") {
    renderBenchmarkReportView();
  }
  if (typeof saveUiState === "function") saveUiState();
}

function matchesReportFilter(q, filterKey) {
  if (!q) return false;
  if (filterKey === "diff") return isEqDiff(q) && !isEqOodRule(q);
  if (filterKey === "ood") return isEqOodRule(q);
  return true;
}

function setBenchmarkReportFilter(filterKey) {
  BENCH_REPORT_FILTER = filterKey;
  if (BENCH_DATA && Array.isArray(BENCH_DATA.questions)) {
    const currentQ = BENCH_DATA.questions[BENCH_SELECTED_IDX];
    if (!matchesReportFilter(currentQ, filterKey)) {
      const firstIdx = BENCH_DATA.questions.findIndex(q => matchesReportFilter(q, filterKey));
      if (firstIdx >= 0) {
        BENCH_SELECTED_IDX = firstIdx;
      }
    }
  }
  renderBenchmarkReportView();
  if (typeof saveUiState === "function") saveUiState();
}

function renderBenchmarkSidebarList() {
  const listEl = document.getElementById("bench-q-list");
  if (!listEl) return;
  if (!BENCH_DATA || !BENCH_DATA.questions) {
    listEl.innerHTML = `<div style="padding:18px 12px; font-size:12px; color:var(--text-sub); text-align:center;">${escapeHtml(BENCH_LOADING_ERROR || "EQ 목록을 불러오는 중입니다…")}</div>`;
    return;
  }

  const searchEl = document.getElementById("bench-q-search");
  const qFilter = (searchEl ? searchEl.value : "").trim().toLowerCase();

  const html = BENCH_DATA.questions.map((q, idx) => {
    const ood = isEqOodRule(q);
    const diff = isEqDiff(q);
    const statusLabel = ood ? "범위 규칙" : (diff ? "결과 갈림" : "");
    const shortTitle = getBenchmarkEqTitle(q);
    const cqId = formatBenchCqId(q.id);
    const agr = getBenchmarkPreAgreementMeta(q.id);
    const hay = `${cqId} ${q.id} ${agr.agrId} ${agr.context} ${shortTitle} ${statusLabel} ${q.question} ${q.gold_answer || ""}`.toLowerCase();
    if (qFilter && !hay.includes(qFilter)) return "";

    const isActive = idx === BENCH_SELECTED_IDX;
    const rightSlot = `<span class="nav-page">${escapeHtml(agr.agrId)}${statusLabel ? ` · ${escapeHtml(statusLabel)}` : ""}</span>`;

    return `
      <div class="nav-item ${isActive ? "active" : ""}" id="bench-q-item-${idx}" onclick="selectBenchmarkQuestion(${idx}, true)">
        <div class="nav-item-top">
          <span class="nav-item-title">${escapeHtml(cqId)} · ${escapeHtml(shortTitle)}</span>
          ${rightSlot}
        </div>
        <div class="nav-item-sub">${escapeHtml(q.question)}</div>
      </div>
    `;
  }).join("");

  listEl.innerHTML = html || `<div style="padding:18px 12px; font-size:12px; color:var(--text-sub); text-align:center;">조건에 맞는 문항이 없습니다.</div>`;
}

function selectBenchmarkQuestion(idx, focusInput = true) {
  if (!BENCH_DATA || !BENCH_DATA.questions) return;
  if (idx < 0 || idx >= BENCH_DATA.questions.length) return;
  BENCH_SELECTED_IDX = idx;
  SELECTED_SCEN_IDX = idx;
  const q = BENCH_DATA.questions[idx];

  const listEl = document.getElementById("bench-q-list");
  if (listEl) {
    listEl.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  }
  const activeEl = document.getElementById(`bench-q-item-${idx}`);
  if (activeEl) activeEl.classList.add("active");

  if (BENCH_MODE === "live") {
    const inputEl = document.getElementById("bench-chat-input");
    if (inputEl) {
      inputEl.value = q.question;
      autoResizeAgentTextarea(inputEl);
      if (focusInput) inputEl.focus();
    }
  } else {
    renderBenchmarkReportView();
  }
  if (typeof saveUiState === "function") saveUiState();
}

function stepBenchmarkReportQuestion(delta) {
  if (!BENCH_DATA || !Array.isArray(BENCH_DATA.questions)) return;
  const indices = BENCH_DATA.questions
    .map((q, i) => ({ q, i }))
    .filter(({ q }) => matchesReportFilter(q, BENCH_REPORT_FILTER))
    .map(({ i }) => i);
  if (!indices.length) return;
  const curPos = indices.indexOf(BENCH_SELECTED_IDX);
  const nextPos = curPos < 0 ? 0 : (curPos + delta + indices.length) % indices.length;
  selectBenchmarkQuestion(indices[nextPos], false);
}

function jumpToBenchmarkLiveWithQuestion(idx) {
  if (!BENCH_DATA || !BENCH_DATA.questions || !BENCH_DATA.questions[idx]) return;
  BENCH_SELECTED_IDX = idx;
  switchBenchmarkMode("live");
  const inputEl = document.getElementById("bench-chat-input");
  if (inputEl) {
    inputEl.value = BENCH_DATA.questions[idx].question;
    autoResizeAgentTextarea(inputEl);
    inputEl.focus();
  }
}

function renderBenchmarkWelcomeMessages() {
  const ragBox = document.getElementById("bench-rag-messages");
  const graphBox = document.getElementById("bench-graphrag-messages");
  const isEcom = typeof ACTIVE_PROJECT !== "undefined" && ACTIVE_PROJECT === "ecommerce-ontology";
  if (ragBox) {
    ragBox.innerHTML = `
      <div class="agent-msg-row msg-agent">
        <div class="msg-agent-bubble">
          <div class="msg-agent-topbar">
            <div class="msg-agent-meta-left">
              <span class="agent-neutral-pill">Vector RAG Agent</span>
            </div>
          </div>
          <div class="agent-md-body">
            <h3>${isEcom ? "K마켙 VectorDB 기반 커머스 마진·재고·캠페인 에이전트" : "별빛은행 VectorDB 기반 금융 심사·리스크·준법 에이전트"}</h3>
            <ul>
              <li><strong>Step 1 · <code>vertex_rag_search</code>:</strong> 원본 PDF 10종을 RAG Engine 대상으로 하여 상위 ${isEcom ? "3" : "8"}개 청크를 검색합니다. (chunk 512 / overlap 100)</li>
              <li><strong>Step 2 · <code>execute_sql</code>:</strong> 스키마 참조하여 SQL 실행합니다.</li>
              <li><strong>Step 3 · <code>answer_step</code>:</strong> 검색된 청크와 SQL 결과를 조합해 최종 답변을 작성합니다.</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }
  if (graphBox) {
    graphBox.innerHTML = `
      <div class="agent-msg-row msg-agent">
        <div class="msg-agent-bubble">
          <div class="msg-agent-topbar">
            <div class="msg-agent-meta-left">
              <span class="agent-neutral-pill">Graph Agent</span>
            </div>
          </div>
          <div class="agent-md-body">
            <h3>${isEcom ? "K마켙 온톨로지 기반 커머스 마진·재고·캠페인 에이전트" : "별빛은행 온톨로지 기반 금융 심사·리스크·준법 에이전트"}</h3>
            <ul>
              <li><strong>Step 0 · 엔티티 사전 그라운딩:</strong> <code>ont_entity_aliases</code> 최장일치 매칭 및 Knowledge Catalog 클래스 앵커 바인딩</li>
              <li><strong>Step 1 · 통합 GQL 탐색 및 Dry-Run 검증:</strong> 정적·Dry-Run 검증 및 Cloud Spanner Data Boost 실시간 원장 결합</li>
              <li><strong>Step 2 · Dataplex Knowledge Catalog 유효성 게이트:</strong> <code>okf</code> Aspect 실시간 조회 (<code>stable/verified ➔ ALLOW</code>, <code>deprecated ➔ SUPERSEDED_RESOLVED / BLOCKED_DEPRECATED</code>)</li>
              <li><strong>Step 3 · BigQuery ObjectRef 서명 URL 원문 인출:</strong> <code>OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')</code>로 GCS 마크다운 정본 인출 및 SHA-256 무결성 검증</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }
}

function resetBenchmarkLiveChat() {
  BENCH_LIVE_TURNS = [];
  renderBenchmarkWelcomeMessages();
  if (BENCH_DATA && BENCH_DATA.questions && BENCH_DATA.questions[BENCH_SELECTED_IDX]) {
    const inputEl = document.getElementById("bench-chat-input");
    if (inputEl) {
      inputEl.value = BENCH_DATA.questions[BENCH_SELECTED_IDX].question;
      autoResizeAgentTextarea(inputEl);
    }
  }
}

function handleBenchmarkInputKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendBenchmarkLiveChat();
  }
}

async function readNdjsonStream(resp, onStage) {
  let data = null;
  if (resp.body && typeof resp.body.getReader === "function") {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const evt = JSON.parse(trimmed);
          if (evt.type === "stage" && evt.text) {
            onStage(evt.text);
          } else if (evt.type === "result" && evt.data) {
            data = evt.data;
          } else if (evt.ok !== undefined) {
            data = evt;
          }
        } catch (_e) {}
      }
    }
    if (!data && buf.trim()) {
      try {
        const evt = JSON.parse(buf.trim());
        data = evt.data || evt;
      } catch (_e) {}
    }
  } else {
    data = await resp.json();
  }
  return data;
}

async function sendBenchmarkLiveChat() {
  if (BENCH_IS_SENDING) return;
  const inputEl = document.getElementById("bench-chat-input");
  const ragBox = document.getElementById("bench-rag-messages");
  const graphBox = document.getElementById("bench-graphrag-messages");
  const sendBtn = document.getElementById("bench-send-btn");
  if (!inputEl || !ragBox || !graphBox) return;

  const questionText = inputEl.value.trim();
  if (!questionText) return;

  inputEl.value = "";
  autoResizeAgentTextarea(inputEl);
  BENCH_IS_SENDING = true;
  if (sendBtn) sendBtn.disabled = true;

  const ts = Date.now();
  const ragStageId = `bench-rag-stage-${ts}`;
  const graphStageId = `bench-graph-stage-${ts}`;

  [
    { box: ragBox, stageId: ragStageId, initText: "원격 RAG 엔진 호출 준비 중..." },
    { box: graphBox, stageId: graphStageId, initText: "엔티티 별칭 및 KC 클래스 앵커를 바인딩하고 있습니다..." }
  ].forEach(({ box, stageId, initText }) => {
    const uRow = document.createElement("div");
    uRow.className = "agent-msg-row msg-user";
    uRow.innerHTML = `<div class="msg-user-bubble">${escapeHtml(questionText)}</div>`;
    box.appendChild(uRow);

    const aRow = document.createElement("div");
    aRow.className = "agent-msg-row msg-agent";
    aRow.id = `${stageId}-row`;
    aRow.innerHTML = `
      <div class="msg-agent-bubble">
        <div class="agent-loading-line">
          <span class="material-symbols-outlined gcp-spin-sync" style="color:var(--gcp-blue); font-size:18px; flex-shrink:0;">sync</span>
          <span id="${stageId}" class="agent-loading-text">${escapeHtml(initText)}</span>
        </div>
      </div>
    `;
    box.appendChild(aRow);
    box.scrollTop = box.scrollHeight;
  });

  const activeProj = typeof ACTIVE_PROJECT !== "undefined" ? ACTIVE_PROJECT : "finance-ontology";

  const runRag = async () => {
    const rowEl = document.getElementById(`${ragStageId}-row`);
    try {
      const resp = await fetch("/api/rag/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: activeProj, question: questionText, stream: true })
      });
      const data = await readNdjsonStream(resp, (txt) => {
        const el = document.getElementById(ragStageId);
        if (el) el.textContent = txt;
      });
      if (!data || !data.ok) {
        throw new Error((data && data.error) || "RAG 에이전트 응답 오류");
      }
      if (rowEl) {
        rowEl.innerHTML = renderLiveRagBubbleHtml(data);
      }
    } catch (err) {
      if (rowEl) {
        rowEl.innerHTML = `
          <div class="msg-agent-bubble blocked-bubble">
            <div class="msg-agent-topbar">
              <div class="msg-agent-meta-left">
                <span class="agent-neutral-pill">Vector RAG Agent</span>
              </div>
            </div>
            <div style="font-size:12.5px; color:var(--gcp-red);">${escapeHtml(String(err.message || err))}</div>
          </div>
        `;
      }
    }
    ragBox.scrollTop = ragBox.scrollHeight;
  };

  const runGraphRag = async () => {
    const rowEl = document.getElementById(`${graphStageId}-row`);
    try {
      const resp = await fetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: activeProj, num: null, question: questionText, stream: true })
      });
      const data = await readNdjsonStream(resp, (txt) => {
        const el = document.getElementById(graphStageId);
        if (el) el.textContent = txt;
      });
      if (!data || !data.ok) {
        throw new Error((data && data.error) || "Graph 에이전트 응답 오류");
      }
      if (rowEl) {
        rowEl.innerHTML = renderLiveGraphRagBubbleHtml(data);
      }
    } catch (err) {
      if (rowEl) {
        rowEl.innerHTML = `
          <div class="msg-agent-bubble blocked-bubble">
            <div class="msg-agent-topbar">
              <div class="msg-agent-meta-left">
                <span class="agent-neutral-pill">Graph Agent</span>
              </div>
            </div>
            <div style="font-size:12.5px; color:var(--gcp-red);">${escapeHtml(String(err.message || err))}</div>
          </div>
        `;
      }
    }
    graphBox.scrollTop = graphBox.scrollHeight;
  };

  try {
    await Promise.allSettled([runRag(), runGraphRag()]);
    BENCH_LIVE_TURNS.push({ question: questionText, at: new Date().toISOString() });
  } finally {
    BENCH_IS_SENDING = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

function renderLiveRagBubbleHtml(data) {
  const chunks = data.rag_chunks || [];
  const docIds = Array.from(new Set(chunks.map(c => c.doc_id).filter(Boolean)));
  const elapsedPart = data.elapsed_s !== undefined ? `, ${data.elapsed_s}초` : "";
  const chunkRows = chunks.map((c, idx) => `
    <tr>
      <td><code>#${idx + 1}</code></td>
      <td><code>${escapeHtml(c.doc_id || "-")}</code></td>
      <td>${typeof c.score === "number" ? c.score.toFixed(3) : "-"}</td>
      <td style="font-size:11.5px; color:var(--text-sub);">${escapeHtml((c.text || "").slice(0, 180))}…</td>
    </tr>
  `).join("");

  return `
    <div class="msg-agent-bubble">
      <div class="msg-agent-topbar">
        <div class="msg-agent-meta-left">
          <span class="agent-neutral-pill">Vector RAG Agent</span>
        </div>
      </div>
      <div class="agent-md-body">
        ${formatBenchmarkMarkdown(data.answer_markdown || "")}
      </div>
      <details class="query-accordion">
        <summary>
          <span>실행 내역 보기 (RAG 검색 쿼리 · 상위 청크 ${chunks.length}건 · 검색 문서: ${escapeHtml(docIds.join(", ") || "없음")} · BigQuery SQL${escapeHtml(elapsedPart)})</span>
          <span class="material-symbols-outlined qa-chevron">expand_more</span>
        </summary>
        <div class="query-accordion-body">
          <div>
            <div class="section-label">
              <span>Step 1 · vertex_rag_search (Vertex AI RAG 코퍼스 상위 ${chunks.length}건 인출)</span>
              <span>검색 문서: ${escapeHtml(docIds.join(", ") || "없음")}</span>
            </div>
            <pre class="query-code-pre" style="margin-bottom:8px;">${escapeHtml(data.rag_query || "(검색 쿼리 없음)")}</pre>
            <div class="agent-table-scroll">
              <table class="mod-table">
                <thead><tr><th>순번</th><th>문서 ID</th><th>유사도</th><th>청크 발췌</th></tr></thead>
                <tbody>${chunkRows || `<tr><td colspan="4">청크 없음</td></tr>`}</tbody>
              </table>
            </div>
          </div>
          <div>
            <div class="section-label">
              <span>Step 2 · execute_sql (BigQuery 관계형 SQL 1회 실행)</span>
              <span>${escapeHtml(data.sql_status || "상태 기록 없음")}</span>
            </div>
            <pre class="query-code-pre">${escapeHtml(data.sql || "(SQL 없음)")}</pre>
          </div>
        </div>
      </details>
    </div>
  `;
}

function renderLiveGraphRagBubbleHtml(data) {
  if (data.conversational_only) {
    return `
      <div class="msg-agent-bubble">
        <div class="msg-agent-topbar">
          <div class="msg-agent-meta-left">
            <span class="agent-neutral-pill">Graph Agent</span>
          </div>
        </div>
        <div class="agent-md-body">
          ${formatBenchmarkMarkdown(data.answer_markdown || "")}
        </div>
      </div>
    `;
  }

  const qa = data.gql_accordion || {};
  const isBlocked = Boolean(data.blocked);

  return `
    <div class="msg-agent-bubble ${isBlocked ? "blocked-bubble" : ""}">
      <div class="msg-agent-topbar">
        <div class="msg-agent-meta-left">
          <span class="agent-neutral-pill">Graph Agent</span>
        </div>
      </div>

      <div class="agent-md-body">
        ${formatBenchmarkMarkdown(data.answer_markdown || "")}
      </div>

      <details class="query-accordion">
        <summary>
          <span>${escapeHtml(qa.title || "실행된 GQL 쿼리 및 경로 분석")}</span>
          <span class="material-symbols-outlined qa-chevron">expand_more</span>
        </summary>
        <div class="query-accordion-body">
          ${renderGraphragStepsHtml(data).html}
        </div>
      </details>
    </div>
  `;
}

// ----------------------------------------------------------------------------
// Markdown + Wrong-Span Highlighting (Sentinel injection before line parsing)
// ----------------------------------------------------------------------------
function formatBenchmarkInlineMd(text) {
  let s = escapeHtml(text);
  const stashed = [];
  const stash = (html) => {
    const token = `\x00STASH${stashed.length}\x00`;
    stashed.push(html);
    return token;
  };
  s = s.replace(/`\[([^\]]+)\]`/g, (_, inner) => {
    return stash(`<span class="agent-cite-pill" style="cursor:default;">[${inner}]</span>`);
  });
  s = s.replace(/`([^`]+)`/g, (_, codeInner) => stash(`<code>${codeInner}</code>`));
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[\s(])_([^_]+)_(?=$|[\s).,!?;:])/g, "$1<em>$2</em>");
  s = s.replace(/\x00STASH(\d+)\x00/g, (_, idx) => stashed[Number(idx)] || "");
  return s;
}

function formatBenchmarkMarkdown(mdText, wrongSpans = []) {
  if (!mdText) return "";
  let raw = String(mdText);

  const validSpans = (wrongSpans || [])
    .map((sp, idx) => ({ ...sp, idx }))
    .filter(sp => sp.found && typeof sp.start === "number" && typeof sp.end === "number" && sp.start >= 0 && sp.end > sp.start && sp.end <= raw.length)
    .sort((a, b) => a.start - b.start);

  const nonOverlapping = [];
  let lastEnd = -1;
  for (const sp of validSpans) {
    if (sp.start >= lastEnd) {
      nonOverlapping.push(sp);
      lastEnd = sp.end;
    }
  }

  for (let i = nonOverlapping.length - 1; i >= 0; i--) {
    const sp = nonOverlapping[i];
    const sTok = `\u0001WSTART${sp.idx}\u0002`;
    const eTok = `\u0001WEND\u0002`;
    const slice = raw.slice(sp.start, sp.end);
    const wrapped = sTok + slice.split("\n").join(`${eTok}\n${sTok}`) + eTok;
    raw = raw.slice(0, sp.start) + wrapped + raw.slice(sp.end);
  }

  const lines = raw.split("\n");
  const out = [];
  let inList = false;
  let inTable = false;
  let tableHeader = [];
  let tableRows = [];

  function flushList() {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  }

  function flushTable() {
    if (inTable) {
      const thHtml = tableHeader.map(h => `<th>${formatBenchmarkInlineMd(h)}</th>`).join("");
      const trHtml = tableRows.map(r => `<tr>${r.map(c => `<td>${formatBenchmarkInlineMd(c)}</td>`).join("")}</tr>`).join("");
      out.push(`<div class="agent-table-scroll"><table class="mod-table"><thead><tr>${thHtml}</tr></thead><tbody>${trHtml}</tbody></table></div>`);
      inTable = false;
      tableHeader = [];
      tableRows = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList();
      const cells = trimmed.slice(1, -1).split("|").map(c => c.trim());
      if (cells.every(c => /^[-:\s]+$/.test(c))) continue;
      if (!inTable) {
        inTable = true;
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    } else {
      flushTable();
    }

    if (!trimmed) {
      flushList();
      continue;
    }

    if (trimmed.startsWith("### ")) {
      flushList();
      out.push(`<h3>${formatBenchmarkInlineMd(trimmed.slice(4))}</h3>`);
    } else if (trimmed.startsWith("#### ")) {
      flushList();
      out.push(`<h4>${formatBenchmarkInlineMd(trimmed.slice(5))}</h4>`);
    } else if (trimmed.startsWith("> ")) {
      flushList();
      out.push(`<blockquote>${formatBenchmarkInlineMd(trimmed.slice(2))}</blockquote>`);
    } else if (trimmed.startsWith("- ")) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${formatBenchmarkInlineMd(trimmed.slice(2))}</li>`);
    } else {
      flushList();
      out.push(`<p>${formatBenchmarkInlineMd(trimmed)}</p>`);
    }
  }
  flushList();
  flushTable();

  let html = out.join("\n");
  html = html.replace(/\u0001WSTART(\d+)\u0002/g, (_, idxStr) => {
    const sp = (wrongSpans || [])[Number(idxStr)] || {};
    const tip = sp.why ? `오답 사유: ${sp.why}` : "오답 스팬";
    return `<mark class="bench-wrong-span" title="${escapeHtml(tip)}">`;
  });
  html = html.replace(/\u0001WEND\u0002/g, "</mark>");
  return html;
}

// ----------------------------------------------------------------------------
// Static EQ 20 Report View (Full-Width 3-Tier Layout · Module 2/3/5 Neutral Theme)
// ----------------------------------------------------------------------------
function selectBenchmarkEqCustomOption(ev, idx) {
  if (ev) ev.stopPropagation();
  const wrap = document.getElementById("bench-eq-custom-select");
  if (wrap) wrap.classList.remove("open");
  selectBenchmarkQuestion(idx, false);
}

function renderBenchmarkReportView() {
  const wrap = document.getElementById("bench-report-wrap");
  if (!wrap) return;
  if (!BENCH_DATA || !BENCH_DATA.questions) {
    wrap.innerHTML = `<div class="mod-card" style="padding:18px;">${escapeHtml(BENCH_LOADING_ERROR || "정적 비교 리포트 데이터를 불러오는 중입니다…")}</div>`;
    return;
  }

  const qs = BENCH_DATA.questions || [];
  const summary = BENCH_DATA.summary || {};
  const total = summary.total || qs.length;
  const gCorrect = (summary.correct || {}).graphrag ?? 0;
  const rCorrect = (summary.correct || {}).rag ?? 0;
  const q = qs[BENCH_SELECTED_IDX] || qs[0];
  const curOod = isEqOodRule(q);
  const curDiff = isEqDiff(q);
  const curStatus = curOod ? "범위 규칙" : (curDiff ? "결과 갈림" : "");
  const curTitle = getBenchmarkEqTitle(q);

  const eqOptionsHtml = qs.map((item, idx) => {
    const isSel = idx === BENCH_SELECTED_IDX;
    const ood = isEqOodRule(item);
    const diff = isEqDiff(item);
    const statusLabel = ood ? "범위 규칙" : (diff ? "결과 갈림" : "");
    const shortTitle = getBenchmarkEqTitle(item);
    const itemCqId = formatBenchCqId(item.id);
    const itemAgr = getBenchmarkPreAgreementMeta(item.id);
    return `
      <div
        class="gcp-custom-select-opt ${isSel ? "selected" : ""}"
        data-idx="${idx}"
        onclick="selectBenchmarkEqCustomOption(event, ${idx})"
      >
        <span style="min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ${escapeHtml(itemCqId)} · ${escapeHtml(shortTitle)}
        </span>
        <span style="display:inline-flex; align-items:center; gap:8px; flex-shrink:0;">
          <span class="nav-page">${escapeHtml(itemAgr.agrId)}${statusLabel ? ` · ${escapeHtml(statusLabel)}` : ""}</span>
          <span class="material-symbols-outlined gcp-opt-check" style="opacity:${isSel ? "1" : "0"};">check</span>
        </span>
      </div>
    `;
  }).join("");

  wrap.innerHTML = `
    <!-- 1. Slim Summary & GCP Custom Select Bar (Module 02/04/05 Neutral Theme) -->
    <div class="mod-card bench-select-card" style="padding:12px 18px;">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:14px; flex-wrap:wrap;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="font-size:13.5px; font-weight:700; color:var(--text);">사전 합의 CQ ${total} 단일 평가 결과</span>
          <span class="agent-neutral-pill">Graph Agent 정답 <strong style="color:var(--text); margin-left:4px;">${gCorrect} / ${total}</strong></span>
          <span class="agent-neutral-pill">Vector RAG Agent 정답 <strong style="color:var(--text); margin-left:4px;">${rCorrect} / ${total}</strong></span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:320px; max-width:540px;">
          <span style="font-size:12px; font-weight:600; color:var(--text-sub); white-space:nowrap;">평가 CQ 선택</span>
          <div class="gcp-custom-select" id="bench-eq-custom-select" style="flex:1; min-width:0;">
            <button type="button" class="gcp-select gcp-custom-select-btn" onclick="toggleGcpCustomSelect(event, this)">
              <span class="gcp-custom-select-val" id="bench-eq-select-val" style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding-right:4px;">
                <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(formatBenchCqId(q.id))} · ${escapeHtml(curTitle)}</span>
                ${curStatus ? `<span class="nav-page" style="flex-shrink:0;">${escapeHtml(curStatus)}</span>` : ""}
              </span>
            </button>
            <div class="gcp-custom-select-menu" id="bench-eq-select-menu" style="max-height:320px;">
              ${eqOptionsHtml}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. Selected Question & Gold Answer Header -->
    ${renderReportQuestionHeaderHtml(q, BENCH_SELECTED_IDX)}

    <!-- 3. Left (Vector RAG Agent) vs Right (Graph Agent) Strict 50:50 Cards -->
    <div class="bench-report-grid">
      ${renderReportArmCardHtml(q, "rag")}
      ${renderReportArmCardHtml(q, "graphrag")}
    </div>
  `;
}

function renderReportQuestionHeaderHtml(q, idx) {
  const ood = isEqOodRule(q);
  const diff = isEqDiff(q);
  const statusLabel = ood ? "범위 규칙" : (diff ? "결과 갈림" : "");
  const shortTitle = getBenchmarkEqTitle(q);
  const cqId = formatBenchCqId(q.id);
  const agr = getBenchmarkPreAgreementMeta(q.id);

  const evHtml = (q.evidence || []).map(ev => {
    const docId = String(ev.doc || "");
    const docName = BENCH_DOC_NAMES[docId] ? ` · ${BENCH_DOC_NAMES[docId]}` : "";
    const pageStr = ev.page !== undefined && ev.page !== null ? ` (p.${ev.page})` : "";
    return `
      <span class="agent-neutral-pill" title="${escapeHtml(ev.quote || "")}">
        문서 ${escapeHtml(docId)}${escapeHtml(docName)}${escapeHtml(pageStr)}
      </span>
    `;
  }).join("");

  return `
    <div class="mod-card" style="padding:14px 18px;">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; min-width:0;">
          <span class="agent-neutral-pill" style="font-weight:700; color:var(--gcp-blue); border-color:rgba(26,115,232,0.35);">${escapeHtml(cqId)}</span>
          <span class="agent-neutral-pill" style="font-weight:600;">${escapeHtml(agr.agrId)} · ${escapeHtml(agr.context)}</span>
          ${statusLabel ? `<span class="agent-neutral-pill">${escapeHtml(statusLabel)}</span>` : ""}
          <span style="font-size:14px; font-weight:700; color:var(--text);">${escapeHtml(shortTitle)}</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
          <button
            type="button"
            class="gcp-action-btn"
            style="height:28px; padding:0 10px; font-size:11.5px; line-height:1;"
            onclick="openIntroCqAlignmentTab()"
          >
            사전 합의 매트릭스
          </button>
          <button
            type="button"
            class="gcp-action-btn"
            style="height:28px; padding:0 12px; font-size:11.5px; line-height:1;"
            onclick="jumpToBenchmarkLiveWithQuestion(${idx})"
          >
            라이브 질의로 실행
          </button>
        </div>
      </div>

      <div style="margin-top:8px; font-size:13.5px; font-weight:600; color:var(--text); line-height:1.5;">
        ${escapeHtml(q.question)}
      </div>

      <div style="margin-top:8px; padding:8px 12px; border-radius:6px; background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--gcp-blue); font-size:12px; line-height:1.5; display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px;">
          <strong>비즈니스 사전 정의 · 고객 합의 기준 (<code>${escapeHtml(agr.agrId)}</code>):</strong> ${escapeHtml(agr.rule)}
        </div>
        <span class="agent-neutral-pill" style="font-family:var(--mono); font-size:11px;">${escapeHtml(agr.edges)}</span>
      </div>

      <div style="margin-top:8px; padding:9px 12px; border-radius:6px; background:var(--code-bg); border:1px solid var(--border); font-size:12.5px; line-height:1.55; display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px;">
          <strong>CQ 인수 평가 정답 기준:</strong> ${escapeHtml(q.gold_answer || "")}
        </div>
        ${evHtml ? `<div style="display:flex; gap:6px; flex-wrap:wrap; flex-shrink:0;">${evHtml}</div>` : ""}
      </div>
    </div>
  `;
}

function renderReportArmCardHtml(q, arm) {
  const isRag = arm === "rag";
  const armObj = q[arm] || {};
  const judge = armObj.judge || {};
  const isPass = judge.verdict === "correct";
  const isOod = judge.rule === "out_of_domain";
  const wrongSpans = judge.wrong_spans || [];
  const missing = judge.missing || [];

  const title = isRag ? "Vector RAG Agent" : "Graph Agent";
  const badgeHtml = isPass
    ? `<span class="agent-neutral-pill" style="color:var(--text); font-weight:600;">${isOod ? "정답 · 범위 규칙" : "정답"}</span>`
    : `<span class="agent-neutral-pill" style="border-color:var(--gcp-red); color:var(--gcp-red); background:var(--surface); font-weight:600;">${isOod ? "오답 · 범위 규칙" : "오답"}</span>`;

  const issueBullets = [
    ...wrongSpans.map(sp => `
      <li>
        <strong>오류 구절:</strong>
        <code style="color:var(--gcp-red); font-weight:600;">"${escapeHtml(sp.quote || "")}"</code>
        ${sp.why ? `— ${escapeHtml(sp.why)}` : ""}
      </li>
    `),
    ...missing.map(m => `
      <li><strong>누락 사항:</strong> ${escapeHtml(m)}</li>
    `)
  ].join("");

  let traceDetailsHtml = "";
  if (isRag) {
    const chunks = armObj.rag_chunks || [];
    const docIds = Array.from(new Set(chunks.map(c => c.doc_id).filter(Boolean)));
    const elapsedPart = armObj.elapsed_s !== undefined ? `, ${armObj.elapsed_s}초` : "";
    const chunkRows = chunks.map((c, idx) => `
      <tr>
        <td><code>#${idx + 1}</code></td>
        <td><code>${escapeHtml(c.doc_id || "-")}</code></td>
        <td>${typeof c.score === "number" ? c.score.toFixed(3) : "-"}</td>
        <td style="font-size:11.5px; color:var(--text-sub);">${escapeHtml((c.text || "").slice(0, 180))}…</td>
      </tr>
    `).join("");

    traceDetailsHtml = `
      <details class="query-accordion">
        <summary>
          <span>실행 내역 보기 (RAG 검색 쿼리 · 상위 청크 ${chunks.length}건 · 검색 문서: ${escapeHtml(docIds.join(", ") || "없음")} · BigQuery SQL${escapeHtml(elapsedPart)})</span>
          <span class="material-symbols-outlined qa-chevron">expand_more</span>
        </summary>
        <div class="query-accordion-body">
          <div>
            <div class="section-label">
              <span>Step 1 · vertex_rag_search (Vertex AI RAG 코퍼스 상위 ${chunks.length}건 인출)</span>
              <span>검색 문서: ${escapeHtml(docIds.join(", ") || "없음")}</span>
            </div>
            <pre class="query-code-pre" style="margin-bottom:8px;">${escapeHtml(armObj.rag_query || "(검색 쿼리 없음)")}</pre>
            <div class="agent-table-scroll">
              <table class="mod-table">
                <thead><tr><th>순번</th><th>문서 ID</th><th>유사도</th><th>청크 발췌</th></tr></thead>
                <tbody>${chunkRows || `<tr><td colspan="4">청크 없음</td></tr>`}</tbody>
              </table>
            </div>
          </div>
          <div>
            <div class="section-label">
              <span>Step 2 · execute_sql (BigQuery 관계형 SQL 1회 실행)</span>
              <span>${escapeHtml(armObj.sql_status || "상태 기록 없음")}</span>
            </div>
            <pre class="query-code-pre">${escapeHtml(armObj.sql || "(SQL 실행 없음)")}</pre>
          </div>
        </div>
      </details>
    `;
  } else {
    // Everything below comes from the recorded run (compare_run.json → eq_compare.json, re-collected 2026-09-29).
    // Values pass through the remote client as strings: "None" / "" mean "not recorded" and are never shown as data.
    const rec = (v) => (v === undefined || v === null || v === "" || v === "None" ? null : v);
    const num = (v) => { const r = rec(v); const n = Number(r); return r === null || Number.isNaN(n) ? null : n; };
    const tr = armObj.trace || {};
    const qa = armObj.gql_accordion || {};
    const fetched = tr.fetched || [];
    const mode = rec(armObj.mode) || rec(tr.mode) || "모드 기록 없음";
    const calls = num(armObj.tool_calls ?? tr.tool_calls_used);
    const callsStr = calls === null ? "도구 호출 수 기록 없음" : `도구 호출 ${calls}회`;
    const elapsedStr = armObj.elapsed_s !== undefined ? `${armObj.elapsed_s}초` : "-";
    const reason = rec(tr.reason);
    const aliasHits = Array.isArray(qa.alias_hits) ? qa.alias_hits : [];

    // Mode decision (engine.py): CQ template score 100 → fixed FULL_GRAPHRAG with the reason
    // "검증된 벤치마크 질의(...) 앵커 매칭"; otherwise `_gemini_plan_turn` returns mode + reason.
    const byTemplate = (reason || "").startsWith("검증된 벤치마크 질의");
    const planBlockHtml = `
      <div>
        <div class="section-label">
          <span>${byTemplate ? "모드 판정 · CQ 템플릿 일치 (점수 100)" : "모드 판정 · _gemini_plan_turn"}</span>
          <span style="white-space:nowrap; flex-shrink:0;">${escapeHtml(mode)} · ${escapeHtml(callsStr)}</span>
        </div>
        <pre class="query-code-pre">${escapeHtml(reason || "(판정 사유 기록 없음)")}</pre>
      </div>`;

    if (mode === "OUT_OF_DOMAIN" || mode === "META_HELP") {
      traceDetailsHtml = `
        <details class="query-accordion">
          <summary>
            <span>${escapeHtml(`실행 내역 보기 (모드 판정 ${mode} · ${callsStr}, ${elapsedStr})`)}</span>
            <span class="material-symbols-outlined qa-chevron">expand_more</span>
          </summary>
          <div class="query-accordion-body">
            ${planBlockHtml}
            <div>
              <div class="section-label"><span>Step 1 – 3 · graph_query · kc_lookup · fetch_provision</span><span>실행 안 함</span></div>
              <pre class="query-code-pre">${escapeHtml(`${mode} 경로는 안내 응답만 돌려주고 도구를 부르지 않습니다 (기록된 tool_calls_used = ${calls === null ? "-" : calls}).`)}</pre>
            </div>
          </div>
        </details>
      `;
    } else {
      const hops = num(qa.hops);
      const maxHops = num(qa.max_hops);
      const dryRunBytes = num(qa.dry_run_bytes);
      const rows = num(tr.gql_row_count);
      // Step 1 loop state (ADR 0016) — shared with Module 05. `bqjob_gql` (engine placeholder, no job id) is
      // never shown as a job; records collected before the loop fall back to job id / gql_repaired.
      const loop = describeGqlLoop(qa, tr);
      const jobId = loop.jobId;
      const hopStr = hops === null ? "hop 기록 없음" : `${hops} Hops${maxHops === null ? "" : ` ≤ max ${maxHops}`}`;
      const aliasBadgesHtml = aliasHits.length > 0
        ? aliasHits.map(h => `<span class="agent-neutral-pill"><code>${escapeHtml(h.surface)}</code> ➔ <code>${escapeHtml(h.entity_class)}:${escapeHtml(h.canonical_id)}</code></span>`).join(" ")
        : `<span class="agent-neutral-pill">사전 바인딩 엔티티 없음 (부서·용어 컨텍스트 직접 진입)</span>`;
      const summaryTitle = mode === "LEDGER_ONLY"
        ? `실행 내역 보기 (LEDGER_ONLY · ${loop.summary} · ${hopStr} · ${callsStr}, ${elapsedStr})`
        : `실행 내역 보기 (${mode} · ${loop.summary} · ${hopStr} · 인출 조문 ${fetched.length}건 · ${callsStr}, ${elapsedStr})`;
      const step1RightStr = loop.executed
        ? `Dry-Run: ${dryRunBytes === null ? "-" : dryRunBytes.toLocaleString()} B · 행 ${rows === null ? "-" : rows}`
        : "Dry-Run 실패 · 실행 안 함";
      const step1LineStr = loop.executed ? `${loop.line} · Job: ${jobId || "기록 없음"}` : loop.line;
      const step1BodyHtml = loop.refused
        ? renderGqlAttemptsHtml(loop.attempts, { open: true, title: `검증에 실패한 GQL ${loop.attempts.filter((a) => a && !a.ok).length}건 (실행 안 함)` })
        : `<pre class="query-code-pre">${escapeHtml(rec(qa.gql_query) || "(GQL 기록 없음)")}</pre>${renderGqlAttemptsHtml(loop.attempts)}`;

      // The engine writes a fixed "KC ALLOW" into step2_right; count the verdicts that step2_log actually records.
      const verdictCounts = {};
      (String(rec(qa.step2_log) || "").match(/verdict=([A-Z_]+)/g) || []).forEach(m => {
        const v = m.slice("verdict=".length);
        verdictCounts[v] = (verdictCounts[v] || 0) + 1;
      });
      const verdictStr = Object.entries(verdictCounts).map(([v, n]) => `${v} ${n}`).join(" · ");
      const step2BlockHtml = rec(qa.step2_log) ? `
        <div>
          <div class="section-label">
            <span>${escapeHtml(rec(qa.step2_label) || "Step 2 · kc_lookup")}</span>
            <span style="white-space:nowrap; flex-shrink:0;">${escapeHtml(verdictStr || "판정 기록 없음")}</span>
          </div>
          <pre class="query-code-pre">${escapeHtml(qa.step2_log)}</pre>
        </div>` : "";

      const step3BlockHtml = rec(qa.step3_log) ? `
        <div>
          <div class="section-label">
            <span>${escapeHtml(rec(qa.step3_label) || "Step 3 · governance_gate ➔ fetch_provision")}</span>
            <span style="white-space:nowrap; flex-shrink:0;">인출 조문 ${fetched.length}건</span>
          </div>
          <pre class="query-code-pre">${escapeHtml(formatStepLogSql(qa.step3_log))}</pre>
        </div>` : (fetched.length > 0 ? `
        <div>
          <div class="section-label">
            <span>Step 3 · governance_gate ➔ fetch_provision</span>
            <span>인출 조문 ${fetched.length}건</span>
          </div>
          <pre class="query-code-pre">${escapeHtml(fetched.join("\n"))}</pre>
        </div>` : "");

      const skippedHtml = loop.refused ? `
        <div>
          <div class="section-label"><span>Step 2 · Step 3 · kc_lookup · fetch_provision</span><span>실행 안 함 (답변 거절)</span></div>
        </div>` : mode === "LEDGER_ONLY" ? `
        <div>
          <div class="section-label"><span>Step 2 · Step 3 · kc_lookup · fetch_provision</span><span>생략 (LEDGER_ONLY)</span></div>
        </div>` : "";

      traceDetailsHtml = `
        <details class="query-accordion">
          <summary>
            <span>${escapeHtml(summaryTitle)}</span>
            <span class="material-symbols-outlined qa-chevron">expand_more</span>
          </summary>
          <div class="query-accordion-body">
            <div>
              <div class="section-label"><span>Step 0 · before_agent_callback (ont_entity_aliases 최장일치 ➔ KC 앵커 바인딩)</span><span>Callback</span></div>
              <div style="display:flex; flex-wrap:wrap; gap:6px;">${aliasBadgesHtml}</div>
            </div>
            ${planBlockHtml}
            <div>
              <div class="section-label" style="margin-bottom:2px;">
                <span>Step 1 · graph_query (ISO/IEC 39075 GQL · Spanner Data Boost 통합 · ${escapeHtml(hopStr)})</span>
                <span style="white-space:nowrap; flex-shrink:0;">${escapeHtml(step1RightStr)}</span>
              </div>
              <div style="font-family:var(--mono); font-size:11px; color:var(--text-sub); margin-bottom:6px;">
                ${escapeHtml(step1LineStr)}
              </div>
              ${step1BodyHtml}
            </div>
            ${step2BlockHtml}
            ${step3BlockHtml}
            ${skippedHtml}
          </div>
        </details>
      `;
    }
  }

  return `
    <div class="mod-card" style="display:flex; flex-direction:column; gap:12px; ${!isPass ? "border-color:var(--gcp-red);" : ""}">
      <div class="mod-card-header" style="margin-bottom:0;">
        <div class="mod-card-title">${escapeHtml(title)}</div>
        ${badgeHtml}
      </div>

      <!-- Unified Verdict Callout (Neutral code-bg, zero neon fill) -->
      <div class="bench-verdict-box ${isPass ? "pass" : "fail"}">
        <div><strong>판정 근거:</strong> ${escapeHtml(judge.reason || "")}</div>
        ${issueBullets ? `
          <ul style="margin:6px 0 0 0; padding:6px 0 0 18px; border-top:1px dashed var(--border); font-size:12px;">
            ${issueBullets}
          </ul>
        ` : ""}
      </div>

      <!-- Answer Body with Wrong Spans Highlighted -->
      <div class="agent-md-body" style="padding:4px 2px;">
        ${formatBenchmarkMarkdown(armObj.answer || "", wrongSpans)}
      </div>

      ${traceDetailsHtml}
    </div>
  `;
}

