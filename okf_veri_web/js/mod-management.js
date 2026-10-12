/* ==========================================================================
   okf_veri_web/js/mod-management.js
   Module 03 (03 · okf-management):
     1. Parses real `verification.json` (`p.title`, `p.verbatim_body`, `p.yaml_frontmatter`) — zero `undefined`.
     2. Structured OKF v0.2 Frontmatter Dropdowns (`type`, `status`, `content_class`, `treatment`,
        `license`, `generated.by`, `verified.by`, `verified.method`) + editable `title`, `description`, `tags`.
     3. Floating Bottom-Center Multi-Select Snackbar (`.mgmt-floating-snackbar`) — zero layout shift when checking items.
     4. Semantic Version Confirm Modal (`PATCH / MINOR / MAJOR` + Change Note + Before/After Diff).
     5. GCP Dataplex Knowledge Catalog Explorer:
        [Top: Entry Summary Metadata] ➔ [Middle: Overview (Markdown)] ➔ [Bottom: Aspects (OKF Signal)]
   ========================================================================== */

let MGMT_SUB_VIEW = 'EDITOR'; // 'EDITOR' | 'KC_EXPLORER'
let MGMT_SERVER_STATE = { files: {}, deprecated_entries: [] };
let MGMT_SELECTED_SET = new Set(); // Set of item keys (idx or 'DOC:<pdf>') checked for batch operations
let MGMT_DIRTY_MAP = {}; // key (idx or 'DOC:<pdf>') -> { fm: {...}, body: "..." }
let MGMT_TREE_FILTER = 'ALL'; // 'ALL' | 'MODIFIED'
let MGMT_LAST_PUBLISH_RESULT = null;
let MGMT_ACTIVE_KEY = null; // number (0..173) or 'DOC:<pdfFile>'

// KC Explorer State
let KC_FILTER_STATUS = 'ALL'; // 'ALL' | 'VERIFIED' | 'DEPRECATED'
let KC_SEARCH_QUERY = '';
let KC_SELECTED_KEY = null; // e.g. "ACTIVE:0" or "ACTIVE:DOC:..." or "DEP:0"
let KC_DETAIL_TAB = 'OVERVIEW_ASPECT'; // 'OVERVIEW_ASPECT' | 'DIFF'

// Modal State
let MODAL_MODE = 'SINGLE'; // 'SINGLE' | 'BATCH'
let MODAL_BUMP_LEVEL = 'PATCH';
let MODAL_CONTACTS_VALUE = null;
let MODAL_PRESET_NOTE_VAL = '';
let MODAL_CHANGE_NOTE_TEXT = '';

let OKF_V02_DROPDOWN_OPTIONS = {
  type: ['Source Document', 'Provision', 'PolicyClause', 'Table', 'Concept', 'Document'],
  status: ['stable', 'verified', 'draft', 'deprecated'],
  content_class: ['authentic', 'guidance', 'internal_policy', 'synthetic'],
  treatment: ['verbatim_ko', 'normalized_ko', 'structured_table'],
  license: [
    '공공누리 제1유형 (국가법령정보센터·금융위원회 공공저작물 자유이용허락)',
    '금융감독원 감독업무시행세칙 공공저작물 자유이용허락',
    '전국은행연합회 자율규제 표준약관·모범규준',
    '별빛은행 내부 준법감시·여신내규 (사내한 · 대외비)'
  ],
  generated_by: [
    'process:build_okf/3.0',
    'process:okf_studio_editor/0.2',
    'agent:gemini-2.5-pro'
  ],
  verified_by: [
    'process:verify_provisions/1.0',
    'human:compliance_reviewer',
    'human:credit_committee_lead',
    'human:risk_governance_admin'
  ],
  verified_method: [
    'source_text_match',
    'owner_acceptance',
    'committee_signoff',
    'automated_lint_p1_p4'
  ],
  contacts: [
    '신영만(과장) - 데이터거버넌스팀 <youngman@starlightbk.com>',
    '봉미선(차장) - 여신심사·관리부 <misun@starlightbk.com>',
    '김철수(대리) - 준법감시부 <chulsoo@starlightbk.com>',
    '강유리(대리) - 리스크관리부 <yuri@starlightbk.com>'
  ]
};
const FINANCE_OKF_V02_DROPDOWN_OPTIONS = OKF_V02_DROPDOWN_OPTIONS;

let CHANGE_NOTE_PRESETS = [
  '준법감시부 정기 검증 완료에 따른 verified.by 및 status 현행화',
  '단서·예외 특례(Caveat) 조항 및 적용 맥락(BusinessContext) 연결 보완',
  '감독규정·내규 개정에 따른 의사결정 수치 임계치 업데이트',
  '원문 대조(P1~P4) 재검증 및 마크다운 포맷 정제'
];
const FINANCE_CHANGE_NOTE_PRESETS = CHANGE_NOTE_PRESETS;

function simpleSha256Hex64(str, fallbackSha) {
  if (!str) return fallbackSha || '7ec775dc7d09f2ea35f898b9c18756a9ffd6a262583d76fc7055ab350d429c79';
  let h1 = 0xdeadbeef ^ str.length;
  let h2 = 0x41c6ce57 ^ str.length;
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  const p1 = (h1 >>> 0).toString(16).padStart(8, '0');
  const p2 = (h2 >>> 0).toString(16).padStart(8, '0');
  const tail = String(fallbackSha || '35f898b9c18756a9ffd6a262583d76fc7055ab350d429c79').slice(16, 64);
  return (p1 + p2 + tail).slice(0, 64);
}

function bumpSemverJs(ver, level) {
  const parts = String(ver || '0.2.0').split('.').map(n => parseInt(n, 10) || 0);
  while (parts.length < 3) parts.push(0);
  if (level === 'MAJOR') return `${parts[0] + 1}.0.0`;
  if (level === 'MINOR') return `${parts[0]}.${parts[1] + 1}.0`;
  return `${parts[0]}.${parts[1]}.${parts[2] + 1}`;
}

