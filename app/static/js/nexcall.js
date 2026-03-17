/**
 * NexCall AI — JavaScript utilitaires partagés v2.0
 * À inclure après base.html ou dans chaque page via <script src="/static/js/nexcall.js">
 */

/* ── Clock ─────────────────────────────────────────────────────── */
(function initClock() {
  const el = document.getElementById('nx-clock');
  if (!el) return;
  const update = () => {
    el.textContent = new Date().toLocaleTimeString('fr-FR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };
  update();
  setInterval(update, 1000);
})();

/* ── Toast ──────────────────────────────────────────────────────── */
let _toastTimer = null;
function showToast(msg, type = 'info', duration = 3200) {
  const el = document.getElementById('nx-toast') || document.getElementById('toast');
  if (!el) return;
  clearTimeout(_toastTimer);
  el.textContent = '';
  // Add icon
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const icon  = document.createElement('span');
  icon.textContent = icons[type] || 'ℹ';
  icon.style.cssText = 'font-size:14px;font-weight:700;flex-shrink:0';
  const text = document.createElement('span');
  text.textContent = msg;
  el.appendChild(icon); el.appendChild(text);
  el.className = `nx-toast ${type} show`;
  _toastTimer = setTimeout(() => el.classList.remove('show'), duration);
}

/* ── API helpers ────────────────────────────────────────────────── */
async function api(url, opts = {}) {
  try {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  } catch (e) {
    console.error('[NexCall] API error:', url, e.message);
    showToast(e.message, 'error');
    return null;
  }
}

const apiGet   = url       => api(url);
const apiPost  = (url, d)  => api(url, { method: 'POST',   body: JSON.stringify(d) });
const apiPut   = (url, d)  => api(url, { method: 'PUT',    body: JSON.stringify(d) });
const apiPatch = (url, d)  => api(url, { method: 'PATCH',  body: JSON.stringify(d || {}) });
const apiDel   = url       => api(url, { method: 'DELETE' });

/* ── Format helpers ─────────────────────────────────────────────── */
function fmtDur(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const m = Math.floor(seconds / 60), s = seconds % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2,'0')}s` : `${s}s`;
}

function fmtDate(iso, short = false) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (short) return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    return d.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

function fmtPhone(p) { return p || '—'; }

function fmtScore(n) {
  const v = Math.round(n || 0);
  return `<div style="display:flex;align-items:center;gap:8px;min-width:110px">
    <div class="score-bar" style="flex:1"><div class="score-fill" style="width:${v}%"></div></div>
    <span style="font-family:monospace;font-size:11px;color:var(--text2);width:26px">${v}</span>
  </div>`;
}

function escHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

/* ── Badge builders ─────────────────────────────────────────────── */
function statusBadge(s) {
  const map = {
    completed:   ['badge-green',  '✓ Terminé'],
    in_progress: ['badge-blue',   '● En cours'],
    ringing:     ['badge-orange', '◌ Sonne'],
    transferred: ['badge-purple', '→ Transféré'],
    failed:      ['badge-red',    '✗ Échec'],
    no_answer:   ['badge-gray',   '— Sans rép.'],
  };
  const [cls, lbl] = map[s] || ['badge-gray', s || '—'];
  return `<span class="badge ${cls}">${lbl}</span>`;
}

function intentBadge(i) {
  const map = {
    devis:       ['badge-green',  'Devis'],
    achat:       ['badge-blue',   'Achat'],
    information: ['badge-gray',   'Info'],
    reclamation: ['badge-red',    'Réclamation'],
    transfert:   ['badge-purple', 'Transfert'],
    fin:         ['badge-teal',   'Fin'],
  };
  if (!i) return '<span style="color:var(--text4)">—</span>';
  const [cls, lbl] = map[i] || ['badge-gray', i];
  return `<span class="badge ${cls}">${lbl}</span>`;
}

function campStatusBadge(s) {
  const map = {
    draft:     ['badge-gray',   'Brouillon'],
    active:    ['badge-green',  '● Actif'],
    paused:    ['badge-orange', '⏸ Pausé'],
    completed: ['badge-blue',   '✓ Terminé'],
  };
  const [cls, lbl] = map[s] || ['badge-gray', s || '—'];
  return `<span class="badge ${cls}">${lbl}</span>`;
}

function hotBadge(isHot) {
  return isHot
    ? '<span class="badge badge-orange">🔥 Chaud</span>'
    : '<span class="badge badge-gray">Tiède</span>';
}

/* ── Bar chart ──────────────────────────────────────────────────── */
function renderBarChart(containerId, data) {
  const el = document.getElementById(containerId);
  if (!el || !data?.length) return;
  const max = Math.max(...data.map(d => d.calls || d.count || 0), 1);
  el.innerHTML = data.map(d => {
    const val = d.calls ?? d.count ?? 0;
    const pct = Math.max(4, (val / max) * 100);
    return `<div class="bar-col" title="${val} appels le ${d.date}">
      <div style="flex:1;display:flex;align-items:flex-end;width:100%">
        <div class="bar-fill" style="height:${pct}%"></div>
      </div>
      <div class="bar-lbl">${d.date}</div>
    </div>`;
  }).join('');
}

/* ── Pagination ─────────────────────────────────────────────────── */
function renderPagination(containerId, total, page, limit, onPageFn) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const pages = Math.ceil(total / limit);
  if (pages <= 1) { el.innerHTML = ''; return; }

  const range  = 5;
  const start  = Math.max(1, page - Math.floor(range / 2));
  const end    = Math.min(pages, start + range - 1);

  let html = '<div style="display:flex;gap:4px;justify-content:flex-end;padding:12px 16px">';
  if (page > 1) html += `<button class="btn btn-ghost btn-sm" onclick="${onPageFn}(${page-1})">←</button>`;
  for (let i = start; i <= end; i++) {
    const active = i === page ? 'btn-primary' : 'btn-ghost';
    html += `<button class="btn ${active} btn-sm" onclick="${onPageFn}(${i})">${i}</button>`;
  }
  if (page < pages) html += `<button class="btn btn-ghost btn-sm" onclick="${onPageFn}(${page+1})">→</button>`;
  html += `<span style="font-size:11px;color:var(--text3);align-self:center;margin-left:6px">${total} résultats</span>`;
  html += '</div>';
  el.innerHTML = html;
}

/* ── Modal helpers ──────────────────────────────────────────────── */
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

// Close modal on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// Close on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

/* ── Tags input ─────────────────────────────────────────────────── */
class TagInput {
  constructor(wrapperId, inputId) {
    this.wrapper = document.getElementById(wrapperId);
    this.input   = document.getElementById(inputId);
    this.tags    = [];
    if (!this.wrapper || !this.input) return;
    this.input.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        this.add(this.input.value.trim());
        this.input.value = '';
      }
      if (e.key === 'Backspace' && !this.input.value && this.tags.length) {
        this.remove(this.tags[this.tags.length - 1]);
      }
    });
  }
  add(val) {
    if (!val || this.tags.includes(val)) return;
    this.tags.push(val);
    this._render();
  }
  remove(val) {
    this.tags = this.tags.filter(t => t !== val);
    this._render();
  }
  setTags(arr) { this.tags = [...(arr || [])]; this._render(); }
  getTags()    { return [...this.tags]; }
  _render() {
    // Remove existing tag elements
    this.wrapper.querySelectorAll('.tag').forEach(t => t.remove());
    this.tags.forEach(t => {
      const el = document.createElement('span');
      el.className = 'tag';
      el.innerHTML = `${escHtml(t)}<button class="tag-rm" title="Supprimer">×</button>`;
      el.querySelector('.tag-rm').addEventListener('click', () => this.remove(t));
      this.wrapper.insertBefore(el, this.input);
    });
  }
}

/* ── Copy to clipboard ──────────────────────────────────────────── */
function copyToClipboard(text, msg = 'Copié !') {
  navigator.clipboard?.writeText(text).then(() => showToast(msg, 'success'));
}

/* ── Debounce ───────────────────────────────────────────────────── */
function debounce(fn, delay = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

/* ── Number formatting ──────────────────────────────────────────── */
function fmtNumber(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n ?? 0);
}

/* ── Confirm helper ─────────────────────────────────────────────── */
function nx_confirm(msg) { return confirm(msg); }

/* ── Export CSV helper ──────────────────────────────────────────── */
function downloadCSV(url) { window.open(url, '_blank'); }

/* ── Auto-reload (live updates) ─────────────────────────────────── */
class AutoRefresh {
  constructor(fn, interval = 30000) {
    this.fn  = fn;
    this.ms  = interval;
    this.tid = null;
  }
  start() {
    this.stop();
    this.tid = setInterval(() => this.fn(), this.ms);
  }
  stop() {
    if (this.tid) clearInterval(this.tid);
    this.tid = null;
  }
}

/* ── Page init log ──────────────────────────────────────────────── */
console.info('%c NexCall AI v2.0 ', 'background:#22c55e;color:#fff;font-weight:bold;border-radius:4px;padding:2px 8px;');
