/* ==========================================================================
   okf_veri_web/js/mod-bq-graph.js
   Module 04 (bq-graph): BigQuery Property Graph Studio (`starlight_bank_ontology.finance_graph`)
     - Mode 1 (Class View): Three.js 3D 2-Layer Class Schema Graph
       * Upper Plate (ONTOLOGY LAYER): 9 Classes (LoanContract central hub + 7 LDM + BusinessContext)
       * Lower Plate (LEX LAYER): 2 Classes (SourceDocument + Provision with 3 self-referential loops)
       * 14 Edges (7 LDM + 3 Vertical ONT↔LEX Bridges + 4 LEX)
     - Mode 2 (Instance View): 4 Curated Competency Questions (CQ01, CQ07, CQ09, CQ12)
       * Renders the live 2-Layer Ontology ↔ LEX Instance Subgraph for each CQ
   ========================================================================== */

let bqThreeViz = null;
let bqVisNet = null;
let bqCurrentInstNodes = [];
let bqCurrentInstEdges = [];
let bqInstPhysics = true;
let bqCqBannerVisible = true;

class BqClass3DVisualizer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.LAYER_Y_ONT = 105;
    this.LAYER_Y_LEX = -105;
    this.nodes = new Map();
    this.meshGroup = new THREE.Group();
    this.lineGroup = new THREE.Group();
    this.plateGroup = new THREE.Group();
    this.initScene();
  }

  initScene() {
    const width = this.container.clientWidth || 900;
    const height = this.container.clientHeight || 680;
    const isDark = document.body.classList.contains('dark-mode');

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(isDark ? 0x1f1f1f : 0xf8f9fa);

    this.camera = new THREE.PerspectiveCamera(44, width / height, 1, 4000);
    this.camera.position.set(0, 145, 650);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.92));
    const dLight = new THREE.DirectionalLight(0xffffff, 0.65);
    dLight.position.set(250, 500, 250);
    this.scene.add(dLight);

    this.scene.add(this.plateGroup);
    this.scene.add(this.lineGroup);
    this.scene.add(this.meshGroup);

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.renderer.domElement.addEventListener('click', (e) => this.onClick(e));

    this.rebuildThemeAndGraph();
    this.animate();
  }

  rebuildThemeAndGraph() {
    const isDark = document.body.classList.contains('dark-mode');
    const isLight = !isDark;
    this.scene.background = new THREE.Color(isLight ? 0xf8f9fa : 0x1f1f1f);

    while (this.plateGroup.children.length) this.plateGroup.remove(this.plateGroup.children[0]);
    while (this.meshGroup.children.length) this.meshGroup.remove(this.meshGroup.children[0]);
    while (this.lineGroup.children.length) this.lineGroup.remove(this.lineGroup.children[0]);
    this.nodes.clear();

    this.plateGroup.add(
      this.createPlate(
        this.LAYER_Y_ONT,
        0x3b6ea5,
        "ONTOLOGY LAYER (정형 원장 8종 · 비즈니스 맥락 1종 — 9 Classes)",
        isLight
      )
    );
    this.plateGroup.add(
      this.createPlate(
        this.LAYER_Y_LEX,
        0x3b735b,
        "LEX LAYER (비정형 OKF 문서 루트 1종 · 조문 1종 — 2 Classes)",
        isLight
      )
    );

    BQ_CLASS_NODES.forEach(n => {
      const plateY = n.layer === 'ONT' ? this.LAYER_Y_ONT : this.LAYER_Y_LEX;
      const nodeY = plateY + 6;
      const rad = n.radius || 14;
      const geom = new THREE.SphereGeometry(rad, 28, 28);
      const mat = new THREE.MeshStandardMaterial({ color: n.color, roughness: 0.48, metalness: 0.08 });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(n.x, nodeY, n.z);
      mesh.userData = n;
      this.meshGroup.add(mesh);

      // Subtle ring for central hubs (LoanContract / OrderItem / Product & Provision)
      if (n.id === 'CLS_LOAN' || n.id === 'CLS_ORDER_ITEM' || (n.id === 'CLS_PRODUCT' && (n.radius || 14) >= 17) || n.id === 'CLS_PROVISION') {
        const ringGeom = new THREE.RingGeometry(rad + 3.5, rad + 5.5, 36);
        const ringMat = new THREE.MeshBasicMaterial({
          color: (n.id === 'CLS_LOAN' || n.id === 'CLS_ORDER_ITEM' || n.id === 'CLS_PRODUCT') ? 0x3b6ea5 : 0x3b735b,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.36
        });
        const ring = new THREE.Mesh(ringGeom, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.set(n.x, plateY + 1.0, n.z);
        this.plateGroup.add(ring);
      }

      const sprite = this.createNodePillSprite(n.label, n.ko, n.color, isLight);
      sprite.position.set(n.x, nodeY + rad + 16, n.z);
      sprite.userData = n;
      this.meshGroup.add(sprite);

      this.nodes.set(n.id, { data: n, mesh });
    });

    BQ_CLASS_EDGES.forEach(e => {
      const s = this.nodes.get(e.source);
      const t = this.nodes.get(e.target);
      if (!s || !t) return;

      // Render self-referential loops on Provision (HAS_EXCEPTION_PROVISO, DELEGATES_TO_INTERNAL, CONFLICTS_BY_SECTOR)
      if (e.isSelfLoop) {
        const p = s.mesh.position;
        const loopConfigs = [
          { cp1: new THREE.Vector3(p.x + 85, p.y + 4, p.z - 95), cp2: new THREE.Vector3(p.x + 175, p.y + 4, p.z - 35), labelPos: new THREE.Vector3(p.x + 138, p.y + 15, p.z - 62) },
          { cp1: new THREE.Vector3(p.x + 195, p.y + 4, p.z - 40), cp2: new THREE.Vector3(p.x + 195, p.y + 4, p.z + 45), labelPos: new THREE.Vector3(p.x + 188, p.y + 15, p.z + 2) },
          { cp1: new THREE.Vector3(p.x + 175, p.y + 4, p.z + 40), cp2: new THREE.Vector3(p.x + 85, p.y + 4, p.z + 100), labelPos: new THREE.Vector3(p.x + 138, p.y + 15, p.z + 68) }
        ];
        const cfg = loopConfigs[e.loopIdx || 0];
        const curve = new THREE.CubicBezierCurve3(p.clone(), cfg.cp1, cfg.cp2, p.clone());
        const tubeGeom = new THREE.TubeGeometry(curve, 36, 0.45, 8, false);
        const tubeMat = new THREE.MeshBasicMaterial({
          color: e.color || 0xa85c56,
          transparent: true,
          opacity: 0.78
        });
        this.lineGroup.add(new THREE.Mesh(tubeGeom, tubeMat));

        const badge = this.createEdgeBadgeSprite(e.rel, e.color || 0xa85c56, isLight);
        badge.position.copy(cfg.labelPos);
        badge.userData = s.data;
        this.meshGroup.add(badge);
        return;
      }

      const color = e.color || (e.isBridge ? 0xb88a44 : 0x6b88a8);
      const startPos = s.mesh.position.clone();
      const endPos = t.mesh.position.clone();
      let curve;
      if (e.isBridge) {
        curve = new THREE.LineCurve3(startPos, endPos);
      } else {
        // Gentle upward arch above the plate so intra-layer connecting lines never touch the grid
        const midCtrl = new THREE.Vector3().addVectors(startPos, endPos).multiplyScalar(0.5);
        midCtrl.y += 8;
        curve = new THREE.QuadraticBezierCurve3(startPos, midCtrl, endPos);
      }

      const tubeRadius = e.isBridge ? 0.55 : 0.42;
      const tubeGeom = new THREE.TubeGeometry(curve, 24, tubeRadius, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: e.isBridge ? 0.82 : 0.74
      });
      this.lineGroup.add(new THREE.Mesh(tubeGeom, tubeMat));

      // Sleek directional arrowhead cone near target sphere
      const tParam = 0.79;
      const conePos = curve.getPoint(tParam);
      const tangent = curve.getTangent(tParam).normalize();
      const coneGeom = new THREE.ConeGeometry(tubeRadius * 3.1, 6.2, 12);
      const coneMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.84 });
      const cone = new THREE.Mesh(coneGeom, coneMat);
      cone.position.copy(conePos);
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
      this.lineGroup.add(cone);

      if (e.isBridge || e.rel === 'PART_OF_DOCUMENT' || e.rel === 'SCOPES_PORTFOLIO') {
        const mid = curve.getPoint(0.5);
        if (e.rel === 'PART_OF_DOCUMENT' || e.rel === 'SCOPES_PORTFOLIO') mid.y += 9;
        const badge = this.createEdgeBadgeSprite(
          e.rel === 'INVOKES_PROVISION' ? 'INVOKES_PROVISION (term_key)' : e.rel,
          color,
          isLight
        );
        badge.position.copy(mid);
        this.lineGroup.add(badge);
      }
    });
  }

  createPlate(y, borderColor, title, isLight) {
    const group = new THREE.Group();
    const geom = new THREE.PlaneGeometry(680, 290);
    const mat = new THREE.MeshPhysicalMaterial({
      color: isLight ? 0xffffff : 0x242628,
      transparent: true,
      opacity: isLight ? 0.88 : 0.82,
      roughness: 0.35,
      side: THREE.DoubleSide
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = y;
    group.add(mesh);

    const grid = new THREE.GridHelper(660, 22, isLight ? 0xe0e3e7 : 0x35383b, isLight ? 0xf1f3f4 : 0x2c2e30);
    grid.position.y = y + 0.4;
    group.add(grid);

    const borderGeom = new THREE.EdgesGeometry(geom);
    const borderMat = new THREE.LineBasicMaterial({ color: borderColor, transparent: true, opacity: 0.48 });
    const border = new THREE.LineSegments(borderGeom, borderMat);
    border.rotation.x = -Math.PI / 2;
    border.position.y = y;
    group.add(border);

    const titleSprite = this.createPlateTitleSprite(title, borderColor, isLight);
    titleSprite.position.set(-190, y + 10, -132);
    group.add(titleSprite);
    return group;
  }

  createPlateTitleSprite(text, colorHex, isLight) {
    const canvas = document.createElement('canvas');
    canvas.width = 760;
    canvas.height = 84;
    const ctx = canvas.getContext('2d');
    const hex = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.95)' : 'rgba(36, 38, 40, 0.95)';
    ctx.strokeStyle = hex;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.roundRect(8, 8, 744, 68, 16);
    ctx.fill();
    ctx.stroke();
    ctx.font = '600 21px "Google Sans", "Noto Sans KR", sans-serif';
    ctx.fillStyle = hex;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 380, 42);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }));
    sprite.scale.set(172, 19, 1);
    return sprite;
  }

  createNodePillSprite(enLabel, koLabel, colorHex, isLight) {
    const canvas = document.createElement('canvas');
    canvas.width = 540;
    canvas.height = 132;
    const ctx = canvas.getContext('2d');
    const hex = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(38, 40, 42, 0.96)';
    ctx.strokeStyle = hex;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.roundRect(12, 12, 516, 108, 20);
    ctx.fill();
    ctx.stroke();

    ctx.font = '600 23px "Google Sans", sans-serif';
    ctx.fillStyle = isLight ? '#202124' : '#e3e3e3';
    ctx.textAlign = 'center';
    ctx.fillText(enLabel, 270, 54);

    ctx.font = '500 17.5px "Noto Sans KR", sans-serif';
    ctx.fillStyle = isLight ? '#5f6368' : '#9aa0a6';
    ctx.fillText(koLabel, 270, 89);

    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }));
    sprite.scale.set(92, 22.5, 1);
    return sprite;
  }

  createEdgeBadgeSprite(label, colorHex, isLight) {
    const canvas = document.createElement('canvas');
    canvas.width = 440;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const hex = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.fillStyle = isLight ? 'rgba(248, 249, 250, 0.95)' : 'rgba(36, 38, 40, 0.95)';
    ctx.strokeStyle = hex;
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.roundRect(8, 8, 424, 48, 12);
    ctx.fill();
    ctx.stroke();

    ctx.font = '600 17px "Roboto Mono", "Google Sans", monospace';
    ctx.fillStyle = hex;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, 220, 32);

    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }));
    sprite.scale.set(72, 10.5, 1);
    return sprite;
  }

  onClick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const hits = this.raycaster.intersectObjects(this.meshGroup.children, true);
    if (hits.length > 0 && hits[0].object.userData && hits[0].object.userData.id) {
      openBqClassInspector(hits[0].object.userData);
    }
  }

  resize() {
    if (!this.container) return;
    const w = this.container.clientWidth || 900;
    const h = this.container.clientHeight || 680;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    TWEEN.update();
    if (this.controls) this.controls.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }
}

