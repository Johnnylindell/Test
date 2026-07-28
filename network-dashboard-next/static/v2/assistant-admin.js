import { api, query } from "/assets/api.js";
import { badge, dateTime, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const notice = document.querySelector("#v2-notice");
let readOnly = true;
let currentResult = null;

function announce(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5500);
}

function resultRows(results) {
  if (!results?.length) return emptyState("Inga sökträffar", "Svaret kan fortfarande innehålla ett förslag eller en förklaring.");
  return `<div class="list">${results.map(item => `<div class="row"><div class="row__main"><strong>${escapeHtml(item.title || "Träff")}</strong><span>${escapeHtml(item.detail || "")}</span></div>${item.url ? `<a class="button button--small" href="${escapeHtml(item.url)}">Öppna</a>` : ""}</div>`).join("")}</div>`;
}

function proposalHtml(proposal) {
  if (!proposal) return emptyState("Ingen mutation föreslagen", "Läsfrågor och sökningar kräver ingen bekräftelse.");
  return `<div class="assistant-proposal"><strong>${escapeHtml(proposal.description || "Föreslagen åtgärd")}</strong><small>Giltig till ${escapeHtml(dateTime(proposal.expires_at))}</small><button id="assistant-admin-confirm" class="button button--primary" type="button"${readOnly ? " disabled" : ""}>${readOnly ? "Bekräftelse blockerad i parallelläge" : "Bekräfta en gång"}</button></div>`;
}

function renderResult() {
  const target = document.querySelector("#assistant-admin-result");
  if (!target) return;
  if (!currentResult) {
    target.innerHTML = emptyState("Ingen fråga körd", "Testa en sökning eller ett förslag från exemplen ovan.");
    return;
  }
  target.innerHTML = `<div class="list"><div class="row"><div class="row__main"><strong>Avsikt</strong><span>${escapeHtml(currentResult.intent || "okänd")}</span></div>${badge(currentResult.network_model_used ? "Nätverksmodell" : "Lokal logik", currentResult.network_model_used ? "warning" : "good")}</div><div class="row"><div class="row__main"><strong>Svar</strong><span>${escapeHtml(currentResult.reply || "")}</span></div></div><div class="row"><div class="row__main"><strong>Bekräftelse krävs</strong><span>${currentResult.requires_confirmation ? "Ja" : "Nej"}</span></div>${badge(currentResult.requires_confirmation ? "Kontrollerad mutation" : "Endast läsning", currentResult.requires_confirmation ? "warning" : "good")}</div></div><h3>Träffar</h3>${resultRows(currentResult.results || [])}<h3>Förslag</h3>${proposalHtml(currentResult.proposal)}`;
  document.querySelector("#assistant-admin-confirm")?.addEventListener("click", confirmProposal);
}

function render() {
  content.innerHTML = `<section class="hero"><p class="eyebrow">Lokal och bekräftelsestyrd</p><h2>Testa familjeassistenten</h2><p>Verifiera sökningar, avsiktsklassning och signerade förslag utan att visa hemligheter eller rå bekräftelsetoken.</p><div class="stats"><div class="stat"><strong>0</strong><span>Nätverksmodeller</span></div><div class="stat"><strong>10 min</strong><span>Förslagets giltighet</span></div><div class="stat"><strong>1 gång</strong><span>Bekräftelse</span></div></div></section>${readOnly ? `<section class="mode-banner"><strong>Skrivskyddat parallelläge</strong><span>Frågor och sökningar fungerar. Bekräftelse av föreslagna mutationer är blockerad.</span></section>` : ""}<div class="grid"><section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Testfråga</p><h2>Fråga appens lokala data</h2></div>${badge("Ingen extern AI", "good")}</div><div class="toolbar assistant-examples"><button type="button" data-assistant-admin-example="Vad ska jag göra?">Vad är viktigast?</button><button type="button" data-assistant-admin-example="Var finns laddaren?">Hitta en sak</button><button type="button" data-assistant-admin-example="Lägg mjölk på inköpslistan">Föreslå inköp</button><button type="button" data-assistant-admin-example="Påminn mig om tandläkaren">Föreslå påminnelse</button></div><form id="assistant-admin-form" class="form"><label class="field"><span>Fråga</span><textarea name="message" required minlength="2" maxlength="500" placeholder="Sök i appen eller föreslå en åtgärd…"></textarea></label><div class="form__actions"><button class="button button--primary">Kör test</button></div></form></section><section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Sanerat resultat</p><h2>Assistentens svar</h2></div>${badge("Token visas inte", "good")}</div><div id="assistant-admin-result"></div></section><section class="card"><div class="card__header"><div><p class="eyebrow">Säkerhetskontrakt</p><h2>Vad vyn verifierar</h2></div></div><div class="list"><div class="row"><div class="row__main"><strong>Datakälla</strong><span>Endast Next-databasen och lokala regler</span></div></div><div class="row"><div class="row__main"><strong>Mutationer</strong><span>Signerad, tidsbegränsad och profilbunden bekräftelse</span></div></div><div class="row"><div class="row__main"><strong>Återanvändning</strong><span>Bekräftelsen kan konsumeras en gång</span></div></div></div></section></div>`;
  document.querySelector("#assistant-admin-form")?.addEventListener("submit", submitQuery);
  content.querySelectorAll("[data-assistant-admin-example]").forEach(button => button.addEventListener("click", () => {
    const input = document.querySelector('#assistant-admin-form textarea[name="message"]');
    input.value = button.dataset.assistantAdminExample || "";
    document.querySelector("#assistant-admin-form")?.requestSubmit();
  }));
  renderResult();
}

async function load() {
  history.replaceState(null, "", "#assistant-admin");
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.assistantAdminView === "true"));
  content.innerHTML = skeleton(5);
  try {
    const security = await api("/api/v2/admin/security/overview");
    readOnly = Boolean(security.read_only);
    render();
  } catch (error) {
    content.innerHTML = errorState(error);
  }
}

async function submitQuery(event) {
  event.preventDefault();
  const input = event.currentTarget.querySelector('textarea[name="message"]');
  const message = String(input.value || "").trim();
  if (message.length < 2) return;
  const target = document.querySelector("#assistant-admin-result");
  target.innerHTML = skeleton(2);
  try {
    currentResult = await api(query("/api/v2/assistant/query", { q: message }));
    renderResult();
  } catch (error) {
    currentResult = null;
    target.innerHTML = errorState(error);
  }
}

async function confirmProposal() {
  const token = currentResult?.proposal?.token;
  if (!token) return;
  if (readOnly) return announce("Bekräftelse är blockerad i parallelläge", "warning");
  if (!window.confirm("Genomför den föreslagna assistentåtgärden en gång?")) return;
  const button = document.querySelector("#assistant-admin-confirm");
  if (button) button.disabled = true;
  try {
    const result = await api("/api/v2/assistant/confirm", { method: "POST", body: { token } });
    currentResult = null;
    renderResult();
    announce(result.message || "Assistentåtgärden genomfördes");
  } catch (error) {
    if (button) button.disabled = false;
    announce(error.message || "Bekräftelsen misslyckades", "danger");
  }
}

function installNav() {
  if (nav.querySelector("[data-assistant-admin-view]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.assistantAdminView = "true";
  button.textContent = "Assistent";
  button.addEventListener("click", load);
  nav.append(button);
}

const observer = new MutationObserver(installNav);
observer.observe(nav, { childList: true });
installNav();
