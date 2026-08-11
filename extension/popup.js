const DEFAULT_BASE_URL = "https://heat.nilow.space";

const form = document.getElementById("analyze-form");
const matchInput = document.getElementById("match-input");
const baseUrlInput = document.getElementById("base-url");
const saveBtn = document.getElementById("save-settings");
const status = document.getElementById("status");

chrome.storage.sync.get("baseUrl").then(({ baseUrl }) => {
  baseUrlInput.value = baseUrl || "";
});

saveBtn.addEventListener("click", async () => {
  const value = baseUrlInput.value.trim().replace(/\/+$/, "");
  await chrome.storage.sync.set({ baseUrl: value || DEFAULT_BASE_URL });
  status.textContent = "Saved.";
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const raw = matchInput.value.trim();
  if (!raw) return;

  // Just open the web app with the match pre-analyzed via the site UI —
  // the popup closes when a new tab opens, so the panel flow lives on the page.
  const { baseUrl } = await chrome.storage.sync.get("baseUrl");
  const base = baseUrl || DEFAULT_BASE_URL;
  status.textContent = "Analyzing…";

  chrome.runtime.sendMessage({ type: "ANALYZE_MATCH", matchId: raw }, (response) => {
    if (chrome.runtime.lastError || !response?.ok) {
      status.textContent = `Failed: ${
        chrome.runtime.lastError?.message || response?.error || "unknown error"
      }`;
      return;
    }
    status.textContent = "Done — cached on the server. Opening web app…";
    chrome.tabs.create({ url: base });
  });
});