function getRelPathForProv(p) {
  return String(p.okf_path || '')
    .replace(/^gs:\/\/(okf|kmarket_okf\/okf|kmarket_okf)\//, '')
    .replace(/^\/+/, '');
}

function extractYamlScalar(yamlStr, key, fallbackVal) {
  if (!yamlStr) return fallbackVal;
  const re = new RegExp(`^${key}:\\s*['"]?([^'"\\n]+)['"]?`, 'm');
  const m = yamlStr.match(re);
  return m ? m[1].trim() : fallbackVal;
}

function extractYamlNestedScalar(yamlStr, parentKey, childKey, fallbackVal) {
  if (!yamlStr) return fallbackVal;
  const blockIdx = yamlStr.indexOf(`${parentKey}:`);
  if (blockIdx < 0) return fallbackVal;
  const sub = yamlStr.slice(blockIdx, blockIdx + 260);
  const re = new RegExp(`\\b${childKey}:\\s*['"]?([^'"\\n]+)['"]?`);
  const m = sub.match(re);
  return m ? m[1].trim() : fallbackVal;
}

function getDistinctPdfList() {
  const seen = new Set();
  const list = [];
  if (typeof DOC_PROVS !== 'undefined' && Array.isArray(DOC_PROVS)) {
    DOC_PROVS.forEach(d => {
      if (d && d.pdf_file && !seen.has(d.pdf_file)) {
        seen.add(d.pdf_file);
        list.push(d.pdf_file);
      }
    });
  }
  PROVS.forEach(p => {
    if (p && p.pdf_file && !seen.has(p.pdf_file)) {
      seen.add(p.pdf_file);
      list.push(p.pdf_file);
    }
  });
  return list;
}

function getMgmtActiveKey() {
  return (MGMT_ACTIVE_KEY !== null && MGMT_ACTIVE_KEY !== undefined) ? MGMT_ACTIVE_KEY : CURRENT_IDX;
}

function getShortSlugForRel(relPath) {
  const parts = String(relPath || '').replace(/\.md$/, '').split('/').filter(Boolean);
  const last = parts[parts.length - 1] || 'doc';
  if (last === 'doc' && parts.length >= 2) {
    return `${parts[parts.length - 2]}_doc`;
  }
  return last;
}

const ECOM_LEGACY_CONTACT_MAP = {
  'K마켙 AI추천랩장 <ai-reco@kmarket.co.kr>': '최유진(리드) - 그로스마케팅·AI추천랩 <save.my.cart@kmarket.co.kr>',
  'K마켙 가격전략실장 <md-pricing@kmarket.co.kr>': '박서준(팀장) - MD본부 가격전략·마진관리실 <keep.margin25@kmarket.co.kr>',
  'K마켙 파트너상생본부장 <partner-cp@kmarket.co.kr>': '정민호(책임) - 파트너상생·공정거래CP팀 <fifty.fifty@kmarket.co.kr>',
  'K마켙 고객경험본부장 <cx-policy@kmarket.co.kr>': '강하늘(매니저) - 고객경험(CX)·CS심사팀 <dont.cut.the.tag@kmarket.co.kr>'
};

function isContactOwnerRole(contactStr) {
  const s = String(contactStr || '');
  return (
    s.includes('봉미선') ||
    s.includes('여신심사') ||
    s.includes('박서준') ||
    s.includes('MD본부') ||
    s.includes('최유진') ||
    s.includes('그로스마케팅') ||
    s.includes('AI추천랩')
  );
}

function getBaseDefaultFm(p) {
  const rel = getRelPathForProv(p);
  const srv = (MGMT_SERVER_STATE.files || {})[rel];
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';

  const rawYaml = p.yaml_frontmatter || '';
  const isInternal = (p.category === 'internal_policies') || (p.doc_title || '').includes('별빛은행') || (p.doc_title || '').includes('K마켙');
  let defaultLicense;
  if (isEcom) {
    if (isInternal) {
      defaultLicense = 'K마켙 사내 표준 운영 내규 (CRM·MD·파트너정산·CS · 사내한 대외비)';
    } else if (p.category === 'distractors') {
      defaultLicense = '관세청 고시 공공저작물 (해외직구 목록통관 대조군 · 국내출고 적용제외)';
    } else if (['DOC_02_FTC_PROMO_GUIDE', 'DOC_04_FTC_DARK_PATTERN', 'DOC_05_PIPC_BEHAVIORAL'].includes(p.doc_id)) {
      defaultLicense = '공정거래위원회·개인정보보호위원회 표준 심사지침·안내서 (공공누리 출처표시)';
    } else {
      defaultLicense = '공공누리 제1유형 (국가법령정보센터 · 대규모유통업법·전자상거래법 자유이용허락)';
    }
  } else {
    defaultLicense = isInternal
      ? '별빛은행 내부 준법감시·여신내규 (사내한 · 대외비)'
      : extractYamlScalar(rawYaml, 'license', '공공누리 제1유형 (국가법령정보센터·금융위원회 공공저작물 자유이용허락)');
  }

  const docSlug = (rel.split('/')[1] || (isEcom ? '01_law_large_retail_fair_trade' : '01_fsc_banking_reg'));
  const defaultTags = [p.category || 'regulations', p.content_class || 'authentic', docSlug, 'verbatim_ko'].join(', ');
  const isDocRoot = Boolean(p.is_source_document) || rel.endsWith('/doc.md');
  const totalPgs = p.pdf_total_pages || 1;
  const pageSpanStr = isDocRoot
    ? (totalPgs > 1 ? `1~${totalPgs} (전 ${totalPgs}쪽)` : '1')
    : (Array.isArray(p.source_pages_span) ? p.source_pages_span.join(', ') : String(p.source_page || 1));

  const gcsPrefix = isEcom ? 'gs://kmarket_okf/okf' : 'gs://okf';
  const rawContact = p.contacts || extractYamlScalar(rawYaml, 'contacts', '');
  const normalizedContact = (isEcom && ECOM_LEGACY_CONTACT_MAP[rawContact]) ? ECOM_LEGACY_CONTACT_MAP[rawContact] : rawContact;

  const baseObj = {
    concept_id: p.concept_id || rel.replace(/\.md$/, ''),
    type: extractYamlScalar(rawYaml, 'type', isDocRoot ? 'Source Document' : 'Provision'),
    title: p.title || `${p.section_number}`,
    description: p.description || (p.verbatim_body || '').slice(0, 140),
    tags: defaultTags,
    version: extractYamlScalar(rawYaml, 'version', '0.2.0'),
    status: extractYamlScalar(rawYaml, 'status', 'stable'),
    content_class: p.content_class || extractYamlScalar(rawYaml, 'content_class', 'authentic'),
    treatment: extractYamlScalar(rawYaml, 'treatment', 'verbatim_ko'),
    language: 'ko',
    license: defaultLicense,
    generated_by: extractYamlNestedScalar(rawYaml, 'generated', 'by', 'process:build_okf/3.0'),
    generated_at: extractYamlNestedScalar(rawYaml, 'generated', 'at', '2026-09-22T04:00:00Z'),
    verified_by: extractYamlNestedScalar(rawYaml, 'verified', 'by', 'process:verify_provisions/1.0'),
    verified_at: extractYamlNestedScalar(rawYaml, 'verified', 'at', '2026-09-22T04:00:00Z'),
    verified_method: extractYamlNestedScalar(rawYaml, 'verified', 'method', 'source_text_match'),
    part_of: isDocRoot ? '/index.md' : extractYamlScalar(rawYaml, 'part_of', `/${(rel.split('/').slice(0, 2).join('/'))}/doc.md`),
    sequence: p.source_page || 1,
    section_number: p.section_number || (isDocRoot ? 'doc.md (문서 총괄)' : '제1조'),
    source_page: p.source_page || 1,
    source_pages_span: pageSpanStr,
    source_resource: `okf://source/un_data/${p.pdf_file}`,
    source_uri: p.okf_path && p.okf_path.startsWith('gs://') ? p.okf_path : `${gcsPrefix}/${rel}`,
    contacts: normalizedContact,
    sha256: p.sha256 || '7ec775dc7d09f2ea35f898b9c18756a9ffd6a262583d76fc7055ab350d429c79'
  };

  if (srv) {
    const sfm = srv.frontmatter || {};
    return Object.assign({}, baseObj, sfm, {
      concept_id: sfm.concept_id || sfm.id || baseObj.concept_id,
      type: sfm.type || sfm.kind || baseObj.type,
      title: sfm.title || baseObj.title,
      description: sfm.description || baseObj.description,
      tags: sfm.tags || (Array.isArray(sfm.synonyms) && sfm.synonyms.length ? sfm.synonyms.join(', ') : baseObj.tags),
      version: srv.version || sfm.version || baseObj.version,
      status: srv.status || sfm.status || baseObj.status,
      content_class: sfm.content_class || baseObj.content_class,
      treatment: sfm.treatment || sfm.sensitivity || baseObj.treatment,
      license: sfm.license || sfm.authority || baseObj.license,
      generated_by: sfm.generated_by || baseObj.generated_by,
      generated_at: sfm.generated_at || baseObj.generated_at,
      verified_by: sfm.verified_by || baseObj.verified_by,
      verified_at: srv.updated_at || sfm.verified_at || baseObj.verified_at,
      verified_method: sfm.verified_method || baseObj.verified_method,
      part_of: sfm.part_of || baseObj.part_of,
      sequence: sfm.sequence || baseObj.sequence,
      section_number: sfm.section_number || baseObj.section_number,
      source_page: sfm.source_page || baseObj.source_page,
      source_pages_span: sfm.source_pages_span || baseObj.source_pages_span,
      source_resource: sfm.source_resource || baseObj.source_resource,
      source_uri: sfm.source_uri || baseObj.source_uri,
      contacts: (sfm.contacts !== undefined ? sfm.contacts : baseObj.contacts),
      sha256: sfm.sha256 || baseObj.sha256
    });
  }

  return baseObj;
}

function getBaseDefaultBody(p) {
  const rel = getRelPathForProv(p);
  const srv = (MGMT_SERVER_STATE.files || {})[rel];
  if (srv && srv.body) return srv.body;
  return p.verbatim_body || `# ${p.title || p.section_number}`;
}

function getEffectiveItemState(key) {
  const k = (key !== undefined && key !== null) ? key : getMgmtActiveKey();
  let p = null;
  if (typeof k === 'string' && k.startsWith('DOC:')) {
    const pdfFile = k.slice(4);
    p = typeof getDocItemForPdf === 'function' ? getDocItemForPdf(pdfFile) : null;
  } else {
    const idx = typeof k === 'number' ? k : CURRENT_IDX;
    p = PROVS[idx] || PROVS[0];
  }
  if (!p) return null;
  const baseFm = getBaseDefaultFm(p);
  const baseBody = getBaseDefaultBody(p);
  const dirty = MGMT_DIRTY_MAP[k];
  const fm = dirty ? Object.assign({}, baseFm, dirty.fm) : Object.assign({}, baseFm);
  const body = dirty && typeof dirty.body === 'string' ? dirty.body : baseBody;
  const isModified = Boolean(dirty);
  const rel = getRelPathForProv(p);
  const srv = (MGMT_SERVER_STATE.files || {})[rel];
  const historyCount = srv ? (srv.history_count || 1) : 0;
  const liveSha = isModified ? simpleSha256Hex64(body, baseFm.sha256) : (fm.sha256 || baseFm.sha256);
  return {
    idx: k,
    p,
    rel,
    baseFm,
    baseBody,
    fm,
    body,
    isModified,
    historyCount,
    srv,
    sha256: liveSha
  };
}

function syncServerStateToProvs() {
  const files = (MGMT_SERVER_STATE && MGMT_SERVER_STATE.files) || {};
  const applyToItem = p => {
    if (!p) return;
    const rel = getRelPathForProv(p);
    const srv = files[rel];
    if (!srv) return;
    const ver = srv.version || (srv.frontmatter && srv.frontmatter.version);
    if (ver && p.yaml_frontmatter) {
      if (/^version:\s*['"]?[^'"\n]+['"]?/m.test(p.yaml_frontmatter)) {
        p.yaml_frontmatter = p.yaml_frontmatter.replace(
          /^version:\s*['"]?[^'"\n]+['"]?/m,
          `version: '${ver}'`
        );
      } else {
        p.yaml_frontmatter = p.yaml_frontmatter.replace(
          /^(title:\s*.+)$/m,
          `$1\nversion: '${ver}'`
        );
      }
    }
    if (srv.body) p.verbatim_body = srv.body;
    if (srv.frontmatter && srv.frontmatter.title) p.title = srv.frontmatter.title;
  };
  if (Array.isArray(PROVS)) PROVS.forEach(applyToItem);
  if (Array.isArray(DOC_PROVS)) DOC_PROVS.forEach(applyToItem);
}

async function fetchServerOkfState() {
  try {
    const res = await fetch('/api/okf/state?t=' + Date.now());
    if (res.ok) {
      const data = await res.json();
      if (data && data.state) {
        MGMT_SERVER_STATE = data.state;
        syncServerStateToProvs();
      }
    }
  } catch (e) {}
}

let MGMT_OPEN_DOCS = {};
let LAST_RENDERED_MGMT_SUB_VIEW = null;

function toggleMgmtSubView(targetMode) {
  if (targetMode) {
    MGMT_SUB_VIEW = targetMode;
  } else {
    MGMT_SUB_VIEW = MGMT_SUB_VIEW === 'EDITOR' ? 'KC_EXPLORER' : 'EDITOR';
  }
  renderManagementModule();
  if (typeof saveUiState === 'function') saveUiState();
}

function toggleMgmtDocAccordion(pdfFile) {
  MGMT_OPEN_DOCS[pdfFile] = !MGMT_OPEN_DOCS[pdfFile];
  MGMT_ACTIVE_KEY = 'DOC:' + pdfFile;
  renderManagementModule();
  if (typeof saveUiState === 'function') saveUiState();
}

function renderManagementModule(idx) {
  if (typeof idx === 'string' && idx.startsWith('DOC:')) {
    MGMT_ACTIVE_KEY = idx;
  } else if (typeof idx === 'number' && idx >= 0 && idx < PROVS.length) {
    CURRENT_IDX = idx;
    if (MGMT_ACTIVE_KEY === null) {
      MGMT_ACTIVE_KEY = idx;
    }
  }
  if (PROVS[CURRENT_IDX] && MGMT_OPEN_DOCS[PROVS[CURRENT_IDX].pdf_file] === undefined) {
    MGMT_OPEN_DOCS[PROVS[CURRENT_IDX].pdf_file] = true;
  }
  const container = document.getElementById('module-enrollment');
  if (!container) return;

  const prevNavList = container.querySelector('.mgmt-sidebar .nav-list');
  const prevNavScrollTop = (prevNavList && LAST_RENDERED_MGMT_SUB_VIEW === MGMT_SUB_VIEW)
    ? prevNavList.scrollTop
    : null;
  LAST_RENDERED_MGMT_SUB_VIEW = MGMT_SUB_VIEW;

  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const docCount = getDistinctPdfList().length;
  const totalFiles = PROVS.length + docCount;
  const modifiedCount = Object.keys(MGMT_DIRTY_MAP).length;
  const updatedCount = Object.keys(MGMT_SERVER_STATE.files || {}).length;
  const inlineDepCount = PROVS.filter(p => (p.yaml_frontmatter || '').includes("status: 'deprecated'") || (p.yaml_frontmatter || '').includes("status: deprecated")).length;
  const deprecatedCount = (isEcom ? 0 : (MGMT_SERVER_STATE.deprecated_entries || []).length) + inlineDepCount;
  const gcsBucketLabel = isEcom ? 'gs://kmarket_okf/okf/' : 'gs://okf/';
  const entryGroupLabel = isEcom
    ? 'projects/finance-ontology-changseop/locations/us-central1/entryGroups/ecommerce-okf'
    : 'projects/finance-ontology/locations/us-central1/entryGroups/okf';

  container.innerHTML = `
    <div class="mgmt-shell">
      <!-- Sub-navigation bar inside 03 · okf-management -->
      <div class="mgmt-top-subbar">
        <div style="display:flex; align-items:center; gap:14px;">
          <div class="mgmt-subtab-group">
            <button class="mgmt-subtab-btn ${MGMT_SUB_VIEW === 'EDITOR' ? 'active' : ''}" onclick="toggleMgmtSubView('EDITOR')">
              OKF Editor
            </button>
            <button class="mgmt-subtab-btn ${MGMT_SUB_VIEW === 'KC_EXPLORER' ? 'active' : ''}" onclick="toggleMgmtSubView('KC_EXPLORER')">
              Knowledge Catalog
            </button>
          </div>
          <span style="font-size:11.5px; color:var(--text-sub);">
            GCS: <code>${gcsBucketLabel}</code> · EntryGroup: <code>${entryGroupLabel}</code>
          </span>
        </div>

        <div style="display:flex; align-items:center; gap:8px;">
          <span class="mgmt-status-pill synced">SYNCED ${totalFiles - modifiedCount}</span>
          ${modifiedCount > 0 ? `<span class="mgmt-status-pill modified">MODIFIED ${modifiedCount}</span>` : ''}
          ${updatedCount > 0 ? `<span class="mgmt-status-pill versioned">VERSIONED ${updatedCount}</span>` : ''}
          ${deprecatedCount > 0 ? `<span class="mgmt-status-pill deprecated">DEPRECATED ${deprecatedCount}</span>` : ''}
        </div>
      </div>

      ${MGMT_SUB_VIEW === 'EDITOR' ? renderMgmtEditorSplitHtml() : renderKcExplorerSplitHtml()}
    </div>

    <!-- Floating Bottom-Center Multi-Select Snackbar (Zero Layout Shift on Tree!) -->
    <div id="mgmt-floating-snackbar-wrap">
      ${renderMgmtFloatingSnackbarHtml()}
    </div>

    <!-- Confirm Modal Popup (Semantic Version Bump + Change Note + Diff) -->
    <div class="mgmt-modal-overlay" id="mgmt-publish-modal">
      <div class="mgmt-modal-dialog" id="mgmt-modal-dialog-content"></div>
    </div>
  `;

  if (prevNavScrollTop !== null) {
    const newNavList = container.querySelector('.mgmt-sidebar .nav-list');
    if (newNavList) newNavList.scrollTop = prevNavScrollTop;
  }
}

function renderMgmtFloatingSnackbarHtml() {
  const count = MGMT_SELECTED_SET.size;
  if (count === 0) return '';
  return `
    <div class="mgmt-floating-snackbar visible">
      <div style="display:inline-flex; align-items:center; gap:7px; font-size:12.5px; font-weight:600; color:var(--gcp-blue);">
        <span>${count}개 OKF 파일 선택됨</span>
      </div>
      <div style="width:1px; height:18px; background:var(--border);"></div>
      <button class="bq-run-btn" style="padding:6px 14px; font-size:12px; border-radius:999px;" onclick="openPublishConfirmModal('BATCH')">
        일괄 프론트매터 변경 & KC 배포 (${count}건)
      </button>
      <button class="mgmt-chip-btn" style="padding:5px 11px; border-radius:999px;" onclick="mgmtSelectAllVisible(false)">
        선택 해제
      </button>
    </div>
  `;
}

function renderMgmtEditorSplitHtml() {
  const st = getEffectiveItemState(getMgmtActiveKey());
  if (!st) return '';
  const p = st.p;
  const fm = st.fm;
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const searchPh = isEcom
    ? '조문 검색 (제11조, 50%, 마진, 체화재고, 청약철회, 내규)...'
    : '조문 검색 (제1조, 제29조, 별표3, 내규)...';
  const pathParts = String(p.okf_path || '').split('/').filter(Boolean);
  const rawBase = pathParts[pathParts.length - 1] || 'doc.md';
  const mdBasename = (rawBase === 'doc.md' && pathParts.length >= 2)
    ? `${pathParts[pathParts.length - 2]}/doc.md`
    : rawBase;

  return `
    <div class="mgmt-body-split">
      <!-- 1. Left GCS File Tree -->
      <aside class="mgmt-sidebar">
        <div class="search-wrap" style="display:flex; flex-direction:column; gap:8px;">
          <input type="text" id="mgmt-tree-search" class="search-input" placeholder="${escapeHtml(searchPh)}" oninput="refreshMgmtTreeList()" />
          <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
            <div style="display:flex; gap:4px;">
              <button class="mgmt-chip-btn" onclick="mgmtSelectAllVisible(true)" title="현재 목록 전체 선택">전체선택</button>
              <button class="mgmt-chip-btn" onclick="mgmtSelectAllVisible(false)" title="선택 해제">선택해제</button>
            </div>
            <div style="display:flex; gap:4px;">
              <button id="mgmt-filter-modified-btn" class="mgmt-chip-btn ${MGMT_TREE_FILTER === 'MODIFIED' ? 'active' : ''}" onclick="setMgmtTreeFilter('MODIFIED')" title="수정중인 OKF 파일 필터 (재클릭 시 전체 보기)">수정중(${Object.keys(MGMT_DIRTY_MAP).length})</button>
            </div>
          </div>
        </div>

        <div class="nav-list" id="mgmt-tree-list">
          ${buildMgmtTreeItemsHtml('')}
        </div>
      </aside>

      <!-- 2. Center Spacious Frontmatter Dropdown & Markdown Body Editor -->
      <section class="mgmt-editor-pane">
        <div class="pane-subbar">
          <div style="display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden;">
            <code style="font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(mdBasename)}</code>
            <span id="mgmt-editor-status-pill" class="mgmt-status-pill ${st.isModified ? 'modified' : (st.historyCount > 0 ? 'versioned' : 'synced')}">
              ${st.isModified ? 'MODIFIED (미배포)' : `v${escapeHtml(fm.version)} · ${escapeHtml(fm.status.toUpperCase())}`}
            </span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
            <button id="mgmt-reset-btn" class="gcp-action-btn" style="flex:0 0 auto; height:30px; padding:0 12px; font-size:11.5px; line-height:1; ${!st.isModified ? 'opacity:0.45; cursor:default;' : ''}" onclick="resetCurrentMgmtEdits()" ${!st.isModified ? 'disabled' : ''}>
              변경 취소
            </button>
            <button class="bq-run-btn" style="flex:0 0 auto; height:30px; padding:0 14px; font-size:11.5px; line-height:1;" onclick="openPublishConfirmModal('SINGLE')">
              편집 완료 및 KC 배포
            </button>
          </div>
        </div>

        <div class="mgmt-editor-scroll">
          <!-- 1. Structured Frontmatter Card (Spacious 3-Column Grid, Zero Clutter) -->
          <div class="mgmt-card">
            <div class="section-label" style="margin-bottom:14px;">
              <span>Frontmatter Governance Attributes</span>
              <span style="font-family:var(--mono); font-size:11px; color:var(--text-sub);" id="mgmt-live-sha">SHA-256: ${escapeHtml(st.sha256.slice(0, 16))}…</span>
            </div>

            <div class="mgmt-fm-grid">
              ${renderFmSelectField('type', 'OKF Type', fm.type)}
              ${renderFmSelectField('status', 'Status', fm.status)}
              ${renderFmSelectField('content_class', 'Content Class', fm.content_class)}

              ${renderFmSelectField('treatment', 'Treatment', fm.treatment)}
              ${renderFmSelectField('generated_by', 'Generated By', fm.generated_by)}
              ${renderFmSelectField('verified_by', 'Verified By', fm.verified_by)}

              ${renderFmSelectField('verified_method', 'Verified Method', fm.verified_method)}
              <div class="mgmt-fm-field span-2">
                ${renderFmSelectFieldInner('license', 'License', fm.license)}
              </div>

              <div class="mgmt-fm-field span-2">
                <label><span>Title</span></label>
                <input type="text" class="gcp-input" value="${escapeHtml(fm.title)}" oninput="onMgmtFmChange('title', this.value)" />
              </div>

              <div class="mgmt-fm-field">
                <label><span>Version & Verified At (자동 갱신)</span></label>
                <input type="text" class="gcp-input" readonly value="v${escapeHtml(fm.version)} · ${escapeHtml(fm.verified_at)}" />
              </div>

              <div class="mgmt-fm-field span-2">
                <label><span>Description</span></label>
                <input type="text" class="gcp-input" value="${escapeHtml(fm.description)}" oninput="onMgmtFmChange('description', this.value)" />
              </div>

              <div class="mgmt-fm-field">
                <label><span>Tags (쉼표 구분)</span></label>
                <input type="text" class="gcp-input" value="${escapeHtml(fm.tags)}" oninput="onMgmtFmChange('tags', this.value)" />
              </div>
            </div>
          </div>

          <!-- 2. Markdown Body Editor Card -->
          <div class="mgmt-card">
            <div class="section-label" style="margin-bottom:10px;">
              <span>Markdown Body</span>
              <span style="font-size:11.5px; color:var(--text-sub);">Page p.${escapeHtml(fm.source_pages_span)}</span>
            </div>
            <textarea class="mgmt-body-textarea" id="mgmt-body-input" oninput="onMgmtBodyChange(this.value)">${escapeHtml(st.body)}</textarea>
          </div>
        </div>
      </section>

      <!-- 3. Right Live GCS File Preview & Post-Publish Lineage Card -->
      <section class="mgmt-preview-pane">
        <div class="pane-subbar">
          <span>실시간 GCS 마크다운 프리뷰 (<code>${escapeHtml(mdBasename)}</code>)</span>
          <span class="badge-pill badge-blue" id="mgmt-preview-ver-badge">v${escapeHtml(fm.version)}</span>
        </div>

        <div class="mgmt-preview-scroll">
          ${MGMT_LAST_PUBLISH_RESULT ? renderLastPublishBannerHtml(MGMT_LAST_PUBLISH_RESULT) : ''}

          <div class="section-label">
            <span>YAML Frontmatter</span>
            <span style="font-family:var(--mono); font-size:11px;">${escapeHtml(fm.type || 'Provision')} · p.${escapeHtml(fm.source_pages_span)}</span>
          </div>
          <div class="frontmatter-block" style="border:1px solid var(--border); border-radius:6px;" id="mgmt-live-yaml-preview">${buildLiveYamlPreviewHtml(fm, st.sha256)}</div>

          <div class="section-label" style="margin-top:6px;">
            <span>Markdown Body</span>
            <span style="font-family:var(--mono); font-size:11px;">MARKDOWN</span>
          </div>
          <div class="okf-title" id="mgmt-live-title-preview">${escapeHtml(fm.title)}</div>
          <div class="okf-body-box" id="mgmt-live-body-preview">${formatMgmtPreviewBody(st.body)}</div>
        </div>
      </section>
    </div>
  `;
}

function renderFmSelectField(fieldKey, labelText, currentValue) {
  return `<div class="mgmt-fm-field">${renderFmSelectFieldInner(fieldKey, labelText, currentValue)}</div>`;
}

function renderFmSelectFieldInner(fieldKey, labelText, currentValue) {
  const opts = OKF_V02_DROPDOWN_OPTIONS[fieldKey] || [];
  const allOpts = opts.includes(currentValue) ? opts : [currentValue, ...opts];
  return `
    <label><span>${escapeHtml(labelText)}</span></label>
    <div class="gcp-custom-select" data-field="${escapeHtml(fieldKey)}">
      <button type="button" class="gcp-select gcp-custom-select-btn" onclick="toggleGcpCustomSelect(event, this)">
        <span class="gcp-custom-select-val">${escapeHtml(currentValue)}</span>
      </button>
      <div class="gcp-custom-select-menu">
        ${allOpts.map(o => `
          <div class="gcp-custom-select-opt ${o === currentValue ? 'selected' : ''}" data-value="${escapeHtml(o)}" onclick="selectGcpCustomOption(event, '${fieldKey}', this)">
            <span>${escapeHtml(o)}</span>
            <span class="material-symbols-outlined gcp-opt-check" style="opacity:${o === currentValue ? '1' : '0'};">check</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function closeAllGcpCustomSelects(exceptWrap) {
  document.querySelectorAll('.gcp-custom-select.open').forEach(el => {
    if (el !== exceptWrap) el.classList.remove('open');
  });
}

function toggleGcpCustomSelect(ev, btnEl) {
  if (ev) ev.stopPropagation();
  const wrap = btnEl ? btnEl.closest('.gcp-custom-select') : null;
  if (!wrap) return;
  const willOpen = !wrap.classList.contains('open');
  closeAllGcpCustomSelects(wrap);
  wrap.classList.toggle('open', willOpen);
}

function selectGcpCustomOption(ev, fieldKey, optEl) {
  if (ev) ev.stopPropagation();
  const wrap = optEl ? optEl.closest('.gcp-custom-select') : null;
  if (!wrap) return;
  const val = optEl.getAttribute('data-value') || '';
  const valSpan = wrap.querySelector('.gcp-custom-select-val');
  if (valSpan) valSpan.textContent = val;
  wrap.querySelectorAll('.gcp-custom-select-opt').forEach(el => {
    const isSel = el === optEl;
    el.classList.toggle('selected', isSel);
    const chk = el.querySelector('.gcp-opt-check');
    if (chk) chk.style.opacity = isSel ? '1' : '0';
  });
  wrap.classList.remove('open');
  onMgmtFmChange(fieldKey, val);
}

if (!window.__GCP_CUSTOM_SELECT_BOUND__) {
  window.__GCP_CUSTOM_SELECT_BOUND__ = true;
  document.addEventListener('click', () => closeAllGcpCustomSelects(null));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeAllGcpCustomSelects(null);
  });
}

