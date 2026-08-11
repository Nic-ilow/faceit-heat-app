// Content script — runs on faceit.com pages.
//
// Faceit is a single-page app, so we can't rely on the page loading once:
// we watch for URL changes and (re)inject our button whenever the user
// lands on a match room URL like:
//   https://www.faceit.com/en/cs2/room/1-abcdef-...
//
// The button asks the background service worker to call the Faceit Heat API,
// then renders the results in an overlay panel.

const ROOM_RE = /\/room\/([0-9a-z-]+)/i;

let currentMatchId = null;
let panelEl = null;

function getMatchIdFromUrl() {
  const m = window.location.pathname.match(ROOM_RE);
  return m ? m[1] : null;
}

// ---------- UI ----------

function heatColor(score) {
  // performance_score roughly ranges 0–3+; map to cold→hot.
  if (score >= 2.0) return "#ff4d4d";
  if (score >= 1.5) return "#ff8c42";
  if (score >= 1.0) return "#ffd166";
  if (score > 0) return "#7bdff2";
  return "#6c757d";
}

function buildButton() {
  const btn = document.createElement("button");
  btn.id = "faceit-heat-btn";
  btn.textContent = "🔥 Heat check";
  btn.addEventListener("click", onHeatCheck);
  document.body.appendChild(btn);
  return btn;
}

function removeUi() {
  document.getElementById("faceit-heat-btn")?.remove();
  panelEl?.remove();
  panelEl = null;
}

function showPanel(contentNode) {
  panelEl?.remove();
  panelEl = document.createElement("div");
  panelEl.id = "faceit-heat-panel";

  const header = document.createElement("div");
  header.className = "fh-header";

  const title = document.createElement("span");
  title.textContent = "Faceit Heat";
  header.appendChild(title);

  const close = document.createElement("button");
  close.className = "fh-close";
  close.textContent = "✕";
  close.addEventListener("click", () => {
    panelEl?.remove();
    panelEl = null;
  });
  header.appendChild(close);

  panelEl.appendChild(header);
  panelEl.appendChild(contentNode);
  document.body.appendChild(panelEl);
}

function statusNode(text) {
  const div = document.createElement("div");
  div.className = "fh-status";
  div.textContent = text;
  return div;
}

function teamTable(team) {
  const wrap = document.createElement("div");
  wrap.className = "fh-team";

  const name = document.createElement("div");
  name.className = "fh-team-name";
  name.textContent = team.name;
  wrap.appendChild(name);

  const table = document.createElement("table");
  table.className = "fh-table";
  table.innerHTML =
    "<thead><tr><th>Player</th><th>K/D</th><th>K/R</th><th>W/L</th><th>Heat</th></tr></thead>";
  const tbody = document.createElement("tbody");

  for (const p of team.players) {
    const tr = document.createElement("tr");

    const nameTd = document.createElement("td");
    nameTd.textContent = p.nickname;
    tr.appendChild(nameTd);

    const kdTd = document.createElement("td");
    kdTd.textContent = p.data_available ? p.kd_ratio.toFixed(2) : "—";
    tr.appendChild(kdTd);

    const krTd = document.createElement("td");
    krTd.textContent = p.data_available ? p.kr_ratio.toFixed(2) : "—";
    tr.appendChild(krTd);

    const wlTd = document.createElement("td");
    wlTd.textContent = p.data_available
      ? `${p.wins_count}/${p.match_count - p.wins_count}`
      : "—";
    tr.appendChild(wlTd);

    const heatTd = document.createElement("td");
    if (p.data_available) {
      const badge = document.createElement("span");
      badge.className = "fh-badge";
      badge.style.background = heatColor(p.performance_score);
      badge.textContent = p.performance_score.toFixed(2);
      heatTd.appendChild(badge);
    } else {
      heatTd.textContent = "no data";
      heatTd.className = "fh-nodata";
    }
    tr.appendChild(heatTd);

    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

function resultsNode(matchData) {
  const wrap = document.createElement("div");
  wrap.className = "fh-results";
  wrap.appendChild(teamTable(matchData.team1));
  wrap.appendChild(teamTable(matchData.team2));

  const note = document.createElement("div");
  note.className = "fh-note";
  note.textContent = "Heat = session performance score from the last 24h of matches.";
  wrap.appendChild(note);
  return wrap;
}

// ---------- Actions ----------

function onHeatCheck() {
  if (!currentMatchId) return;
  showPanel(statusNode("Analyzing lobby… this can take ~10–20s for a fresh match."));

  chrome.runtime.sendMessage(
    { type: "ANALYZE_MATCH", matchId: currentMatchId },
    (response) => {
      if (chrome.runtime.lastError) {
        showPanel(statusNode(`Extension error: ${chrome.runtime.lastError.message}`));
        return;
      }
      if (!response?.ok) {
        showPanel(statusNode(`Failed: ${response?.error || "unknown error"}`));
        return;
      }
      showPanel(resultsNode(response.matchData));
    }
  );
}

// ---------- SPA URL watching ----------

function onUrlMaybeChanged() {
  const matchId = getMatchIdFromUrl();
  if (matchId === currentMatchId) return;
  currentMatchId = matchId;
  removeUi();
  if (matchId) buildButton();
}

// MutationObserver fires on SPA re-renders; cheap check since we only compare URLs.
new MutationObserver(onUrlMaybeChanged).observe(document.body, {
  childList: true,
  subtree: true,
});
onUrlMaybeChanged();
