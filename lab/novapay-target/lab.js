const API_BASE = "__PIKATRAP_API_URL__";
const API = `${API_BASE}/api/v1/telemetry`;
const sessionKey = "pikatrap-lab-session";
const requestedSession = new URLSearchParams(location.search).get("session_id");
const sessionId = requestedSession || localStorage.getItem(sessionKey) || `novapay-lab-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
localStorage.setItem(sessionKey, sessionId);

async function checkContainment() {
  try {
    const response = await fetch(`${API_BASE}/api/v1/sessions/${encodeURIComponent(sessionId)}/containment`);
    if (!response.ok) return;
    const state = await response.json();
    if (state.contained) quarantine(state.containment_action);
  } catch { /* The lab remains usable until the local API is available. */ }
}
window.setInterval(checkContainment, 1500);

async function report(action, details = {}) {
  const marker = `${sessionId}:${action}`;
  if (sessionStorage.getItem(marker)) return;
  try {
    const response = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        source: "novapay_lab_web",
        source_ip: "172.20.0.10",
        asset_type: "web_decoy",
        action,
        details: { ...details, lab: "defender-owned NovaPay simulation" }
      })
    });
    const result = await response.json();
    if (!response.ok || result.session_status === "CONTAINED") {
      if (response.status === 423 || result.session_status === "CONTAINED") sessionStorage.setItem(marker, "1");
      quarantine(result.detail || result.containment_action);
      return;
    }
    sessionStorage.setItem(marker, "1");
  } catch { console.warn("PikaTrap API is not running yet."); }
}

function quarantine(message = "PikaTrap has quarantined this simulated attacker session.") {
  if (document.getElementById("pikatrap-quarantine")) return;
  const notice = document.createElement("div");
  notice.id = "pikatrap-quarantine";
  notice.innerHTML = `<strong>SESSION QUARANTINED</strong><span>${message}</span><small>Fake credentials have been revoked inside this defender-owned lab.</small>`;
  document.body.append(notice);
  document.querySelectorAll("a, button").forEach(element => {
    if (element.getAttribute("onclick")?.includes("resetLab")) return;
    element.addEventListener("click", event => event.preventDefault());
    element.setAttribute("aria-disabled", "true");
  });
}

function resetLab() {
  localStorage.setItem(sessionKey, sessionId);
  sessionStorage.clear();
  location.href = requestedSession ? `/?session_id=${encodeURIComponent(requestedSession)}` : "/";
}
