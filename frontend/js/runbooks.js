// js/runbooks.js

// ── Parse ticket ID from URL ──
const params   = new URLSearchParams(window.location.search);
const issueKey = params.get("id") || "UNKNOWN";

// Redirect child tickets to their parent
if (issueKey !== "UNKNOWN" && issueKey.includes(".")) {
  window.location.replace(`runbooks.html?id=${issueKey.split(".")[0]}`);
}

document.getElementById("ticketBadge").textContent = issueKey;

let checkedItems = new Set();

// ─────────────────────────────────────────────
// STATUS BAR
// ─────────────────────────────────────────────
const DOT_COLORS = { running: "#facc15", done: "#4ade80", error: "#f87171" };

function setStatus(state, text) {
  const dot = document.getElementById("statusDot");
  const c   = DOT_COLORS[state] || "#64748b";
  dot.className = "status-dot " + state;
  document.getElementById("statusText").textContent = text;
  document.getElementById("statusTime").textContent = new Date().toLocaleTimeString();
}

// ─────────────────────────────────────────────
// PROGRESS BAR
// ─────────────────────────────────────────────
function setProgress(pct) {
  document.getElementById("progressBar").style.width = pct + "%";
}

function updateProgress() {
  const total = document.querySelectorAll("[data-check]").length;
  if (total) setProgress(Math.round((checkedItems.size / total) * 100));
}

// ─────────────────────────────────────────────
// COLLAPSIBLE SECTIONS
// ─────────────────────────────────────────────
function toggleSection(id) {
  const body = document.getElementById("body-" + id);
  const chev = document.getElementById("chev-" + id);
  const open = body.style.display !== "none";
  body.style.display = open ? "none" : "block";
  chev.classList.toggle("open", !open);
}

// ─────────────────────────────────────────────
// CHECKLIST TOGGLE
// ─────────────────────────────────────────────
function toggleCheck(idx) {
  const item = document.querySelector(`[data-check="${idx}"]`);
  if (!item) return;
  if (checkedItems.has(idx)) {
    checkedItems.delete(idx);
    item.classList.remove("checked");
  } else {
    checkedItems.add(idx);
    item.classList.add("checked");
  }
  updateProgress();
}

// ─────────────────────────────────────────────
// COPY COMMAND
// ─────────────────────────────────────────────
function copyCmd(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "✓ Copied";
    setTimeout(() => (btn.textContent = "Copy"), 1500);
  });
}

// ─────────────────────────────────────────────
// SECTION CARD BUILDER
// ─────────────────────────────────────────────
function buildCard(icon, title, count, id, bodyHtml, delay) {
  return `
    <div class="section-card" style="animation-delay:${delay}s">
      <div class="section-head" onclick="toggleSection('${id}')">
        <div class="section-head-left">
          <div class="section-icon">${icon}</div>
          <span class="section-title">${title}</span>
          ${count ? `<span class="section-count">${count}</span>` : ""}
        </div>
        <span class="chevron open" id="chev-${id}">▼</span>
      </div>
      <div class="section-body" id="body-${id}">${bodyHtml}</div>
    </div>`;
}

// ─────────────────────────────────────────────
// RUNBOOK INFO PANEL (title + category only)
// ─────────────────────────────────────────────
function showRunbookInfo(data) {
  if (data.match_type !== "runbook_match") return;
  document.getElementById("runbookInfo").classList.add("show");
  document.getElementById("infoTitle").textContent    = data.runbook_title    || "—";
  document.getElementById("infoCategory").textContent = data.runbook_category || "—";
}

// ─────────────────────────────────────────────
// MAIN RENDER
// ─────────────────────────────────────────────
function renderRunbook(data) {
  document.getElementById("skeletonLoader")?.remove();

  showRunbookInfo(data);

  const checklist = data.checklist || data.checks || [];
  const commands  = data.commands  || data.steps  || [];
  const rca       = data.rca       || data.root_cause        || null;
  const recs      = data.recommendations || data.notes       || null;

  let html = "";

  // ── Checklist ──
  if (checklist.length) {
    const items = checklist.map((item, i) => {
      const label = typeof item === "string"
        ? item
        : (item.label || item.name || item.step || JSON.stringify(item));
      return `
        <div class="check-item" data-check="${i}" onclick="toggleCheck(${i})">
          <div class="chk-box"></div>
          <span class="chk-label">${label}</span>
        </div>`;
    }).join("");

    html += buildCard(
      "✅", "Pre-flight Checklist", `${checklist.length} items`,
      "checklist", `<div class="checklist">${items}</div>`, 0.05
    );
  }

  // ── Commands ──
  if (commands.length) {
    const cmds = commands.map((cmd, i) => {
      const label   = typeof cmd === "string"
        ? `Command ${i + 1}`
        : (cmd.label || cmd.name || `Command ${i + 1}`);
      const command = typeof cmd === "string"
        ? cmd
        : (cmd.command || cmd.cmd || cmd.script || "");

      return `
        <div class="command-block">
          <div class="cmd-header">
            <span class="cmd-label">${label}</span>
            <button class="copy-btn" onclick="copyCmd(\`${command.replace(/`/g, "\\`")}\`, this)">Copy</button>
          </div>
          <div class="cmd-code">${command}</div>
        </div>`;
    }).join("");

    html += buildCard(
      "⌨", "Commands", `${commands.length} commands`,
      "commands", `<div class="command-list">${cmds}</div>`, 0.1
    );
  }

  // ── Root Cause Analysis ──
  if (rca) {
    html += buildCard(
      "🔍", "Root Cause Analysis", "", "rca",
      `<p style="font-size:.875rem;line-height:1.7">${rca}</p>`, 0.15
    );
  }

  // ── Recommendations ──
  if (recs) {
    html += buildCard(
      "💡", "Recommendations", "", "recs",
      `<p style="font-size:.875rem;line-height:1.7">${recs}</p>`, 0.2
    );
  }

  // ── Nothing returned ──
  if (!html) {
    html = `
      <div class="state-box">
        <div class="icon">📭</div>
        <div>No checklist or commands returned by the runbook API.</div>
        <div style="margin-top:.5rem;color:#a855f7;font-size:.75rem">
          Check your runbook service response shape.
        </div>
      </div>`;
  }

  document.getElementById("mainContent").innerHTML = html;
  setStatus("done", `Runbook loaded for ${issueKey}`);
  setProgress(0);
}

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────
async function init() {
  setStatus("running", `Fetching runbook for ${issueKey}...`);

  const res = await apiRequest(`/tickets/${issueKey}/runbook`);

  if (!res || res.error) {
    document.getElementById("skeletonLoader")?.remove();
    document.getElementById("mainContent").innerHTML = `
      <div class="state-box">
        <div class="icon">❌</div>
        <div style="color:#f87171;font-weight:600">Failed to load runbook</div>
        <div style="margin-top:.5rem">${res?.message || "Unknown error"}</div>
      </div>`;
    setStatus("error", "Failed to load runbook");
    return;
  }

  renderRunbook(res);
}

document.addEventListener("DOMContentLoaded", init);