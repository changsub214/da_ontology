/* ==========================================================================
   okf_veri_web/js/mod-validation.js
   Module 02 (okf-validation): PDF <-> OKF Verbatim Compare & Knowledge Graph
   Graph Design: 100% Faithful to reference `비정형_viz.html` across ALL scopes
   (ALL, 01, 02, 05, 10, CORE) and shared with 04 · bq-graph Instance View.
   ========================================================================== */

let network = null;
let physicsEnabled = true;
let graphNodes = [];
let graphEdges = [];

function colorizeYaml(yamlText) {
  return escapeHtml(yamlText)
    .replace(/^---$/gm, '<span class="yaml-delim">---</span>')
    .replace(/^([a-zA-Z0-9_]+):/gm, '<span class="yaml-key">$1</span>:');
}

function highlightTerms(escaped) {
  return escaped.replace(
    /(100분의 0\.9 이상|100분의 0\.85 이상|100분의 10 이상|100분의 20 이상|100분의 50|100분의 25|100분의 10|건설업\(F\)|도매 및 소매업\(G\)|숙박 및 음식점업\(H\)|부동산 및 임대업\(L\)|우선변제자산|6개월 이상 연속|선택적으로 적용|특허권 단독 취득|marketing_opt_in = True|marketing_opt_in = False|available_stock == 0|stock_age_days &gt;= 90|promo_cost_share_ratio|CLEARANCE_OVERRIDE|VIP_RETENTION|VOLUNTARY_PROMO_FILING|3영업일 이내|7일 이내|3개월 이내)/g,
    '<span class="hl-term">$1</span>'
  );
}

function isCaveatProvision(p) {
  if (!p) return false;
  return CAVEAT_SECTIONS.has(p.concept_id) || CAVEAT_SECTIONS.has(p.section_number);
}

function getProvisionShortLabel(p) {
  if (!p) return '';
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  if (isEcom && typeof ECOMMERCE_DOC_SHORT_NAMES === 'object' && ECOMMERCE_DOC_SHORT_NAMES[p.doc_id]) {
    return `${ECOMMERCE_DOC_SHORT_NAMES[p.doc_id]} ${p.section_number}`;
  }
  return p.section_number;
}

