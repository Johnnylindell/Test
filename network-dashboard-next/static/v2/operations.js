import { api } from "/assets/api.js";
import { badge, dateTime, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const notice = document.querySelector("#v2-notice");
let readOnly = true;
let external = false;
let lastAgentToken = null;

function announce(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 6000);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>${end}</div>`;
}

function list(items, mapper, title = "Ingen data") {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState(title);
}

function size(value) {
  const bytes = Number(value || 0);
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${Math.round(bytes / 1024)} kB`;
}

function actionButton(label, action, value, tone = "") {
  const blocked = readOnly || !external;
  return `<button class="button button--small${tone ? ` button--${tone}` : ""}" type="button" data-operation-action="${escapeHtml(action)}" data-value="${escapeHtml(value)}"${blocked ? " disabled" : ""}>${escapeHtml(label)}</button>`;
}

function render(data) {
  const system = data.system || {};
  const disk = system.disk || {};
  const memory = system.memory || {};
  const services = data.services || [];
  const agents = data.agents || [];
  const baselines = data.baselines || [];
  content.innerHTML = `<section class="hero"><p class="eyebrow">Tillåtet och spårbart</p><h2>Drift och datoragenter</h2><p>Systemstatus, explicit service-whitelist, säkra agentkommandon och baslinjejämförelser.</p><div class="stats"><div class="stat"><strong>${disk.used_percent || 0}%</strong><span>Disk används</span></div><div class="stat"><strong>${memory.used_percent || 0}%</strong><span>Minne används</span></div><div class="stat"><strong>${agents.filter(agent => agent.online).length}</strong><span>Agenter online</span></div></div></section>${readOnly || !external ? `<section class="mode-banner"><strong>Driftåtgärder blockerade</strong><span>Status kan läsas, men service- och agentkommandon kräver skrivläge och externa sidoeffekter.</span></section>` : ""}<div class="grid">
    <section class="card"><div class="card__header"><div><p class="eyebrow">Den här servern</p><h2>Systemstatus</h2></div>${badge("Ingen shellåtkomst", "good")}</div><div class="list">${row("Disk", `${size(disk.used_bytes)} av ${size(disk.total_bytes)}`, badge(`${disk.used_percent || 0}%`, disk.used_percent > 90 ? "danger" : "good"))}${row("Minne", `${size(memory.available_bytes)} tillgängligt`, badge(`${memory.used_percent || 0}%`, memory.used_percent > 90 ? "danger" : "good"))}${row("Upptid", `${Math.floor((system.uptime_seconds || 0) / 3600)} timmar`)}${row("Load average", (system.load_average || []).map(value => Number(value).toFixed(2)).join(" / ") || "saknas")}</div></section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">systemd --user</p><h2>Tillåtna tjänster</h2></div>${badge(String(services.length), "neutral")}</div>${list(services, service => row(service.label, `${service.unit_name} · ${service.status?.active_state || "okänd"}/${service.status?.sub_state || "okänd"}`, `<div class="row__actions">${actionButton("Start", "service-start", service.id)}${actionButton("Starta om", "service-restart", service.id)}${actionButton("Stoppa", "service-stop", service.id, "danger")}<button class="button button--small button--danger" data-operation-action="service-delete" data-value="${escapeHtml(service.id)}"${readOnly ? " disabled" : ""}>Ta bort</button></div>`), "Inga tjänster i tillåtelselistan")}<form id="managed-service-form" class="form"><label class="field"><span>Namn</span><input name="label" required placeholder="LAN watcher"></label><label class="field"><span>systemd unit</span><input name="unit_name" required pattern="[A-Za-z0-9_.@-]+\.service" placeholder="hermes-lan-watch.service"></label><div class="form__actions"><button class="button button--primary"${readOnly ? " disabled" : ""}>Lägg till i whitelist</button></div></form></section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Begränsade klienter</p><h2>Datoragenter</h2></div>${badge(`${agents.filter(agent => agent.online).length} online`, agents.some(agent => agent.online) ? "good" : "warning")}</div>${lastAgentToken ? `<div class="token-reveal"><strong>Agenttoken – visas bara nu</strong><code>${escapeHtml(lastAgentToken.token)}</code><small>Agent: ${escapeHtml(lastAgentToken.name)} · spara token i agentens skyddade konfigurationsfil.</small></div>` : ""}${list(agents, agent => row(agent.name, `${agent.online ? "Online" : "Offline"}${agent.last_seen ? ` · ${dateTime(agent.last_seen)}` : " · aldrig ansluten"}`, `<div class="row__actions">${actionButton("Samla status", "agent-status", agent.id)}${actionButton("Uppdatera dashboard", "agent-refresh", agent.id)}${actionButton("Notis", "agent-notify", agent.id)}<button class="button button--small button--danger" data-operation-action="agent-delete" data-value="${escapeHtml(agent.id)}"${readOnly ? " disabled" : ""}>Ta bort</button></div>`), "Inga datoragenter")}<form id="agent-create-form" class="form"><label class="field"><span>Agentnamn</span><input name="name" required placeholder="Johnnys dator"></label><div class="form__actions"><button class="button button--primary"${readOnly ? " disabled" : ""}>Skapa agent och engångstoken</button></div></form></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Jämförelsepunkt</p><h2>Baslinjer</h2></div></div>${list(baselines, baseline => row(baseline.label, `${dateTime(baseline.created_at)} · ${baseline.created_by}`, `<button class="button button--small" data-operation-action="baseline-compare" data-value="${escapeHtml(baseline.id)}">Jämför</button>`), "Inga baslinjer")}<form id="baseline-form" class="form"><label class="field"><span>Etikett</span><input name="label" value="Manuell baslinje" required></label><div class="form__actions"><button class="button button--primary"${readOnly ? " disabled" : ""}>Spara baslinje</button></div></form><div id="baseline-result"></div></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Senaste</p><h2>Agentkommandon</h2></div></div>${list((data.commands || []).slice(0, 50), command => row(`${command.agent_name}: ${command.command_type}`, `${command.status} · ${dateTime(command.created_at)}`), "Inga agentkommandon")}</section>
  </div>`;
  bind();
}

