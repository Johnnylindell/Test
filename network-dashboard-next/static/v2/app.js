import { api, accessControl } from "/assets/api.js";
import { badge, card, emptyState, errorState, escapeHtml, money, renderInto, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");

const views = {
  overview: { label: "Översikt", endpoint: "/api/v2/home/summary", render: renderOverview },
  budget: { label: "Budget", endpoint: "/api/v2/budget/overview", render: renderBudget },
  integrations: { label: "Integrationer", endpoint: "/api/v2/admin/integrations/overview", render: renderIntegrations },
  homelab: { label: "Homelab", endpoint: "/api/v2/admin/homelab/overview", render: renderHomelab },
};

function list(items, mapper) {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState("Ingen data");
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>${end}</div>`;
}

function renderOverview(data) {
  const totals = data.totals || {};
  return `<section class="hero"><p>Version 2</p><h2>Administrativ arbetsyta</h2><p>Ny modulär frontend ovanpå de migrerade API:erna.</p><div class="stats"><div class="stat"><strong>${totals.open_reminders || 0}</strong><span>Påminnelser</span></div><div class="stat"><strong>${totals.open_routines || 0}</strong><span>Rutiner</span></div><div class="stat"><strong>${totals.open_checklist_items || 0}</strong><span>Uppgifter</span></div></div></section>`;
}

function renderBudget(data) {
  const budget = data.budget || data;
  const totals = budget.totals || {};
  return `<div class="grid">${card("Aktuell månad", `<p><strong>${escapeHtml(budget.current || "Inte vald")}</strong></p><div class="list">${row("Inkomst", money(totals.income))}${row("Utgifter", money(totals.expenses_actual))}${row("Sparande", money(totals.savings))}${row("Saldo", money(totals.balance_actual), badge(totals.balance_actual >= 0 ? "Plus" : "Minus", totals.balance_actual >= 0 ? "good" : "danger"))}</div>`)}${card("Utgifter", list(budget.expenses || [], item => row(item.category, `Budget ${money(item.budgeted)}`, money(item.actual))))}</div>`;
}

function renderIntegrations(data) {
  const items = data.items || data.integrations || [];
  return `<div class="grid">${card("Integrationer", list(items, item => row(item.label || item.id, item.detail || item.status || "", badge(item.ok ? "OK" : item.configured ? "Kontrollera" : "Ej konfigurerad", item.ok ? "good" : "warning"))))}${card("Direktkontroller", `<div class="toolbar"><button data-probe="ha">Testa Home Assistant</button><button data-probe="tailscale">Testa Tailscale</button></div><div id="probe-result">${emptyState("Ingen kontroll körd")}</div>`)}</div>`;
}

function renderHomelab(data) {
  const integrations = data.integrations || [];
  const devices = data.device_profiles || [];
  return `<div class="grid">${card("Lokal status", `<div class="list">${row("Live-prober", data.live_probes_performed ? "Utförda" : "Inte utförda", badge(data.live_probes_performed ? "Aktiv" : "Säker", data.live_probes_performed ? "warning" : "good"))}${row("Känsliga värden", data.sensitive_values_exposed ? "Exponerade" : "Dolda", badge(data.sensitive_values_exposed ? "Varning" : "Dolda", data.sensitive_values_exposed ? "danger" : "good"))}</div>`)}${card("Enhetsprofiler", list(devices.slice(0, 20), item => row(item.name || item.label || item.mac || "Enhet", item.owner || item.type || "")))}${card("Integrationer", list(integrations, item => row(item.name || item.id, item.configured ? "Konfigurerad" : "Inte konfigurerad")))}</div>`;
}

async function probe(kind) {
  const target = document.querySelector("#probe-result");
  target.innerHTML = skeleton(2);
  const path = kind === "ha" ? "/api/v2/admin/integrations/home-assistant/status?fresh=true" : "/api/v2/admin/integrations/tailscale/status?fresh=true";
  try {
    const result = await api(path);
    target.innerHTML = `<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
  } catch (error) {
    target.innerHTML = errorState(error);
  }
}

async function openView(name) {
  const view = views[name] || views.overview;
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.view === name));
  content.innerHTML = skeleton(5);
  try {
    const data = await api(view.endpoint);
    content.innerHTML = view.render(data);
    content.querySelectorAll("[data-probe]").forEach(button => button.addEventListener("click", () => probe(button.dataset.probe)));
  } catch (error) {
    content.innerHTML = errorState(error);
  }
  location.hash = name;
}

async function bootstrap() {
  try {
    const access = await accessControl();
    if (!access.admin) throw new Error("Adminsession krävs");
    nav.innerHTML = Object.entries(views).map(([id, view]) => `<button type="button" data-view="${id}">${escapeHtml(view.label)}</button>`).join("");
    nav.querySelectorAll("button").forEach(button => button.addEventListener("click", () => openView(button.dataset.view)));
    await openView((location.hash || "#overview").slice(1));
  } catch (error) {
    renderInto(content, errorState(error));
  }
}

bootstrap();
