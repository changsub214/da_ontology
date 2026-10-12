/* ==========================================================================
   okf_veri_web/js/state.js
   Global Application State, Theme Controller (Default: GCP Light Mode),
   localStorage Persistence, and Module Router.
   ========================================================================== */

const STATE_KEY = 'okf_veri_ui_state_v4';
const TAB_SESSION_KEY = 'okf_veri_tab_session_v1';
const HARD_RELOAD_FLAG_KEY = 'okf_veri_hard_reload_flag_v1';
let IS_INITIALIZING = true;
let ACTIVE_PROJECT = 'finance-ontology';
const PROJECT_REGISTRY = {
  'finance-ontology': {
    id: 'finance-ontology',
    domainDir: 'finance',
    title: 'Google Cloud | Finance Ontology & OKF v0.2 Studio',
    verificationUrl: '../finance/okf/verification.json',
    unDataPrefix: '../finance/data/un_data/',
    introArchUrl: 'data/intro_arch.json',
    eqCompareUrl: 'data/eq_compare.json'
  },
  'ecommerce-ontology': {
    id: 'ecommerce-ontology',
    domainDir: 'ecommerce',
    title: 'Google Cloud | K마켙 Ecommerce Ontology & OKF v0.2 Studio',
    verificationUrl: '../ecommerce/okf/verification.json',
    unDataPrefix: '../ecommerce/data/un_data/',
    introArchUrl: 'data/ecommerce/intro_arch.json',
    eqCompareUrl: 'data/ecommerce/eq_compare.json'
  }
};
let PROVS = [];
let DOC_PROVS = [];
let CURRENT_IDX = 0;
let ACTIVE_DOC_PDF = null;
let OPEN_DOCS = {};
let GRAPH_MODE = false;
let ACTIVE_MODULE = 'intro';
let SELECTED_SCEN_IDX = 0;
let INTRO_TAB = 'sys';          // 01 · Intro tab id (tabs come from data/intro_arch.json)
let BQ_GRAPH_MODE = 'CLASS';
let BQ_QUERY_IDX = 0;
let FM_OPEN = false;
let GRAPH_DETAIL_OPEN = true;

if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
  window.addEventListener('keydown', (e) => {
    const isHardR = (e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'R' || e.key === 'r' || e.code === 'KeyR');
    const isShiftF5 = e.shiftKey && e.key === 'F5';
    if (isHardR || isShiftF5) {
      try {
        sessionStorage.setItem(HARD_RELOAD_FLAG_KEY, '1');
      } catch (_) {}
    }
  }, true);
}

function syncProjectSelectUi(projId) {
  const target = PROJECT_REGISTRY[projId] ? projId : 'finance-ontology';
  ACTIVE_PROJECT = target;
  const valEl = document.getElementById('project-select-val');
  if (valEl) valEl.textContent = target;
  const wrap = document.getElementById('project-custom-select');
  if (wrap) {
    wrap.querySelectorAll('.gcp-custom-select-opt').forEach(el => {
      const isSel = el.getAttribute('data-value') === target;
      el.classList.toggle('selected', isSel);
      const chk = el.querySelector('.gcp-opt-check');
      if (chk) chk.style.opacity = isSel ? '1' : '0';
    });
  }
  if (PROJECT_REGISTRY[target] && PROJECT_REGISTRY[target].title) {
    document.title = PROJECT_REGISTRY[target].title;
  }
  const searchEl = document.getElementById('nav-search');
  if (searchEl) {
    searchEl.placeholder = target === 'ecommerce-ontology'
      ? '조문 검색 (제11조, 50%, 마진, 체화재고, 청약철회)...'
      : '조문 검색 (제29조, 별표3, 제14조, 특허)...';
  }
}

