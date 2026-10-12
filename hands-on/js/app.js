/**
 * Google Cloud x Gemini Enterprise App Workshop Guide
 * Interactive JavaScript Controller (js/app.js)
 */

document.addEventListener('DOMContentLoaded', () => {
  initImageModal();
  initTabs();
  initKeyboardNavigation();
  initMobileDrawer();
  initProjectIdController();
});

/* ==========================================================================
   1. TAB SWITCHING & URL HASH SYNCHRONIZATION
   ========================================================================== */

const VALID_TABS = ['tab-overview', 'tab-step0', 'tab-step1', 'tab-step2', 'tab-step3', 'tab-faq', 'tab-admin-script'];

function getValidTabs() {
  const domTabs = Array.from(document.querySelectorAll('.tab-content')).map(el => el.id);
  return domTabs.length > 0 ? domTabs : VALID_TABS;
}

function switchTab(tabId, targetEl, updateHash = true) {
  const validTabs = getValidTabs();
  if (!validTabs.includes(tabId)) {
    tabId = 'tab-overview';
  }

  // Hide all tab contents
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));

  // Deactivate all navigation items
  document.querySelectorAll('[data-tab]').forEach(el => {
    el.classList.remove('active');
    if (el.hasAttribute('aria-selected')) {
      el.setAttribute('aria-selected', 'false');
    }
  });

  // Update Roving Tabindex
  updateTabindex(tabId);

  // Show target tab
  const targetTab = document.getElementById(tabId);
  if (targetTab) {
    targetTab.classList.add('active');
  }

  // Toggle Project ID config banner: hide on overview & faq, show on step tabs
  const banner = document.querySelector('.project-id-config-banner');
  if (banner) {
    if (tabId === 'tab-overview' || tabId === 'tab-faq') {
      banner.style.display = 'none';
    } else {
      banner.style.display = 'flex';
    }
  }

  // Activate matching navigation elements by data-tab
  document.querySelectorAll(`[data-tab="${tabId}"]`).forEach(el => {
    el.classList.add('active');
    if (el.hasAttribute('aria-selected')) {
      el.setAttribute('aria-selected', 'true');
    }
  });

  // Synchronize URL Hash
  if (updateHash && location.hash !== '#' + tabId) {
    if (history.pushState) {
      history.pushState(null, null, '#' + tabId);
    } else {
      location.hash = '#' + tabId;
    }
  }

  // Close mobile drawer if open
  closeMobileMenu();

  // Scroll to top
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.scrollTo({ top: 0, behavior: prefersReduced ? 'auto' : 'smooth' });
}

function updateTabindex(tabId) {
  document.querySelectorAll('[role="tab"]').forEach(tab => {
    if (tab.getAttribute('data-tab') === tabId) {
      tab.setAttribute('tabindex', '0');
    } else {
      tab.setAttribute('tabindex', '-1');
    }
  });
}

function initTabs() {
  const validTabs = getValidTabs();
  const initialHash = location.hash.replace('#', '');
  if (initialHash && validTabs.includes(initialHash)) {
    switchTab(initialHash, null, false);
  } else {
    switchTab('tab-overview', null, false);
  }

  window.addEventListener('hashchange', () => {
    const validTabsOnHash = getValidTabs();
    const hash = location.hash.replace('#', '');
    if (hash && validTabsOnHash.includes(hash)) {
      switchTab(hash, null, false);
    }
  });
}

/* ==========================================================================
   2. KEYBOARD NAVIGATION (APG TABLIST PATTERN)
   ========================================================================== */

function initKeyboardNavigation() {
  document.querySelectorAll('[role="tablist"]').forEach(tablist => {
    tablist.addEventListener('keydown', (e) => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) return;

      const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
      if (tabs.length === 0) return;

      const currentIndex = tabs.indexOf(document.activeElement);
      if (currentIndex === -1) return;

      e.preventDefault();
      let nextIndex = currentIndex;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        nextIndex = (currentIndex + 1) % tabs.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (e.key === 'Home') {
        nextIndex = 0;
      } else if (e.key === 'End') {
        nextIndex = tabs.length - 1;
      }

      const nextTab = tabs[nextIndex];
      nextTab.focus();
      const tabId = nextTab.getAttribute('data-tab');
      if (tabId) {
        switchTab(tabId, nextTab);
      }
    });
  });
}