function bqCamReset() {
  if (!bqThreeViz) return;
  new TWEEN.Tween(bqThreeViz.camera.position).to({ x: 0, y: 145, z: 650 }, 850).easing(TWEEN.Easing.Cubic.Out).start();
  new TWEEN.Tween(bqThreeViz.controls.target).to({ x: 0, y: 0, z: 0 }, 850).easing(TWEEN.Easing.Cubic.Out).start();
}

function bqCamTop() {
  if (!bqThreeViz) return;
  new TWEEN.Tween(bqThreeViz.camera.position).to({ x: 0, y: 720, z: 10 }, 850).easing(TWEEN.Easing.Cubic.Out).start();
  new TWEEN.Tween(bqThreeViz.controls.target).to({ x: 0, y: 0, z: 0 }, 850).easing(TWEEN.Easing.Cubic.Out).start();
}

function bqCamSplit() {
  if (!bqThreeViz) return;
  new TWEEN.Tween(bqThreeViz.camera.position).to({ x: 0, y: 18, z: 670 }, 850).easing(TWEEN.Easing.Cubic.Out).start();
  new TWEEN.Tween(bqThreeViz.controls.target).to({ x: 0, y: 0, z: 0 }, 850).easing(TWEEN.Easing.Cubic.Out).start();
}