async function load() {
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.operationsView === "true"));
  content.innerHTML = skeleton(6);
  try {
    const [data, security] = await Promise.all([
      api("/api/v2/operations/overview"),
      api("/api/v2/admin/security/overview"),
    ]);
    readOnly = Boolean(security.read_only);
    external = Boolean(security.external_side_effects);
    render(data);
  } catch (error) {
    content.innerHTML = errorState(error);
  }
}

async function mutate(path, options, message) {
  try {
    const result = await api(path, options);
    announce(message);
    return result;
  } catch (error) {
    announce(error.message || "Åtgärden misslyckades", "danger");
    return null;
  }
}

async function submitService(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget).entries());
  if (await mutate("/api/v2/operations/services", { method: "POST", body: values }, "Tjänsten lades till")) await load();
}

async function submitAgent(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget).entries());
  const result = await mutate("/api/v2/operations/agents", { method: "POST", body: values }, "Agenten skapades");
  if (result?.agent) {
    lastAgentToken = result.agent;
    await load();
  }
}

async function submitBaseline(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget).entries());
  if (await mutate("/api/v2/operations/baselines", { method: "POST", body: values }, "Baslinjen sparades")) await load();
}

async function handleAction(event) {
  const target = event.target.closest("[data-operation-action]");
  if (!target) return;
  const action = target.dataset.operationAction;
  const id = target.dataset.value;
  if (action.startsWith("service-") && action !== "service-delete") {
    const serviceAction = action.replace("service-", "");
    if (!window.confirm(`${serviceAction} den tillåtna tjänsten?`)) return;
    if (await mutate(`/api/v2/operations/services/${encodeURIComponent(id)}/action`, { method: "POST", body: { action: serviceAction, confirm: true } }, "Serviceåtgärden genomfördes")) await load();
    return;
  }
  if (action === "service-delete") {
    if (!window.confirm("Ta bort tjänsten från tillåtelselistan?")) return;
    if (await mutate(`/api/v2/operations/services/${encodeURIComponent(id)}`, { method: "DELETE" }, "Tjänsten togs bort")) await load();
    return;
  }
  if (action === "agent-delete") {
    if (!window.confirm("Ta bort agenten och dess kommandohistorik?")) return;
    if (await mutate(`/api/v2/operations/agents/${encodeURIComponent(id)}`, { method: "DELETE" }, "Agenten togs bort")) await load();
    return;
  }
  if (action.startsWith("agent-")) {
    const command = action.replace("agent-", "") === "status" ? "collect_status" : action.replace("agent-", "") === "refresh" ? "refresh_dashboard" : "notify";
    const payload = command === "notify" ? { message: window.prompt("Notismeddelande:", "Hej från Lindells app") || "" } : {};
    if (command === "notify" && !payload.message) return;
    if (!window.confirm(`Skicka kommandot ${command} till agenten?`)) return;
    if (await mutate(`/api/v2/operations/agents/${encodeURIComponent(id)}/commands`, { method: "POST", body: { command_type: command, payload, confirm: true } }, "Agentkommandot köades")) await load();
    return;
  }
  if (action === "baseline-compare") {
    const targetResult = document.querySelector("#baseline-result");
    targetResult.innerHTML = skeleton(2);
    try {
      const result = await api(`/api/v2/operations/baselines/${encodeURIComponent(id)}/compare`);
      const changes = result.changes || {};
      targetResult.innerHTML = `<div class="list">${row("Disk", `${changes.disk_used_percent?.before ?? "?"}% → ${changes.disk_used_percent?.after ?? "?"}%`)}${row("Minne", `${changes.memory_used_percent?.before ?? "?"}% → ${changes.memory_used_percent?.after ?? "?"}%`)}${row("Agenter online", `${changes.agents_online?.before ?? 0} → ${changes.agents_online?.after ?? 0}`)}${list(changes.services || [], change => row(change.unit_name, `${change.before || "saknas"} → ${change.after || "saknas"}`), "Inga serviceförändringar")}</div>`;
    } catch (error) {
      targetResult.innerHTML = errorState(error);
    }
  }
}

function bind() {
  document.querySelector("#managed-service-form")?.addEventListener("submit", submitService);
  document.querySelector("#agent-create-form")?.addEventListener("submit", submitAgent);
  document.querySelector("#baseline-form")?.addEventListener("submit", submitBaseline);
  content.addEventListener("click", handleAction, { once: true });
}

function installNav() {
  if (nav.querySelector("[data-operations-view]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.operationsView = "true";
  button.textContent = "Drift";
  button.addEventListener("click", load);
  nav.append(button);
}

const observer = new MutationObserver(installNav);
observer.observe(nav, { childList: true });
installNav();