function buildOkfDetailMarkup(p) {
  const relMatches = SEMANTIC_EDGES.filter(e =>
    (e.fromId || e.toId)
      ? (e.fromId === p.concept_id || e.toId === p.concept_id)
      : (e.fromSec === p.section_number || e.toSec === p.section_number)
  );
  let relHtml = '';
  if (relMatches.length > 0) {
    relHtml = `
      <div class="section-label">
        <span>Business Semantic Relations (${relMatches.length})</span>
        <span>클릭 시 연결 조문 이동</span>
      </div>
      <div class="biz-edge-list">
        ${relMatches.map(e => {
          const isOut = (e.fromId || e.toId)
            ? (e.fromId === p.concept_id)
            : (e.fromSec === p.section_number);
          const otherSec = isOut ? e.toSec : e.fromSec;
          const otherKey = isOut ? (e.toId || e.toSec) : (e.fromId || e.fromSec);
          const otherProv = PROVS.find(x => x.concept_id === otherKey || x.section_number === otherKey);
          const otherPage = otherProv && otherProv.source_page ? `p.${otherProv.source_page}` : '';
          let dotColor = '#3b6ea5';
          if (e.rel.includes('EXCEPTION') || e.rel.includes('OVERRULES')) dotColor = '#a85c56';
          else if (e.rel.includes('CONFLICT')) dotColor = '#b88a44';
          return `
            <div class="biz-edge-item" onclick="selectBySectionName('${escapeHtml(otherKey)}')" title="${escapeHtml(otherProv ? otherProv.title : otherSec)}">
              <div class="biz-edge-top">
                <span class="edge-badge"><span class="edge-dot" style="background:${dotColor};"></span>${escapeHtml(e.rel)}</span>
                <span class="edge-jump-meta">${escapeHtml(otherSec)}${otherPage ? ` (${escapeHtml(otherPage)})` : ''} ↗</span>
              </div>
              <div class="edge-target">
                <span class="edge-kw">from</span>
                <span class="${isOut ? 'edge-sec-self' : 'edge-sec-peer'}">${escapeHtml(e.fromSec)}</span>
                <span class="edge-arrow">➔</span>
                <span class="edge-kw">to</span>
                <span class="${isOut ? 'edge-sec-peer' : 'edge-sec-self'}">${escapeHtml(e.toSec)}</span>
              </div>
              <div class="edge-reason">${escapeHtml(e.reason)}</div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  const okfTypeLabel = p.is_source_document ? 'Source Document (doc.md)' : 'Provision';
  const spanStr = Array.isArray(p.source_pages_span) ? p.source_pages_span.join(', ') : String(p.source_page || 1);
  const subpathHtml = p.okf_path ? `<div class="okf-subpath-line">${escapeHtml(p.okf_path)}</div>` : '';
  return `
    ${subpathHtml}
    ${relHtml}
    <details class="fm-accordion" ${FM_OPEN ? 'open' : ''} ontoggle="onFmToggle(this.open)">
      <summary>
        <span class="fm-summary-left">
          <span>YAML Frontmatter</span>
          <span class="fm-summary-meta">${escapeHtml(okfTypeLabel)} · p.${escapeHtml(spanStr)}</span>
        </span>
        <span class="material-symbols-outlined fm-chevron">expand_more</span>
      </summary>
      <div class="frontmatter-block">${colorizeYaml(p.yaml_frontmatter)}</div>
    </details>

    <div class="section-label">
      <span>Markdown Body (Verbatim Source Text)</span>
    </div>
    <div class="okf-title">${escapeHtml(p.title)}</div>
    <div class="okf-body-box">${highlightTerms(escapeHtml(p.verbatim_body))}</div>
  `;
}

function toggleGraphView(fromRestore = false) {
  GRAPH_MODE = !GRAPH_MODE;
  const compareWs = document.getElementById('compare-workspace');
  const graphWs = document.getElementById('graph-workspace');
  const btn = document.getElementById('btn-view-switch');
  const icon = document.getElementById('view-switch-icon');
  const txt = document.getElementById('view-switch-text');

  btn.classList.toggle('active', GRAPH_MODE);
  if (GRAPH_MODE) {
    compareWs.style.display = 'none';
    graphWs.style.display = 'flex';
    icon.textContent = 'vertical_split';
    txt.textContent = 'Split View';
    requestAnimationFrame(() => {
      buildOkfGraph(document.getElementById('graph-scope-select').value);
      if (!fromRestore || GRAPH_DETAIL_OPEN) {
        openGraphDetailForIdx(CURRENT_IDX);
      }
    });
  } else {
    graphWs.style.display = 'none';
    compareWs.style.display = 'flex';
    icon.textContent = 'hub';
    txt.textContent = 'Graph View';
    selectItem(CURRENT_IDX);
  }
  saveUiState();
}

function openCurrentInPdfCompare() {
  if (GRAPH_MODE) toggleGraphView();
}

function closeGraphDetail() {
  GRAPH_DETAIL_OPEN = false;
  document.getElementById('graph-detail-panel').classList.remove('open');
  saveUiState();
}

function openGraphDetailForIdx(idx) {
  CURRENT_IDX = idx;
  ACTIVE_DOC_PDF = null;
  GRAPH_DETAIL_OPEN = true;
  const p = PROVS[CURRENT_IDX];
  if (!p) return;
  const fileName = p.okf_path.split('/').pop();
  const pathEl = document.getElementById('graph-detail-path');
  if (pathEl) {
    pathEl.textContent = fileName;
    pathEl.title = `${fileName} (${p.okf_path})`;
  }
  const bodyEl = document.getElementById('graph-detail-body');
  if (bodyEl) {
    bodyEl.innerHTML = buildOkfDetailMarkup(p);
    bodyEl.scrollTop = 0;
  }
  document.getElementById('graph-detail-panel').classList.add('open');
  saveUiState();
}

/**
 * Shared Graph Builder following `비정형_viz.html` exact hierarchy & styling:
 *   1. Document Root (`#3b82f6`, dot, size 34)
 *   2. Major Section / Chapter (`#06b6d4`, dot, size 22)
 *   3. Provision / Sub-Clause Chunks (`#10b981` normal / `#ef4444` exception / `#f97316` distractor, dot, size 15)
 *   4. Business Entities (`#ec4899`, diamond, size 12, dashed `#db2777` MENTIONS edges)
 *   5. Semantic Business Edges (`OVERRULES_WITH_EXCEPTION`, `DELEGATES_CRITERIA_TO`, etc.)
 *
 * When a smaller scope (`DOC_02`, `DOC_05`, `DOC_10`, `CORE`, or GQL Scenario) is selected,
 * sub-clause chunks (항·호·목) and extracted domain entity diamonds are automatically included
 * so the radial hub-and-spoke constellation density matches `비정형_viz.html` 100%.
 */
function buildVizStyleGraphData(filteredProvs, expandSubClauses = false, extraInstanceRows = []) {
  const nodes = [];
  const edges = [];
  const nodeSet = new Set();
  const primaryProvSet = new Set();
  const docSeen = new Set();
  const isDark = document.body.classList.contains('dark-mode');
  const labelMainColor = isDark ? '#f8fafc' : '#202124';
  const labelSubColor = isDark ? '#cbd5e1' : '#3c4043';
  const edgeBgColor = isDark ? '#1f1f1f' : '#f8f9fa';
  const structEdgeColor = isDark ? '#334155' : '#cbd5e1';

  const idToProv = {};
  const secToProvId = {};
  PROVS.forEach((p, idx) => {
    const rec = { id: p.concept_id, idx, p };
    idToProv[p.concept_id] = rec;
    if (!secToProvId[p.section_number]) {
      secToProvId[p.section_number] = rec;
    }
  });

  filteredProvs.forEach(p => {
    const provIdx = PROVS.indexOf(p);
    const [cat, docDir, partDir] = p.concept_id.split('/');
    const docNodeId = `DOC::${p.doc_id}`;
    const partNodeId = `PART::${docDir}/${partDir}`;

    docSeen.add(p.doc_id);
    primaryProvSet.add(p.concept_id);

    // 1. Document Root Node (Muted Enterprise Palette: #3b6ea5 / #527a9a)
    if (!nodeSet.has(docNodeId)) {
      nodeSet.add(docNodeId);
      nodes.push({
        id: docNodeId,
        label: p.pdf_file.replace(/\.pdf$/, '').slice(0, 26),
        title: p.doc_title || p.pdf_file,
        shape: 'dot',
        size: 34,
        color: (p.content_class === 'synthetic' || p.category === 'internal_policies') ? '#527a9a' : '#3b6ea5',
        font: { color: labelMainColor, size: 13.5, face: 'Google Sans, Noto Sans KR' },
        provIdx
      });
    }

    // 2. Major Section Node (Muted Blue-Gray: #6b88a8)
    if (!nodeSet.has(partNodeId)) {
      nodeSet.add(partNodeId);
      const cleanPartLabel = p.part_title
        ? p.part_title.replace(/`/g, '').replace(/\s*\([^)]*\)$/, '').slice(0, 22)
        : partDir;
      nodes.push({
        id: partNodeId,
        label: cleanPartLabel,
        title: p.part_title || partDir,
        shape: 'dot',
        size: 22,
        color: '#6b88a8',
        font: { color: labelSubColor, size: 11.5, face: 'Google Sans, Noto Sans KR' },
        provIdx
      });
      edges.push({
        from: docNodeId,
        to: partNodeId,
        color: { color: isDark ? '#475569' : '#94a3b8', highlight: '#6b88a8' },
        width: 2.2,
        arrows: 'to'
      });
    }

    // 3. Provision Node (Muted Sage #3b735b / Muted Terracotta #a85c56 / Muted Ochre #b88a44)
    const isCav = isCaveatProvision(p);
    let pColor = '#3b735b';
    if (p.category === 'distractors') pColor = '#b88a44';
    else if (isCav) pColor = '#a85c56';

    if (!nodeSet.has(p.concept_id)) {
      nodeSet.add(p.concept_id);
      nodes.push({
        id: p.concept_id,
        label: `${getProvisionShortLabel(p)}\n(p.${p.source_page})`,
        title: p.title,
        shape: 'dot',
        size: isCav ? 17 : 15,
        color: pColor,
        font: { color: labelSubColor, size: 10.5, face: 'Google Sans, Noto Sans KR' },
        provIdx
      });
      edges.push({
        from: partNodeId,
        to: p.concept_id,
        color: { color: structEdgeColor, highlight: '#6b88a8' },
        width: 1.5,
        arrows: 'to'
      });
    }

    // When viewing single documents (02, 05, 10) or CORE/Scenario subgraphs,
    // expand each provision's internal paragraphs/clauses (항·호·목) as Chunk nodes
    // and key domain terms as Entity diamonds.
    if (expandSubClauses && p.verbatim_body) {
      const lines = p.verbatim_body
        .split(/\n+/)
        .map(l => l.trim())
        .filter(l => l.length > 12);
      const maxChunks = Math.min(lines.length, 4);
      for (let i = 0; i < maxChunks; i++) {
        const subId = `${p.concept_id}::SUB_${i + 1}`;
        if (!nodeSet.has(subId)) {
          nodeSet.add(subId);
          const snippet = lines[i].slice(0, 18) + (lines[i].length > 18 ? '…' : '');
          const isExLine = /다만|예외|제외|선택적|유예|감경|특례|무효|금지|차단|제한|100분의 0\.9|100분의 10|100분의 50|100분의 25|90일 이상|홀로그램/.test(lines[i]);
          nodes.push({
            id: subId,
            label: snippet,
            title: lines[i],
            shape: 'dot',
            size: 12.5,
            color: isExLine ? '#a85c56' : '#3b735b',
            font: { color: labelSubColor, size: 9.5, face: 'Google Sans, Noto Sans KR' },
            provIdx
          });
          edges.push({
            from: p.concept_id,
            to: subId,
            color: { color: structEdgeColor, highlight: '#6b88a8' },
            width: 1.2,
            arrows: 'to'
          });
        }
      }
    }
  });

  // 4. Semantic Business Relation Edges
  let semEdgeCnt = 0;
  SEMANTIC_EDGES.forEach(se => {
    const s = (se.fromId && idToProv[se.fromId]) || secToProvId[se.fromSec];
    const d = (se.toId && idToProv[se.toId]) || secToProvId[se.toSec];
    if (!s || !d) return;
    const sInPrimary = primaryProvSet.has(s.id);
    const dInPrimary = primaryProvSet.has(d.id);
    if (!sInPrimary && !dInPrimary) return;

    [s, d].forEach(endpoint => {
      if (!nodeSet.has(endpoint.id)) {
        nodeSet.add(endpoint.id);
        const ep = endpoint.p;
        const epCav = isCaveatProvision(ep);
        let epColor = '#3b735b';
        if (ep.category === 'distractors') epColor = '#b88a44';
        else if (epCav) epColor = '#a85c56';
        nodes.push({
          id: ep.concept_id,
          label: `[타문서 연결]\n${getProvisionShortLabel(ep)} (p.${ep.source_page})`,
          title: `${ep.pdf_file} · ${ep.title}`,
          shape: 'dot',
          size: epCav ? 16 : 14,
          color: epColor,
          font: { color: labelSubColor, size: 10, face: 'Google Sans, Noto Sans KR' },
          provIdx: endpoint.idx
        });
      }
    });

    semEdgeCnt++;
    edges.push({
      from: s.id,
      to: d.id,
      label: se.rel,
      title: se.reason,
      color: { color: se.color, highlight: labelMainColor },
      width: 2.2,
      arrows: 'to',
      font: { color: labelMainColor, size: 9, background: edgeBgColor, strokeWidth: 0, face: 'Google Sans' }
    });
  });

  // 5. Business Entity Diamond Nodes (Muted Ochre Gold: #b88a44)
  SEMANTIC_ENTITIES.forEach(ent => {
    const rawRefs = Array.isArray(ent.matchIds) && ent.matchIds.length > 0
      ? ent.matchIds.map(id => idToProv[id])
      : (ent.matchSec || []).map(s => secToProvId[s]);
    const hasPrimary = rawRefs.some(x => x && primaryProvSet.has(x.id));
    const linked = rawRefs.filter(x => x && nodeSet.has(x.id));
    if (hasPrimary && linked.length > 0) {
      nodeSet.add(ent.id);
      nodes.push({
        id: ent.id,
        label: ent.name,
        shape: 'diamond',
        size: 12,
        color: '#b88a44',
        font: { color: isDark ? '#e2c07d' : '#7c581e', size: 10, face: 'Google Sans, Noto Sans KR' },
        provIdx: linked[0].idx
      });
      linked.forEach(target => {
        edges.push({
          from: target.id,
          to: ent.id,
          color: { color: isDark ? '#9a7338' : '#b88a44', highlight: '#b88a44' },
          dashes: [2, 4],
          width: 1.4,
          arrows: 'to'
        });
      });
    }
  });

  // 6. Optional Core Banking Ledger Row Instances (for 04 · bq-graph Instance View)
  extraInstanceRows.forEach(row => {
    nodeSet.add(row.id);
    nodes.push({
      id: row.id,
      label: row.label,
      title: row.title,
      shape: 'dot',
      size: 18,
      color: '#38bdf8',
      font: { color: labelMainColor, size: 11, face: 'Google Sans, Noto Sans KR' },
      ledgerRow: row
    });
    if (row.linkCust && nodeSet.has(row.linkCust)) {
      edges.push({
        from: row.linkCust,
        to: row.id,
        color: { color: '#0284c7', highlight: '#38bdf8' },
        width: 2,
        arrows: 'to'
      });
    }
    if (row.linkEnt && nodeSet.has(row.linkEnt)) {
      edges.push({
        from: row.id,
        to: row.linkEnt,
        color: { color: '#db2777', highlight: '#f472b6' },
        dashes: [2, 4],
        width: 1.5,
        arrows: 'to'
      });
    }
    row.matchSec.forEach(sec => {
      const target = idToProv[sec] || secToProvId[sec];
      if (target && nodeSet.has(target.id)) {
        edges.push({
          from: row.id,
          to: target.id,
          label: 'GOVERNED_BY',
          color: { color: '#38bdf8', highlight: labelMainColor },
          width: 2,
          arrows: 'to',
          font: { color: labelMainColor, size: 9, background: edgeBgColor, strokeWidth: 0, face: 'Google Sans' }
        });
      }
    });
  });

  return { nodes, edges, docCount: docSeen.size, provCount: filteredProvs.length, semEdgeCnt };
}

let GRAPH_SCOPE_LABELS = {
  ALL: '전체 10개 PDF · 184개 Concept 전체',
  DOC_01_FSC_BANK_REG: '01. 은행업감독규정 (130개 조문)',
  DOC_02_LAW_ANNEX3: '02. 별표3 자산건전성 분류기준 (7개 호·목)',
  DOC_05_FSC_KFB_RATE: '05. 대출금리 산정체계 개선방안 (6개 절)',
  DOC_10_SYNTHETIC_BYULBIT_POLICY: '10. 별빛은행 당행 내규 (6개 조문)',
  CORE: '핵심 시나리오 및 단서·예외 서브그래프'
};
const FINANCE_GRAPH_SCOPE_LABELS = GRAPH_SCOPE_LABELS;

function syncGraphScopeCustomSelectUi(scope = 'ALL') {
  if (!GRAPH_SCOPE_LABELS[scope]) scope = 'ALL';
  const hiddenEl = document.getElementById('graph-scope-select');
  if (hiddenEl) hiddenEl.value = scope;
  const valEl = document.getElementById('okf-graph-scope-select-val');
  if (valEl) valEl.textContent = GRAPH_SCOPE_LABELS[scope] || GRAPH_SCOPE_LABELS.ALL;
  const menuEl = document.getElementById('okf-graph-scope-select-menu');
  if (menuEl) {
    menuEl.innerHTML = Object.entries(GRAPH_SCOPE_LABELS).map(([k, lbl]) => {
      const isSel = k === scope;
      return `
        <div class="gcp-custom-select-opt ${isSel ? 'selected' : ''}" data-value="${escapeHtml(k)}" onclick="selectGraphScopeCustomOption(event, '${escapeHtml(k)}')">
          <span>${escapeHtml(lbl)}</span>
          <span class="material-symbols-outlined gcp-opt-check" style="opacity:${isSel ? '1' : '0'};">check</span>
        </div>`;
    }).join('');
  }
}

function selectGraphScopeCustomOption(ev, scope) {
  if (ev) ev.stopPropagation();
  const wrap = document.getElementById('okf-graph-scope-custom-select');
  if (wrap) wrap.classList.remove('open');
  syncGraphScopeCustomSelectUi(scope);
  buildOkfGraph(scope);
}

function buildOkfGraph(scope = 'ALL') {
  syncGraphScopeCustomSelectUi(scope);
  saveUiState();
  const filteredProvs = PROVS.filter(p => {
    if (scope === 'ALL') return true;
    if (scope === 'CORE') return isCaveatProvision(p);
    return p.doc_id === scope;
  });

  const expandSubClauses = (scope !== 'ALL' && scope !== 'DOC_01_FSC_BANK_REG');
  const built = buildVizStyleGraphData(filteredProvs, expandSubClauses, []);
  graphNodes = built.nodes;
  graphEdges = built.edges;

  document.getElementById('g-stat-docs').textContent = String(built.docCount);
  document.getElementById('g-stat-provs').textContent = String(built.provCount);
  document.getElementById('g-stat-edges').textContent = String(built.semEdgeCnt);

  const container = document.getElementById('network-canvas');
  const data = {
    nodes: new vis.DataSet(graphNodes),
    edges: new vis.DataSet(graphEdges)
  };
  // Exact physics options from `비정형_viz.html` lines 557-568
  const options = {
    physics: {
      enabled: physicsEnabled,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -35,
        centralGravity: 0.008,
        springLength: 85,
        springConstant: 0.08,
        damping: 0.45
      },
      stabilization: { iterations: 140 }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      keyboard: true
    }
  };

  if (network) network.destroy();
  network = new vis.Network(container, data, options);

  network.once('stabilizationIterationsDone', function () {
    network.fit({ animation: { duration: 350 } });
    setTimeout(() => {
      if (network && network.getScale() > 0.95) {
        network.moveTo({ scale: 0.90, animation: { duration: 250 } });
      }
    }, 380);
  });

  network.on('click', function (params) {
    if (params.nodes.length > 0) {
      const clickedId = params.nodes[0];
      const nObj = graphNodes.find(n => n.id === clickedId);
      if (nObj && typeof nObj.provIdx === 'number') {
        openGraphDetailForIdx(nObj.provIdx);
      }
    }
  });
}

function searchGraphNode(term) {
  const q = (term || '').trim().toLowerCase();
  if (!q || !network) return;
  const found = graphNodes.find(n => String(n.label).toLowerCase().includes(q));
  if (found) {
    network.selectNodes([found.id]);
    network.focus(found.id, { scale: 1.25, animation: { duration: 450 } });
    if (typeof found.provIdx === 'number') openGraphDetailForIdx(found.provIdx);
  }
}

function fitGraph() {
  if (network) network.fit({ animation: true });
}

function togglePhysics() {
  physicsEnabled = !physicsEnabled;
  if (network) network.setOptions({ physics: { enabled: physicsEnabled } });
}

function toggleDocGroup(pdf) {
  OPEN_DOCS[pdf] = !OPEN_DOCS[pdf];
  ACTIVE_DOC_PDF = pdf;
  renderSidebar();
  const docItem = typeof getDocItemForPdf === 'function' ? getDocItemForPdf(pdf) : null;
  if (docItem) {
    const unDataPrefix = (typeof PROJECT_REGISTRY !== 'undefined' && PROJECT_REGISTRY[ACTIVE_PROJECT] && PROJECT_REGISTRY[ACTIVE_PROJECT].unDataPrefix) || '../finance/data/un_data/';
    const pdfUrl = `${unDataPrefix}${encodeURIComponent(docItem.pdf_file)}#page=1&zoom=100`;
    document.getElementById('pdf-name-label').textContent = docItem.pdf_file;
    document.getElementById('pdf-page-label').textContent = `1~${docItem.pdf_total_pages}쪽 (문서 총괄) / 총 ${docItem.pdf_total_pages}쪽`;
    const frame = document.getElementById('pdf-frame');
    if (frame.getAttribute('data-src') !== pdfUrl) {
      frame.removeAttribute('src');
      setTimeout(() => {
        frame.src = pdfUrl;
        frame.setAttribute('data-src', pdfUrl);
      }, 15);
    }
    const pathParts = String(docItem.okf_path || '').split('/').filter(Boolean);
    const dispLabel = pathParts.length >= 2 ? `${pathParts[pathParts.length - 2]}/doc.md` : 'doc.md';
    document.getElementById('okf-file-label').textContent = dispLabel;
    document.getElementById('okf-reader').innerHTML = buildOkfDetailMarkup(docItem);
  }
  saveUiState();
}

function renderSidebar() {
  const q = (document.getElementById('nav-search').value || '').trim().toLowerCase();
  const box = document.getElementById('nav-list');
  const byDoc = {};

  PROVS.forEach((p, idx) => {
    if (q) {
      const hay = `${p.section_number} ${p.title} ${p.pdf_file} ${p.verbatim_body}`.toLowerCase();
      if (!hay.includes(q)) return;
    }
    byDoc[p.pdf_file] = byDoc[p.pdf_file] || [];
    byDoc[p.pdf_file].push({ ...p, idx });
  });

  box.innerHTML = Object.entries(byDoc).map(([pdf, items]) => {
    const isOpen = q ? true : Boolean(OPEN_DOCS[pdf]);
    const isDocActive = ACTIVE_DOC_PDF === pdf;
    return `
      <div class="doc-section">
        <div class="doc-group-title ${isDocActive ? 'active-doc' : ''}" onclick="toggleDocGroup('${escapeHtml(pdf)}')" title="클릭 시 조문 목록 펼치기/접기 및 doc.md 열람">
          <span>${escapeHtml(pdf.slice(0, 24))}</span>
          <span style="font-size:11px; font-weight:500; color:var(--text-sub);">${items.length}</span>
        </div>
        <div class="doc-items ${isOpen ? '' : 'collapsed'}">
          ${items.map(it => `
            <div class="nav-item ${!ACTIVE_DOC_PDF && it.idx === CURRENT_IDX ? 'active' : ''}" onclick="selectItem(${it.idx})">
              <div class="nav-item-top">
                <span>${escapeHtml(it.section_number)}</span>
                <span class="nav-page">p.${it.source_page}</span>
              </div>
              <div class="nav-item-sub">${escapeHtml(it.title)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }).join('');
}

function selectBySectionName(secNameOrId) {
  const idx = PROVS.findIndex(p => p.concept_id === secNameOrId || p.section_number === secNameOrId);
  if (idx < 0) return;
  const p = PROVS[idx];
  if (GRAPH_MODE) {
    const scopeEl = document.getElementById('graph-scope-select');
    const curScope = scopeEl ? scopeEl.value : 'ALL';
    const onCanvas = graphNodes.some(n => n.id === p.concept_id);
    if (!onCanvas) {
      const nextScope = (p.doc_id && GRAPH_SCOPE_LABELS && GRAPH_SCOPE_LABELS[p.doc_id])
        ? p.doc_id
        : (isCaveatProvision(p) && curScope !== 'ALL' ? 'CORE' : 'ALL');
      buildOkfGraph(nextScope);
    }
    openGraphDetailForIdx(idx);
    if (network && p && graphNodes.some(n => n.id === p.concept_id)) {
      network.selectNodes([p.concept_id]);
      network.focus(p.concept_id, { scale: 1.25, animation: { duration: 400 } });
    }
  } else {
    selectItem(idx);
  }
}

function selectItem(idx) {
  CURRENT_IDX = idx;
  ACTIVE_DOC_PDF = null;
  const p = PROVS[CURRENT_IDX];
  if (!p) return;
  OPEN_DOCS[p.pdf_file] = true;
  renderSidebar();

  const unDataPrefix = (typeof PROJECT_REGISTRY !== 'undefined' && PROJECT_REGISTRY[ACTIVE_PROJECT] && PROJECT_REGISTRY[ACTIVE_PROJECT].unDataPrefix) || '../finance/data/un_data/';
  const pdfUrl = `${unDataPrefix}${encodeURIComponent(p.pdf_file)}#page=${p.source_page}&zoom=100`;
  const pdfLabelEl = document.getElementById('pdf-name-label');
  if (pdfLabelEl) {
    pdfLabelEl.textContent = p.pdf_file;
    pdfLabelEl.title = p.pdf_file;
  }
  document.getElementById('pdf-page-label').textContent = `${p.source_pages_span.join(', ')}쪽 / 총 ${p.pdf_total_pages}쪽`;
  const frame = document.getElementById('pdf-frame');
  if (frame.getAttribute('data-src') !== pdfUrl) {
    frame.removeAttribute('src');
    setTimeout(() => {
      frame.src = pdfUrl;
      frame.setAttribute('data-src', pdfUrl);
    }, 15);
  }

  const fileName = p.okf_path.split('/').pop();
  const okfFileEl = document.getElementById('okf-file-label');
  if (okfFileEl) {
    okfFileEl.textContent = fileName;
    okfFileEl.title = `${fileName} (${p.okf_path})`;
  }
  const readerEl = document.getElementById('okf-reader');
  if (readerEl) {
    readerEl.innerHTML = buildOkfDetailMarkup(p);
    readerEl.scrollTop = 0;
  }
  saveUiState();
}
