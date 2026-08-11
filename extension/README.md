# Faceit Heat — Browser Extension

Chrome/Brave extension (Manifest V3) that puts a **🔥 Heat check** button on
Faceit match room pages. It calls the Faceit Heat backend
(`/api/v2/analyze/`) and shows each player's session K/D, K/R, W/L, and
performance score in an overlay — no tab switching.

## Load it (Chrome or Brave)

1. Open `chrome://extensions` (Brave: `brave://extensions`)
2. Toggle **Developer mode** (top right)
3. Click **Load unpacked** and select this `extension/` folder
4. Open any Faceit match room — the button appears bottom-right

After editing files, hit the reload icon on the extension card. Content
script changes also need a page refresh on faceit.com.

## Local development

The extension talks to `https://heat.nilow.space` by default. To test
against a local backend:

1. Run the Django app locally on port 8001
2. Click the extension icon → **Settings** → set API base URL to
   `http://localhost:8001` → Save

## How it works — the 3 contexts of an MV3 extension

An extension is not one program — it's three isolated JS contexts that talk
via message passing:

```
faceit.com page                extension origin              extension origin
┌─────────────────┐   message   ┌────────────────┐            ┌───────────┐
│  content.js     │ ──────────► │ background.js  │            │ popup.js  │
│  (injected into │ ◄────────── │ (service       │ ◄─message─ │ (toolbar  │
│   the page)     │   response  │  worker)       │            │  popup)   │
└─────────────────┘             └───────┬────────┘            └───────────┘
                                        │ fetch (no CORS, thanks to
                                        ▼  host_permissions)
                              heat.nilow.space/api/v2/analyze/
```

- **`content.js`** runs *inside* faceit.com pages. It can read/modify the
  page DOM, but it shares the page's origin — so fetching
  `heat.nilow.space` from here would be blocked by CORS. It also can't use
  most `chrome.*` APIs.
- **`background.js`** is a *service worker*: no DOM, event-driven, killed
  when idle (don't keep state in globals you can't lose). It runs in the
  extension's own origin, and because `heat.nilow.space` is listed in
  `host_permissions`, it can fetch it without any CORS handshake. All
  network calls live here.
- **`popup.js`** runs in the toolbar popup (its own tiny HTML page). It
  dies the moment the popup closes, which is why long-running flows belong
  on the page or in the worker, not here.

Communication is `chrome.runtime.sendMessage(...)` +
`chrome.runtime.onMessage.addListener(...)`. One gotcha used in
`background.js`: an async listener must `return true` to keep the response
channel open, or `sendResponse` silently stops working.

### Handling Faceit's SPA navigation

Faceit never does a full page load when you click around, so `content.js`
can't just run once on load. A `MutationObserver` watches for DOM changes
and re-checks `location.pathname` against the room URL pattern
(`/room/<match-id>`), injecting or removing the button as you navigate.

### Storage

`chrome.storage.sync` holds the API base URL setting. Unlike
`localStorage`, it's shared across all extension contexts and synced to
your browser profile.

## Publishing later (optional)

- Chrome Web Store: one-time $5 developer fee, upload a zip of this folder.
  Brave installs straight from the Chrome Web Store.
- You'll need real icons first (`"icons"` key in `manifest.json`,
  16/48/128 px PNGs) — omitted for now, Chrome shows a default puzzle icon.
