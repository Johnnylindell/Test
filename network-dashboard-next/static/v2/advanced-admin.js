import { api } from "/assets/api.js";
import { badge, dateTime, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const notice = document.querySelector("#v2-notice");
let active = false;
let currentBundle = null;

function announce(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 6000);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${end}</div>`;
}

function list(items, mapper, title = "Ingen data", detail = "") {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState(title, detail);
}

function migrationRows(data) {
  return list((data.migrations || []).slice(-20), item => row(
    `${item.version} · ${item.name}`,
    item.applied_at ? dateTime(item.applied_at) : "Inte tillämpad",
    badge(item.status === "applied" && item.checksum_match ? "Tillämpad" : item.checksum_match ? item.status : "Checksumma", item.status === "applied" && item.checksum_match ? "good" : "danger"),
  ), "Inga migrationer hittades");
}

function breakerRows(breakers) {
  const entries = Object.entries(breakers || {});
  return list(entries, ([key, value]) => row(
    key,
    `${value.failures || 0} fel${value.last_error ? ` · ${value.last_error}` : ""}`,
    badge(value.open ? "Öppen" : value.half_open ? "Halvöppen" : "Stängd", value.open ? "danger" : value.half_open ? "warning" : "good"),
  ), "Inga circuit breakers har aktiverats", "De skapas först när en integration används.");
}

function gapRows(gaps) {
  return list(gaps, gap => row(
    gap.id,
    (gap.missing || []).join(", ") || gap.status,
    badge(gap.status || "partial", gap.status === "missing" ? "danger" : "warning"),
  ), "Inga paritygap", "Alla registrerade funktionsområden är markerade som kompletta.");
}

function render(data) {
  currentBundle = data.support_bundle || null;
  const runtime = data.runtime || {};
  const database = data.database || {};
  const migrations = data.migrations || {};
  const parity = data.parity || {};
  const transcription = data.transcription || {};
  const breakers = data.circuit_breakers || {};
  const migrationHealthy = Boolean(migrations.ok);
  const isolationHealthy = Boolean(database.isolated_from_live && runtime.live_port_untouched);
  content.innerHTML = `<section class="hero"><p class="eyebrow">Avancerat · sanerad supportyta</p><h2>Teknisk hälsa utan hemligheter</h2><p>Driftflaggor, isolering, databasintegritet, migrationer, cache, circuit breakers och parity samlat i en administratörsskyddad vy.</p><div class="stats"><div class="stat"><strong>${data.ok ? "OK" : "Kontrollera"}</strong><span>Samlad hälsa</span></div><div class="stat"><strong>${migrations.pending ?? "?"}</strong><span>Väntande migrationer</span></div><div class="stat"><strong>${parity.summary?.complete || 0}/${parity.summary?.total || 0}</strong><span>Kompletta områden</span></div></div></section>
  <div class="advanced-toolbar"><button class="button" type="button" data-advanced-action="refresh">Uppdatera</button><button class="button button--soft" type="button" data-advanced-action="copy">Kopiera supportbundle</button><button class="button button--warning" type="button" data-advanced-action="clear-cache">Töm cache</button><button class="button button--warning" type="button" data-advanced-action="reset-breakers">Återställ breakers</button></div>
  <div class="grid">
    <section class="card"><div class="card__header"><div><p class="eyebrow">Skyddsgränser</p><h2>Runtime</h2></div>${badge(isolationHealthy ? "Isolerad" : "Varning", isolationHealthy ? "good" : "danger")}</div><div class="list">${row("Appversion", data.support_bundle?.app_version || "okänd")}${row("Port", String(runtime.selected_port || "dynamisk"), badge(runtime.live_port_untouched ? "Inte 8792" : "Liveport", runtime.live_port_untouched ? "good" : "danger"))}${row("Read-only", runtime.read_only ? "Aktivt" : "Av", badge(runtime.read_only ? "Skyddat" : "Skrivläge", runtime.read_only ? "good" : "warning"))}${row("Externa sidoeffekter", runtime.external_side_effects ? "Aktiva" : "Avstängda", badge(runtime.external_side_effects ? "Aktiva" : "Blockerade", runtime.external_side_effects ? "warning" : "good"))}${row("Legacy-skrivningar", runtime.legacy_writes ? "Tillåtna" : "Blockerade", badge(runtime.legacy_writes ? "Varning" : "Blockerade", runtime.legacy_writes ? "danger" : "good"))}</div></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">SQLite</p><h2>Databas</h2></div>${badge(database.integrity === "ok" ? "Integritet OK" : "Fel", database.integrity === "ok" ? "good" : "danger")}</div><div class="list">${row("Sökväg", database.path || "okänd")}${row("Separat från live", database.isolated_from_live ? "Ja" : "Nej", badge(database.isolated_from_live ? "Isolerad" : "Samma databas", database.isolated_from_live ? "good" : "danger"))}${row("Integritetskontroll", database.integrity || "saknas")}</div></section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Schema</p><h2>Migrationer</h2></div>${badge(migrationHealthy ? "Synkroniserade" : "Kontrollera", migrationHealthy ? "good" : "danger")}</div><div class="stats"><div class="stat"><strong>${migrations.pending ?? "?"}</strong><span>Väntande</span></div><div class="stat"><strong>${migrations.failed ?? "?"}</strong><span>Misslyckade</span></div><div class="stat"><strong>${migrations.checksum_errors ?? "?"}</strong><span>Checksummefel</span></div></div>${migrationRows(migrations)}</section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Minne</p><h2>Cache</h2></div>${badge(String(data.cache?.entries || 0), "neutral")}</div><p>Cachetömning påverkar bara temporära integrations- och statusvärden. Ingen databasdata raderas.</p></section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Resiliens</p><h2>Circuit breakers</h2></div>${badge(String(Object.keys(breakers).length), "neutral")}</div>${breakerRows(breakers)}</section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Funktionsparitet</p><h2>Återstående gap</h2></div>${badge(`${parity.summary?.complete || 0}/${parity.summary?.total || 0}`, parity.gaps?.length ? "warning" : "good")}</div>${gapRows(parity.gaps || [])}</section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Familjeassistent</p><h2>Röstfallback</h2></div>${badge(transcription.available ? "Redo" : transcription.state || "Av", transcription.available ? "good" : "warning")}</div><div class="list">${row("Backend", transcription.backend || "saknas")}${row("Modell", transcription.model || "inte konfigurerad")}${row("Lokal modell", transcription.model_local ? "Ja" : "Nej")}${row("Ljud sparas", transcription.audio_persisted ? "Ja" : "Nej", badge(transcription.audio_persisted ? "Varning" : "Nej", transcription.audio_persisted ? "danger" : "good"))}${row("Extern transkribering", transcription.external_transcription_service_used ? "Ja" : "Nej", badge(transcription.external_transcription_service_used ? "Varning" : "Nej", transcription.external_transcription_service_used ? "danger" : "good"))}</div><p class="helper">${escapeHtml(transcription.message || "")}</p></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Bakgrund</p><h2>Scheduler och integrationer</h2></div></div><div class="list">${row("Scheduler", data.scheduler?.active ? "Aktiv" : data.scheduler?.configured ? "Konfigurerad men av" : "Inte konfigurerad")}${row("Integrationer konfigurerade", String(data.integrations?.configured || 0))}${row("Integrationsvärden saknas", String(data.integrations?.missing || 0))}${row("Känsliga värden exponerade", data.sensitive_values_exposed ? "Ja" : "Nej", badge(data.sensitive_values_exposed ? "Varning" : "Nej", data.sensitive_values_exposed ? "danger" : "good"))}</div></section>
  </div>`;
}

async function load() {
  active = true;
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.advancedView === "true"));
  content.innerHTML = skeleton(7);
  try {
    render(await api("/api/v2/admin/advanced/overview"));
  } catch (error) {
    content.innerHTML = errorState(error);
  }
}

async function mutate(path, message) {
  try {
    await api(path, { method: "POST", body: { confirm: true } });
    announce(message);
    await load();
  } catch (error) {
    announce(error.message || "Åtgärden misslyckades", "danger");
  }
}

async function copyBundle() {
  if (!currentBundle) return;
  const text = JSON.stringify(currentBundle, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    announce("Sanerad supportbundle kopierades");
  } catch {
    window.prompt("Kopiera supportbundle:", text);
  }
}

function handleClick(event) {
  const target = event.target.closest("[data-advanced-action]");
  if (!target || !active) return;
  const action = target.dataset.advancedAction;
  if (action === "refresh") return load();
  if (action === "copy") return copyBundle();
  if (action === "clear-cache") {
    if (!window.confirm("Töm all temporär cache? Ingen databasdata påverkas.")) return;
    return mutate("/api/v2/admin/advanced/cache/clear", "Cachet tömdes");
  }
  if (action === "reset-breakers") {
    if (!window.confirm("Återställ alla circuit breakers? Integrationer kan då provas igen direkt.")) return;
    return mutate("/api/v2/admin/advanced/breakers/reset", "Circuit breakers återställdes");
  }
}

function installNav() {
  if (nav.querySelector("[data-advanced-view]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.advancedView = "true";
  button.textContent = "Avancerat";
  button.addEventListener("click", load);
  nav.append(button);
}

nav.addEventListener("click", event => {
  if (!event.target.closest("[data-advanced-view]")) active = false;
});
content.addEventListener("click", handleClick);

const observer = new MutationObserver(installNav);
observer.observe(nav, { childList: true });
installNav();