async function loadProjectBundle(projId, resetSelection = false) {
  const target = PROJECT_REGISTRY[projId] ? projId : 'finance-ontology';
  syncProjectSelectUi(target);
  if (typeof applyProjectDomainData === 'function') {
    applyProjectDomainData(target);
  }
  const cfg = PROJECT_REGISTRY[target];
  const res = await fetch(cfg.verificationUrl + '?t=' + Date.now());
  const data = await res.json();
  PROVS = data.provisions || [];
  DOC_PROVS = data.documents || [];

  if (resetSelection) {
    OPEN_DOCS = {};
    ACTIVE_DOC_PDF = null;
    if (typeof INTRO_DATA !== 'undefined') INTRO_DATA = null;
    if (typeof INTRO_DATA_ERR !== 'undefined') INTRO_DATA_ERR = null;
    if (typeof MGMT_OPEN_DOCS !== 'undefined') MGMT_OPEN_DOCS = {};
    if (typeof MGMT_ACTIVE_KEY !== 'undefined') MGMT_ACTIVE_KEY = null;
    if (typeof KC_SELECTED_KEY !== 'undefined') KC_SELECTED_KEY = null;
    BQ_QUERY_IDX = 0;
    if (typeof bqCurrentInstNodes !== 'undefined') bqCurrentInstNodes = [];
    if (typeof bqCurrentInstEdges !== 'undefined') bqCurrentInstEdges = [];
    if (typeof closeBqDrawer === 'function') closeBqDrawer();
    if (typeof AGENT_STUDIO_INITIALIZED !== 'undefined') AGENT_STUDIO_INITIALIZED = false;
    if (typeof BENCH_INITIALIZED !== 'undefined') BENCH_INITIALIZED = false;
    if (typeof BENCH_DATA !== 'undefined') BENCH_DATA = null;

    if (target === 'ecommerce-ontology') {
      const art11Idx = PROVS.findIndex(p => String(p.section_number).includes('제11조제3항'));
      CURRENT_IDX = art11Idx >= 0 ? art11Idx : 0;
    } else {
      const art29Idx = PROVS.findIndex(p => p.section_number === '제29조');
      CURRENT_IDX = art29Idx >= 0 ? art29Idx : 0;
    }
    if (PROVS[CURRENT_IDX]) OPEN_DOCS[PROVS[CURRENT_IDX].pdf_file] = true;
    renderSidebar();
    selectItem(CURRENT_IDX);
    if (typeof syncGraphScopeCustomSelectUi === 'function') {
      syncGraphScopeCustomSelectUi('ALL');
    }
    if (GRAPH_MODE && typeof buildOkfGraph === 'function') {
      buildOkfGraph('ALL');
    }
    if (ACTIVE_MODULE === 'intro' && typeof renderIntroModule === 'function') {
      renderIntroModule();
    } else if (ACTIVE_MODULE === 'okf-management' && typeof renderManagementModule === 'function') {
      renderManagementModule(CURRENT_IDX);
    } else if (ACTIVE_MODULE === 'bq-graph' && typeof initOrUpdateBqGraphStudio === 'function') {
      initOrUpdateBqGraphStudio();
    } else if (ACTIVE_MODULE === 'agent' && typeof renderAgentModule === 'function') {
      renderAgentModule(0);
    } else if (ACTIVE_MODULE === 'rag-vs-graphrag' && typeof renderBenchmarkModule === 'function') {
      renderBenchmarkModule(0);
    }
  }
}

async function selectProjectOption(ev, projId) {
  if (ev && ev.stopPropagation) ev.stopPropagation();
  const wrap = document.getElementById('project-custom-select');
  if (wrap) wrap.classList.remove('open');
  await loadProjectBundle(projId, true);
  saveUiState();
}

function readSavedState() {
  try {
    const rawV4 = localStorage.getItem(STATE_KEY);
    if (rawV4) return JSON.parse(rawV4);
    const rawV3 = localStorage.getItem('okf_veri_ui_state_v3');
    if (rawV3) {
      const v3 = JSON.parse(rawV3);
      // Migrate to Clean GCP Light Mode by default per design overhaul
      v3.darkMode = false;
      return v3;
    }
    return {};
  } catch (e) {
    return {};
  }
}