/* ==========================================================================
   3. CLIPBOARD COPY FUNCTIONS
   ========================================================================== */

function copyCode(elementId, btnElement) {
  const target = document.getElementById(elementId);
  if (!target) return;
  const codeText = target.textContent;
  navigator.clipboard.writeText(codeText).then(() => {
    triggerBtnFeedback(btnElement);
  }).catch(err => {
    console.error('Copy failed:', err);
  });
}

function copyText(text, btnElement) {
  navigator.clipboard.writeText(text).then(() => {
    triggerBtnFeedback(btnElement);
  }).catch(err => {
    console.error('Copy failed:', err);
  });
}

function triggerBtnFeedback(btn) {
  if (!btn) return;

  if (btn._copyTimer) {
    clearTimeout(btn._copyTimer);
  }

  if (!btn._originalHTML) {
    btn._originalHTML = btn.innerHTML;
  }

  btn.innerHTML = `<svg class="nav-icon" viewBox="0 0 24 24" style="width:14px; height:14px;"><polyline points="20 6 9 17 4 12"></polyline></svg><span>복사 완료!</span>`;
  btn.style.backgroundColor = 'var(--color-success)';
  btn.style.color = '#FFFFFF';
  btn.style.borderColor = 'var(--color-success)';

  btn._copyTimer = setTimeout(() => {
    if (btn._originalHTML) {
      btn.innerHTML = btn._originalHTML;
      delete btn._originalHTML;
    }
    btn.style.backgroundColor = '';
    btn.style.color = '';
    btn.style.borderColor = '';
    delete btn._copyTimer;
  }, 2000);
}

/* ==========================================================================
   4. COLLAPSIBLE CODE BLOCKS
   ========================================================================== */

function toggleCodeExpand(btn) {
  const wrapper = btn.closest('.code-wrapper');
  if (!wrapper) return;

  const textSpan = btn.querySelector('span');
  const icon = btn.querySelector('.toggle-icon');
  const isExpanded = wrapper.classList.contains('expanded');

  if (isExpanded) {
    wrapper.classList.remove('expanded');
    if (textSpan) textSpan.textContent = '코드 전체 보기 (스크립트 전개)';
    if (icon) icon.style.transform = 'rotate(0deg)';
    wrapper.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } else {
    wrapper.classList.add('expanded');
    if (textSpan) textSpan.textContent = '접기';
    if (icon) icon.style.transform = 'rotate(180deg)';
  }
}

/* ==========================================================================
   5. STEP 3 QUERY FILTER
   ========================================================================== */

