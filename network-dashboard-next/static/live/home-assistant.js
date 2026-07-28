import { api } from "/assets/api.js";
import { badge, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

let access = null;
let runtime = null;
let dialog = null;

function allowed() {
  return Boolean(access?.admin || access?.sections?.includes("homeassistant"));
}

function ensureDialog() {
  if (dialog) return dialog;
  dialog = document.createElement("dialog");
  dialog.id = "home-assistant-dialog";
  dialog.className = "sheet sheet--home";
  dialog.innerHTML = `
    <form method="dialog" class="sheet__header">
      <div><p class="eyebrow">Smarta hemmet</p><h2>Home Assistant</h2></div>
      <button class="icon-button" value="cancel" aria-label="Stäng">×</button>
    </form>
    <div id="home-assistant-sheet-body" class="sheet__body">${skeleton(4)}</div>`;
  document.body.append(dialog);
  dialog.addEventListener("click", handleClick);
  return dialog;
}

function openDialog() {
  if (!allowed()) return;
  const target = ensureDialog();
  if (typeof target.showModal === "function") target.showModal();
  else target.setAttribute("open", "");
}

function announce(message, tone = "good") {
  const notice = document.querySelector("#app-notice");
  if (!notice) return;
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5000);
}

function serviceButton(entity, service, label) {
  const blocked = runtime?.read_only || !runtime?.external_side_effects;
  const adult = access?.admin || ["johnny", "kristina"].includes(String(access?.user || "").toLowerCase());
  return `<button class="button button--small" type="button" data-ha-entity="${escapeHtml(entity.entity_id)}" data-ha-service="${escapeHtml(service)}"${blocked || !adult ? " disabled" : ""}>${escapeHtml(label)}</button>`;
}

function renderEntity(entity) {
  const labels = {
    turn_on: "På",
    turn_off: "Av",
    toggle: "Växla",
    open_cover: "Öppna",
    close_cover: "Stäng",
    stop_cover: "Stopp",
  };
  const actions = (entity.services || []).map(service => serviceButton(entity, service, labels[service] || service)).join("");
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(entity.name)}</strong><span>${escapeHtml(entity.state || "okänd")}</span></div><div class="row__actions">${entity.favorite ? badge("Favorit", "good") : ""}${actions}</div></div>`;
}

function setupGuidance(data) {
  const missing = new Set(data.missing || []);
  if (missing.has("url") && missing.has("token")) {
    return "Både basadressen och en long-lived access token behöver sparas av en administratör under Version 2 → Integrationsinställningar.";
  }
  if (missing.has("token")) {
    return "Basadressen är hittad, men en Home Assistant long-lived access token behöver sparas av en administratör under Version 2 → Integrationsinställningar.";
  }
  if (missing.has("url")) {
    return "En token är hittad, men Home Assistants basadress behöver sparas av en administratör under Version 2 → Integrationsinställningar.";
  }
  return "Kontrollera Home Assistant-inställningarna under Version 2 → Integrationsinställningar.";
}

function render(data) {
  const body = document.querySelector("#home-assistant-sheet-body");
  if (!body) return;
  if (!data.configured) {
    body.innerHTML = emptyState(data.message || "Home Assistant är inte konfigurerad", setupGuidance(data));
    return;
  }
  if (!data.ok) {
    body.innerHTML = errorState(new Error(data.message || "Home Assistant kunde inte nås"));
    return;
  }
  const blocked = runtime?.read_only || !runtime?.external_side_effects;
  body.innerHTML = `${blocked ? `<section class="mode-banner"><strong>Visningsläge</strong><span>Styrning är avstängd i parallellversionen, men aktuell status kan granskas.</span></section>` : ""}
    <div class="stats"><div class="stat"><strong>${data.summary?.entities || 0}</strong><span>Entiteter</span></div><div class="stat"><strong>${data.summary?.active || 0}</strong><span>Aktiva</span></div><div class="stat"><strong>${data.summary?.favorites || 0}</strong><span>Favoriter</span></div></div>
    <div class="home-groups">${(data.groups || []).map(group => `<section class="card"><div class="card__header"><div><p class="eyebrow">${escapeHtml(group.id)}</p><h2>${escapeHtml(group.label)}</h2></div>${badge(String(group.entities?.length || 0), "neutral")}</div><div class="list">${(group.entities || []).map(renderEntity).join("")}</div></section>`).join("") || emptyState("Inga tillåtna entiteter")}</div>`;
}

async function load() {
  if (!allowed()) return;
  const body = document.querySelector("#home-assistant-sheet-body");
  if (body) body.innerHTML = skeleton(5);
  try {
    const [data, home] = await Promise.all([
      api("/api/v2/home-assistant/overview"),
      api("/api/v2/home/summary"),
    ]);
    runtime = home.runtime || {};
    render(data);
  } catch (error) {
    if (body) body.innerHTML = errorState(error);
  }
}

async function handleClick(event) {
  const target = event.target.closest("[data-ha-entity]");
  if (!target || !allowed()) return;
  target.disabled = true;
  try {
    await api("/api/v2/home-assistant/service", {
      method: "POST",
      body: { entity_id: target.dataset.haEntity, service: target.dataset.haService },
    });
    announce("Home Assistant uppdaterades");
    await load();
  } catch (error) {
    announce(error.message || "Åtgärden misslyckades", "danger");
  }
}

function addEntryPoints() {
  const grids = document.querySelectorAll(".quick-grid");
  for (const grid of grids) {
    const existing = grid.querySelector("[data-home-assistant-open]");
    if (!allowed()) {
      existing?.remove();
      continue;
    }
    if (existing) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.homeAssistantOpen = "true";
    button.innerHTML = "<strong>Smarta hemmet</strong><small>Lampor, klimat och scener</small>";
    button.addEventListener("click", () => {
      openDialog();
      load();
    });
    grid.append(button);
  }
}

async function initialize() {
  try {
    access = await api("/api/access-control");
  } catch {
    access = null;
  }
  addEntryPoints();
}

const observer = new MutationObserver(addEntryPoints);
observer.observe(document.querySelector("#app-main"), { childList: true, subtree: true });
initialize();
