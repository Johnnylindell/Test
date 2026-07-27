import { api } from "/assets/api.js";
import { badge, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

let access = null;
let runtime = null;
let dialog = null;

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

function render(data) {
  const body = document.querySelector("#home-assistant-sheet-body");
  if (!body) return;
  if (!data.configured) {
    body.innerHTML = emptyState("Home Assistant är inte konfigurerad", "Lägg in URL och token via Next-inställningarna först.");
    return;
  }
  if (!data.ok) {
    body.innerHTML = errorState(new Error("Home Assistant kunde inte nås"));
    return;
  }
  const blocked = runtime?.read_only || !runtime?.external_side_effects;
  body.innerHTML = `${blocked ? `<section class="mode-banner"><strong>Visningsläge</strong><span>Styrning är avstängd i parallellversionen, men aktuell status kan granskas.</span></section>` : ""}
    <div class="stats"><div class="stat"><strong>${data.summary?.entities || 0}</strong><span>Entiteter</span></div><div class="stat"><strong>${data.summary?.active || 0}</strong><span>Aktiva</span></div><div class="stat"><strong>${data.summary?.favorites || 0}</strong><span>Favoriter</span></div></div>
    <div class="home-groups">${(data.groups || []).map(group => `<section class="card"><div class="card__header"><div><p class="eyebrow">${escapeHtml(group.id)}</p><h2>${escapeHtml(group.label)}</h2></div>${badge(String(group.entities?.length || 0), "neutral")}</div><div class="list">${(group.entities || []).map(renderEntity).join("")}</div></section>`).join("") || emptyState("Inga tillåtna entiteter")}</div>`;
}

async function load() {
  const body = document.querySelector("#home-assistant-sheet-body");
  if (body) body.innerHTML = skeleton(5);
  try {
    const [data, accessData, home] = await Promise.all([
      api("/api/v2/home-assistant/overview"),
      api("/api/access-control"),
      api("/api/v2/home/summary"),
    ]);
    access = accessData;
    runtime = home.runtime || {};
    render(data);
  } catch (error) {
    if (body) body.innerHTML = errorState(error);
  }
}

async function handleClick(event) {
  const target = event.target.closest("[data-ha-entity]");
  if (!target) return;
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
    if (grid.querySelector("[data-home-assistant-open]")) continue;
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

const observer = new MutationObserver(addEntryPoints);
observer.observe(document.querySelector("#app-main"), { childList: true, subtree: true });
addEntryPoints();