function filterQueries() {
  const filterInput = document.getElementById('queryFilterInput');
  if (!filterInput) return;
  const filterValue = filterInput.value.toLowerCase().trim();
  const queryCards = document.querySelectorAll('.query-card');

  queryCards.forEach(card => {
    const text = card.innerText.toLowerCase();
    if (text.includes(filterValue)) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

/* ==========================================================================
   6. IMAGE LIGHTBOX MODAL
   ========================================================================== */

function initImageModal() {
  document.querySelectorAll('.step-image-card').forEach(card => {
    card.addEventListener('click', () => {
      const img = card.querySelector('img');
      const caption = card.querySelector('.step-image-caption span');
      if (img) {
        openImageModal(img.src, caption ? caption.innerText : img.alt);
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeImageModal();
  });
}

function openImageModal(imgSrc, captionText) {
  const modal = document.getElementById('imageModal');
  const modalImg = document.getElementById('modalImage');
  const modalCaption = document.getElementById('modalCaption');

  if (modal && modalImg) {
    modalImg.src = imgSrc;
    if (modalCaption) modalCaption.innerText = captionText || '';
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

function closeImageModal() {
  const modal = document.getElementById('imageModal');
  if (modal) {
    modal.classList.remove('show');
    document.body.style.overflow = '';
  }
}

/* ==========================================================================
   7. MOBILE DRAWER NAVIGATION
   ========================================================================== */

function initMobileDrawer() {
  const menuToggleBtn = document.getElementById('menuToggleBtn');
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  function updateSidebarInert() {
    if (!sidebar) return;
    if (window.innerWidth <= 1080) {
      sidebar.inert = !sidebar.classList.contains('open');
    } else {
      sidebar.inert = false;
    }
  }

  if (menuToggleBtn && sidebar && sidebarBackdrop) {
    menuToggleBtn.addEventListener('click', () => {
      const isOpen = sidebar.classList.toggle('open');
      sidebarBackdrop.classList.toggle('show', isOpen);
      menuToggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      menuToggleBtn.setAttribute('aria-label', isOpen ? '메뉴 닫기' : '메뉴 열기');
      updateSidebarInert();
    });

    sidebarBackdrop.addEventListener('click', closeMobileMenu);
    window.addEventListener('resize', updateSidebarInert);
    updateSidebarInert();
  }
}

function closeMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const menuToggleBtn = document.getElementById('menuToggleBtn');

  if (sidebar) sidebar.classList.remove('open');
  if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
  if (menuToggleBtn) {
    menuToggleBtn.setAttribute('aria-expanded', 'false');
    menuToggleBtn.setAttribute('aria-label', '메뉴 열기');
  }
}

/* ==========================================================================
   6. GLOBAL PROJECT ID REPLACEMENT CONTROLLER
   ========================================================================== */

let currentProjectId = 'YOUR_PROJECT_ID';

function initProjectIdController() {
  // 1. Cache raw templates for all code blocks and copy values using textContent
  const targets = document.querySelectorAll('pre, .copy-card-value');
  targets.forEach(el => {
    if (el.id === 'global-project-id-input') return;
    if (!el.dataset.rawTemplate) {
      el.dataset.rawTemplate = el.textContent;
    }
  });

  const storedId = localStorage.getItem('gcp_project_id');
  const inputEl = document.getElementById('global-project-id-input');
  const labelEl = document.getElementById('current-project-id-label');

  if (storedId && storedId.trim() !== '') {
    currentProjectId = storedId.trim();
    if (inputEl) inputEl.value = currentProjectId;
  } else {
    currentProjectId = 'YOUR_PROJECT_ID';
    if (inputEl) inputEl.value = '';
  }

  if (inputEl && !inputEl._enterListenerAttached) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        applyGlobalProjectId();
      }
    });
    inputEl._enterListenerAttached = true;
  }

  if (labelEl) {
    labelEl.textContent = currentProjectId;
  }

  // Render project ID to DOM
  renderProjectIdToDOM(currentProjectId);
}

function applyGlobalProjectId(explicitId = null) {
  const inputEl = document.getElementById('global-project-id-input');
  const labelEl = document.getElementById('current-project-id-label');
  const newId = (explicitId || (inputEl ? inputEl.value : '')).trim();

  if (!newId) {
    showToast('⚠️ 프로젝트 ID를 입력해 주세요.');
    return;
  }

  currentProjectId = newId;
  localStorage.setItem('gcp_project_id', newId);

  if (inputEl) inputEl.value = newId;
  if (labelEl) labelEl.textContent = newId;

  // Render replacement across all code blocks
  renderProjectIdToDOM(newId);

  showToast(`✅ 프로젝트 ID [${newId}]가 모든 쿼리에 적용되었습니다!`);
}

function renderProjectIdToDOM(projId) {
  const targets = document.querySelectorAll('pre, .copy-card-value');
  targets.forEach(el => {
    if (el.id === 'global-project-id-input') return;
    
    if (!el.dataset.rawTemplate) {
      el.dataset.rawTemplate = el.textContent;
    }

    const template = el.dataset.rawTemplate;
    if (template) {
      const updated = template
        .replaceAll('finance-ontology-changseop', projId)
        .replaceAll('partner-caa-project-0827', projId)
        .replaceAll('YOUR_PROJECT_ID', projId)
        .replaceAll('[YOUR_GCP_PROJECT_ID]', projId)
        .replaceAll('YOUR_GCP_PROJECT_ID', projId);

      el.textContent = updated;
    }
  });
}

function showToast(message) {
  let toast = document.getElementById('global-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'global-toast';
    toast.className = 'toast-notification';
    document.body.appendChild(toast);
  }

  toast.innerText = message;
  toast.classList.add('show');

  if (window.toastTimeout) {
    clearTimeout(window.toastTimeout);
  }

  window.toastTimeout = setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}