function openBqClassInspector(cls) {
  const relEdges = BQ_CLASS_EDGES.filter(e => e.source === cls.id || e.target === cls.id);
  const layerTitle = cls.layer === 'ONT' ? 'ONTOLOGY LAYER (정형 원장·맥락)' : 'LEX LAYER (비정형 법규·조문)';
  const drawerTitleEl = document.getElementById('bq-drawer-title');
  if (drawerTitleEl) {
    drawerTitleEl.textContent = `Class · ${cls.label} (${cls.layer})`;
    drawerTitleEl.title = `Class · ${cls.label} (${cls.layer}) — ${cls.ko || ''}`;
  }

  const propsHtml = Array.isArray(cls.props)
    ? `<table class="mod-table" style="margin-bottom:14px;">
        <thead><tr><th>Property</th><th>Type</th><th>1-Line Description (OPTIONS)</th></tr></thead>
        <tbody>
          ${cls.props.map(p => `
            <tr>
              <td><code>${escapeHtml(p.name)}</code></td>
              <td style="white-space:nowrap; font-size:11px; color:var(--text-sub);">${escapeHtml(p.type || '')}</td>
              <td style="font-size:11.5px; color:var(--text-sub);">${escapeHtml(p.desc || '')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>`
    : '';

  const anchorHtml = cls.anchor
    ? `<div class="section-label"><span>Dataplex KC Custom Aspect (ontology-class-anchors)</span><span>${escapeHtml(cls.anchor.anchor_type)}</span></div>
       <div class="trace-step" style="margin-bottom:14px;">
         <div style="font-size:11.5px; color:var(--text-sub); line-height:1.6;">
           • <strong>Alias Group:</strong> <code>${escapeHtml(cls.anchor.alias_group)}</code> &nbsp;|&nbsp; <strong>Bind Key:</strong> <code>${escapeHtml(cls.anchor.match_bind_key)}</code><br>
           • <strong>GQL Match Snippet:</strong> <code>${escapeHtml(cls.anchor.gql_match_template)}</code><br>
           • <strong>Planner Instruction:</strong> ${escapeHtml(cls.anchor.planner_instruction)}
         </div>
       </div>`
    : '';

  document.getElementById('bq-drawer-body').innerHTML = `
    <div class="section-label"><span>BigQuery Property Graph Class Definition</span><span>${escapeHtml(layerTitle)}</span></div>
    <div class="okf-title" style="margin-bottom:6px;">${escapeHtml(cls.label)} — ${escapeHtml(cls.ko)}</div>
    <div style="font-size:12.5px; color:var(--text); background:var(--gcp-blue-bg); border-radius:6px; padding:8px 11px; margin-bottom:12px;">
      ${escapeHtml(cls.desc || '')}
    </div>
    <div style="font-size:12px; color:var(--text-sub); line-height:1.65; margin-bottom:14px;">
      • <strong>Primary Key:</strong> <code>${escapeHtml(cls.pk)}</code><br>
      • <strong>Graph View:</strong> <code>${escapeHtml(cls.view || cls.table)}</code><br>
      • <strong>Physical Source:</strong> <code>${escapeHtml(cls.table)}</code>
    </div>
    ${anchorHtml}
    <div class="section-label"><span>Node Properties &amp; 1-Line Descriptions</span><span>l1.yaml SSOT</span></div>
    ${propsHtml}
    <div class="section-label"><span>BigQuery CREATE PROPERTY GRAPH Node DDL</span></div>
    <div class="frontmatter-block" style="border:1px solid var(--border); border-radius:6px; margin-bottom:14px;">${escapeHtml(cls.ddl)}</div>
    <div class="section-label"><span>Connected Class Relations (${relEdges.length})</span></div>
    <div class="biz-edge-list">
      ${relEdges.map(e => {
        const srcNode = BQ_CLASS_NODES.find(n => n.id === e.source);
        const tgtNode = BQ_CLASS_NODES.find(n => n.id === e.target);
        const srcLabel = srcNode ? srcNode.label : e.source;
        const tgtLabel = tgtNode ? tgtNode.label : e.target;
        return `
        <div class="biz-edge-item">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="edge-badge">${escapeHtml(e.rel)}</span>
            <code style="font-size:10.5px; color:var(--text-sub);">${escapeHtml(e.view || '')}</code>
          </div>
          <div class="edge-target">${escapeHtml(srcLabel)} ➔ ${escapeHtml(tgtLabel)}</div>
          <div class="edge-reason">${escapeHtml(e.desc || '')}</div>
        </div>
      `;
      }).join('')}
    </div>
  `;
  document.getElementById('bq-detail-drawer').classList.add('open');
}

function closeBqDrawer() {
  document.getElementById('bq-detail-drawer').classList.remove('open');
}

function toggleBqCqBanner() {
  bqCqBannerVisible = !bqCqBannerVisible;
  const banner = document.getElementById('bq-cq-banner');
  if (banner && BQ_GRAPH_MODE === 'INSTANCE') {
    banner.style.display = bqCqBannerVisible ? 'block' : 'none';
  }
}

function syncBqGqlCustomSelectUi(idx) {
  const preset = BQ_GQL_PRESETS[idx] || BQ_GQL_PRESETS[0];
  const valEl = document.getElementById('bq-gql-select-val');
  if (valEl && preset) valEl.textContent = preset.title;
  const menuEl = document.getElementById('bq-gql-select-menu');
  if (menuEl) {
    menuEl.innerHTML = BQ_GQL_PRESETS.map((p, pIdx) => {
      const isSel = pIdx === idx;
      return `
        <div class="gcp-custom-select-opt ${isSel ? 'selected' : ''}" data-idx="${pIdx}" onclick="selectBqGqlCustomOption(event, ${pIdx})">
          <span>${escapeHtml(p.title)}</span>
          <span class="material-symbols-outlined gcp-opt-check" style="opacity:${isSel ? '1' : '0'};">check</span>
        </div>`;
    }).join('');
  }
}

function selectBqGqlCustomOption(ev, idx) {
  if (ev) ev.stopPropagation();
  const wrap = document.getElementById('bq-gql-custom-select');
  if (wrap) wrap.classList.remove('open');
  onBqGqlSelectChange(idx);
}

let bqRawRowsOpen = false;
let bqCqNoteOpen = false;

function toggleBqRawRowsPanel() {
  bqRawRowsOpen = !bqRawRowsOpen;
  const el = document.getElementById('bq-raw-rows-panel');
  if (el) el.style.display = bqRawRowsOpen ? 'block' : 'none';
  const btn = document.getElementById('bq-btn-raw-rows');
  if (btn) btn.classList.toggle('active', bqRawRowsOpen);
}

function toggleBqCqNotePanel() {
  bqCqNoteOpen = !bqCqNoteOpen;
  const el = document.getElementById('bq-cq-note-panel');
  if (el) el.style.display = bqCqNoteOpen ? 'block' : 'none';
  const btn = document.getElementById('bq-btn-cq-note');
  if (btn) btn.classList.toggle('active', bqCqNoteOpen);
}

function setBqQueryStatusChip() {
  // Status chip removed from GQL editor header; button state & job banner handle feedback.
}

function onBqGqlSelectChange(idx) {
  BQ_QUERY_IDX = (idx >= 0 && idx < BQ_GQL_PRESETS.length) ? idx : 0;
  syncBqGqlCustomSelectUi(BQ_QUERY_IDX);
  const preset = BQ_GQL_PRESETS[BQ_QUERY_IDX] || BQ_GQL_PRESETS[0];
  const codeEl = document.getElementById('bq-gql-code');
  if (codeEl) {
    if ('value' in codeEl) codeEl.value = preset.gql;
    else codeEl.textContent = preset.gql;
  }
  setBqQueryStatusChip(`Template Loaded (${preset.cqId}) · Click Run`, 'template');
  saveUiState();
}

function setBqGraphMode(mode) {
  BQ_GRAPH_MODE = mode;
  document.getElementById('bq-btn-class-mode').classList.toggle('active', mode === 'CLASS');
  document.getElementById('bq-btn-inst-mode').classList.toggle('active', mode === 'INSTANCE');
  document.getElementById('bq-three-container').style.display = mode === 'CLASS' ? 'block' : 'none';
  document.getElementById('bq-cam-toolbar').style.display = mode === 'CLASS' ? 'flex' : 'none';
  const instTb = document.getElementById('bq-inst-toolbar');
  if (instTb) instTb.style.display = mode === 'INSTANCE' ? 'flex' : 'none';
  const banner = document.getElementById('bq-cq-banner');
  if (banner) banner.style.display = (mode === 'INSTANCE' && bqCqBannerVisible) ? 'block' : 'none';
  document.getElementById('bq-vis-container').style.display = mode === 'INSTANCE' ? 'block' : 'none';

  if (mode === 'CLASS') {
    document.getElementById('bq-stat-n').textContent = '11';
    document.getElementById('bq-stat-n-lbl').textContent = 'Ontology Classes';
    document.getElementById('bq-stat-e').textContent = '15';
    document.getElementById('bq-stat-e-lbl').textContent = 'Class Relations';
    const sb = document.getElementById('bq-stat-b');
    const sbLbl = document.getElementById('bq-stat-b-lbl');
    if (sb) sb.textContent = '3';
    if (sbLbl) sbLbl.textContent = 'ONT↔LEX Bridges';
    if (!bqThreeViz) {
      bqThreeViz = new BqClass3DVisualizer('bq-three-container');
    } else {
      bqThreeViz.rebuildThemeAndGraph();
      bqThreeViz.resize();
    }
  } else if (mode === 'INSTANCE' && bqCurrentInstNodes.length === 0) {
    runBqGqlQuery();
  }
  saveUiState();
}

function renderBqRawRowsTable(rawRows) {
  if (!Array.isArray(rawRows) || rawRows.length === 0) {
    return '<div style="font-size:11.5px; color:var(--text-sub); padding:6px 0;">반환된 레코드가 없습니다.</div>';
  }
  const cols = Object.keys(rawRows[0]).slice(0, 9);
  return `
    <div style="max-height:165px; overflow:auto; border:1px solid var(--border); border-radius:6px; margin-top:8px; background:var(--bg);">
      <table class="mod-table" style="margin:0; font-size:11px;">
        <thead>
          <tr>${cols.map(c => `<th style="padding:5px 8px; white-space:nowrap;">${escapeHtml(c)}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${rawRows.map(r => `
            <tr>
              ${cols.map(c => `<td style="padding:4px 8px; white-space:nowrap; font-family:'Roboto Mono', monospace; font-size:10.5px;">${escapeHtml(String(r[c] ?? ''))}</td>`).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

async function runBqGqlQuery() {
  if (BQ_QUERY_IDX < 0 || BQ_QUERY_IDX >= BQ_GQL_PRESETS.length) {
    BQ_QUERY_IDX = 0;
  }
  syncBqGqlCustomSelectUi(BQ_QUERY_IDX);

  const preset = BQ_GQL_PRESETS[BQ_QUERY_IDX] || BQ_GQL_PRESETS[0];
  const codeEl = document.getElementById('bq-gql-code');
  const currentGql = (codeEl && ('value' in codeEl ? codeEl.value : codeEl.textContent) || '').trim() || preset.gql;
  if (codeEl) {
    if ('value' in codeEl && !codeEl.value.trim()) codeEl.value = currentGql;
    else if (!('value' in codeEl) && !codeEl.textContent.trim()) codeEl.textContent = currentGql;
  }

  BQ_GRAPH_MODE = 'INSTANCE';
  document.getElementById('bq-btn-class-mode').classList.remove('active');
  document.getElementById('bq-btn-inst-mode').classList.add('active');
  document.getElementById('bq-three-container').style.display = 'none';
  document.getElementById('bq-cam-toolbar').style.display = 'none';
  const instTb = document.getElementById('bq-inst-toolbar');
  if (instTb) instTb.style.display = 'flex';
  document.getElementById('bq-vis-container').style.display = 'block';

  const runBtn = document.getElementById('bq-run-query-btn') || document.getElementById('bq-run-gql-btn');
  const origBtnHtml = runBtn ? runBtn.innerHTML : '';
  if (runBtn) {
    runBtn.disabled = true;
    runBtn.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px;">hourglass_top</span> Querying BigQuery...`;
  }
  setBqQueryStatusChip('Querying BigQuery...', 'running');

  const banner = document.getElementById('bq-cq-banner');
  let dotsTimer = null;
  if (banner && bqCqBannerVisible) {
    banner.style.display = 'block';
    banner.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
        <div style="display:flex; align-items:center; gap:8px; font-size:12px; color:var(--text-sub);">
          <span class="material-symbols-outlined gcp-spin-sync" style="font-size:16px; color:#b88a44;">sync</span>
          <span>BigQuery Graph 실행 중<span id="bq-running-dots" style="display:inline-block; min-width:14px;">.</span></span>
        </div>
        <button class="icon-close-btn" onclick="toggleBqCqBanner()" title="배너 숨기기" style="padding:2px; margin-top:-2px; flex-shrink:0;">
          <span class="material-symbols-outlined" style="font-size:16px;">close</span>
        </button>
      </div>
    `;
    let dotStep = 1;
    dotsTimer = setInterval(() => {
      const dotsEl = document.getElementById('bq-running-dots');
      if (!dotsEl) return;
      dotStep = (dotStep % 3) + 1;
      dotsEl.textContent = '.'.repeat(dotStep);
    }, 380);
  }

  let liveData = null;
  try {
    const resp = await fetch('/api/bq-graph/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: typeof ACTIVE_PROJECT !== 'undefined' ? ACTIVE_PROJECT : 'finance-ontology',
        queryIdx: BQ_QUERY_IDX,
        gql: currentGql
      })
    });
    if (resp.ok) {
      const json = await resp.json();
      if (json && json.ok) {
        if (json.use_preset_topology) {
          const objRefs = json.objectrefs || {};
          const mergedNodes = (preset.nodes || []).map(n => {
            const copy = Object.assign({}, n, { record: Object.assign({}, n.record || {}) });
            const slotId = copy.record.provision_slot_id || copy.matchSec || '';
            const docId = copy.record.doc_id || '';
            const refKey = copy.classLabel === 'Provision' && slotId
              ? `PROVISION::${slotId}`
              : (copy.classLabel === 'SourceDocument' && docId ? `DOC::${docId}` : '');
            if (refKey && objRefs[refKey]) {
              copy.record.gcs_obj_ref = objRefs[refKey].gcs_obj_ref;
              copy.objectRefLive = objRefs[refKey].objectRefLive;
            }
            return copy;
          });
          liveData = Object.assign({}, json, {
            nodes: mergedNodes,
            edges: preset.edges || []
          });
        } else if (Array.isArray(json.nodes) && json.nodes.length > 0) {
          liveData = json;
        }
      }
    }
  } catch (err) {
    console.warn('Live BigQuery query fallback to local preset:', err);
  } finally {
    if (dotsTimer) clearInterval(dotsTimer);
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.innerHTML = origBtnHtml || `<span class="material-symbols-outlined" style="font-size:16px;">play_arrow</span> Run GQL Query`;
    }
  }

  const activeNodes = liveData ? liveData.nodes : (preset.nodes || []);
  const activeEdges = liveData ? liveData.edges : (preset.edges || []);
  const jobId = liveData ? liveData.job_id : 'local_preset_fallback';
  const elapsedMs = liveData ? liveData.elapsed_ms : 0;
  const rowCount = liveData ? liveData.row_count : activeNodes.length;
  const rawRows = liveData ? (liveData.raw_rows || []) : [];
  const summaryText = liveData && liveData.summary ? liveData.summary : preset.verdict;
  const modeLabel = liveData ? (liveData.mode || preset.cqId) : preset.cqId;

  setBqQueryStatusChip(
    liveData ? `LIVE BQ · ${elapsedMs}ms · ${rowCount} rows` : `Fallback · ${activeNodes.length} nodes`,
    liveData ? 'live' : 'template'
  );

  const isDark = document.body.classList.contains('dark-mode');
  const labelMainColor = isDark ? '#e3e3e3' : '#202124';
  const edgeBgColor = isDark ? 'rgba(31, 31, 31, 0.88)' : 'rgba(255, 255, 255, 0.92)';

  // Render Live BigQuery Job Execution & Result Bar
  if (banner) {
    banner.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px; flex-wrap:nowrap; margin-bottom:7px;">
        <div style="display:flex; align-items:center; gap:7px; flex-wrap:wrap; min-width:0;">
          <span class="mod-badge">${liveData ? 'LIVE BQ JOB' : 'PRESET'} · ${escapeHtml(modeLabel)}</span>
          <code style="font-size:11px; color:var(--text-sub);">job_id: ${escapeHtml(jobId)}</code>
          <span style="font-size:11px; color:var(--text-sub);">· <strong>${escapeHtml(String(elapsedMs))} ms</strong> · <strong>${escapeHtml(String(rowCount))} rows</strong> · <strong>${escapeHtml(String(activeNodes.length))} Nodes / ${escapeHtml(String(activeEdges.length))} Edges</strong></span>
        </div>
        <button class="icon-close-btn" onclick="toggleBqCqBanner()" title="배너 숨기기" style="padding:2px; margin-top:-2px; flex-shrink:0;">
          <span class="material-symbols-outlined" style="font-size:16px;">close</span>
        </button>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
        <div style="flex:1; min-width:260px; background:var(--bg); border:1px solid var(--border-subtle); color:var(--text); padding:6px 10px; border-radius:6px; font-size:12px;">
          <strong style="color:var(--text);">실측 결과:</strong> ${escapeHtml(summaryText)}
        </div>
        <div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
          ${rawRows.length > 0 ? `
            <button id="bq-btn-raw-rows" class="mgmt-chip-btn ${bqRawRowsOpen ? 'active' : ''}" onclick="toggleBqRawRowsPanel()">
              <span class="material-symbols-outlined" style="font-size:14px;">table_rows</span> Raw Rows (${rawRows.length})
            </button>
          ` : ''}
          <button id="bq-btn-cq-note" class="mgmt-chip-btn ${bqCqNoteOpen ? 'active' : ''}" onclick="toggleBqCqNotePanel()">
            <span class="material-symbols-outlined" style="font-size:14px;">info</span> CQ 해설
          </button>
        </div>
      </div>
      <div id="bq-raw-rows-panel" style="display:${bqRawRowsOpen ? 'block' : 'none'};">
        ${renderBqRawRowsTable(rawRows)}
      </div>
      <div id="bq-cq-note-panel" style="display:${bqCqNoteOpen ? 'block' : 'none'}; margin-top:8px; padding-top:7px; border-top:1px dashed var(--border); font-size:11.5px; color:var(--text-sub); line-height:1.55;">
        <div style="margin-bottom:3px; color:var(--text);"><strong>현업 질의 (${escapeHtml(preset.cqId)}):</strong> "${escapeHtml(preset.question)}"</div>
        <div>${escapeHtml(preset.answerDetail)}</div>
      </div>
    `;
    banner.style.display = bqCqBannerVisible ? 'block' : 'none';
  }

  // Build 2-Layer Ontology <-> LEX Instance Graph
  const visNodes = activeNodes.map(n => {
    const isBox = n.shape === 'box';
    const isDoc = n.classLabel === 'SourceDocument';
    return {
      id: n.id,
      label: n.label,
      title: n.title,
      shape: n.shape || 'dot',
      size: n.size || 18,
      margin: isBox ? (isDoc ? 11 : 9) : undefined,
      color: {
        background: isBox
          ? (isDoc ? (isDark ? '#23312b' : '#f2f7f4') : (isDark ? '#28292a' : '#ffffff'))
          : n.color,
        border: n.color,
        highlight: {
          background: isBox ? (isDark ? '#303134' : '#eef3f0') : n.color,
          border: labelMainColor
        }
      },
      borderWidth: isBox ? (isDoc ? 2.4 : 2.0) : 1.8,
      font: {
        color: labelMainColor,
        size: 11.5,
        face: 'Google Sans, Noto Sans KR',
        multi: false
      },
      instData: n
    };
  });

  const visEdges = activeEdges.map((e, i) => ({
    id: `E_${modeLabel}_${i}`,
    from: e.from,
    to: e.to,
    label: e.label,
    color: { color: e.color || '#6b88a8', highlight: labelMainColor },
    width: e.width || 1.6,
    dashes: Boolean(e.dashes),
    arrows: 'to',
    font: {
      color: labelMainColor,
      size: 9.5,
      background: edgeBgColor,
      strokeWidth: 0,
      face: 'Roboto Mono, Google Sans'
    }
  }));

  bqCurrentInstNodes = visNodes;
  bqCurrentInstEdges = visEdges;

  const bridgeCnt = visEdges.filter(e =>
    e.label.includes('INVOKES_PROVISION') ||
    e.label.includes('GOVERNED_BY_CRITERIA') ||
    e.label.includes('EVALUATED_UNDER_PROVISION')
  ).length;

  document.getElementById('bq-stat-n').textContent = String(visNodes.length);
  document.getElementById('bq-stat-n-lbl').textContent = `${modeLabel} Nodes`;
  document.getElementById('bq-stat-e').textContent = String(visEdges.length);
  document.getElementById('bq-stat-e-lbl').textContent = `${modeLabel} Edges`;
  const sb = document.getElementById('bq-stat-b');
  const sbLbl = document.getElementById('bq-stat-b-lbl');
  if (sb) sb.textContent = String(bridgeCnt);
  if (sbLbl) sbLbl.textContent = 'ONT↔LEX Bridges';

  const container = document.getElementById('bq-vis-container');
  if (bqVisNet) bqVisNet.destroy();
  bqVisNet = new vis.Network(
    container,
    { nodes: new vis.DataSet(visNodes), edges: new vis.DataSet(visEdges) },
    {
      physics: {
        enabled: bqInstPhysics,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -55,
          centralGravity: 0.009,
          springLength: 118,
          springConstant: 0.07,
          damping: 0.48
        },
        stabilization: { iterations: 160 }
      },
      interaction: {
        hover: true,
        tooltipDelay: 180,
        keyboard: true
      }
    }
  );

  bqVisNet.once('stabilizationIterationsDone', () => {
    bqVisNet.fit({ animation: { duration: 350 } });
    setTimeout(() => {
      if (bqVisNet && bqVisNet.getScale() > 0.95) {
        bqVisNet.moveTo({ scale: 0.88, animation: { duration: 250 } });
      }
    }, 380);
  });

  bqVisNet.on('click', (params) => {
    if (params.nodes.length > 0) {
      const clickedId = params.nodes[0];
      const nObj = bqCurrentInstNodes.find(x => x.id === clickedId);
      if (!nObj || !nObj.instData) return;
      openBqInstanceInspector(nObj.instData);
    }
  });
  saveUiState();
}

function openBqInstanceInspector(inst) {
  const relEdges = bqCurrentInstEdges.filter(e => e.from === inst.id || e.to === inst.id);
  const layerBadge = inst.layer === 'ONT' ? 'ONTOLOGY LAYER · Instance' : 'LEX LAYER · OKF ObjectRef Node';
  const drawerTitleEl = document.getElementById('bq-drawer-title');
  if (drawerTitleEl) {
    const tStr = `${inst.classLabel} · ${inst.id.split('::').pop()}`;
    drawerTitleEl.textContent = tStr;
    drawerTitleEl.title = `${tStr} (${inst.title || inst.id})`;
  }

  let okfJumpAndPreviewHtml = '';
  if (inst.layer === 'LEX') {
    const objLive = inst.objectRefLive;
    if (objLive && (objLive.verbatim_body || objLive.yaml_frontmatter)) {
      const fmRaw = `---\n${objLive.yaml_frontmatter || ''}\n---`;
      const fmFormatted = typeof colorizeYaml === 'function' ? colorizeYaml(fmRaw) : escapeHtml(fmRaw);
      const bodyFormatted = typeof highlightTerms === 'function'
        ? highlightTerms(escapeHtml(objLive.verbatim_body || ''))
        : escapeHtml(objLive.verbatim_body || '');
      const fmOpenAttr = typeof FM_OPEN !== 'undefined' && FM_OPEN ? 'open' : '';
      okfJumpAndPreviewHtml = `
        ${objLive.yaml_frontmatter ? `
          <details class="fm-accordion" style="margin-top:14px;" ${fmOpenAttr} ontoggle="if(typeof onFmToggle==='function') onFmToggle(this.open)">
            <summary>
              <span class="fm-summary-left">
                <span>YAML Frontmatter</span>
              </span>
              <span class="material-symbols-outlined fm-chevron">expand_more</span>
            </summary>
            <div class="frontmatter-block">${fmFormatted}</div>
          </details>
        ` : ''}
        <div class="section-label" style="margin-top:12px;">
          <span>Verbatim Markdown Body</span>
        </div>
        <div class="okf-body-box">${bodyFormatted}</div>
      `;
    } else if (inst.matchSec || (inst.record && inst.record.provision_slot_id)) {
      const slotId = inst.record && inst.record.provision_slot_id;
      const p = PROVS.find(x => x.concept_id === inst.matchSec || (slotId && x.concept_id === slotId) || x.section_number === inst.matchSec);
      if (p && typeof buildOkfDetailMarkup === 'function') {
        okfJumpAndPreviewHtml = `
          <div style="margin-top:14px;">
            ${buildOkfDetailMarkup(p)}
          </div>
        `;
      }
    }
  }

  const graphDsName = (typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology')
    ? 'kmarket_ontology'
    : 'starlight_bank_ontology';

  document.getElementById('bq-drawer-body').innerHTML = `
    <div class="section-label"><span>${escapeHtml(layerBadge)}</span><span>Class: ${escapeHtml(inst.classLabel)}</span></div>
    <div class="okf-title" style="white-space:pre-line; margin-bottom:8px;">${escapeHtml(inst.label)}</div>
    <div style="font-size:12px; color:var(--text-sub); line-height:1.65; margin-bottom:10px;">
      • <strong>Graph View:</strong> <code>${graphDsName}.${escapeHtml(inst.viewName || '')}</code><br>
      • <strong>Source Store:</strong> <code>${escapeHtml(inst.sourceStore || '')}</code>
    </div>
    ${inst.verdictNote ? `
      <div style="background:var(--gcp-blue-bg); color:var(--gcp-blue); border-radius:6px; padding:9px 12px; font-size:12px; font-weight:600; margin-bottom:12px;">
        • CQ 추론 역할: ${escapeHtml(inst.verdictNote)}
      </div>
    ` : ''}
    <div class="section-label"><span>Live Instance Record Properties (JSON)</span></div>
    <div class="frontmatter-block" style="border:1px solid var(--border); border-radius:6px; margin-bottom:14px;">${escapeHtml(JSON.stringify(inst.record || {}, null, 2))}</div>
    <div class="section-label"><span>Connected Instance Edges (${relEdges.length})</span></div>
    <div class="biz-edge-list">
      ${relEdges.map(e => `
        <div class="biz-edge-item">
          <span class="edge-badge">${escapeHtml(e.label.replace(/\n/g, ' '))}</span>
          <div class="edge-target">${escapeHtml(e.from)} ➔ ${escapeHtml(e.to)}</div>
        </div>
      `).join('')}
    </div>
    ${okfJumpAndPreviewHtml}
  `;
  document.getElementById('bq-detail-drawer').classList.add('open');
}

function initOrUpdateBqGraphStudio() {
  if (BQ_QUERY_IDX < 0 || BQ_QUERY_IDX >= BQ_GQL_PRESETS.length) {
    BQ_QUERY_IDX = 0;
  }
  syncBqGqlCustomSelectUi(BQ_QUERY_IDX);
  const preset = BQ_GQL_PRESETS[BQ_QUERY_IDX] || BQ_GQL_PRESETS[0];
  const codeEl = document.getElementById('bq-gql-code');
  if (codeEl) {
    if ('value' in codeEl) codeEl.value = preset.gql;
    else codeEl.textContent = preset.gql;
  }
  const isEcom = typeof ACTIVE_PROJECT !== 'undefined' && ACTIVE_PROJECT === 'ecommerce-ontology';
  const legDescs = document.querySelectorAll('#module-bq-graph .bq-legend-grid .legend-col-desc');
  if (legDescs.length >= 2) {
    legDescs[0].textContent = isEcom
      ? '· OrderItem · Product 양대 허브 + 원장 6종 + BusinessContext (SCOPES_PORTFOLIO)'
      : '· LoanContract 허브 + 원장 7종 + BusinessContext (SCOPES_PORTFOLIO)';
    legDescs[1].textContent = isEcom
      ? '· SourceDocument(10) + Provision(36)'
      : '· SourceDocument(10) + Provision(174)';
  }
  setBqQueryStatusChip(`Template Loaded (${preset.cqId}) · Click Run`, 'template');
  if (BQ_GRAPH_MODE === 'INSTANCE') {
    runBqGqlQuery();
  } else {
    setBqGraphMode('CLASS');
  }
}


