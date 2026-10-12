/* ==========================================================================
   okf_veri_web/js/mod-agent.js
   Module 05 (05 · agent): Starlight GraphRAG Agent Studio
   - Left Sidebar: Module 04 title/sub typography + Module 02/03 .nav-item style (01. ~ 21.)
   - Center/Right Wide Chat Studio: 90-8-2 Neutral Grayscale (zero neon fills, strict overflow containment)
   - Click question in sidebar -> populates bottom textarea (Enter or Send dispatches)
   - Agent bubble: Markdown answer on top + single bottom .query-accordion
   - Slide-out Right Evidence Artifact Drawer (KC 유효성 판정 · ObjectRef 원문 · Spanner·BQ 원장)
   ========================================================================== */

/* --------------------------------------------------------------------------
   Step 1 GQL loop display (ADR 0016): validate (static checks + dry-run) → repair ≤ cap → execute once;
   no GQL passes → the turn is refused. Shared by Module 05 (live turns) and Module 06 (recorded runs).
   Records collected before the loop carry no gql_status: a real job id means graph_query ran; the
   engine's `bqjob_gql` placeholder means it never ran (the dry-run failed and the old repair branch
   was unreachable — EQ10 / EQ16 collected 2026-09-29 08:22Z).
   -------------------------------------------------------------------------- */
const GQL_STOP_REASON_KO = {
  max_repairs: (k) => `교정 ${k}회 후에도 검증 실패`,
  repeated_gql: () => "교정이 이미 실패한 GQL 을 다시 내놓아 중단",
  budget_exhausted: () => "도구 호출 한도 초과",
  execute_invalid: () => "실행 직전 재검증 실패",
};

function _gqlRec(v) {
  return v === undefined || v === null || v === "" || v === "None" ? null : v;
}

function _gqlNum(v) {
  const r = _gqlRec(v);
  const n = Number(r);
  return r === null || Number.isNaN(n) ? null : n;
}

function describeGqlLoop(qa, tr) {
  qa = qa || {};
  tr = tr || {};
  const pick = (k) => (_gqlRec(tr[k]) !== null ? tr[k] : qa[k]);
  const rawJob = _gqlRec(qa.job_id);
  const jobId = rawJob && rawJob !== "bqjob_gql" ? String(rawJob) : null;
  const recorded = _gqlRec(pick("gql_status"));
  const status = recorded || (jobId ? "executed" : "not_executed_legacy");
  const rounds = _gqlNum(pick("gql_repair_rounds")) ?? (tr.gql_repaired === true ? 1 : tr.gql_repaired === false ? 0 : null);
  const validations = _gqlNum(pick("gql_validations"));
  const stopReason = _gqlRec(pick("gql_stop_reason"));
  const attempts = Array.isArray(qa.gql_attempts) ? qa.gql_attempts : [];
  const why = stopReason && GQL_STOP_REASON_KO[stopReason] ? GQL_STOP_REASON_KO[stopReason](rounds ?? 0) : (stopReason || "사유 기록 없음");
  const valStr = validations === null ? "" : `검증 ${validations}회 · `;
  let summary, line;
  if (status === "executed") {
    summary = rounds > 0 ? `GQL 1회 (교정 ${rounds}회)` : "GQL 1회";
    if (!recorded) {
      // legacy record: the pre-loop wording, so the cards collected with 0 repairs read exactly as before
      line = tr.gql_repaired === true ? "GQL 교정 1회 (_gemini_repair_gql)" : tr.gql_repaired === false ? "GQL 교정 없음" : "교정 여부 기록 없음";
    } else {
      line = rounds > 0 ? `${valStr}교정 ${rounds}회 · 실행 1회` : "GQL 교정 없음";
    }
  } else if (status === "refused") {
    summary = `GQL 미실행 · 교정 ${rounds ?? 0}회 실패 · 답변 거절`;
    line = `${valStr}교정 ${rounds ?? 0}회 · 실행 0회 · 답변 거절 (${why})`;
  } else {
    summary = "GQL 미실행";
    line = _gqlNum(qa.dry_run_bytes) ? "GQL 미실행 · Job 기록 없음 (수정 전 코드로 수집)"
      : "GQL 미실행 — dry-run 검증 실패 · 교정 미호출 (수정 전 코드로 수집) · 인출 조문은 계획 단계 선택분";
  }
  return {
    status, jobId, rounds, validations, stopReason, why, attempts, summary, line,
    executed: status === "executed",
    refused: status === "refused",
  };
}

function renderGqlAttemptsHtml(attempts, opts = {}) {
  const failed = (attempts || []).filter((a) => a && !a.ok);
  if (!failed.length) return "";
  const kindLabel = (a) => (a.kind === "planner" ? "최초 GQL" : "교정 GQL");
  const items = failed.map((a) => {
    const flag = a.repair_error ? "교정 호출 실패" : a.repeated ? "이전 실패 GQL 반복 → 중단" : "검증 실패";
    const errs = (a.errors || []).map((e) => `<li>${escapeHtml(String(e))}</li>`).join("");
    const hints = (a.hints || []).length ? `<div style="font-size:11px; color:var(--text-sub); margin:2px 0 4px;">힌트: ${escapeHtml(a.hints.join(" · "))}</div>` : "";
    return `
      <div style="margin-top:8px;">
        <div class="section-label" style="margin-bottom:2px;"><span>시도 ${escapeHtml(String(a.n ?? "-"))} · ${kindLabel(a)}</span><span>${flag}</span></div>
        <ul style="margin:2px 0 4px; padding-left:18px; font-size:11.5px;">${errs}</ul>
        ${hints}
        ${a.gql ? `<pre class="query-code-pre">${escapeHtml(a.gql)}</pre>` : ""}
      </div>`;
  }).join("");
  return `
    <details class="gql-attempts" ${opts.open ? "open" : ""} style="margin-top:6px;">
      <summary style="cursor:pointer; font-size:12px; color:var(--text-sub);">${escapeHtml(opts.title || `검증에 실패한 시도 ${failed.length}건 보기`)}</summary>
      ${items}
    </details>`;
}

/* Step logs carry single-line SQL (e.g. fetch_provision `SELECT … FROM … WHERE provision_slot_id IN ('…', …)`).
   Display-only: break clauses and IN-list items onto their own lines; non-SQL lines pass through untouched. */