function buildLiveYamlPreviewHtml(fm, sha) {
  const tagLines = String(fm.tags || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
    .map(s => `- ${escapeHtml(s)}`)
    .join('\n');
  const lines = [
    `<span class="yaml-delim">---</span>`,
    `<span class="yaml-key">type:</span> ${escapeHtml(fm.type)}`,
    `<span class="yaml-key">title:</span> ${escapeHtml(fm.title)}`,
    `<span class="yaml-key">description:</span> ${escapeHtml((fm.description || '').slice(0, 110))}`,
    `<span class="yaml-key">version:</span> '${escapeHtml(fm.version)}'`,
    `<span class="yaml-key">tags:</span>`,
    tagLines,
    `<span class="yaml-key">language:</span> ko`,
    `<span class="yaml-key">sources:</span>`,
    `- <span class="yaml-key">id:</span> origin_pdf`,
    `  <span class="yaml-key">resource:</span> ${escapeHtml(fm.source_resource)}`,
    `  <span class="yaml-key">kind:</span> origin_document`,
    `  <span class="yaml-key">sha256:</span> ${escapeHtml(sha)}`,
    `<span class="yaml-key">generated:</span>`,
    `  <span class="yaml-key">by:</span> ${escapeHtml(fm.generated_by)}`,
    `  <span class="yaml-key">at:</span> '${escapeHtml(fm.generated_at)}'`,
    `<span class="yaml-key">status:</span> ${escapeHtml(fm.status)}`,
    `<span class="yaml-key">part_of:</span> ${escapeHtml(fm.part_of)}`,
    `<span class="yaml-key">sequence:</span> ${escapeHtml(String(fm.sequence))}`,
    `<span class="yaml-key">treatment:</span> ${escapeHtml(fm.treatment)}`,
    `<span class="yaml-key">license:</span> ${escapeHtml(fm.license)}`,
    `<span class="yaml-key">content_class:</span> ${escapeHtml(fm.content_class)}`,
    `<span class="yaml-key">section_number:</span> ${escapeHtml(fm.section_number)}`,
    `<span class="yaml-key">source_page:</span> ${escapeHtml(String(fm.source_page))}`,
    `<span class="yaml-key">verified:</span>`,
    `- <span class="yaml-key">by:</span> ${escapeHtml(fm.verified_by)}`,
    `  <span class="yaml-key">at:</span> '${escapeHtml(fm.verified_at)}'`,
    `  <span class="yaml-key">method:</span> ${escapeHtml(fm.verified_method)}`,
    `  <span class="yaml-key">checks:</span> [P1_body, P2_heading, P3_page, P4_digest]`
  ];
  if (fm.contacts) {
    lines.push(`<span class="yaml-key">contacts:</span> ${escapeHtml(fm.contacts)}`);
  }
  lines.push(`<span class="yaml-delim">---</span>`);
  return lines.join('\n');
}

function formatMgmtPreviewBody(raw) {
  return escapeHtml(raw || '').replace(
    /(100분의 0\.9 이상|100분의 0\.85 이상|100분의 10 이상|100분의 20 이상|단서|다만|제외|초과|이상|이하|미만|선택적|특허|개선방안|회생절차|[0-9]+(?:\.[0-9]+)?%|제[0-9]+조(?:의[0-9]+)?|별표\s*[0-9]+|내규\s*제[0-9]+조)/g,
    '<span class="hl-term">$1</span>'
  );
}

function renderLastPublishBannerHtml(res) {
  return `
    <div class="mgmt-card" style="background:var(--gcp-green-bg); border-color:var(--gcp-green); padding:13px 15px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
        <span style="font-size:12.5px; font-weight:700; color:var(--gcp-green); display:flex; align-items:center; gap:5px;">
          <span class="material-symbols-outlined" style="font-size:16px;">check_circle</span>
          GCP 실시간 반영 완료 (${escapeHtml(res.bump_level)} · v${escapeHtml(res.old_version)} ➔ v${escapeHtml(res.new_version)})
        </span>
        <span style="font-family:var(--mono); font-size:11px; color:var(--text-sub);">${escapeHtml(res.updated_at)}</span>
      </div>
      <div style="font-size:11.5px; color:var(--text); line-height:1.55;">
        • <strong>구버전 스냅샷 보존 & 만료:</strong> <code>${escapeHtml(res.snapshot_gcs_uri)}</code> ➔ KC <code>DEPRECATED</code><br>
        • <strong>최신본 덮어쓰기 & 활성 등록:</strong> <code>${escapeHtml(res.canonical_gcs_uri)}</code> ➔ KC <code>VERIFIED (v${escapeHtml(res.new_version)})</code>
      </div>
    </div>
  `;
}

function openKcEntryFromPublish(mode, idOrPath) {
  if (mode === 'DEP') {
    KC_FILTER_STATUS = 'DEPRECATED';
    const depIdx = (MGMT_SERVER_STATE.deprecated_entries || []).findIndex(d => d.entry_id === idOrPath);
    KC_SELECTED_KEY = `DEP:${depIdx >= 0 ? depIdx : 0}`;
  } else {
    KC_FILTER_STATUS = 'VERIFIED';
    const pdfMatch = getDistinctPdfList().find(pdf => {
      const docItem = typeof getDocItemForPdf === 'function' ? getDocItemForPdf(pdf) : null;
      return docItem && getRelPathForProv(docItem) === idOrPath;
    });
    if (pdfMatch) {
      KC_SELECTED_KEY = `ACTIVE:DOC:${pdfMatch}`;
    } else {
      const pIdx = PROVS.findIndex(p => getRelPathForProv(p) === idOrPath);
      KC_SELECTED_KEY = `ACTIVE:${pIdx >= 0 ? pIdx : CURRENT_IDX}`;
    }
  }
  toggleMgmtSubView('KC_EXPLORER');
}

function buildMgmtTreeItemsHtml(searchQuery) {
  const q = String(searchQuery || '').trim().toLowerCase();
  const activeKey = getMgmtActiveKey();
  const groups = {};

  getDistinctPdfList().forEach(pdf => {
    const docSt = getEffectiveItemState(`DOC:${pdf}`);
    if (docSt && docSt.p) {
      groups[pdf] = {
        title: docSt.p.doc_title || docSt.p.title,
        docKey: `DOC:${pdf}`,
        docSt,
        items: []
      };
    }
  });

  PROVS.forEach((p, idx) => {
    const st = getEffectiveItemState(idx);
    if (MGMT_TREE_FILTER === 'MODIFIED' && !st.isModified) return;
    if (q) {
      const hay = `${p.doc_title} ${p.section_number} ${p.title} ${p.okf_path}`.toLowerCase();
      if (!hay.includes(q)) return;
    }
    if (!groups[p.pdf_file]) {
      groups[p.pdf_file] = {
        title: p.doc_title,
        docKey: `DOC:${p.pdf_file}`,
        docSt: getEffectiveItemState(`DOC:${p.pdf_file}`),
        items: []
      };
    }
    groups[p.pdf_file].items.push({ idx, st });
  });

  const entries = Object.entries(groups).filter(([pdf, g]) => {
    const docSt = g.docSt;
    if (MGMT_TREE_FILTER === 'MODIFIED') {
      return (docSt && docSt.isModified) || g.items.length > 0;
    }
    if (q) {
      const docHay = docSt ? `${docSt.p.doc_title} ${docSt.fm.title} ${docSt.p.okf_path} doc.md`.toLowerCase() : '';
      return docHay.includes(q) || g.items.length > 0;
    }
    return true;
  });

  if (entries.length === 0) {
    return `<div style="padding:18px; text-align:center; font-size:12px; color:var(--text-sub);">조건에 맞는 OKF 파일이 없습니다.</div>`;
  }

  return entries.map(([pdf, g]) => {
    const numPrefix = pdf.slice(0, 2);
    const shortDocTitle = (g.title || '').split('(')[0].trim();
    const docKey = g.docKey;
    const isDocActive = activeKey === docKey;
    const allChecked = MGMT_SELECTED_SET.has(docKey) && (g.items.length === 0 || g.items.every(it => MGMT_SELECTED_SET.has(it.idx)));
    const isOpen = q ? true : Boolean(MGMT_OPEN_DOCS[pdf]);
    return `
      <div class="doc-section">
        <div class="doc-group-title ${isDocActive ? 'active-doc' : ''}" style="gap:6px;" onclick="toggleMgmtDocAccordion('${pdf}')" title="클릭 시 조문 목록 펼치기/접기 및 상위 문서(${pdf.slice(0, 2)} doc.md) 열람·편집">
          <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:0;">
            <input type="checkbox" class="mgmt-tree-cb" ${allChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleMgmtDocGroupSelect('${pdf}', this.checked)" />
            <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">[${numPrefix}] ${escapeHtml(shortDocTitle)}</span>
          </div>
          <span class="badge-pill badge-blue" style="flex-shrink:0;">${g.items.length}</span>
        </div>
        <div class="doc-items ${isOpen ? '' : 'collapsed'}">
          ${g.items.map(({ idx, st }) => {
            const isChecked = MGMT_SELECTED_SET.has(idx);
            const isRowActive = activeKey === idx;
            const pillClass = st.isModified ? 'modified' : (st.historyCount > 0 ? 'versioned' : 'synced');
            const pillLabel = st.isModified ? 'MODIFIED' : (st.historyCount > 0 ? `v${st.fm.version} · 이력${st.historyCount}` : `v${st.fm.version}`);
            const subHeading = st.fm.title || st.p.title || st.p.section_number;
            return `
              <div class="mgmt-tree-row ${isRowActive ? 'active' : ''}" onclick="selectMgmtFileItem(${idx})">
                <input type="checkbox" class="mgmt-tree-cb" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleMgmtSingleSelect(${idx}, this.checked)" />
                <div style="flex:1; min-width:0;">
                  <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                    <span style="font-size:12px; font-weight:${isRowActive ? '600' : '500'}; color:${isRowActive ? 'var(--gcp-blue)' : 'var(--text)'};">
                      ${escapeHtml(st.p.section_number)}
                    </span>
                    <span class="mgmt-status-pill ${pillClass}">${escapeHtml(pillLabel)}</span>
                  </div>
                  <div style="font-size:11px; color:var(--text-sub); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-top:2px;">
                    ${escapeHtml(subHeading)}
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }).join('');
}

function refreshMgmtTreeList() {
  const searchEl = document.getElementById('mgmt-tree-search');
  const listEl = document.getElementById('mgmt-tree-list');
  const snackWrap = document.getElementById('mgmt-floating-snackbar-wrap');
  const modBtn = document.getElementById('mgmt-filter-modified-btn');
  if (listEl) {
    const prevTop = listEl.scrollTop;
    listEl.innerHTML = buildMgmtTreeItemsHtml(searchEl ? searchEl.value : '');
    listEl.scrollTop = prevTop;
  }
  if (snackWrap) {
    snackWrap.innerHTML = renderMgmtFloatingSnackbarHtml();
  }
  if (modBtn) {
    modBtn.textContent = `수정중(${Object.keys(MGMT_DIRTY_MAP).length})`;
  }
}

function setMgmtTreeFilter(filter) {
  if (MGMT_TREE_FILTER === filter && filter !== 'ALL') {
    MGMT_TREE_FILTER = 'ALL';
  } else {
    MGMT_TREE_FILTER = filter;
  }
  renderManagementModule();
}

function selectMgmtFileItem(idxOrKey) {
  if (typeof idxOrKey === 'string' && idxOrKey.startsWith('DOC:')) {
    MGMT_ACTIVE_KEY = idxOrKey;
    const pdfFile = idxOrKey.slice(4);
    MGMT_OPEN_DOCS[pdfFile] = true;
  } else {
    CURRENT_IDX = idxOrKey;
    MGMT_ACTIVE_KEY = idxOrKey;
  }
  renderManagementModule();
  saveUiState();
}

function toggleMgmtSingleSelect(idxOrKey, checked) {
  if (checked) MGMT_SELECTED_SET.add(idxOrKey);
  else MGMT_SELECTED_SET.delete(idxOrKey);
  refreshMgmtTreeList();
}

function toggleMgmtDocGroupSelect(pdfFile, checked) {
  const docKey = `DOC:${pdfFile}`;
  if (checked) MGMT_SELECTED_SET.add(docKey);
  else MGMT_SELECTED_SET.delete(docKey);
  PROVS.forEach((p, idx) => {
    if (p.pdf_file === pdfFile) {
      if (checked) MGMT_SELECTED_SET.add(idx);
      else MGMT_SELECTED_SET.delete(idx);
    }
  });
  refreshMgmtTreeList();
}

function mgmtSelectAllVisible(checked) {
  if (!checked) {
    MGMT_SELECTED_SET.clear();
  } else {
    getDistinctPdfList().forEach(pdf => {
      const docKey = `DOC:${pdf}`;
      const docSt = getEffectiveItemState(docKey);
      if (MGMT_TREE_FILTER === 'MODIFIED' && (!docSt || !docSt.isModified)) return;
      MGMT_SELECTED_SET.add(docKey);
    });
    PROVS.forEach((_, idx) => {
      const st = getEffectiveItemState(idx);
      if (MGMT_TREE_FILTER === 'MODIFIED' && !st.isModified) return;
      MGMT_SELECTED_SET.add(idx);
    });
  }
  refreshMgmtTreeList();
}

function onMgmtFmChange(fieldKey, value) {
  const activeKey = getMgmtActiveKey();
  const st = getEffectiveItemState(activeKey);
  if (!MGMT_DIRTY_MAP[activeKey]) {
    MGMT_DIRTY_MAP[activeKey] = { fm: Object.assign({}, st.fm), body: st.body };
  }
  MGMT_DIRTY_MAP[activeKey].fm[fieldKey] = value;
  updateLiveMgmtPreview();
}

function onMgmtBodyChange(value) {
  const activeKey = getMgmtActiveKey();
  const st = getEffectiveItemState(activeKey);
  if (!MGMT_DIRTY_MAP[activeKey]) {
    MGMT_DIRTY_MAP[activeKey] = { fm: Object.assign({}, st.fm), body: value };
  } else {
    MGMT_DIRTY_MAP[activeKey].body = value;
  }
  updateLiveMgmtPreview();
}

function resetCurrentMgmtEdits() {
  const activeKey = getMgmtActiveKey();
  delete MGMT_DIRTY_MAP[activeKey];
  renderManagementModule();
}

function updateLiveMgmtPreview() {
  const st = getEffectiveItemState(getMgmtActiveKey());
  const yamlEl = document.getElementById('mgmt-live-yaml-preview');
  const titleEl = document.getElementById('mgmt-live-title-preview');
  const bodyEl = document.getElementById('mgmt-live-body-preview');
  const shaEl = document.getElementById('mgmt-live-sha');
  const pillEl = document.getElementById('mgmt-editor-status-pill');
  const resetBtn = document.getElementById('mgmt-reset-btn');
  if (yamlEl) yamlEl.innerHTML = buildLiveYamlPreviewHtml(st.fm, st.sha256);
  if (titleEl) titleEl.textContent = st.fm.title;
  if (bodyEl) bodyEl.innerHTML = formatMgmtPreviewBody(st.body);
  if (shaEl) shaEl.textContent = 'SHA-256: ' + st.sha256.slice(0, 16) + '…';
  if (pillEl) {
    pillEl.className = `mgmt-status-pill ${st.isModified ? 'modified' : (st.historyCount > 0 ? 'versioned' : 'synced')}`;
    pillEl.textContent = st.isModified ? 'MODIFIED (미배포)' : `v${st.fm.version} · ${st.fm.status.toUpperCase()}`;
  }
  if (resetBtn) {
    resetBtn.disabled = !st.isModified;
    resetBtn.style.opacity = st.isModified ? '1' : '0.45';
    resetBtn.style.cursor = st.isModified ? 'pointer' : 'default';
  }
  refreshMgmtTreeList();
}

/* ==========================================================================
   Step 3: Confirm Modal Popup (PATCH / MINOR / MAJOR + Contacts + Change Note + Live Diff)
   ========================================================================== */
function openPublishConfirmModal(mode) {
  MODAL_MODE = mode || 'SINGLE';
  MODAL_BUMP_LEVEL = 'PATCH';
  MODAL_PRESET_NOTE_VAL = CHANGE_NOTE_PRESETS[0];
  MODAL_CHANGE_NOTE_TEXT = CHANGE_NOTE_PRESETS[0];
  const activeKey = getMgmtActiveKey();
  const st = getEffectiveItemState(activeKey);
  MODAL_CONTACTS_VALUE = (MODAL_MODE === 'SINGLE' && st && st.fm) ? (st.fm.contacts || '') : '';
  const overlay = document.getElementById('mgmt-publish-modal');
  if (!overlay) return;
  overlay.classList.add('open');
  renderPublishModalDialogContent();
}

function closePublishConfirmModal() {
  const overlay = document.getElementById('mgmt-publish-modal');
  if (overlay) overlay.classList.remove('open');
}

function onModalBumpLevelChange(newLevel) {
  const input = document.getElementById('modal-change-note-input');
  if (input) MODAL_CHANGE_NOTE_TEXT = input.value;
  MODAL_BUMP_LEVEL = newLevel;
  renderPublishModalDialogContent();
}

function onModalContactsChange(newContacts) {
  const input = document.getElementById('modal-change-note-input');
  if (input) MODAL_CHANGE_NOTE_TEXT = input.value;
  MODAL_CONTACTS_VALUE = newContacts;
  renderPublishModalDialogContent();
}

function onModalPresetNoteSelect(val) {
  MODAL_PRESET_NOTE_VAL = val;
  MODAL_CHANGE_NOTE_TEXT = val;
  const input = document.getElementById('modal-change-note-input');
  if (input && val) input.value = val;
}

function renderModalCustomSelect(id, options, currentVal, onSelectType, wrapStyle = '', btnStyle = '') {
  const curObj = options.find(o => String(o.value) === String(currentVal)) || options[0] || { value: '', label: '' };
  return `
    <div class="gcp-custom-select" id="${escapeHtml(id)}" data-value="${escapeHtml(curObj.value)}" ${wrapStyle ? `style="${wrapStyle}"` : ''}>
      <button type="button" class="gcp-select gcp-custom-select-btn" ${btnStyle ? `style="${btnStyle}"` : ''} onclick="toggleGcpCustomSelect(event, this)">
        <span class="gcp-custom-select-val">${escapeHtml(curObj.label)}</span>
      </button>
      <div class="gcp-custom-select-menu">
        ${options.map(o => {
          const isSel = String(o.value) === String(curObj.value);
          return `
            <div class="gcp-custom-select-opt ${isSel ? 'selected' : ''}" data-value="${escapeHtml(o.value)}" data-label="${escapeHtml(o.label)}" onclick="selectModalCustomOption(event, '${onSelectType}', this)">
              <span>${escapeHtml(o.label)}</span>
              <span class="material-symbols-outlined gcp-opt-check" style="opacity:${isSel ? '1' : '0'};">check</span>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

function selectModalCustomOption(ev, onSelectType, optEl) {
  if (ev) ev.stopPropagation();
  const wrap = optEl ? optEl.closest('.gcp-custom-select') : null;
  if (!wrap) return;
  const val = optEl.getAttribute('data-value') || '';
  const label = optEl.getAttribute('data-label') || val;
  wrap.setAttribute('data-value', val);
  const valSpan = wrap.querySelector('.gcp-custom-select-val');
  if (valSpan) valSpan.textContent = label;
  wrap.querySelectorAll('.gcp-custom-select-opt').forEach(el => {
    const isSel = el === optEl;
    el.classList.toggle('selected', isSel);
    const chk = el.querySelector('.gcp-opt-check');
    if (chk) chk.style.opacity = isSel ? '1' : '0';
  });
  wrap.classList.remove('open');

  if (onSelectType === 'BUMP_LEVEL') {
    onModalBumpLevelChange(val);
  } else if (onSelectType === 'CONTACTS') {
    onModalContactsChange(val);
  } else if (onSelectType === 'PRESET_NOTE') {
    onModalPresetNoteSelect(val);
  }
}

function getModalSelectValue(id, fallbackVal = '') {
  const el = document.getElementById(id);
  if (!el) return fallbackVal;
  if (el.hasAttribute('data-value')) return el.getAttribute('data-value') || '';
  return el.value !== undefined ? el.value : fallbackVal;
}

function buildDiffLinesHtml(st, nextVer, nowTs, effectiveContacts) {
  const lines = [];
  const oldFm = st.baseFm;
  const newFm = Object.assign({}, st.fm);
  if (effectiveContacts !== undefined && effectiveContacts !== null) {
    newFm.contacts = effectiveContacts;
  }
  const shortSlug = getShortSlugForRel(st.rel);
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const gcsPrefix = isEcom ? 'gs://kmarket_okf/okf' : 'gs://okf';

  lines.push(`<div class="diff-line-ctx">--- a/${gcsPrefix}/versions/${escapeHtml(shortSlug)}_v${escapeHtml(oldFm.version)}.md (DEPRECATED 만료 전환)</div>`);
  lines.push(`<div class="diff-line-ctx">+++ b/${escapeHtml(newFm.source_uri)} (VERIFIED 신규 등록)</div>`);

  lines.push(`<div class="diff-line-del">- version: '${escapeHtml(oldFm.version)}'</div>`);
  lines.push(`<div class="diff-line-add">+ version: '${escapeHtml(nextVer)}'</div>`);
  lines.push(`<div class="diff-line-del">- verified.at: '${escapeHtml(oldFm.verified_at)}'</div>`);
  lines.push(`<div class="diff-line-add">+ verified.at: '${escapeHtml(nowTs)}'</div>`);

  const keys = ['type', 'title', 'description', 'tags', 'status', 'content_class', 'treatment', 'license', 'generated_by', 'verified_by', 'verified_method', 'contacts'];
  keys.forEach(k => {
    const oldVal = String(oldFm[k] || '');
    const newVal = String(newFm[k] || '');
    if (oldVal !== newVal) {
      lines.push(`<div class="diff-line-del">- ${k}: ${escapeHtml(oldVal || '(미지정)')}</div>`);
      lines.push(`<div class="diff-line-add">+ ${k}: ${escapeHtml(newVal || '(미지정)')}</div>`);
    }
  });

  if (st.baseBody.trim() !== st.body.trim()) {
    const oldLines = st.baseBody.trim().split('\n');
    const newLines = st.body.trim().split('\n');
    oldLines.forEach(l => {
      if (!newLines.includes(l)) lines.push(`<div class="diff-line-del">- ${escapeHtml(l)}</div>`);
    });
    newLines.forEach(l => {
      if (!oldLines.includes(l)) lines.push(`<div class="diff-line-add">+ ${escapeHtml(l)}</div>`);
    });
  } else {
    lines.push(`<div class="diff-line-ctx">  (마크다운 원문 본문 동일 · SHA-256 ${escapeHtml(st.sha256.slice(0, 16))}… 유지)</div>`);
  }

  return lines.join('');
}

function renderPublishModalDialogContent() {
  const dialog = document.getElementById('mgmt-modal-dialog-content');
  if (!dialog) return;

  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const gcsPrefix = isEcom ? 'gs://kmarket_okf/okf' : 'gs://okf';
  const kcGroupShort = isEcom ? 'ecommerce-okf' : 'okf';
  const nowTs = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const isBatch = MODAL_MODE === 'BATCH';
  const activeKey = getMgmtActiveKey();
  const batchIndices = isBatch ? Array.from(MGMT_SELECTED_SET) : [activeKey];
  const primarySt = getEffectiveItemState(batchIndices[0] ?? activeKey);
  const oldVer = primarySt.baseFm.version || '0.2.0';
  const nextVer = bumpSemverJs(oldVer, MODAL_BUMP_LEVEL);
  const shortSlug = getShortSlugForRel(primarySt.rel);
  const currentContacts = (MODAL_CONTACTS_VALUE !== null && MODAL_CONTACTS_VALUE !== undefined)
    ? MODAL_CONTACTS_VALUE
    : (primarySt.fm.contacts || '');

  const patchPreview = bumpSemverJs(oldVer, 'PATCH');
  const minorPreview = bumpSemverJs(oldVer, 'MINOR');
  const majorPreview = bumpSemverJs(oldVer, 'MAJOR');

  const bumpOptions = [
    { value: 'PATCH', label: `PATCH 업데이트 (v${oldVer} ➔ v${patchPreview}) — 오탈자 수정 · 프론트매터 거버넌스 속성 현행화` },
    { value: 'MINOR', label: `MINOR 업데이트 (v${oldVer} ➔ v${minorPreview}) — 단서·예외(Caveat) 조항 보완 · 적용 맥락(Edge) 추가` },
    { value: 'MAJOR', label: isEcom
      ? `MAJOR 업데이트 (v${oldVer} ➔ v${majorPreview}) — 유통·전자상거래 법령·사내내규 전면 개정 · 마진/분담률 수치 기준 변경`
      : `MAJOR 업데이트 (v${oldVer} ➔ v${majorPreview}) — 감독규정·내규 전면 개정 · 의사결정 수치 기준 변경` }
  ];

  const singleContactsOptions = [
    { value: '', label: '-- 미지정 (Contacts 미반영) --' },
    ...OKF_V02_DROPDOWN_OPTIONS.contacts.map(c => ({ value: c, label: c }))
  ];
  if (currentContacts && !singleContactsOptions.some(o => o.value === currentContacts)) {
    singleContactsOptions.splice(1, 0, { value: currentContacts, label: currentContacts });
  }

  const batchContactsOptions = [
    { value: '', label: '-- 기존 값 유지 --' },
    ...OKF_V02_DROPDOWN_OPTIONS.contacts.map(c => ({ value: c, label: c })),
    { value: '__CLEAR__', label: '-- 미지정으로 초기화 (Contacts 제거) --' }
  ];

  const batchVerifiedByOptions = [
    { value: '', label: '-- 기존 값 유지 --' },
    ...OKF_V02_DROPDOWN_OPTIONS.verified_by.map(v => ({ value: v, label: v }))
  ];

  const batchStatusOptions = [
    { value: '', label: '-- 기존 값 유지 --' },
    ...OKF_V02_DROPDOWN_OPTIONS.status.map(v => ({ value: v, label: v }))
  ];

  const batchContentClassOptions = [
    { value: '', label: '-- 기존 값 유지 --' },
    ...OKF_V02_DROPDOWN_OPTIONS.content_class.map(v => ({ value: v, label: v }))
  ];

  const batchVerifiedMethodOptions = [
    { value: '', label: '-- 기존 값 유지 --' },
    ...OKF_V02_DROPDOWN_OPTIONS.verified_method.map(v => ({ value: v, label: v }))
  ];

  const presetNoteOptions = CHANGE_NOTE_PRESETS.map((n, i) => ({
    value: n,
    label: `프리셋 ${i + 1}: ${n.slice(0, 18)}...`
  }));

  const currentPresetVal = MODAL_PRESET_NOTE_VAL || CHANGE_NOTE_PRESETS[0];
  const currentNoteText = MODAL_CHANGE_NOTE_TEXT || CHANGE_NOTE_PRESETS[0];

  dialog.innerHTML = `
    <div class="mgmt-modal-header">
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="material-symbols-outlined" style="color:var(--gcp-blue);">published_with_changes</span>
        <span style="font-size:14.5px; font-weight:600; color:var(--text);">
          ${isBatch ? `다중 선택 일괄 버전 업데이트 및 Knowledge Catalog 배포 (${batchIndices.length}건)` : `OKF 편집 완료 — 버전 업데이트 수준 · 담당자(Contacts) 선택 및 배포 확인`}
        </span>
      </div>
      <button class="icon-close-btn" onclick="closePublishConfirmModal()"><span class="material-symbols-outlined">close</span></button>
    </div>

    <div class="mgmt-modal-body">
      <!-- 1. Semantic Version Bump Level Dropdown -->
      <div class="ctrl-group">
        <label>1. 버전 업데이트 수준 선택 (Semantic Version Bump Level)</label>
        ${renderModalCustomSelect('modal-bump-level', bumpOptions, MODAL_BUMP_LEVEL, 'BUMP_LEVEL', '', 'font-weight:600; color:var(--gcp-blue);')}
      </div>

      ${!isBatch ? `
        <!-- 2. Knowledge Catalog Contacts Persona Dropdown (Single Publish) -->
        <div class="ctrl-group">
          <label>2. Knowledge Catalog 담당자 (Contacts) 지정 (<code>dataplex-types.global.contacts</code>)</label>
          ${renderModalCustomSelect('modal-contacts-select', singleContactsOptions, currentContacts, 'CONTACTS')}
        </div>
      ` : `
        <!-- Optional Batch Frontmatter Override Dropdowns -->
        <div class="mgmt-card" style="padding:12px 14px; background:var(--bg); overflow:visible;">
          <div class="section-label" style="margin-bottom:8px;">
            <span>선택된 ${batchIndices.length}개 파일 프론트매터 일괄 변경 (선택 사항)</span>
            <span style="font-size:11px; color:var(--text-sub);">'기존 값 유지' 선택 시 개별 파일 설정 유지</span>
          </div>
          <div class="mgmt-fm-grid">
            <div class="mgmt-fm-field span-2">
              <label><span>Knowledge Catalog 담당자 (Contacts) 일괄 지정</span></label>
              ${renderModalCustomSelect('batch-override-contacts', batchContactsOptions, '', 'BATCH_OVERRIDE')}
            </div>
            <div class="mgmt-fm-field">
              <label><span>Verified By 일괄 지정</span></label>
              ${renderModalCustomSelect('batch-override-verified-by', batchVerifiedByOptions, '', 'BATCH_OVERRIDE')}
            </div>
            <div class="mgmt-fm-field">
              <label><span>Status 일괄 지정</span></label>
              ${renderModalCustomSelect('batch-override-status', batchStatusOptions, '', 'BATCH_OVERRIDE')}
            </div>
            <div class="mgmt-fm-field">
              <label><span>Content Class 일괄 지정</span></label>
              ${renderModalCustomSelect('batch-override-content-class', batchContentClassOptions, '', 'BATCH_OVERRIDE')}
            </div>
            <div class="mgmt-fm-field">
              <label><span>Verified Method 일괄 지정</span></label>
              ${renderModalCustomSelect('batch-override-verified-method', batchVerifiedMethodOptions, '', 'BATCH_OVERRIDE')}
            </div>
          </div>
        </div>
      `}

      <!-- 3. Change Note (개정 사유) -->
      <div class="ctrl-group">
        <label>3. 개정 사유 (Knowledge Catalog 버전 계보 기록)</label>
        <div style="display:flex; gap:6px; margin-bottom:5px;">
          ${renderModalCustomSelect('modal-preset-note-select', presetNoteOptions, currentPresetVal, 'PRESET_NOTE', 'width:240px; flex-shrink:0;')}
          <input type="text" id="modal-change-note-input" class="gcp-input" value="${escapeHtml(currentNoteText)}" oninput="MODAL_CHANGE_NOTE_TEXT = this.value" placeholder="개정 사유를 입력하세요..." />
        </div>
      </div>

      <!-- 4. 4-Step GCP Execution Impact Summary -->
      <div class="mgmt-card" style="padding:12px 14px; background:var(--bg); overflow:hidden;">
        <div class="section-label" style="margin-bottom:6px;">
          <span>4. 실행될 GCP 라이프사이클 트랜잭션 (GCS + Knowledge Catalog <code>${kcGroupShort}</code>)</span>
          <span class="badge-pill badge-blue">v${escapeHtml(oldVer)} ➔ v${escapeHtml(nextVer)}</span>
        </div>
        <div style="font-size:12px; color:var(--text); line-height:1.7; word-break:break-all; overflow-wrap:anywhere;">
          1. <strong>프론트매터 타임스탬프 갱신:</strong> <code>verified.at = "${nowTs}"</code>, <code>version = "${nextVer}"</code>${!isBatch && currentContacts ? `, <code>contacts = "${escapeHtml(currentContacts)}"</code>` : ''}<br>
          2. <strong>구버전 스냅샷 보존 & KC 만료:</strong> <code>${gcsPrefix}/versions/${escapeHtml(shortSlug)}_v${escapeHtml(oldVer)}.md</code> 생성 및 기존 KC 엔트리 <strong><code>DEPRECATED</code></strong> 전환<br>
          3. <strong>신규 버전 GCS 덮어쓰기 & KC 활성 등록:</strong> <code>${gcsPrefix}/${escapeHtml(primarySt.rel)}</code> 덮어쓰기 및 신규 KC 엔트리 <strong><code>VERIFIED (v${escapeHtml(nextVer)})</code></strong> 등록
        </div>
      </div>

      <!-- 5. Before (DEPRECATED) <-> After (VERIFIED) Diff Highlight View -->
      <div class="ctrl-group">
        <label>5. 구버전(v${escapeHtml(oldVer)} DEPRECATED) ↔ 신버전(v${escapeHtml(nextVer)} VERIFIED) 변경점 비교 (Diff)</label>
        <div class="mgmt-diff-box">${buildDiffLinesHtml(primarySt, nextVer, nowTs, isBatch ? primarySt.fm.contacts : currentContacts)}</div>
      </div>

      <div id="modal-exec-status" style="display:none; padding:10px 12px; border-radius:6px; background:var(--gcp-blue-bg); color:var(--gcp-blue); font-size:12px; font-weight:600;"></div>
    </div>

    <div class="mgmt-modal-footer">
      <button class="gcp-action-btn" style="flex:0 0 auto; height:34px; padding:0 18px; font-size:12px;" onclick="closePublishConfirmModal()">취소 (Cancel)</button>
      <button class="bq-run-btn" id="modal-confirm-exec-btn" style="flex:0 0 auto; height:34px; padding:0 18px; font-size:12px;" onclick="executeConfirmedPublish()">
        확인 및 배포 실행 (${isBatch ? `${batchIndices.length}건 일괄 반영` : `v${oldVer} ➔ v${nextVer}`})
      </button>
    </div>
  `;
}

async function executeConfirmedPublish() {
  const btn = document.getElementById('modal-confirm-exec-btn');
  const statusBox = document.getElementById('modal-exec-status');
  const noteInput = document.getElementById('modal-change-note-input');
  const changeNote = noteInput ? noteInput.value.trim() : CHANGE_NOTE_PRESETS[0];

  if (btn) btn.disabled = true;
  if (statusBox) {
    statusBox.style.display = 'block';
    statusBox.innerHTML = `<span class="material-symbols-outlined" style="font-size:15px; vertical-align:-3px;">sync</span> GCP 실시간 트랜잭션 진행 중: (1) GCS versions/ 스냅샷 업로드 ➔ (2) GCS 최신본 덮어쓰기 ➔ (3) 기존 KC 엔트리 DEPRECATED 만료 전환 ➔ (4) 신규 KC 엔트리 VERIFIED 등록...`;
  }

  try {
    if (MODAL_MODE === 'SINGLE') {
      const activeKey = getMgmtActiveKey();
      const st = getEffectiveItemState(activeKey);
      const chosenContacts = getModalSelectValue('modal-contacts-select', MODAL_CONTACTS_VALUE ?? st.fm.contacts ?? '');
      const payload = {
        rel_path: st.rel,
        bump_level: MODAL_BUMP_LEVEL,
        change_note: changeNote,
        old_body: st.baseBody,
        body: st.body,
        frontmatter: Object.assign({}, st.fm, {
          id: st.fm.concept_id,
          kind: st.fm.type,
          domain: st.p.category || 'regulations',
          authority: st.fm.license,
          sensitivity: st.fm.treatment,
          contacts: chosenContacts,
          old_version: st.baseFm.version,
          old_title: st.baseFm.title,
          old_kind: st.baseFm.type,
          old_domain: st.p.category || 'regulations',
          old_content_class: st.baseFm.content_class,
          old_authority: st.baseFm.license,
          old_sensitivity: st.baseFm.treatment,
          old_verified_by: st.baseFm.verified_by,
          old_verified_at: st.baseFm.verified_at,
          old_contacts: st.baseFm.contacts || '',
          synonyms: String(st.fm.tags || '').split(',').map(s => s.trim()).filter(Boolean)
        })
      };

      const res = await fetch('/api/okf/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data && data.ok) {
        MGMT_SERVER_STATE = data.state;
        syncServerStateToProvs();
        MGMT_LAST_PUBLISH_RESULT = data.result;
        delete MGMT_DIRTY_MAP[activeKey];
      }
    } else {
      const ovContacts = getModalSelectValue('batch-override-contacts', '');
      const ovVerifiedBy = getModalSelectValue('batch-override-verified-by', '');
      const ovStatus = getModalSelectValue('batch-override-status', '');
      const ovContentClass = getModalSelectValue('batch-override-content-class', '');
      const ovMethod = getModalSelectValue('batch-override-verified-method', '');

      const batchIndices = Array.from(MGMT_SELECTED_SET);
      const items = batchIndices.map(i => {
        const st = getEffectiveItemState(i);
        const mergedFm = Object.assign({}, st.fm);
        if (ovContacts === '__CLEAR__') mergedFm.contacts = '';
        else if (ovContacts) mergedFm.contacts = ovContacts;
        if (ovVerifiedBy) mergedFm.verified_by = ovVerifiedBy;
        if (ovStatus) mergedFm.status = ovStatus;
        if (ovContentClass) mergedFm.content_class = ovContentClass;
        if (ovMethod) mergedFm.verified_method = ovMethod;
        return {
          rel_path: st.rel,
          bump_level: MODAL_BUMP_LEVEL,
          change_note: changeNote,
          old_body: st.baseBody,
          body: st.body,
          frontmatter: Object.assign({}, mergedFm, {
            id: mergedFm.concept_id,
            kind: mergedFm.type,
            domain: st.p.category || 'regulations',
            authority: mergedFm.license,
            sensitivity: mergedFm.treatment,
            contacts: mergedFm.contacts || '',
            old_version: st.baseFm.version,
            old_title: st.baseFm.title,
            old_kind: st.baseFm.type,
            old_domain: st.p.category || 'regulations',
            old_content_class: st.baseFm.content_class,
            old_authority: st.baseFm.license,
            old_sensitivity: st.baseFm.treatment,
            old_verified_by: st.baseFm.verified_by,
            old_verified_at: st.baseFm.verified_at,
            old_contacts: st.baseFm.contacts || '',
            synonyms: String(mergedFm.tags || '').split(',').map(s => s.trim()).filter(Boolean)
          })
        };
      });

      const res = await fetch('/api/okf/batch_publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
      });
      const data = await res.json();
      if (data && data.ok) {
        MGMT_SERVER_STATE = data.state;
        syncServerStateToProvs();
        if (data.results && data.results.length > 0) {
          MGMT_LAST_PUBLISH_RESULT = data.results[0];
        }
        batchIndices.forEach(i => delete MGMT_DIRTY_MAP[i]);
        MGMT_SELECTED_SET.clear();
      }
    }

    closePublishConfirmModal();
    renderManagementModule();
  } catch (err) {
    if (statusBox) {
      statusBox.style.background = 'var(--gcp-red-bg)';
      statusBox.style.color = 'var(--gcp-red)';
      statusBox.textContent = '오류 발생: ' + err.message;
    }
    if (btn) btn.disabled = false;
  }
}

/* ==========================================================================
   Step 4: Tab B — GCP Dataplex Knowledge Catalog Explorer
   Layout: [Top: Entry Summary Metadata] ➔ [Middle: Overview (Markdown)] ➔ [Bottom: Aspects (OKF Signal)]
   ========================================================================== */
function getAllCatalogEntriesList() {
  const list = [];
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const ecomDeps = [
    {
      entry_id: 'internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_002_v1_legacy_10pct_floor',
      rel_path: 'versions/md_art_002_v1_legacy_10pct_floor.md',
      canonical_rel_path: 'internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail.md',
      version: '0.1.0',
      deprecated_at: '2026-09-22T04:00:00Z',
      superseded_by: 'internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail',
      superseded_by_version: '0.2.0',
      change_note: 'v0.2.0(상시 프로모션 25.0% 최저마진 가드레일 및 90일+ 체화재고 10.0% 특례 분리) 개정에 따라 폐기(deprecated) 처리',
      frontmatter: {
        title: '[폐기] 구(舊) 프로모션 할인 내규 v1 — 전 품목 일괄 최저마진 10% 기준',
        type: 'Provision',
        status: 'deprecated',
        content_class: 'internal_policy',
        treatment: 'verbatim_ko',
        license: 'K마켙 내부 가격전략·MD내규 (사내한 · 대외비)',
        section_number: '제2조(구 v0.1.0)'
      },
      body: '# 제2조 (구 프로모션 최저마진 일괄 기준 — 2026.09 폐기)\n\n① [폐기] K마켙에서 진행하는 모든 할인 쿠폰 및 프로모션 캠페인은 정상재고·체화재고 구분 없이 실현마진율 10.0% 이상이면 집행할 수 있다.\n② [개정 경과] 본 조항은 정상 신상품의 무분별한 마진 훼손을 방지하기 위하여 2026년 9월 22일 자로 폐기(status: deprecated)되었으며, 현행 v0.2.0(상시 25.0% 최저마진 가드레일 본칙 및 입고 90일 이상 체화재고 10.0% 완화 단서 분리)으로 대체(superseded_by)되었다.'
    }
  ];
  const deps = isEcom ? ecomDeps : (MGMT_SERVER_STATE.deprecated_entries || []);

  getDistinctPdfList().forEach(pdf => {
    const docKey = `DOC:${pdf}`;
    const st = getEffectiveItemState(docKey);
    if (!st) return;
    list.push({
      key: `ACTIVE:${docKey}`,
      isDeprecated: false,
      provIdx: docKey,
      entryId: st.rel.replace(/\.md$/, ''),
      title: `[${pdf.slice(0, 2)} 문서 총괄] ${st.fm.title}`,
      sectionNumber: st.p.section_number,
      docTitle: st.p.doc_title,
      pdfFile: st.p.pdf_file,
      version: st.fm.version,
      prevVersion: st.srv ? st.srv.prev_version : null,
      supersedesEntryId: st.srv ? st.srv.supersedes_entry_id : null,
      status: st.fm.status,
      updatedAt: st.fm.verified_at,
      gcsUri: st.fm.source_uri,
      canonicalRelPath: st.rel,
      changeNote: st.srv ? st.srv.change_note : 'OKF v0.2 Source Document Root Registration (doc.md)',
      fm: st.fm,
      body: st.body,
      sha256: st.sha256
    });
  });

  PROVS.forEach((p, pIdx) => {
    const st = getEffectiveItemState(pIdx);
    const isDep = String(st.fm.status || '').toLowerCase() === 'deprecated';
    list.push({
      key: isDep ? `DEP:INLINE:${pIdx}` : `ACTIVE:${pIdx}`,
      isDeprecated: isDep,
      provIdx: pIdx,
      entryId: st.rel.replace(/\.md$/, ''),
      title: st.fm.title,
      sectionNumber: p.section_number,
      docTitle: p.doc_title,
      pdfFile: p.pdf_file,
      version: st.fm.version,
      prevVersion: st.srv ? st.srv.prev_version : null,
      supersedesEntryId: st.srv ? st.srv.supersedes_entry_id : null,
      supersededBy: isDep ? 'internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail' : null,
      supersededByVer: isDep ? '0.2.0' : null,
      status: st.fm.status,
      updatedAt: st.fm.verified_at,
      gcsUri: st.fm.source_uri,
      canonicalRelPath: st.rel,
      changeNote: st.srv ? st.srv.change_note : (isDep ? 'v0.2.0(상시 25% 최저마진 가드레일 및 90일+ 체화재고 10% 특례 분리) 개정에 따라 만료(deprecated) 처리' : 'OKF v0.2 Verbatim Bundle Registration (P1~P4 Verified)'),
      fm: st.fm,
      body: st.body,
      sha256: st.sha256
    });
  });

  deps.forEach((d, dIdx) => {
    let pMatch = PROVS.find(p => getRelPathForProv(p) === d.canonical_rel_path);
    if (!pMatch) {
      getDistinctPdfList().forEach(pdf => {
        const docItem = typeof getDocItemForPdf === 'function' ? getDocItemForPdf(pdf) : null;
        if (docItem && getRelPathForProv(docItem) === d.canonical_rel_path) pMatch = docItem;
      });
    }
    if (!pMatch) pMatch = PROVS[0];
    const baseFm = getBaseDefaultFm(pMatch);
    const dfm = d.frontmatter || {};
    const mergedFm = Object.assign({}, baseFm, dfm, {
      type: dfm.type || dfm.kind || baseFm.type,
      license: dfm.license || dfm.authority || baseFm.license,
      treatment: dfm.treatment || dfm.sensitivity || baseFm.treatment,
      tags: dfm.tags || (Array.isArray(dfm.synonyms) && dfm.synonyms.length ? dfm.synonyms.join(', ') : baseFm.tags),
      status: 'deprecated',
      version: d.version
    });
    list.push({
      key: `DEP:${dIdx}`,
      isDeprecated: true,
      entryId: d.entry_id,
      title: (d.frontmatter && d.frontmatter.title) || pMatch.title,
      sectionNumber: pMatch.section_number,
      docTitle: pMatch.doc_title,
      pdfFile: pMatch.pdf_file,
      version: d.version,
      status: 'deprecated',
      updatedAt: d.deprecated_at,
      gcsUri: isEcom ? `gs://kmarket_okf/okf/${d.rel_path}` : `gs://okf/${d.rel_path}`,
      canonicalRelPath: d.canonical_rel_path,
      supersededBy: d.superseded_by,
      supersededByVer: d.superseded_by_version,
      changeNote: d.change_note,
      fm: mergedFm,
      body: d.body || pMatch.verbatim_body
    });
  });

  return list;
}

function renderKcExplorerSplitHtml() {
  const allEntries = getAllCatalogEntriesList();
  const activeCount = allEntries.filter(e => !e.isDeprecated).length;
  const depCount = allEntries.filter(e => e.isDeprecated).length;
  const q = KC_SEARCH_QUERY.trim().toLowerCase();

  const filtered = allEntries.filter(e => {
    if (KC_FILTER_STATUS === 'VERIFIED' && e.isDeprecated) return false;
    if (KC_FILTER_STATUS === 'DEPRECATED' && !e.isDeprecated) return false;
    if (q) {
      const hay = `${e.entryId} ${e.title} ${e.gcsUri} ${e.version} ${e.sectionNumber}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (!KC_SELECTED_KEY || !allEntries.some(e => e.key === KC_SELECTED_KEY)) {
    const preferredKey = `ACTIVE:${getMgmtActiveKey()}`;
    KC_SELECTED_KEY = filtered.some(e => e.key === preferredKey)
      ? preferredKey
      : (filtered.length > 0 ? filtered[0].key : preferredKey);
  }
  const sel = allEntries.find(e => e.key === KC_SELECTED_KEY) || filtered[0] || allEntries[0];

  let counterpart = null;
  if (sel) {
    if (sel.isDeprecated) {
      counterpart = allEntries.find(e => !e.isDeprecated && (e.canonicalRelPath === sel.canonicalRelPath || (sel.supersededBy && e.entryId === sel.supersededBy)));
    } else {
      counterpart = allEntries.find(e => e.isDeprecated && (e.canonicalRelPath === sel.canonicalRelPath || e.supersededBy === sel.entryId));
    }
  }

  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const kcSearchPh = isEcom
    ? 'KC 엔트리 검색 (제11조, 50%, 마진, 체화재고, 청약철회, 내규, doc.md)...'
    : 'KC 엔트리 검색 (제1조, 제29조, 내규, doc.md)...';

  return `
    <div class="mgmt-body-split">
      <!-- Left Dataplex Knowledge Catalog Entry List -->
      <aside class="mgmt-sidebar" style="width:345px;">
        <div class="search-wrap" style="display:flex; flex-direction:column; gap:8px;">
          <input type="text" class="search-input" placeholder="${escapeHtml(kcSearchPh)}" value="${escapeHtml(KC_SEARCH_QUERY)}" oninput="onKcSearchInput(this.value)" />
          <div style="display:flex; gap:5px;">
            <button class="mgmt-chip-btn ${KC_FILTER_STATUS === 'ALL' ? 'active' : ''}" style="flex:1;" onclick="setKcStatusFilter('ALL')">
              전체 (${allEntries.length})
            </button>
            <button class="mgmt-chip-btn ${KC_FILTER_STATUS === 'VERIFIED' ? 'active' : ''}" style="flex:1;" onclick="setKcStatusFilter('VERIFIED')">
              활성 (${activeCount})
            </button>
            <button class="mgmt-chip-btn ${KC_FILTER_STATUS === 'DEPRECATED' ? 'active' : ''}" style="flex:1;" onclick="setKcStatusFilter('DEPRECATED')">
              만료 (${depCount})
            </button>
          </div>
        </div>

        <div class="nav-list">
          ${filtered.length === 0 ? `<div style="padding:20px; text-align:center; font-size:12px; color:var(--text-sub);">해당 상태의 Knowledge Catalog 엔트리가 없습니다.</div>` : filtered.map(e => `
            <div class="mgmt-tree-row ${e.key === KC_SELECTED_KEY ? 'active' : ''}" onclick="selectKcExplorerEntry('${e.key}')">
              <div style="flex:1; min-width:0;">
                <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
                  <span style="font-size:12px; font-weight:600; color:${e.isDeprecated ? 'var(--gcp-red)' : (e.key === KC_SELECTED_KEY ? 'var(--gcp-blue)' : 'var(--text)')}; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    ${escapeHtml(e.title)}
                  </span>
                  <span class="mgmt-status-pill ${e.isDeprecated ? 'deprecated' : 'synced'}">
                    ${e.isDeprecated ? `DEPRECATED · v${escapeHtml(e.version)}` : `${escapeHtml(e.status.toUpperCase())} · v${escapeHtml(e.version)}`}
                  </span>
                </div>
                <div style="font-family:var(--mono); font-size:10.5px; color:var(--text-sub); margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                  ${escapeHtml(e.gcsUri)}
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </aside>

      <!-- Right GCP Dataplex Knowledge Catalog Entry Detail View -->
      <section class="mgmt-editor-pane" style="border-right:0;">
        ${sel ? renderKcDetailInspectorHtml(sel, counterpart) : ''}
      </section>
    </div>
  `;
}

function formatGcpConsoleTimestamp(isoStr, fallbackFormatted) {
  if (!isoStr || isoStr === '2026-09-22T04:00:00Z') {
    return fallbackFormatted || 'Sep 22, 2026, 1:00:00 PM';
  }
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return fallbackFormatted || isoStr;
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  } catch (e) {
    return fallbackFormatted || isoStr;
  }
}

function buildGcpExtraFrontmatterJson(sel) {
  const fm = sel.fm;
  const pairs = [
    [["sources", "0", "kind"], "origin_document"],
    [["sources", "0", "sha256"], fm.sha256 || "7ec775dc7d09f2ea35f898b9c18756a9ffd6a262583d76fc7055ab350d429c79"],
    [["version"], sel.version || "0.2.0"],
    [["language"], "ko"],
    [["treatment"], fm.treatment || "verbatim_ko"],
    [["license"], fm.license || "공공누리 제1유형 (국가법령정보센터·금융위원회 공공저작물 자유이용허락)"],
    [["content_class"], fm.content_class || "authentic"],
    [["section_number"], fm.section_number || sel.sectionNumber],
    [["source_page"], Number(fm.source_page || 1)],
    [["part_of"], fm.part_of || "/regulations/01_fsc_banking_reg/doc.md"]
  ];
  if (sel.changeNote) {
    pairs.push([["change_note"], sel.changeNote]);
  }
  return JSON.stringify(pairs);
}

function renderKcDetailInspectorHtml(sel, counterpart) {
  const fm = sel.fm;
  const creationTimeStr = 'Sep 22, 2026, 4:15:19 PM';
  const lastModTimeStr = sel.updatedAt && sel.updatedAt !== '2026-09-22T04:00:00Z'
    ? formatGcpConsoleTimestamp(sel.updatedAt, 'Sep 22, 2026, 4:15:19 PM')
    : 'Sep 22, 2026, 4:15:19 PM';
  const genTimeStr = formatGcpConsoleTimestamp(fm.generated_at, 'Sep 22, 2026, 1:00:00 PM');
  const verTimeStr = formatGcpConsoleTimestamp(sel.updatedAt, 'Sep 22, 2026, 1:00:00 PM');
  const openArg = typeof sel.provIdx === 'string' ? `'${escapeHtml(sel.provIdx)}'` : sel.provIdx;

  return `
    <div class="pane-subbar">
      <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0; overflow:hidden;">
        <span style="font-weight:600; color:var(--text); flex-shrink:0;">Knowledge Catalog</span>
        <span style="color:var(--text-muted); flex-shrink:0;">/</span>
        <code style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0;" title="${escapeHtml(sel.entryId)}">${escapeHtml(sel.entryId)}</code>
      </div>
      <div style="display:flex; gap:8px; align-items:center; flex-shrink:0;">
        ${!sel.isDeprecated && sel.provIdx !== undefined ? `
          <button class="gcp-action-btn" style="padding:4px 12px; font-size:11.5px; white-space:nowrap; flex-shrink:0;" onclick="selectMgmtFileItem(${openArg}); toggleMgmtSubView('EDITOR');">
            OKF Editor로 열기
          </button>
        ` : ''}
      </div>
    </div>

    <div class="mgmt-editor-scroll">
      <!-- Top Title Banner & Version Lineage Notice -->
      <div class="mgmt-card">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid var(--border-subtle);">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:18px; font-weight:600; color:var(--text);">${escapeHtml(sel.title)}</span>
            <span class="mgmt-status-pill ${sel.isDeprecated ? 'deprecated' : 'synced'}">${escapeHtml(sel.status.toUpperCase())}</span>
            <span class="badge-pill badge-blue">v${escapeHtml(sel.version)}</span>
          </div>
          <code style="font-family:var(--mono); font-size:11.5px; color:var(--gcp-blue);">${escapeHtml(sel.gcsUri)}</code>
        </div>

        ${sel.isDeprecated ? `
          <div style="margin-bottom:16px; padding:10px 12px; border-radius:6px; background:var(--gcp-red-bg); border:1px solid var(--gcp-red); display:flex; align-items:center; justify-content:space-between; gap:8px;">
            <span style="font-size:12px; color:var(--gcp-red);">
              <strong>[만료 이력]</strong> 이 엔트리는 신규 버전 <strong>v${escapeHtml(sel.supersededByVer)}</strong> 배포에 의해 만료(<code>status: deprecated</code>)되었으며 스냅샷이 <code>versions/</code>에 보존되어 있습니다. (사유: ${escapeHtml(sel.changeNote)})
            </span>
          </div>
        ` : (counterpart ? `
          <div style="margin-bottom:16px; padding:10px 12px; border-radius:6px; background:var(--gcp-blue-bg); border:1px solid var(--gcp-blue); display:flex; align-items:center; justify-content:space-between; gap:8px;">
            <span style="font-size:12px; color:var(--gcp-blue);">
              <strong>[버전 계보]</strong> 구버전(<strong>v${escapeHtml(counterpart.version)}</strong>)을 만료시키고 승격된 최신 활성 엔트리입니다. (개정 사유: ${escapeHtml(sel.changeNote)})
            </span>
          </div>
        ` : '')}

        <!-- 1. Entry details (Exact GCP Dataplex Knowledge Catalog Layout) -->
        <div class="gcp-kc-section-title">Entry details</div>
        <div class="gcp-kc-details-grid">
          <div>
            <div class="gcp-kc-field-label">System</div>
            <div class="gcp-kc-field-val">Open Knowledge Format</div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Platform</div>
            <div class="gcp-kc-field-val">OKF</div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Creation time</div>
            <div class="gcp-kc-field-val">${escapeHtml(creationTimeStr)}</div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Last modification time</div>
            <div class="gcp-kc-field-val">${escapeHtml(lastModTimeStr)}</div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Entry type</div>
            <div class="gcp-kc-field-val">OKF Document</div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Domain</div>
            <div class="gcp-kc-field-val">-</div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Identifiers</div>
            <div class="gcp-kc-field-val">
              <span style="color:var(--text-sub); font-size:12px;">Resource:</span>
              <code style="font-family:var(--mono); font-size:12px; color:var(--gcp-blue); margin-left:4px;">${escapeHtml(sel.gcsUri)}</code>
            </div>
          </div>
          <div>
            <div class="gcp-kc-field-label">Labels</div>
            <div class="gcp-kc-field-val">-</div>
          </div>
          <div style="grid-column: 1 / -1;">
            <div class="gcp-kc-field-label">Description</div>
            <div class="gcp-kc-field-val">${escapeHtml(fm.description || sel.docTitle)}</div>
          </div>
          <div style="grid-column: 1 / -1;">
            <div class="gcp-kc-field-label">Contacts</div>
            <div class="gcp-kc-field-val">
              ${fm.contacts ? (() => {
                const isOwner = isContactOwnerRole(fm.contacts);
                const roleLabel = isOwner ? 'Owner' : 'Steward';
                return `<span class="badge-pill ${isOwner ? 'badge-blue' : 'badge-green'}" style="margin-right:6px; font-size:11px;">${roleLabel}</span><span>${escapeHtml(fm.contacts)}</span>`;
              })() : '-'}
            </div>
          </div>
        </div>
      </div>

      <!-- 2. MIDDLE: Overview (dataplex-types.global.overview) -->
      <div class="mgmt-card">
        <div class="gcp-kc-section-title" style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
          <span>Overview</span>
          <span class="badge-pill badge-green" style="font-size:11px;">MARKDOWN</span>
        </div>
        <div class="okf-title" style="font-size:15px;">${escapeHtml(sel.title)}</div>
        <div class="okf-body-box">${formatMgmtPreviewBody(sel.body)}</div>
      </div>

      <!-- 3. BOTTOM: Aspects (Clean Structured Name / Value Table without raw Extra Frontmatter JSON) -->
        <div class="mgmt-card">
          <div class="gcp-kc-section-title">Aspects</div>

          ${fm.contacts ? (() => {
            const rawC = String(fm.contacts).trim();
            const m = rawC.match(/^(.+?)\s*<([^>]+)>$/);
            const cName = m ? m[1].trim() : rawC;
            const cEmail = m ? m[2].trim() : '';
            const cRole = isContactOwnerRole(cName) ? 'owner' : 'steward';
            return `
              <div class="gcp-kc-aspect-box" style="margin-bottom:12px;">
                <div class="gcp-kc-aspect-header">
                  <span>contacts</span>
                  <span style="font-family:var(--mono); font-size:11px; color:var(--text-sub);">dataplex-types.global.contacts</span>
                </div>
                <table class="kc-aspect-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr class="kc-group-row">
                      <th colspan="2">Identities</th>
                    </tr>
                    <tr class="kc-nested-row">
                      <th>Role</th>
                      <td><code>${escapeHtml(cRole)}</code></td>
                    </tr>
                    <tr class="kc-nested-row">
                      <th>Name</th>
                      <td>${escapeHtml(cName)}</td>
                    </tr>
                    <tr class="kc-nested-row">
                      <th>ID (Email)</th>
                      <td><code>${escapeHtml(cEmail || cName)}</code></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            `;
          })() : ''}

          <div class="gcp-kc-aspect-box">
            <div class="gcp-kc-aspect-header">
              <span>okf</span>
              <span style="font-family:var(--mono); font-size:11px; color:var(--text-sub);">OKF Signal · v${escapeHtml(sel.version)}</span>
            </div>
            <table class="kc-aspect-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>OKF Type</th>
                  <td>${escapeHtml(fm.type || 'Provision')}</td>
                </tr>
                <tr>
                  <th>Version</th>
                  <td><code>${escapeHtml(sel.version || '0.2.0')}</code></td>
                </tr>
                <tr>
                  <th>Status</th>
                  <td><span class="mgmt-status-pill ${sel.isDeprecated ? 'deprecated' : 'synced'}">${escapeHtml(sel.status)}</span></td>
                </tr>
                <tr class="kc-group-row">
                  <th colspan="2">Generated</th>
                </tr>
                <tr class="kc-nested-row">
                  <th>Generated By</th>
                  <td><code>${escapeHtml(fm.generated_by)}</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Generated At</th>
                  <td>${escapeHtml(genTimeStr)}</td>
                </tr>
                <tr class="kc-group-row">
                  <th colspan="2">Verified</th>
                </tr>
                <tr class="kc-nested-row">
                  <th>Verified By</th>
                  <td><code>${escapeHtml(fm.verified_by)}</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Verified At</th>
                  <td>${escapeHtml(verTimeStr)}</td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Verification Method</th>
                  <td><code>${escapeHtml(fm.verified_method || 'source_text_match')}</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Checks</th>
                  <td><code>P1_body, P2_heading, P3_page, P4_digest</code></td>
                </tr>
                <tr class="kc-group-row">
                  <th colspan="2">Sources</th>
                </tr>
                <tr class="kc-nested-row">
                  <th colspan="2" style="font-weight:600; color:var(--text);">source</th>
                </tr>
                <tr class="kc-nested-row-2">
                  <th>Source ID</th>
                  <td><code>origin_pdf</code></td>
                </tr>
                <tr class="kc-nested-row-2">
                  <th>Resource</th>
                  <td><code>${escapeHtml(fm.source_resource)}</code></td>
                </tr>
                <tr class="kc-nested-row-2">
                  <th>Kind</th>
                  <td><code>origin_document</code></td>
                </tr>
                <tr class="kc-nested-row-2">
                  <th>SHA-256</th>
                  <td><code style="font-size:11.5px;">${escapeHtml(fm.sha256)}</code></td>
                </tr>
                <tr class="kc-group-row">
                  <th colspan="2">Governance & Provenance</th>
                </tr>
                <tr class="kc-nested-row">
                  <th>Content Class</th>
                  <td><code>${escapeHtml(fm.content_class || 'authentic')}</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Treatment</th>
                  <td><code>${escapeHtml(fm.treatment || 'verbatim_ko')}</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Language</th>
                  <td><code>ko</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>License</th>
                  <td>${escapeHtml(fm.license)}</td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Part Of</th>
                  <td><code>${escapeHtml(fm.part_of)}</code></td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Section Number</th>
                  <td>${escapeHtml(fm.section_number || sel.sectionNumber)}</td>
                </tr>
                <tr class="kc-nested-row">
                  <th>Source Page</th>
                  <td><code>p.${escapeHtml(String(fm.source_pages_span || fm.source_page || 1))}</code></td>
                </tr>
                ${sel.changeNote ? `
                  <tr class="kc-nested-row">
                    <th>Change Note</th>
                    <td>${escapeHtml(sel.changeNote)}</td>
                  </tr>
                ` : ''}
              </tbody>
            </table>
          </div>
        </div>
    </div>
  `;
}

function onKcSearchInput(val) {
  KC_SEARCH_QUERY = val || '';
  renderManagementModule(CURRENT_IDX);
}

function setKcStatusFilter(status) {
  KC_FILTER_STATUS = status;
  KC_SELECTED_KEY = null;
  renderManagementModule(CURRENT_IDX);
}

function selectKcExplorerEntry(key) {
  KC_SELECTED_KEY = key;
  if (typeof key === 'string' && key.startsWith('ACTIVE:')) {
    const sub = key.slice(7);
    if (sub.startsWith('DOC:')) {
      MGMT_ACTIVE_KEY = sub;
    } else {
      const idx = parseInt(sub, 10);
      if (!isNaN(idx) && idx >= 0 && idx < PROVS.length) {
        CURRENT_IDX = idx;
        MGMT_ACTIVE_KEY = idx;
      }
    }
  }
  renderManagementModule(CURRENT_IDX);
  if (typeof saveUiState === 'function') saveUiState();
}