function saveUiState() {
  if (IS_INITIALIZING) return;
  try {
    const p = PROVS[CURRENT_IDX];
    const scopeEl = document.getElementById('graph-scope-select');
    const state = {
      activeProject: ACTIVE_PROJECT,
      darkMode: document.body.classList.contains('dark-mode'),
      activeModule: ACTIVE_MODULE,
      selectedScenIdx: SELECTED_SCEN_IDX,
      introTab: INTRO_TAB,
      bqGraphMode: BQ_GRAPH_MODE,
      bqQueryIdx: BQ_QUERY_IDX,
      graphMode: GRAPH_MODE,
      graphScope: scopeEl ? scopeEl.value : 'ALL',
      graphDetailOpen: GRAPH_DETAIL_OPEN,
      currentConceptId: p ? p.concept_id : null,
      currentIdx: CURRENT_IDX,
      activeDocPdf: ACTIVE_DOC_PDF,
      openDocs: OPEN_DOCS,
      fmOpen: FM_OPEN,
      mgmtSubView: typeof MGMT_SUB_VIEW !== 'undefined' ? MGMT_SUB_VIEW : 'EDITOR',
      mgmtActiveKey: typeof MGMT_ACTIVE_KEY !== 'undefined' ? MGMT_ACTIVE_KEY : null,
      mgmtOpenDocs: typeof MGMT_OPEN_DOCS !== 'undefined' ? MGMT_OPEN_DOCS : {},
      kcSelectedKey: typeof KC_SELECTED_KEY !== 'undefined' ? KC_SELECTED_KEY : null,
      agentSelectedIdx: typeof AGENT_SELECTED_IDX !== 'undefined' ? AGENT_SELECTED_IDX : 0,
      benchMode: typeof BENCH_MODE !== 'undefined' ? BENCH_MODE : 'live',
      benchSelectedIdx: typeof BENCH_SELECTED_IDX !== 'undefined' ? BENCH_SELECTED_IDX : 0,
      benchReportFilter: typeof BENCH_REPORT_FILTER !== 'undefined' ? BENCH_REPORT_FILTER : 'all'
    };
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch (e) {}
}

function readAndClearHardReloadCookie() {
  try {
    const cookies = String(document.cookie || '').split(';').map(c => c.trim());
    const found = cookies.find(c => c.startsWith('okf_hard_reload='));
    if (!found) return null;
    const val = found.split('=')[1];
    document.cookie = 'okf_hard_reload=0; Path=/; SameSite=Lax';
    return val === '1';
  } catch (_) {
    return null;
  }
}

function isPerformanceHardReload() {
  try {
    if (typeof performance === 'undefined' || typeof performance.getEntriesByType !== 'function') return false;
    const resEntries = performance.getEntriesByType('resource') || [];
    const localAssets = resEntries.filter(r =>
      r.name && (r.name.includes('css/gcp-console.css') || r.name.includes('js/data.js') || r.name.includes('js/state.js'))
    );
    if (localAssets.length === 0) return false;
    return localAssets.every(r => r.transferSize > 0 && r.encodedBodySize > 0 && r.transferSize >= r.encodedBodySize);
  } catch (_) {
    return false;
  }
}

function detectNavigationKind() {
  let hasTabSession = false;
  let hasHardFlag = false;
  try {
    hasTabSession = sessionStorage.getItem(TAB_SESSION_KEY) === '1';
    hasHardFlag = sessionStorage.getItem(HARD_RELOAD_FLAG_KEY) === '1';
    if (hasHardFlag) sessionStorage.removeItem(HARD_RELOAD_FLAG_KEY);
    sessionStorage.setItem(TAB_SESSION_KEY, '1');
  } catch (_) {}

  const cookieHard = readAndClearHardReloadCookie();

  let navType = 'navigate';
  try {
    if (typeof performance !== 'undefined' && typeof performance.getEntriesByType === 'function') {
      const navEntries = performance.getEntriesByType('navigation');
      if (navEntries && navEntries.length > 0 && navEntries[0].type) {
        navType = navEntries[0].type;
      } else if (performance.navigation && performance.navigation.type === 1) {
        navType = 'reload';
      }
    }
  } catch (_) {}

  if (!hasTabSession || navType !== 'reload') {
    return 'new';
  }
  if (hasHardFlag || cookieHard === true || (cookieHard === null && isPerformanceHardReload())) {
    return 'hard-reload';
  }
  return 'reload';
}

function applyInitialTheme() {
  const saved = readSavedState();
  const isDark = Boolean(saved.darkMode);
  document.body.classList.toggle('dark-mode', isDark);
  const tIcon = document.getElementById('theme-icon');
  const tText = document.getElementById('theme-text');
  if (tIcon) tIcon.textContent = isDark ? 'light_mode' : 'dark_mode';
  if (tText) tText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
}

function toggleTheme() {
  const isDark = document.body.classList.toggle('dark-mode');
  document.getElementById('theme-icon').textContent = isDark ? 'light_mode' : 'dark_mode';
  document.getElementById('theme-text').textContent = isDark ? 'Light Mode' : 'Dark Mode';
  saveUiState();
  if (GRAPH_MODE && typeof buildOkfGraph === 'function') {
    buildOkfGraph(document.getElementById('graph-scope-select').value);
  }
  if (ACTIVE_MODULE === 'bq-graph' && typeof initOrUpdateBqGraphStudio === 'function') {
    initOrUpdateBqGraphStudio();
  }
}

function onFmToggle(isOpen) {
  FM_OPEN = Boolean(isOpen);
  saveUiState();
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function switchModule(modId, fromInit = false) {
  if (modId === 'okf-enrollment') modId = 'okf-management';
  ACTIVE_MODULE = modId;
  const railMap = {
    'intro': 'rail-intro',
    'okf-validation': 'rail-okf-validation',
    'okf-management': 'rail-okf-management',
    'bq-graph': 'rail-bq-graph',
    'agent': 'rail-agent',
    'rag-vs-graphrag': 'rail-rag-vs-graphrag'
  };
  Object.entries(railMap).forEach(([k, btnId]) => {
    const el = document.getElementById(btnId);
    if (el) el.classList.toggle('active', k === modId);
  });

  const modIntro = document.getElementById('module-intro');
  const modEnroll = document.getElementById('module-enrollment');
  const modBqGraph = document.getElementById('module-bq-graph');
  const modAgent = document.getElementById('module-agent');
  const modBench = document.getElementById('module-benchmark');
  const compareWs = document.getElementById('compare-workspace');
  const graphWs = document.getElementById('graph-workspace');
  const viewSwitchBtn = document.getElementById('btn-view-switch');

  modIntro.style.display = modId === 'intro' ? 'flex' : 'none';
  modEnroll.style.display = modId === 'okf-management' ? 'flex' : 'none';
  if (modBqGraph) modBqGraph.style.display = modId === 'bq-graph' ? 'flex' : 'none';
  modAgent.style.display = modId === 'agent' ? 'flex' : 'none';
  modBench.style.display = modId === 'rag-vs-graphrag' ? 'flex' : 'none';

  if (modId === 'okf-validation') {
    if (viewSwitchBtn) {
      viewSwitchBtn.style.display = 'inline-flex';
      viewSwitchBtn.classList.toggle('active', GRAPH_MODE);
      const icon = document.getElementById('view-switch-icon');
      const txt = document.getElementById('view-switch-text');
      if (icon) icon.textContent = GRAPH_MODE ? 'vertical_split' : 'hub';
      if (txt) txt.textContent = GRAPH_MODE ? 'Split View' : 'Graph View';
    }
    compareWs.style.display = GRAPH_MODE ? 'none' : 'flex';
    graphWs.style.display = GRAPH_MODE ? 'flex' : 'none';
    if (GRAPH_MODE && typeof buildOkfGraph === 'function') {
      requestAnimationFrame(() => {
        buildOkfGraph(document.getElementById('graph-scope-select').value);
        if (GRAPH_DETAIL_OPEN && typeof openGraphDetailForIdx === 'function') {
          openGraphDetailForIdx(CURRENT_IDX);
        }
      });
    }
  } else {
    if (viewSwitchBtn) viewSwitchBtn.style.display = 'none';
    compareWs.style.display = 'none';
    graphWs.style.display = 'none';
    if (modId === 'intro' && typeof renderIntroModule === 'function') {
      renderIntroModule();
    }
    if (modId === 'okf-management' && typeof renderManagementModule === 'function') {
      renderManagementModule(CURRENT_IDX);
    }
    if (modId === 'bq-graph' && typeof initOrUpdateBqGraphStudio === 'function') {
      requestAnimationFrame(() => initOrUpdateBqGraphStudio());
    }
    if (modId === 'agent' && typeof renderAgentModule === 'function') renderAgentModule(SELECTED_SCEN_IDX);
    if (modId === 'rag-vs-graphrag' && typeof renderBenchmarkModule === 'function') {
      renderBenchmarkModule(typeof BENCH_SELECTED_IDX === 'number' ? BENCH_SELECTED_IDX : SELECTED_SCEN_IDX);
    }
  }

  if (!fromInit) saveUiState();
}

function jumpToValidationSection(secName, wantGraph = false) {
  const idx = PROVS.findIndex(p => p.concept_id === secName || p.section_number === secName);
  if (idx >= 0) CURRENT_IDX = idx;
  GRAPH_MODE = !wantGraph;
  switchModule('okf-validation');
  toggleGraphView();
}

function getDocItemForPdf(pdfFile) {
  if (!pdfFile) return null;
  if (Array.isArray(DOC_PROVS) && DOC_PROVS.length > 0) {
    const found = DOC_PROVS.find(d => d.pdf_file === pdfFile);
    if (found) return found;
  }
  const childProvs = PROVS.filter(p => p.pdf_file === pdfFile);
  if (childProvs.length === 0) return null;
  const first = childProvs[0];
  const parts = String(first.concept_id || '').split('/');
  const catDir = first.category || parts[0] || 'regulations';
  const docDir = parts[1] || '01_fsc_banking_reg';
  const relDocPath = `/${catDir}/${docDir}/doc.md`;
  const totalPages = first.pdf_total_pages || 1;
  const partMap = {};
  childProvs.forEach(cp => {
    const pDir = String(cp.concept_id || '').split('/')[2] || 'sec01';
    if (!partMap[pDir]) partMap[pDir] = cp.part_title || pDir;
  });
  const bodyLines = [
    `# ${first.doc_title}`,
    '',
    `원본 PDF: \`${pdfFile}\` (총 ${totalPages}쪽, 수록 조문 ${childProvs.length}건)[^origin_pdf]`,
    '',
    '## 하위 장·절 디렉터리 (`Parts`)',
    ...Object.entries(partMap).map(([pDir, pTitle]) => `* [${pTitle}](${pDir}/index.md)`),
    '',
    '## 수록 조문 (`Provisions`)',
    ...childProvs.map(cp => {
      const subPath = String(cp.concept_id || '').split('/').slice(2).join('/') + '.md';
      return `* [${cp.title}](${subPath}) — ${cp.source_page}쪽: ${cp.description || ''}`;
    })
  ];
  const yamlStr = [
    '---',
    'type: Source Document',
    `title: ${first.doc_title}`,
    `description: ${first.doc_title} (${pdfFile}, 총 ${totalPages}쪽, ${childProvs.length}개 조문)`,
    'tags:',
    `- ${catDir}`,
    `- ${first.content_class || 'authentic'}`,
    `- ${docDir}`,
    '- verbatim_ko',
    'sources:',
    '- id: origin_pdf',
    `  resource: okf://source/un_data/${pdfFile}`,
    '  kind: origin_document',
    `  sha256: ${first.sha256}`,
    'generated:',
    '  by: process:build_okf/3.0',
    "  at: '2026-09-22T04:00:00Z'",
    'status: stable',
    'language: ko',
    'treatment: verbatim_ko',
    `content_class: ${first.content_class || 'authentic'}`,
    `document_id: ${first.doc_id}`,
    `group: ${catDir}`,
    `source_pages: ${totalPages}`,
    `provision_count: ${childProvs.length}`,
    '---'
  ].join('\n');

  return {
    concept_id: `${catDir}/${docDir}/doc`,
    okf_path: relDocPath,
    doc_id: first.doc_id,
    doc_title: first.doc_title,
    part_title: 'Source Document Root (doc.md)',
    category: catDir,
    content_class: first.content_class || 'authentic',
    pdf_file: pdfFile,
    pdf_total_pages: totalPages,
    sha256: first.sha256,
    section_number: 'doc.md (문서 총괄)',
    title: first.doc_title,
    description: `${first.doc_title} (원본 PDF: ${pdfFile}, 총 ${totalPages}쪽, 수록 조문 ${childProvs.length}개)`,
    source_page: 1,
    source_pages_span: totalPages > 1 ? [1, totalPages] : [1],
    yaml_frontmatter: yamlStr,
    verbatim_body: bodyLines.join('\n'),
    contacts: first.contacts || '',
    is_source_document: true,
    provision_count: childProvs.length
  };
}

async function init() {
  IS_INITIALIZING = true;
  applyInitialTheme();
  const navKind = detectNavigationKind();
  const isResetToIntro = (navKind === 'new' || navKind === 'hard-reload');
  const saved = readSavedState();

  await loadProjectBundle(saved.activeProject || 'finance-ontology', false);

  if (typeof fetchServerOkfState === 'function') {
    await fetchServerOkfState();
  }

  if (!isResetToIntro) {
    if (typeof saved.fmOpen === 'boolean') FM_OPEN = saved.fmOpen;
    if (typeof saved.graphDetailOpen === 'boolean') GRAPH_DETAIL_OPEN = saved.graphDetailOpen;
    if (typeof saved.selectedScenIdx === 'number') SELECTED_SCEN_IDX = saved.selectedScenIdx;
    if (typeof saved.introTab === 'string') INTRO_TAB = saved.introTab;
    if (saved.bqGraphMode === 'CLASS' || saved.bqGraphMode === 'INSTANCE') BQ_GRAPH_MODE = saved.bqGraphMode;
    if (typeof saved.bqQueryIdx === 'number') BQ_QUERY_IDX = saved.bqQueryIdx;
    if (saved.openDocs && typeof saved.openDocs === 'object') OPEN_DOCS = saved.openDocs;
    if (typeof MGMT_SUB_VIEW !== 'undefined' && (saved.mgmtSubView === 'EDITOR' || saved.mgmtSubView === 'KC_EXPLORER')) {
      MGMT_SUB_VIEW = saved.mgmtSubView;
    }
    if (typeof MGMT_ACTIVE_KEY !== 'undefined' && saved.mgmtActiveKey !== undefined && saved.mgmtActiveKey !== null) {
      MGMT_ACTIVE_KEY = saved.mgmtActiveKey;
    }
    if (typeof MGMT_OPEN_DOCS !== 'undefined' && saved.mgmtOpenDocs && typeof saved.mgmtOpenDocs === 'object') {
      MGMT_OPEN_DOCS = saved.mgmtOpenDocs;
    }
    if (typeof KC_SELECTED_KEY !== 'undefined' && typeof saved.kcSelectedKey === 'string') {
      KC_SELECTED_KEY = saved.kcSelectedKey;
    }
    if (typeof AGENT_SELECTED_IDX !== 'undefined' && typeof saved.agentSelectedIdx === 'number') {
      AGENT_SELECTED_IDX = saved.agentSelectedIdx;
    }
    if (typeof BENCH_MODE !== 'undefined' && (saved.benchMode === 'live' || saved.benchMode === 'report')) {
      BENCH_MODE = saved.benchMode;
    }
    if (typeof BENCH_SELECTED_IDX !== 'undefined' && typeof saved.benchSelectedIdx === 'number') {
      BENCH_SELECTED_IDX = saved.benchSelectedIdx;
    }
    if (typeof BENCH_REPORT_FILTER !== 'undefined' && typeof saved.benchReportFilter === 'string') {
      BENCH_REPORT_FILTER = saved.benchReportFilter;
    }

    const scopeEl = document.getElementById('graph-scope-select');
    if (scopeEl && saved.graphScope) {
      scopeEl.value = saved.graphScope;
      if (typeof syncGraphScopeCustomSelectUi === 'function') {
        syncGraphScopeCustomSelectUi(saved.graphScope);
      }
    }
  } else {
    INTRO_TAB = 'sys';
    SELECTED_SCEN_IDX = 0;
    GRAPH_MODE = false;
    BQ_GRAPH_MODE = 'CLASS';
    BQ_QUERY_IDX = 0;
    OPEN_DOCS = {};
    ACTIVE_DOC_PDF = null;
    if (typeof AGENT_SELECTED_IDX !== 'undefined') AGENT_SELECTED_IDX = 0;
    if (typeof BENCH_MODE !== 'undefined') BENCH_MODE = 'live';
    if (typeof BENCH_SELECTED_IDX !== 'undefined') BENCH_SELECTED_IDX = 0;
    if (typeof BENCH_REPORT_FILTER !== 'undefined') BENCH_REPORT_FILTER = 'all';
    const scopeEl = document.getElementById('graph-scope-select');
    if (scopeEl) {
      scopeEl.value = 'ALL';
      if (typeof syncGraphScopeCustomSelectUi === 'function') {
        syncGraphScopeCustomSelectUi('ALL');
      }
    }
  }

  let targetIdx = -1;
  if (!isResetToIntro && saved.currentConceptId) {
    targetIdx = PROVS.findIndex(p => p.concept_id === saved.currentConceptId);
  }
  if (!isResetToIntro && targetIdx < 0 && typeof saved.currentIdx === 'number' && saved.currentIdx >= 0 && saved.currentIdx < PROVS.length) {
    targetIdx = saved.currentIdx;
  }
  if (targetIdx < 0) {
    if (ACTIVE_PROJECT === 'ecommerce-ontology') {
      const art11Idx = PROVS.findIndex(p => String(p.section_number).includes('제11조제3항'));
      targetIdx = art11Idx >= 0 ? art11Idx : 0;
    } else {
      const art29Idx = PROVS.findIndex(p => p.section_number === '제29조');
      targetIdx = art29Idx >= 0 ? art29Idx : 0;
    }
  }
  CURRENT_IDX = targetIdx;
  if (PROVS[CURRENT_IDX]) OPEN_DOCS[PROVS[CURRENT_IDX].pdf_file] = true;

  renderSidebar();
  selectItem(CURRENT_IDX);
  if (!isResetToIntro && saved.activeDocPdf && typeof toggleDocGroup === 'function') {
    OPEN_DOCS[saved.activeDocPdf] = false;
    toggleDocGroup(saved.activeDocPdf);
  }
  renderIntroModule();
  if (typeof renderManagementModule === 'function') renderManagementModule(CURRENT_IDX);
  renderAgentModule(typeof AGENT_SELECTED_IDX === 'number' ? AGENT_SELECTED_IDX : SELECTED_SCEN_IDX);
  renderBenchmarkModule(typeof BENCH_SELECTED_IDX === 'number' ? BENCH_SELECTED_IDX : SELECTED_SCEN_IDX);

  GRAPH_MODE = Boolean(!isResetToIntro && saved.graphMode);
  const startMod = isResetToIntro ? 'intro' : (saved.activeModule || 'intro');
  switchModule(startMod, true);
  IS_INITIALIZING = false;
  saveUiState();
}