function formatStepLogSql(log) {
  if (!log) return "";
  return String(log).split("\n").map((line) => {
    const m = line.match(/^(\s*)(SELECT\s.+)$/i);
    if (!m) return line;
    const ind = m[1];
    let sql = m[2]
      .replace(/\s+(FROM|WHERE|GROUP BY|ORDER BY|LIMIT|AND|OR)\s+/g, (_, kw) => `\n${ind}${kw.length <= 3 ? "  " : ""}${kw} `)
      .replace(/^SELECT\s+/i, `SELECT\n${ind}  `);
    sql = sql.replace(/\bIN\s*\(([^()]*)\)/g, (_, list) => {
      const items = list.split(/,\s*(?=')/).map((x) => x.trim()).filter(Boolean);
      return items.length > 1 ? `IN (\n${items.map((x) => `${ind}    ${x}`).join(",\n")}\n${ind}  )` : `IN (${list})`;
    });
    return ind + sql;
  }).join("\n");
}

/* Step 0–3 body of the GraphRAG "실행된 GQL 쿼리 및 경로 분석" accordion for one live turn.
   Shared by Module 05 (agent studio) and Module 06 (live GraphRAG pane) so both read identically. */
function renderGraphragStepsHtml(data) {
  data = data || {};
  const qa = data.gql_accordion || {};
  const loop = describeGqlLoop(qa, data.adk_trace);
  const isRefused = Boolean(data.refused) || loop.refused;

  const aliasBadgesHtml = (qa.alias_hits && qa.alias_hits.length > 0)
    ? qa.alias_hits.map(h => `<span class="agent-neutral-pill"><code>${escapeHtml(h.surface)}</code> ➔ <code>${escapeHtml(h.entity_class)}:${escapeHtml(h.canonical_id)}</code></span>`).join(" ")
    : `<span class="agent-neutral-pill">사전 바인딩 엔티티 없음 (부서·용어 컨텍스트 직접 진입)</span>`;

  const logBlock = (label, right, log) => `
            <div>
              <div class="section-label">
                <span>${escapeHtml(label)}</span>
                <span style="white-space:nowrap; flex-shrink:0;">${escapeHtml(right || "")}</span>
              </div>
              <pre class="query-code-pre">${escapeHtml(formatStepLogSql(log))}</pre>
            </div>`;
  const step2BlockHtml = qa.step2_log
    ? logBlock(qa.step2_label || "Step 2 · kc_lookup (Dataplex Knowledge Catalog 유효성 판정)", qa.step2_right, qa.step2_log) : "";
  const step3BlockHtml = qa.step3_log
    ? logBlock(qa.step3_label || "Step 3 · governance_gate ➔ fetch_provision (OKF 원문 인출)", qa.step3_right, qa.step3_log) : "";
  const refusedSkipHtml = isRefused ? `
            <div>
              <div class="section-label"><span>Step 2 · Step 3 · kc_lookup · fetch_provision</span><span>실행 안 함 (답변 거절)</span></div>
            </div>` : "";

  const step1RightStr = isRefused ? "Dry-Run 실패 · 실행 안 함" : `Dry-Run: ${(qa.dry_run_bytes || 0).toLocaleString()} B`;
  const step1LineStr = isRefused ? loop.line : `${loop.line} · Job: ${loop.jobId || "기록 없음"}`;
  const step1BodyHtml = isRefused
    ? renderGqlAttemptsHtml(loop.attempts, { open: true, title: `검증에 실패한 GQL ${loop.attempts.filter((a) => a && !a.ok).length}건 (실행 안 함)` })
    : `<pre class="query-code-pre">${escapeHtml(qa.gql_query || "")}</pre>${renderGqlAttemptsHtml(loop.attempts)}`;

  const html = `
            <div>
              <div class="section-label"><span>Step 0 · before_agent_callback (ont_entity_aliases 최장일치 ➔ KC 앵커 바인딩)</span><span>Callback</span></div>
              <div style="display:flex; flex-wrap:wrap; gap:6px;">${aliasBadgesHtml}</div>
            </div>
            <div>
              <div class="section-label" style="margin-bottom:2px;">
                <span>Step 1 · graph_query (ISO/IEC 39075 GQL · Spanner Data Boost 통합 · ${qa.hops || 1} Hops ≤ max ${qa.max_hops || 12})</span>
                <span style="white-space:nowrap; flex-shrink:0;">${escapeHtml(step1RightStr)}</span>
              </div>
              <div style="font-family:var(--mono); font-size:11px; color:var(--text-sub); margin-bottom:6px;">
                ${escapeHtml(step1LineStr)}
              </div>
              ${step1BodyHtml}
            </div>
            ${step2BlockHtml}
            ${step3BlockHtml}
            ${refusedSkipHtml}`;
  return { html, loop, isRefused };
}

let AGENT_QUESTIONS = [
  {
    num: "01",
    title: "정상 여신 대손준비금 추가 적립 산정",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "이번 분기 결산에서 '정상' 여신에 대해 대손준비금을 추가로 쌓아야 해? 쌓아야 하면 얼마고, 어느 계좌 때문이야?"
  },
  {
    num: "02",
    title: "고정 여신 법정 최소 충당금 및 과부족",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "'고정'으로 분류된 여신들 법정 최소 충당금이 얼마야? 지금 장부에 쌓인 것과 비교하면 부족해, 남아?"
  },
  {
    num: "03",
    title: "기촉법 워크아웃 우선변제자산 충당금 특례",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "별빛정밀도 기촉법 워크아웃 들어간 우선변제자산이잖아. 그럼 충당금도 절반만 쌓아도 되는 거지?"
  },
  {
    num: "04",
    title: "당행 대손충당금 적립률(Coverage Ratio) 비교",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "우리 은행 대손충당금 적립률(coverage ratio)이 몇 %야? 국내 은행그룹들이랑 비교하면 어느 수준이야?"
  },
  {
    num: "05",
    title: "리스크관리위원회 기업여신 고정이하 비율",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "다음 주 리스크관리위원회에 올릴 기업여신 부실(고정이하) 비율 뽑아줘."
  },
  {
    num: "06",
    title: "금감원 공시 원화대출 연체율 산정 기준",
    dept_id: "DISCLOSURE",
    dept_name: "재무기획부(공시)",
    question: "금감원 공시에 들어갈 원화대출 연체율은 얼마로 나가? 리스크위원회 숫자랑 왜 달라?"
  },
  {
    num: "07",
    title: "여신관리팀 조기경보 실질 연체율 비교",
    dept_id: "CREDIT_MGMT",
    dept_name: "여신관리팀",
    question: "여신관리팀 조기경보 기준으로 실질 연체율 몇 %야? 공시 수치보다 왜 이렇게 높아?"
  },
  {
    num: "08",
    title: "채권재조정 여신 요주의 유지 근거 및 감사 요건",
    dept_id: "CREDIT_REVIEW",
    dept_name: "기업여신심사부",
    question: "별빛정밀 채권재조정 중인데 고정이하로 안 떨어뜨리고 요주의로 둔 근거가 뭐야? 감사 때 문제 없을까?"
  },
  {
    num: "09",
    title: "30일 초과 연체 기업여신 EOD 처리·유예 판정",
    dept_id: "CREDIT_MGMT",
    dept_name: "여신관리팀",
    question: "연체 30일 넘은 기업여신 중에 기한이익상실(EOD) 바로 처리해야 하는 차주랑 유예할 수 있는 차주 나눠줘. 지금 결재 결과가 내규랑 맞아?"
  },
  {
    num: "10",
    title: "보증서 담보 여신 EOD 유예 요건 충족 계좌",
    dept_id: "CREDIT_REVIEW",
    dept_name: "기업여신심사부",
    question: "담보 잡혀 있는 여신 중에 EOD 유예 요건(보증서 기준)을 채우는 건 어느 거야?"
  },
  {
    num: "11",
    title: "상각 특수채권 적법성 및 연체율 모수 포함 여부",
    dept_id: "COMPLIANCE",
    dept_name: "준법감시부",
    question: "상각 처리한 성진해운물류 건은 규정대로 처리된 거야? 그리고 연체율 지표들엔 이게 들어가, 빠져?"
  },
  {
    num: "12",
    title: "특허 취득 사유 금리인하요구 거절 적법성",
    dept_id: "BRANCH",
    dept_name: "영업점(RM)",
    question: "에이펙스세미콘이 특허 땄다고 금리인하요구 했는데 우리가 거절했잖아. 고객이 '특허 취득은 금리인하 사유로 정해져 있다'고 항의하는데, 거절이 맞아? 뭐라고 통보해야 해?"
  },
  {
    num: "13",
    title: "TCB 운전자금 전결 한도 및 부채비율 위반 점검",
    dept_id: "COMPLIANCE",
    dept_name: "준법감시부",
    question: "TCB 기술혁신 운전자금 계약 중에 영업점장 전결 한도를 넘겨서 우대금리를 준 건이나, 부채비율 기준 넘는 차주 있어?"
  },
  {
    num: "14",
    title: "2월 13일 체결 기준 대출 평균 금리 및 주력 상품",
    dept_id: "BRANCH",
    dept_name: "영업점(RM)",
    question: "2월 13일에 나간 대출들 평균 금리가 얼마였고, 제일 많이 팔린 상품은 뭐야?"
  },
  {
    num: "15",
    title: "비교공시용 대출금리 구성(A+B-C) 및 가산금리 규제",
    dept_id: "COMPLIANCE",
    dept_name: "준법감시부",
    question: "은행연합회 비교공시용으로 우리 상품별 대출금리 구성을 정리해줘. 가산금리가 경쟁사보다 낮아 보이게 할 방법도 있어?"
  },
  {
    num: "16",
    title: "정상 여신 충당금 적립률(0.5%·0.85%·1.0%) 구분",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "정상 여신 충당금 적립률이 문서마다 0.5%, 0.85%, 1% 로 다 다르던데, 우리 여신엔 뭘 적용해야 해? 계좌 수로도 나눠줘."
  },
  {
    num: "17",
    title: "회수의문 여신 업권별 충당금 적립률(50% vs 55%)",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "회수의문 여신은 충당금 55% 쌓는 거 맞지? 우리 3개월 넘게 연체된 계좌가 회수의문으로 떨어지면 몇 % 적용돼?"
  },
  {
    num: "18",
    title: "거액익스포져 한도 규제 적용 및 미구비 스키마 점검",
    dept_id: "COMPLIANCE",
    dept_name: "준법감시부",
    question: "거액익스포져 한도 규제 도입됐다던데, 우리 차주 중에 한도에 걸리는 곳 있어?"
  },
  {
    num: "19",
    title: "신규 대출 실적 집계 기준일(신청·체결·실행일) 차이",
    dept_id: "BRANCH",
    dept_name: "영업점(RM)",
    question: "2월 둘째 주(2/9~2/13) 신규 대출 실적이 얼마야? 영업점 보고랑 자금부 집행 숫자가 다르다던데 왜 그래?"
  },
  {
    num: "20",
    title: "채권재조정 여신 1회 미상환 시 건전성·충당금 영향",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "별빛정밀이 다음 달 상환을 한 번 못 하면 어떻게 돼? 충당금이 얼마나 늘어?"
  },
  {
    num: "21",
    title: "폐기된 구버전 감독규정 스냅샷 호출 차단 검증",
    dept_id: "RISK_MGMT",
    dept_name: "리스크관리부",
    question: "과거 폐기된 구버전 감독규정 스냅샷(versions/art_29_allowance_coverage_ratio_v0.2.0)을 기준으로 이번 분기 정상 여신 대손충당금 적립률을 산정해줘."
  }
];
const FINANCE_AGENT_QUESTIONS = AGENT_QUESTIONS;

let AGENT_STUDIO_INITIALIZED = false;
let AGENT_SELECTED_IDX = 0;
let AGENT_SELECTED_NUM = "01";
let AGENT_TURN_HISTORY = [];
let AGENT_ACTIVE_TURN_IDX = -1;
let AGENT_DRAWER_OPEN = false;
let AGENT_DRAWER_TAB = "KC"; // 'KC' | 'PROVISION' | 'LEDGER'
let AGENT_IS_SENDING = false;

function renderAgentModule(scenIdx = 0) {
  const box = document.getElementById("module-agent");
  if (!box) return;
  const isEcom = typeof ACTIVE_PROJECT !== "undefined" && ACTIVE_PROJECT === "ecommerce-ontology";

  if (!AGENT_STUDIO_INITIALIZED || !document.getElementById("agent-chat-messages")) {
    box.innerHTML = `
      <!-- Top Full-Width Subbar (same frame as Module 06 RAG vs Graph Studio) -->
      <div class="pane-subbar" style="height:46px; padding:0 18px; flex-shrink:0;">
        <div style="display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden;">
          <span class="material-symbols-outlined" style="color:var(--gcp-blue); font-size:19px; line-height:1; flex-shrink:0;">smart_toy</span>
          <span id="agent-top-subbar-title" style="font-size:13.5px; font-weight:600; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            ${isEcom ? "K마켙 Graph 커머스 마진·재고·캠페인 에이전트" : "Starlight Graph 금융 심사 에이전트"}
          </span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
          <button type="button" class="gcp-action-btn" style="flex:0 0 auto; height:30px; padding:0 12px; font-size:11.5px; line-height:1;" onclick="toggleAgentArtifactDrawer()">
            <span id="agent-drawer-toggle-lbl">근거 아티팩트 서랍</span>
          </button>
          <button type="button" class="gcp-action-btn" style="flex:0 0 auto; height:30px; padding:0 12px; font-size:11.5px; line-height:1;" onclick="resetAgentChat()">
            초기화
          </button>
        </div>
      </div>

      <!-- Body Row: Left Sidebar + Chat Column + Slide-out Drawer -->
      <div class="bench-body-row">
        <!-- 1. Left Question Sidebar (Module 04 title typography + Module 02/03 .nav-item style) -->
        <aside class="agent-nav-sidebar">
          <div class="agent-sidebar-header">
            <div class="graph-sidebar-title" id="agent-sidebar-title">${isEcom ? "커머스 의사결정 질의 목록" : "금융 심사 질의 목록"}</div>
            <div class="graph-sidebar-sub">
              질문을 클릭하면 하단 입력창에 채워집니다. (Enter 또는 전송 버튼으로 실행)
            </div>
          </div>
          <div class="search-wrap">
            <input type="text" id="agent-q-search" class="search-input" placeholder="${isEcom ? "질문 검색 (번호, 부서, 마진, 품절, 분담금)..." : "질문 검색 (번호, 부서, 충당금, 연체율, 특허)..."}" oninput="renderAgentQuestionList()" />
          </div>
          <div class="nav-list" id="agent-q-list"></div>
        </aside>

        <!-- 2. Chat Column (Module 06 .bench-arm-col frame) -->
        <section class="agent-chat-pane">
          <div class="bench-arm-header">
            <span>Graph Agent</span>
          </div>
          <div class="agent-chat-messages" id="agent-chat-messages"></div>

          <div class="agent-chat-input-bar">
            <div class="agent-composer-card">
              <textarea
                id="agent-chat-input"
                class="agent-chat-textarea"
                rows="2"
                placeholder="좌측 목록(01. ~ 21.)에서 질문을 클릭하거나 ${isEcom ? "커머스 마진·재고·캠페인" : "금융 심사·규정"} 질의를 입력하세요 (Enter 전송, Shift+Enter 줄바꿈)..."
                onkeydown="handleAgentInputKeydown(event)"
                oninput="autoResizeAgentTextarea(this)"
              ></textarea>
              <div class="agent-composer-footer">
                <button id="agent-send-btn" class="agent-send-btn" onclick="sendAgentChatMessage()" title="질의 전송 (Enter)">
                  <span class="material-symbols-outlined">arrow_upward</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- 3. Slide-out Right Evidence Artifact Drawer -->
        <aside id="agent-artifact-drawer">
          <div class="detail-panel-header">
            <div style="display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden;">
              <code id="agent-drawer-title" style="font-family:var(--mono); font-size:12px; font-weight:600; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">근거 아티팩트</code>
            </div>
            <button type="button" class="icon-close-btn" onclick="closeAgentArtifactDrawer()" title="닫기">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="agent-drawer-tabs">
            <div class="mgmt-subtab-group" style="width:100%; display:flex;">
              <button type="button" class="mgmt-subtab-btn active" style="flex:1; justify-content:center;" id="agent-dtab-KC" onclick="switchAgentDrawerTab('KC')">
                KC 유효성 판정
              </button>
              <button type="button" class="mgmt-subtab-btn" style="flex:1; justify-content:center;" id="agent-dtab-PROVISION" onclick="switchAgentDrawerTab('PROVISION')">
                OKF 원문
              </button>
              <button type="button" class="mgmt-subtab-btn" style="flex:1; justify-content:center;" id="agent-dtab-LEDGER" onclick="switchAgentDrawerTab('LEDGER')">
                테이블 결과
              </button>
            </div>
          </div>
          <div class="detail-panel-body" id="agent-drawer-body"></div>
        </aside>
      </div>
    `;

    AGENT_STUDIO_INITIALIZED = true;
    renderAgentQuestionList();
    renderAgentWelcomeMessage();
    const startQIdx = (typeof AGENT_SELECTED_IDX === "number" && AGENT_SELECTED_IDX >= 0 && AGENT_SELECTED_IDX < AGENT_QUESTIONS.length)
      ? AGENT_SELECTED_IDX
      : 0;
    selectAgentSidebarQuestion(startQIdx, false);
  } else {
    const topT = document.getElementById("agent-top-subbar-title");
    if (topT) topT.textContent = isEcom ? "K마켙 Graph 커머스 마진·재고·캠페인 에이전트" : "Starlight Graph 금융 심사 에이전트";
    const sideT = document.getElementById("agent-sidebar-title");
    if (sideT) sideT.textContent = isEcom ? "커머스 의사결정 질의 목록" : "금융 심사 질의 목록";
    renderAgentQuestionList();
  }
}

function renderAgentQuestionList() {
  const listEl = document.getElementById("agent-q-list");
  if (!listEl) return;
  const searchEl = document.getElementById("agent-q-search");
  const qFilter = (searchEl ? searchEl.value : "").trim().toLowerCase();

  const html = AGENT_QUESTIONS.map((item, idx) => {
    const hay = `${item.num}. ${item.title || ""} ${item.dept_name} ${item.question}`.toLowerCase();
    if (qFilter && !hay.includes(qFilter)) return "";
    const isActive = idx === AGENT_SELECTED_IDX;
    const summaryTitle = item.title || item.question;
    return `
      <div class="nav-item ${isActive ? "active" : ""}" id="agent-q-item-${idx}" onclick="selectAgentSidebarQuestion(${idx}, true)">
        <div class="nav-item-top">
          <span class="nav-item-title">${escapeHtml(item.num)}. ${escapeHtml(summaryTitle)}</span>
          <span class="nav-page">${escapeHtml(item.dept_name)}</span>
        </div>
        <div class="nav-item-sub">${escapeHtml(item.question)}</div>
      </div>
    `;
  }).join("");

  listEl.innerHTML = html || `<div style="padding:18px 12px; font-size:12px; color:var(--text-sub); text-align:center;">검색 조건에 맞는 질문이 없습니다.</div>`;
}

function selectAgentSidebarQuestion(idx, focusInput = true) {
  if (idx < 0 || idx >= AGENT_QUESTIONS.length) return;
  AGENT_SELECTED_IDX = idx;
  const item = AGENT_QUESTIONS[idx];
  AGENT_SELECTED_NUM = item.num;

  const listEl = document.getElementById("agent-q-list");
  if (listEl) {
    listEl.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  } else {
    document.querySelectorAll("#agent-q-list .nav-item").forEach(el => el.classList.remove("active"));
  }
  const activeEl = document.getElementById(`agent-q-item-${idx}`);
  if (activeEl) activeEl.classList.add("active");

  const inputEl = document.getElementById("agent-chat-input");
  if (inputEl) {
    inputEl.value = item.question;
    autoResizeAgentTextarea(inputEl);
    if (focusInput) {
      inputEl.focus();
    }
  }
  if (typeof saveUiState === "function") saveUiState();
}

function autoResizeAgentTextarea(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function handleAgentInputKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendAgentChatMessage();
  }
}

function renderAgentWelcomeMessage() {
  const msgBox = document.getElementById("agent-chat-messages");
  if (!msgBox) return;
  const isEcom = typeof ACTIVE_PROJECT !== "undefined" && ACTIVE_PROJECT === "ecommerce-ontology";
  msgBox.innerHTML = `
    <div class="agent-msg-row msg-agent">
      <div class="msg-agent-bubble">
        <div class="msg-agent-topbar">
          <div class="msg-agent-meta-left">
            <span class="agent-neutral-pill">${isEcom ? "K-Market Graph Agent" : "Starlight Graph Agent"}</span>
          </div>
        </div>
        <div class="agent-md-body">
          <h3>${isEcom ? "K마켙 온톨로지 기반 커머스 마진·재고·캠페인 의사결정 에이전트" : "별빛은행 온톨로지 기반 금융 심사·리스크·준법 에이전트"}</h3>
          <p>좌측 사이드바의 <strong><code>01.</code> ~ <code>21.</code>번 질의</strong> 중 하나를 클릭하면 하단 입력창에 질문이 자동으로 채워집니다. <strong>Enter 키</strong> 또는 우측 하단 <strong>전송 버튼</strong>을 누르면 실시간 BigQuery Graph (<code>${isEcom ? "kmarket_ontology.ecommerce_graph" : "starlight_bank_ontology.finance_graph"}</code>) 기반 분석이 시작됩니다.</p>
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

function resetAgentChat() {
  AGENT_TURN_HISTORY = [];
  AGENT_ACTIVE_TURN_IDX = -1;
  closeAgentArtifactDrawer();
  renderAgentWelcomeMessage();
  selectAgentSidebarQuestion(0, true);
}

function formatAgentMarkdown(mdText, turnIdx) {
  if (!mdText) return "";
  const lines = String(mdText).split("\n");
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
      const thHtml = tableHeader.map(h => `<th>${formatInlineMd(h, turnIdx)}</th>`).join("");
      const trHtml = tableRows.map(r => `<tr>${r.map(c => `<td>${formatInlineMd(c, turnIdx)}</td>`).join("")}</tr>`).join("");
      out.push(`<div class="agent-table-scroll"><table class="mod-table"><thead><tr>${thHtml}</tr></thead><tbody>${trHtml}</tbody></table></div>`);
      inTable = false;
      tableHeader = [];
      tableRows = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const trimmed = raw.trim();

    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList();
      const cells = trimmed.slice(1, -1).split("|").map(c => c.trim());
      if (cells.every(c => /^[-:\s]+$/.test(c))) {
        continue;
      }
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
      out.push(`<h3>${formatInlineMd(trimmed.slice(4), turnIdx)}</h3>`);
    } else if (trimmed.startsWith("#### ")) {
      flushList();
      out.push(`<h4>${formatInlineMd(trimmed.slice(5), turnIdx)}</h4>`);
    } else if (trimmed.startsWith("> ")) {
      flushList();
      out.push(`<blockquote>${formatInlineMd(trimmed.slice(2), turnIdx)}</blockquote>`);
    } else if (trimmed.startsWith("- ")) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${formatInlineMd(trimmed.slice(2), turnIdx)}</li>`);
    } else {
      flushList();
      out.push(`<p>${formatInlineMd(trimmed, turnIdx)}</p>`);
    }
  }
  flushList();
  flushTable();
  return out.join("\n");
}

