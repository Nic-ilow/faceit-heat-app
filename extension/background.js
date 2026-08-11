// Service worker (MV3 "background script").
//
// Why the fetch lives here and not in content.js: content scripts run inside
// faceit.com's origin, so a request to heat.nilow.space from there is
// cross-origin and blocked by CORS. The service worker runs in the
// extension's own origin, and any host listed under host_permissions in
// manifest.json can be fetched from here without CORS headers on the server.

const DEFAULT_BASE_URL = "https://heat.nilow.space";

async function getBaseUrl() {
  const { baseUrl } = await chrome.storage.sync.get("baseUrl");
  return baseUrl || DEFAULT_BASE_URL;
}

async function analyzeMatch(matchId) {
  const baseUrl = await getBaseUrl();
  const res = await fetch(`${baseUrl}/api/v2/analyze/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ match_id: matchId }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Server responded with ${res.status}`);
  }
  return data.match_data;
}

// Content script and popup talk to us via message passing.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "ANALYZE_MATCH") {
    analyzeMatch(message.matchId)
      .then((matchData) => sendResponse({ ok: true, matchData }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    // Returning true keeps the sendResponse channel open for the async reply.
    return true;
  }
});
