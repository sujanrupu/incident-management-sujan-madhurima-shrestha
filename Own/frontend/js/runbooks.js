// js/runbooks.js

// ── Parse ticket ID from URL ──
const params = new URLSearchParams(window.location.search);
const issueKey = params.get("id") || "UNKNOWN";

// ✅ Safer redirect (avoid weird loops)
if (issueKey !== "UNKNOWN" && issueKey.includes(".")) {
  const parent = issueKey.split(".")[0];
  if (parent !== issueKey) {
    window.location.replace(`runbooks.html?id=${parent}`);
  }
}

document.getElementById("ticketBadge").textContent = issueKey;

let checkedItems = new Set();

// ─────────────────────────────────────────────
// STATUS BAR
// ─────────────────────────────────────────────
function setStatus(state, text) {
  const dot = document.getElementById("statusDot");
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
        <span id="chev-${id}" class="chevron">▼</span>
      </div>
      <div id="body-${id}" class="section-body">
        ${bodyHtml}
      </div>
    </div>
  `;
}

// ─────────────────────────────────────────────
// RUNBOOK INFO PANEL
// ─────────────────────────────────────────────
function showRunbookInfo(data) {
  if (data.match_type !== "runbook_match") return;

  document.getElementById("runbookInfo").classList.add("show");
  document.getElementById("infoTitle").textContent = data.runbook_title || "—";
  document.getElementById("infoCategory").textContent = data.runbook_category || "—";
}

// ─────────────────────────────────────────────
// MAIN RENDER
// ─────────────────────────────────────────────
function renderRunbook(data) {
  document.getElementById("skeletonLoader")?.remove();

  // ❌ ONLY TRUE "NO RUNBOOK"
  if (data.match_type === "no_runbook_found") {
    document.getElementById("mainContent").innerHTML = `
      <div class="state-box">
        <div class="icon">📭</div>
        <div style="font-weight:600">No Runbook Found</div>
        <div style="margin-top:.5rem">
          No relevant runbook exists for this issue.
        </div>
      </div>
    `;
    setStatus("done", `No runbook found for ${issueKey}`);
    setProgress(0);
    return;
  }

  // 🔁 DUPLICATE
  if (data.type === "duplicate") {
    document.getElementById("mainContent").innerHTML = `
      <div class="state-box">
        <div class="icon">🔁</div>
        <div style="font-weight:600">Duplicate Ticket</div>
        <div style="margin-top:.5rem">${data.message}</div>
      </div>
    `;
    setStatus("done", "Duplicate ticket");
    return;
  }

  showRunbookInfo(data);

  // ✅ Correct field mapping
  const checklist = data.checklist_steps || data.checklist || [];
  const commands  = data.commands || [];

  let html = "";

  // Checklist
  if (checklist.length) {
    const items = checklist.map((item, i) => `
      <div class="check-item" data-check="${i}" onclick="toggleCheck(${i})">
        <div class="chk-box"></div>
        <span class="chk-label">${item}</span>
      </div>
    `).join("");

    html += buildCard("✅", "Checklist", checklist.length, "checklist", items, 0.05);
  }

  // Commands
  if (commands.length) {
    const cmds = commands.map((cmd, i) => {
      const command = typeof cmd === "string" ? cmd : (cmd.command || "");
      return `
        <div class="command-block">
          <div class="cmd-header">
            <span class="cmd-label">Command ${i + 1}</span>
            <button class="copy-btn" onclick="copyCmd(\`${command.replace(/`/g, "\\`")}\`, this)">Copy</button>
          </div>
          <div class="cmd-code">${command}</div>
        </div>
      `;
    }).join("");

    html += buildCard("⌨", "Commands", commands.length, "commands", cmds, 0.1);
  }

  // Empty fallback
  if (!html) {
    html = `
      <div class="state-box">
        <div class="icon">📭</div>
        <div>No checklist or commands returned</div>
      </div>
    `;
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
    document.getElementById("mainContent").innerHTML = `
      <div class="state-box">
        <div class="icon">❌</div>
        <div>Failed to load runbook</div>
      </div>
    `;
    setStatus("error", "Failed");
    return;
  }

  renderRunbook(res);
}

document.addEventListener("DOMContentLoaded", init);