function formatInlineMd(text, turnIdx) {
  let s = escapeHtml(text);
  const stashed = [];
  const stash = (html) => {
    const token = `\x00STASH${stashed.length}\x00`;
    stashed.push(html);
    return token;
  };
  // Clickable provision / citation pills like `[제29조 · BASE_CRITERIA]` (no pictograms, neutral tone)
  s = s.replace(/`\[([^\]]+)\]`/g, (_, inner) => {
    return stash(`<button type="button" class="agent-cite-pill" onclick="openAgentArtifactForTurn(${turnIdx}, 'PROVISION')">[${inner}]</button>`);
  });
  s = s.replace(/`([^`]+)`/g, (_, codeInner) => stash(`<code>${codeInner}</code>`));
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[\s(])_([^_]+)_(?=$|[\s).,!?;:])/g, "$1<em>$2</em>");
  s = s.replace(/\x00STASH(\d+)\x00/g, (_, idx) => stashed[Number(idx)] || "");
  return s;
}

const AGENT_LOADING_MESSAGES = [
  "엔티티 별칭 및 KC 클래스 앵커를 바인딩하고 있습니다",
  "BigQuery Graph Dry-Run 및 통합 GQL을 실행하고 있습니다",
  "Dataplex Knowledge Catalog에서 조문 유효성을 검증하고 있습니다",
  "BigQuery ObjectRef 서명 URL로 GCS 정본 조문 원문을 인출하고 있습니다"
];

function formatAgentLoadingText(stageOrText, dotCount) {
  const base = typeof stageOrText === "string"
    ? stageOrText
    : AGENT_LOADING_MESSAGES[Math.min(stageOrText, AGENT_LOADING_MESSAGES.length - 1)];
  return `${base}${".".repeat(dotCount)}`;
}

async function sendAgentChatMessage() {
  if (AGENT_IS_SENDING) return;
  const inputEl = document.getElementById("agent-chat-input");
  const msgBox = document.getElementById("agent-chat-messages");
  const sendBtn = document.getElementById("agent-send-btn");
  if (!inputEl || !msgBox) return;

  const questionText = inputEl.value.trim();
  if (!questionText) return;

  const selItem = AGENT_QUESTIONS[AGENT_SELECTED_IDX];
  const reqNum = (selItem && selItem.question.trim() === questionText) ? selItem.num : null;

  inputEl.value = "";
  autoResizeAgentTextarea(inputEl);
  AGENT_IS_SENDING = true;
  if (sendBtn) sendBtn.disabled = true;

  // 1. Append User Bubble
  const userRow = document.createElement("div");
  userRow.className = "agent-msg-row msg-user";
  userRow.innerHTML = `<div class="msg-user-bubble">${escapeHtml(questionText)}</div>`;
  msgBox.appendChild(userRow);

  // 2. Append Single-Line Loading Bubble once (no DOM replacement -> zero flicker)
  const loadingRow = document.createElement("div");
  loadingRow.className = "agent-msg-row msg-agent";
  const loadingTextId = `agent-loading-text-${Date.now()}`;
  let currentStageText = AGENT_LOADING_MESSAGES[0];
  let dotCount = 1;

  loadingRow.innerHTML = `
    <div class="msg-agent-bubble">
      <div class="agent-loading-line">
        <span class="material-symbols-outlined gcp-spin-sync" style="color:var(--gcp-blue); font-size:18px; flex-shrink:0;">sync</span>
        <span id="${loadingTextId}" class="agent-loading-text">${formatAgentLoadingText(currentStageText, dotCount)}</span>
      </div>
    </div>
  `;
  msgBox.appendChild(loadingRow);
  msgBox.scrollTop = msgBox.scrollHeight;

  let tick = 0;
  const loadingTimer = typeof setInterval === "function" ? setInterval(() => {
    tick += 1;
    dotCount = (tick % 3) + 1;
    const txtEl = document.getElementById(loadingTextId);
    if (txtEl) {
      txtEl.textContent = formatAgentLoadingText(currentStageText, dotCount);
    }
  }, 420) : null;

  try {
    const resp = await fetch("/api/agent/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project: typeof ACTIVE_PROJECT !== "undefined" ? ACTIVE_PROJECT : "finance-ontology",
        num: reqNum,
        question: questionText,
        stream: true
      })
    });

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
              currentStageText = evt.text;
              const txtEl = document.getElementById(loadingTextId);
              if (txtEl) {
                txtEl.textContent = formatAgentLoadingText(currentStageText, dotCount);
              }
            } else if (evt.type === "result" && evt.data) {
              data = evt.data;
            } else if (evt.ok !== undefined) {
              data = evt;
            }
          } catch (_e) {
            // ignore partial line
          }
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

    if (!data || !data.ok) {
      throw new Error((data && data.error) || "에이전트 서버 응답 오류");
    }

    const turnIdx = AGENT_TURN_HISTORY.length;
    AGENT_TURN_HISTORY.push(data);
    AGENT_ACTIVE_TURN_IDX = turnIdx;

    if (data.conversational_only) {
      loadingRow.innerHTML = `
        <div class="msg-agent-bubble">
          <div class="msg-agent-topbar">
            <div class="msg-agent-meta-left">
              <span class="agent-neutral-pill">${escapeHtml(data.badge_label || "Starlight Graph Agent")}</span>
            </div>
          </div>
          <div class="agent-md-body">
            ${formatAgentMarkdown(data.answer_markdown, turnIdx)}
          </div>
        </div>
      `;
      return;
    }

    const qa = data.gql_accordion || {};
    const drawer = data.artifact_drawer || {};
    const kcVerdicts = drawer.kc_verdicts || [];
    const isBlocked = Boolean(data.blocked);
    const isLedgerOnly = Boolean(data.ledger_only);
    const steps = renderGraphragStepsHtml(data);
    const isRefused = steps.isRefused;

    const statusBadgeHtml = isRefused
      ? `<span class="agent-neutral-pill">${escapeHtml(data.badge_label || "답변 거절 · GQL 미실행")}</span>`
      : isBlocked
      ? `<span class="agent-neutral-pill">BLOCKED_DEPRECATED · ${escapeHtml(data.incident_id || "INC")}</span>`
      : isLedgerOnly
        ? `<span class="agent-neutral-pill">${escapeHtml(data.badge_label || "Step 1 · GQL 원장 조회")}</span>`
        : `<span class="agent-neutral-pill">KC ALLOW · OKF 원문 검증</span>`;

    const defaultDrawerTab = isBlocked ? "KC" : isLedgerOnly ? "LEDGER" : "PROVISION";
    const openBtnLabel = isLedgerOnly ? "테이블 결과 상세 열기" : "원문·원장 근거 상세 열기";
    // A refused turn ran no kc_lookup / fetch_provision: there is nothing to open in the drawer.
    const openBtnHtml = isRefused ? "" : `
          <button type="button" class="agent-artifact-open-btn" onclick="openAgentArtifactForTurn(${turnIdx}, '${defaultDrawerTab}')">
            ${openBtnLabel}
          </button>`;

    loadingRow.innerHTML = `
      <div class="msg-agent-bubble ${isBlocked ? "blocked-bubble" : ""}">
        <div class="msg-agent-topbar">
          <div class="msg-agent-meta-left">
            <span class="agent-neutral-pill">${escapeHtml(data.matched_id || "01")}. ${escapeHtml(data.dept_name || "리스크관리부")}</span>
            ${statusBadgeHtml}
          </div>${openBtnHtml}
        </div>

        <div class="agent-md-body">
          ${formatAgentMarkdown(data.answer_markdown, turnIdx)}
        </div>

        <details class="query-accordion">
          <summary>
            <span>${escapeHtml(qa.title || "실행된 GQL 쿼리 및 경로 분석")}</span>
            <span class="material-symbols-outlined qa-chevron">expand_more</span>
          </summary>
          <div class="query-accordion-body">
            ${steps.html}
          </div>
        </details>
      </div>
    `;

    if (AGENT_DRAWER_OPEN) {
      renderAgentArtifactDrawer();
    }
  } catch (err) {
    loadingRow.innerHTML = `
      <div class="msg-agent-bubble blocked-bubble">
        <div class="agent-md-body">
          <h3>에이전트 요청 처리 중 오류가 발생했습니다</h3>
          <p><code>${escapeHtml(err.message || String(err))}</code></p>
        </div>
      </div>
    `;
  } finally {
    if (loadingTimer && typeof clearInterval === "function") {
      clearInterval(loadingTimer);
    }
    AGENT_IS_SENDING = false;
    if (sendBtn) sendBtn.disabled = false;
    msgBox.scrollTop = msgBox.scrollHeight;
  }
}

function openAgentArtifactForTurn(turnIdx, defaultTab = "KC") {
  if (turnIdx < 0 || turnIdx >= AGENT_TURN_HISTORY.length) return;
  AGENT_ACTIVE_TURN_IDX = turnIdx;
  AGENT_DRAWER_TAB = defaultTab;
  AGENT_DRAWER_OPEN = true;
  const drawerEl = document.getElementById("agent-artifact-drawer");
  if (drawerEl) drawerEl.classList.add("open");
  renderAgentArtifactDrawer();
}

function toggleAgentArtifactDrawer() {
  const drawerEl = document.getElementById("agent-artifact-drawer");
  if (!drawerEl) return;
  AGENT_DRAWER_OPEN = !AGENT_DRAWER_OPEN;
  drawerEl.classList.toggle("open", AGENT_DRAWER_OPEN);
  if (AGENT_DRAWER_OPEN) {
    renderAgentArtifactDrawer();
  }
}

function closeAgentArtifactDrawer() {
  AGENT_DRAWER_OPEN = false;
  const drawerEl = document.getElementById("agent-artifact-drawer");
  if (drawerEl) drawerEl.classList.remove("open");
}

function switchAgentDrawerTab(tabId) {
  AGENT_DRAWER_TAB = tabId;
  renderAgentArtifactDrawer();
}

function renderAgentArtifactDrawer() {
  const bodyEl = document.getElementById("agent-drawer-body");
  const titleEl = document.getElementById("agent-drawer-title");
  if (!bodyEl) return;

  ["KC", "PROVISION", "LEDGER"].forEach(t => {
    const btn = document.getElementById(`agent-dtab-${t}`);
    if (btn) btn.classList.toggle("active", t === AGENT_DRAWER_TAB);
  });

  if (AGENT_ACTIVE_TURN_IDX < 0 || !AGENT_TURN_HISTORY[AGENT_ACTIVE_TURN_IDX]) {
    bodyEl.innerHTML = `
      <div style="padding:24px 16px; font-size:12.5px; color:var(--text-sub); line-height:1.6; text-align:center;">
        아직 실행된 에이전트 응답이 없습니다.<br>좌측에서 질문(<code>01.</code> ~ <code>21.</code>)을 선택하고 전송하면<br>실시간 <strong>KC 유효성 판정 · ObjectRef 원문 · 테이블 결과</strong>가 이곳에 표시됩니다.
      </div>
    `;
    return;
  }

  const turn = AGENT_TURN_HISTORY[AGENT_ACTIVE_TURN_IDX];
  const drawer = turn.artifact_drawer || {};
  const kcVerdicts = drawer.kc_verdicts || [];
  const provisions = drawer.provisions || [];
  const ledgerTables = drawer.ledger_tables || [];

  if (titleEl) {
    titleEl.textContent = `${turn.matched_id || "01"}. ${turn.dept_name || ""} · 근거 아티팩트`;
  }

  if (AGENT_DRAWER_TAB === "KC") {
    bodyEl.innerHTML = kcVerdicts.map(kv => {
      const isAllowed = kv.decision === "ALLOW" || kv.decision === "SUPERSEDED_RESOLVED";
      const supInfo = kv.superseded_chain_example
        ? `<div style="margin-top:8px; padding:8px 10px; background:var(--code-bg); border:1px solid var(--border); border-radius:6px; font-size:11.5px; line-height:1.5;">
             <strong>참고 · 자동 대체(SUPERSEDED_RESOLVED) 체인 검증:</strong><br>
             <code>${escapeHtml(kv.superseded_chain_example.from)}</code> ➔ <code>${escapeHtml(kv.superseded_chain_example.resolved_to)}</code> (${kv.superseded_chain_example.hops}-hop, 판정: <code>${escapeHtml(kv.superseded_chain_example.decision)}</code>)
           </div>`
        : "";
      return `
        <div class="mod-card ${!isAllowed ? "blocked-card" : ""}" style="padding:14px 16px; margin-bottom:12px;">
          <div class="mod-card-header">
            <span class="mod-card-title" style="font-size:13px;">
              ${escapeHtml(kv.article_no || "조문")}
            </span>
            <span class="agent-neutral-pill">${escapeHtml(kv.decision)} (status=${escapeHtml(kv.status)})</span>
          </div>
          <div style="font-size:12px; color:var(--text-sub);">${escapeHtml(kv.title || "")}</div>
          <div class="agent-table-scroll">
            <table class="mod-table" style="font-size:11.5px;">
              <tbody>
                <tr><th style="width:110px;">KC Entry ID</th><td><code>${escapeHtml(kv.kc_entry_id)}</code></td></tr>
                <tr><th>유효 상태 (status)</th><td><code>${escapeHtml(kv.status)}</code> (v${escapeHtml(kv.version || "0.2.0")})</td></tr>
                <tr><th>게이트 판정</th><td><strong>${escapeHtml(kv.decision)}</strong> (${escapeHtml(kv.reason || "유효 정본 확인")})</td></tr>
                <tr><th>대체 체인 (chain)</th><td><code>${escapeHtml((kv.chain || [kv.kc_entry_id]).join(" -> "))}</code></td></tr>
                ${kv.incident_id ? `<tr><th>발행 티켓 (D5)</th><td><code>${escapeHtml(kv.incident_id)}</code></td></tr>` : ""}
              </tbody>
            </table>
          </div>
          ${supInfo}
        </div>
      `;
    }).join("") || `<div style="padding:16px; font-size:12px; color:var(--text-sub);">조회된 KC 판정 내역이 없습니다.</div>`;
    return;
  }

  if (AGENT_DRAWER_TAB === "PROVISION") {
    if (turn.blocked || provisions.length === 0) {
      bodyEl.innerHTML = `
        <div class="mod-card blocked-card" style="padding:16px;">
          <div style="font-size:13px; font-weight:600; color:var(--text); margin-bottom:6px;">
            OKF 원문 인출 차단됨 (BLOCKED_DEPRECATED)
          </div>
          <div style="font-size:12px; color:var(--text-sub); line-height:1.6;">
            <code>before_tool_callback</code> 거버넌스 게이트가 Dataplex KC 유효성 미통과(<code>status: deprecated</code>, 대체 정본 없음)를 감지하여 BigQuery <code>OBJ.GET_ACCESS_URL</code> 호출 및 GCS 원문 인출을 원천 차단했습니다.
          </div>
        </div>
      `;
      return;
    }

    bodyEl.innerHTML = provisions.map(p => {
      const formattedTargetCols = p.target_columns
        ? p.target_columns.split(",").map(s => s.trim()).filter(Boolean).join(", ")
        : "";
      const formattedMissingCols = p.missing_schema_columns
        ? p.missing_schema_columns.split(",").map(s => s.trim()).filter(Boolean).join(", ")
        : "";
      return `
      <div class="mod-card" style="padding:14px 16px; margin-bottom:14px;">
        <div class="mod-card-header">
          <span class="mod-card-title" style="font-size:13px;">
            [${escapeHtml(p.article_no)}] ${escapeHtml(p.title)}
          </span>
          <span class="agent-neutral-pill">${escapeHtml(p.provision_role)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
          <code style="font-family:var(--mono); font-size:11px; color:var(--text-sub);">${escapeHtml(p.uri)}</code>
          <button type="button" class="gcp-action-btn" style="flex:0 0 auto; padding:4px 10px; font-size:11.5px;" onclick="jumpToValidationSection('${escapeHtml(p.provision_slot_id || p.article_no)}', false)">
            02 · 원문 대조뷰(PDF) 열기
          </button>
        </div>
        <div style="display:flex; flex-direction:column; gap:4px; font-size:11px; color:var(--text-sub); line-height:1.5; background:var(--code-bg); border:1px solid var(--border); border-radius:6px; padding:8px 10px;">
          <div><strong>BigQuery ObjectRef 서명 URL:</strong> <code>${escapeHtml(p.signed_read_url_masked || "OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')")}</code></div>
          <div><strong>MD5 무결성:</strong> <code>${escapeHtml(p.md5_hash || "verified")}</code></div>
          <div><strong>만료시각:</strong> <code>${escapeHtml(p.signed_url_expiry || "-")}</code></div>
          ${formattedTargetCols ? `<div><strong>매핑 원장 컬럼:</strong> <code>${escapeHtml(formattedTargetCols)}</code></div>` : ""}
          ${formattedMissingCols ? `<div><strong>미구비 스키마 컬럼:</strong> <code>${escapeHtml(formattedMissingCols)}</code></div>` : ""}
        </div>
        ${p.yaml_frontmatter ? `
          <details class="fm-accordion" style="margin-bottom:4px;">
            <summary>
              <span class="fm-summary-left"><span>YAML Frontmatter</span></span>
              <span class="material-symbols-outlined fm-chevron">expand_more</span>
            </summary>
            <div class="frontmatter-block">${escapeHtml(p.yaml_frontmatter)}</div>
          </details>
        ` : ""}
        <div class="okf-body-box" style="font-size:12.5px; padding:12px 14px; max-height:300px; overflow-y:auto;">${escapeHtml(p.verbatim_body || "")}</div>
      </div>
    `;
    }).join("");
    return;
  }

  // LEDGER Tab ("테이블 결과")
  if (ledgerTables.length === 0) {
    bodyEl.innerHTML = `<div style="padding:16px; font-size:12px; color:var(--text-sub);">거버넌스 게이트 차단으로 인해 테이블 결과가 없습니다.</div>`;
    return;
  }

  bodyEl.innerHTML = ledgerTables.map(lt => {
    const rows = lt.rows || [];
    let tblHtml = `<div style="font-size:12px; color:var(--text-sub);">조회된 행 없음 (0건 — 위반 건수 없음)</div>`;
    if (rows.length > 0) {
      const cols = Object.keys(rows[0]);
      const ths = cols.map(c => `<th><code>${escapeHtml(c)}</code></th>`).join("");
      const trs = rows.map(r => `<tr>${cols.map(c => `<td>${escapeHtml(String(r[c] ?? "-"))}</td>`).join("")}</tr>`).join("");
      tblHtml = `<div class="agent-table-scroll"><table class="mod-table" style="font-size:11.5px;"><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table></div>`;
    }
    return `
      <div class="mod-card" style="padding:14px 16px; margin-bottom:14px;">
        <div class="mod-card-header">
          <span class="mod-card-title" style="font-size:13px;">
            테이블 결과
          </span>
          <span class="agent-neutral-pill">${lt.row_count} rows · ${lt.elapsed_ms} ms</span>
        </div>
        ${tblHtml}
        <details class="query-accordion" style="margin-top:6px;">
          <summary>
            <span>실행된 통합 GQL 원문 (Job: ${escapeHtml(lt.job_id || "bqjob")})</span>
            <span class="material-symbols-outlined qa-chevron">expand_more</span>
          </summary>
          <div class="query-accordion-body">
            <pre class="query-code-pre">${escapeHtml(lt.sql || "")}</pre>
          </div>
        </details>
      </div>
    `;
  }).join("");
}
