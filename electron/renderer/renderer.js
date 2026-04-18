/**
 * SAGE.ai Desktop — Renderer Script
 * ====================================
 * Handles page navigation, API calls to the FastAPI backend,
 * and all interactive UI logic.
 */

const API_BASE = 'http://localhost:5000';

// ─── State ───
let lastAnswer   = '';
let lastCitations = [];
let lastQuery    = '';

// ─── DOM helpers ───
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── Page Navigation ───
const PAGE_MAP = { q: 'query', i: 'ingest', e: 'export', t: 'terminal', p: 'print' };

function navigateTo(pageId) {
  $$('.page').forEach(p => p.classList.remove('active'));
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  const page = $(`#page-${pageId}`);
  const nav  = $(`.nav-item[data-page="${pageId}"]`);
  if (page) page.classList.add('active');
  if (nav)  nav.classList.add('active');
  if (pageId === 'terminal') refreshLogs();
  if (pageId === 'export')   updateExportPreview();
}

// Nav clicks
$$('.nav-item').forEach(item => {
  item.addEventListener('click', () => navigateTo(item.dataset.page));
});

// Keyboard shortcuts from main process
if (window.sageAPI) {
  window.sageAPI.onNavigate((key) => {
    const pageId = PAGE_MAP[key];
    if (pageId) navigateTo(pageId);
  });
}

// ─── Status check ───
async function checkStatus() {
  const dot  = $('#status-dot');
  const text = $('#status-text');
  try {
    const res  = await fetch(`${API_BASE}/status`);
    const data = await res.json();
    dot.className = data.status === 'ok' ? 'ok' : 'fail';
    text.textContent = data.sage_core ? `Online — ${data.ollama_model}` : 'Online (demo)';
  } catch {
    dot.className = 'fail';
    text.textContent = 'API offline';
  }
}
checkStatus();
setInterval(checkStatus, 15000);

// ─── QUERY PAGE ───
$('#query-send').addEventListener('click', async () => {
  const question = $('#query-input').value.trim();
  if (!question) return;

  $('#query-result').classList.add('hidden');
  $('#query-loading').classList.remove('hidden');
  $('#query-send').disabled = true;

  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Query failed');

    lastQuery    = question;
    lastAnswer   = data.answer;
    lastCitations = data.citations || [];

    $('#query-answer').textContent = data.answer;

    const citDiv = $('#query-citations');
    if (lastCitations.length) {
      citDiv.innerHTML = '<strong>Sources:</strong> ' + lastCitations.map(c => `<span>${c}</span>`).join(' · ');
    } else {
      citDiv.innerHTML = '';
    }

    $('#query-elapsed').textContent = `Completed in ${data.elapsed_seconds}s`;
    $('#query-result').classList.remove('hidden');
  } catch (err) {
    $('#query-answer').textContent = `Error: ${err.message}`;
    $('#query-citations').innerHTML = '';
    $('#query-elapsed').textContent = '';
    $('#query-result').classList.remove('hidden');
  } finally {
    $('#query-loading').classList.add('hidden');
    $('#query-send').disabled = false;
  }
});

// Copy button
$('#query-copy').addEventListener('click', () => {
  const text = lastAnswer + (lastCitations.length ? '\n\nSources: ' + lastCitations.join(', ') : '');
  navigator.clipboard.writeText(text).then(() => {
    const btn = $('#query-copy');
    btn.textContent = '✅ Copied!';
    setTimeout(() => btn.textContent = '📋 Copy', 1500);
  });
});

// Enter to send (Shift+Enter for newline)
$('#query-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('#query-send').click();
  }
});

// ─── INGEST PAGE ───
$('#ingest-btn').addEventListener('click', async () => {
  $('#ingest-status').classList.add('hidden');
  $('#ingest-loading').classList.remove('hidden');
  $('#ingest-btn').disabled = true;

  try {
    const res  = await fetch(`${API_BASE}/ingest`, { method: 'POST' });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Ingest failed');

    $('#ingest-status-title').textContent = data.status === 'ok' ? '✅ Success' : '⚠️ Warning';
    $('#ingest-message').textContent = data.message;
    $('#ingest-elapsed').textContent = `Completed in ${data.elapsed_seconds}s`;
    $('#ingest-status').classList.remove('hidden');
  } catch (err) {
    $('#ingest-status-title').textContent = '❌ Error';
    $('#ingest-message').textContent = err.message;
    $('#ingest-elapsed').textContent = '';
    $('#ingest-status').classList.remove('hidden');
  } finally {
    $('#ingest-loading').classList.add('hidden');
    $('#ingest-btn').disabled = false;
  }
});

// ─── EXPORT PAGE ───
function updateExportPreview() {
  const content = lastAnswer
    ? `SAGE.ai — Diagnostic Export\nDate: ${new Date().toLocaleString()}\n\nQuery: ${lastQuery}\n\n${'='.repeat(60)}\n\n${lastAnswer}\n\n${'='.repeat(60)}\n\nSources:\n${lastCitations.map((c, i) => `  ${i + 1}. ${c}`).join('\n')}`
    : 'No answer to export yet. Run a query first.';
  $('#export-content').textContent = content;
}

$('#export-btn').addEventListener('click', async () => {
  if (!lastAnswer) { alert('No answer to export. Run a query first.'); return; }
  const content = $('#export-content').textContent;
  const defaultName = `SAGE_Export_${new Date().toISOString().slice(0, 10)}.txt`;

  if (window.sageAPI) {
    const result = await window.sageAPI.saveFile(content, defaultName);
    if (result.success) alert(`Exported to: ${result.filePath}`);
  } else {
    // Fallback: browser download
    const blob = new Blob([content], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = defaultName;
    a.click();
  }
});

// ─── TERMINAL PAGE ───
async function refreshLogs() {
  try {
    const res  = await fetch(`${API_BASE}/logs?limit=200`);
    const data = await res.json();
    if (data.logs && data.logs.length) {
      $('#terminal-output').textContent = data.logs
        .map(l => `[${l.timestamp}] ${l.level} — ${l.message}`)
        .join('\n');
      // Auto-scroll to bottom
      const box = $('#terminal-box');
      box.scrollTop = box.scrollHeight;
    } else {
      $('#terminal-output').textContent = 'No log entries yet.';
    }
  } catch {
    $('#terminal-output').textContent = 'Unable to reach API. Is it running on localhost:5000?';
  }
}
$('#terminal-refresh').addEventListener('click', refreshLogs);

// ─── PRINT PAGE ───
$('#print-btn').addEventListener('click', () => window.print());
