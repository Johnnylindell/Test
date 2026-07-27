import { api, accessControl } from "/assets/api.js";
import {
  badge,
  card,
  dateTime,
  emptyState,
  errorState,
  escapeHtml,
  money,
  renderInto,
  skeleton,
} from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const mode = document.querySelector("#v2-mode");
const notice = document.querySelector("#v2-notice");

const state = {
  current: "overview",
  data: null,
  readOnly: true,
  externalSideEffects: false,
};

function list(items, mapper, title = "Ingen data") {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState(title);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>${end}</div>`;
}

function button(label, action, value = "", tone = "") {
  const disabled = state.readOnly ? " disabled" : "";
  return `<button type="button" class="button ${tone ? `button--${tone}` : ""}" data-action="${escapeHtml(action)}" data-value="${escapeHtml(value)}"${disabled}>${escapeHtml(label)}</button>`;
}

function mutationBanner() {
  if (!state.readOnly) return "";
  return `<section class="mode-banner"><strong>Skrivskyddat parallelläge</strong><span>Alla formulär visas för paritetskontroll, men ändringar blockeras tills cutover-läget aktiveras.</span></section>`;
}

function formDisabled() {
  return state.readOnly ? " disabled" : "";
}

function formField(label, name, options = {}) {
  const type = options.type || "text";
  const value = options.value ?? "";
  const required = options.required ? " required" : "";
  const placeholder = options.placeholder ? ` placeholder="${escapeHtml(options.placeholder)}"` : "";
  if (type === "textarea") {
    return `<label class="field"><span>${escapeHtml(label)}</span><textarea name="${escapeHtml(name)}"${placeholder}${required}>${escapeHtml(value)}</textarea></label>`;
  }
  if (type === "select") {
    const values = options.values || [];
    return `<label class="field"><span>${escapeHtml(label)}</span><select name="${escapeHtml(name)}"${required}>${values.map(item => {
      const option = typeof item === "string" ? { value: item, label: item } : item;
      return `<option value="${escapeHtml(option.value)}"${String(option.value) === String(value) ? " selected" : ""}>${escapeHtml(option.label)}</option>`;
    }).join("")}</select></label>`;
  }
  return `<label class="field"><span>${escapeHtml(label)}</span><input type="${escapeHtml(type)}" name="${escapeHtml(name)}" value="${escapeHtml(value)}"${placeholder}${required}></label>`;
}

async function loadSecurity() {
  const security = await api("/api/v2/admin/security/overview");
  state.readOnly = Boolean(security.read_only);
  state.externalSideEffects = Boolean(security.external_side_effects);
  mode.textContent = state.readOnly ? "Read-only" : "Skrivläge";
  mode.className = `badge badge--${state.readOnly ? "warning" : "good"}`;
  return security;
}

const views = {
  overview: { label: "Översikt", load: loadOverview, render: renderOverview },
  budget: { label: "Budget", load: loadBudget, render: renderBudget },
  calendar: { label: "Kalender & Tasks", load: loadCalendar, render: renderCalendar },
  notifications: { label: "Notifieringar", load: loadNotifications, render: renderNotifications },
  wishlists: { label: "Önskelistor", load: loadWishlists, render: renderWishlists },
  household: { label: "Saker hemma", load: loadHousehold, render: renderHousehold },
  security: { label: "Säkerhet", load: loadSecurity, render: renderSecurity },
  backups: { label: "Backuper", load: loadBackups, render: renderBackups },
  integrations: { label: "Integrationer", load: () => api("/api/v2/admin/integrations/overview"), render: renderIntegrations },
  homelab: { label: "Homelab", load: () => api("/api/v2/admin/homelab/overview"), render: renderHomelab },
};

async function loadOverview() {
  const [home, security, diagnostics] = await Promise.all([
    api("/api/v2/home/summary"),
    loadSecurity(),
    api("/api/v2/notifications/diagnostics"),
  ]);
  return { home, security, diagnostics };
}

function renderOverview(data) {
  const totals = data.home?.totals || {};
  return `${mutationBanner()}<section class="hero"><p>Version 2</p><h2>Administrativ arbetsyta</h2><p>Modulär kontrollpanel för den nya familjeappen.</p><div class="stats"><div class="stat"><strong>${totals.open_reminders || 0}</strong><span>Påminnelser</span></div><div class="stat"><strong>${totals.open_routines || 0}</strong><span>Rutiner</span></div><div class="stat"><strong>${totals.open_checklist_items || 0}</strong><span>Uppgifter</span></div></div></section><div class="grid">${card("Driftläge", `<div class="list">${row("Databas", state.readOnly ? "Separat kopia, skrivskyddad" : "Next-databas i skrivläge", badge(state.readOnly ? "Säker test" : "Aktiv", state.readOnly ? "good" : "warning"))}${row("Externa sidoeffekter", state.externalSideEffects ? "Aktiverade" : "Avstängda", badge(state.externalSideEffects ? "Aktiva" : "Blockerade", state.externalSideEffects ? "warning" : "good"))}${row("Legacy-skrivningar", data.security.legacy_writes ? "Tillåtna" : "Blockerade", badge(data.security.legacy_writes ? "Varning" : "Blockerade", data.security.legacy_writes ? "danger" : "good"))}</div>`)}${card("Notifieringar", `<div class="list">${row("Prenumerationer", String(data.diagnostics.subscriptions || 0))}${row("Regler", String(data.diagnostics.rules || 0))}${row("VAPID", data.diagnostics.public_key_configured ? "Konfigurerad" : "Saknas", badge(data.diagnostics.public_key_configured ? "Klar" : "Saknas", data.diagnostics.public_key_configured ? "good" : "warning"))}</div>`)}</div>`;
}

async function loadBudget() {
  const [month, year, sync] = await Promise.all([
    api("/api/v2/budget/overview"),
    api("/api/v2/budget/year"),
    api("/api/v2/budget/sync"),
  ]);
  return { month, year, sync };
}

function renderBudget(data) {
  const budget = data.month?.budget || data.month;
  const totals = budget.totals || {};
  const year = data.year || {};
  const yearTotals = year.totals || {};
  const categories = year.categories || [];
  const sync = data.sync || {};
  return `${mutationBanner()}<div class="grid">${card("Aktuell månad", `<p><strong>${escapeHtml(budget.current || "Inte vald")}</strong></p><div class="list">${row("Inkomst", money(totals.income))}${row("Utgifter", money(totals.expenses_actual))}${row("Sparande", money(totals.savings))}${row("Saldo", money(totals.balance_actual), badge(totals.balance_actual >= 0 ? "Plus" : "Minus", totals.balance_actual >= 0 ? "good" : "danger"))}</div>`)}${card("Året", `<div class="list">${row("Inkomst", money(yearTotals.income))}${row("Utgifter", money(yearTotals.expenses))}${row("Sparande", money(yearTotals.savings))}${row("Balans", money(yearTotals.balance))}</div>`)}${card("Största kategorier", list(categories.slice(0, 10), item => row(item.category, `${item.months || 0} månader`, money(item.amount))))}${card("Säker synk", `<div class="list">${row("Läge", sync.mode || "not_configured", badge(sync.mode === "ready" ? "Redo" : "Kontrollera", sync.mode === "ready" ? "good" : "warning"))}${row("Källa", sync.source_path || "Ingen fil vald")}${row("Konfliktpolicy", sync.conflict_policy || "review")}</div><form class="form" data-form="budget-sync">${formField("Källfil", "source_path", { value: sync.source_path || "", placeholder: "/mnt/c/.../budget.xlsx" })}${formField("Intervall, sekunder", "poll_seconds", { type: "number", value: sync.poll_seconds || 60 })}${formField("Konfliktpolicy", "conflict_policy", { type: "select", value: sync.conflict_policy || "review", values: ["review", "source_wins", "app_wins"] })}<label class="check"><input type="checkbox" name="auto_sync"${sync.auto_sync ? " checked" : ""}> Automatisk synk</label><button class="button"${formDisabled()}>Spara synkinställningar</button></form>`)}${card("Import och export", `<div class="toolbar"><button class="button" type="button" data-action="budget-export">Ladda ned JSON-export</button></div><form class="form" data-form="budget-import">${formField("Budgetexport", "document", { type: "textarea", placeholder: "Klistra in network-dashboard-budget-v1 JSON" })}<label class="check"><input type="checkbox" name="replace"> Ersätt alla blad</label><label class="check"><input type="checkbox" name="confirm"> Jag bekräftar ersättning</label><button class="button"${formDisabled()}>Importera</button></form>`)}</div>`;
}

async function loadCalendar() {
  const [calendar, security] = await Promise.all([api("/api/v2/calendar/overview"), loadSecurity()]);
  return { calendar, security };
}

function renderCalendar(data) {
  const calendar = data.calendar || {};
  const events = calendar.calendar?.events || [];
  const tasks = calendar.tasks?.tasks || [];
  const externalBlocked = !state.externalSideEffects;
  return `${mutationBanner()}${externalBlocked ? `<section class="mode-banner"><strong>Google-skrivningar avstängda</strong><span>Läsning fungerar, men skapa/ändra/radera kräver EXTERNAL_SIDE_EFFECTS=true.</span></section>` : ""}<div class="grid">${card("Kommande händelser", list(events.slice(0, 20), event => row(event.title, `${dateTime(event.start)}${event.location ? ` · ${event.location}` : ""}`)))}${card("Google Tasks", list(tasks.slice(0, 30), task => row(task.title, `${task.tasklist || "Tasks"}${task.due ? ` · ${dateTime(task.due)}` : ""}`, `<div class="row__actions">${button("Klar", "task-complete", `${task.tasklist_id}|${task.id}`)}${button("Radera", "task-delete", `${task.tasklist_id}|${task.id}`, "danger")}</div>`)))}${card("Ny Google Task", `<form class="form" data-form="task-create">${formField("Titel", "title", { required: true })}${formField("Anteckning", "notes", { type: "textarea" })}${formField("Förfallodatum", "due", { type: "datetime-local" })}${formField("Tasklista", "tasklist_id", { value: "@default" })}<button class="button"${formDisabled() || (externalBlocked ? " disabled" : "")}>Skapa uppgift</button></form>`)}${card("Google-status", `<div class="list">${row("Autentisering", calendar.auth?.authenticated ? "Ansluten" : calendar.auth?.status || "Saknas", badge(calendar.auth?.authenticated ? "Ansluten" : "Åtgärd krävs", calendar.auth?.authenticated ? "good" : "warning"))}${row("Händelser", String(calendar.calendar?.count || 0))}${row("Öppna Tasks", String(calendar.tasks?.count || 0))}</div>`)}</div>`;
}

async function loadNotifications() {
  const [overview, rules, diagnostics, security] = await Promise.all([
    api("/api/v2/notifications/overview"),
    api("/api/v2/notifications/rules"),
    api("/api/v2/notifications/diagnostics"),
    loadSecurity(),
  ]);
  return { overview, rules: rules.rules || [], diagnostics, security };
}

function renderNotifications(data) {
  const items = data.overview.items || [];
  const rules = data.rules || [];
  return `${mutationBanner()}<div class="grid">${card("Aktiva aviseringar", list(items.slice(0, 30), item => row(item.message, `${item.type} · ${dateTime(item.created_at)}`, item.read ? badge("Läst", "good") : badge("Ny", "warning"))))}${card("Regler", list(rules, rule => row(rule.id, `${rule.event || rule.type} · ${rule.target || "all"}`, badge(rule.enabled ? "Aktiv" : "Av", rule.enabled ? "good" : "neutral"))))}${card("Kör kontroll", `<p>Kontrollerar påminnelser, rutiner, matplan, inköpsförslag, internet och budget.</p><button class="button" type="button" data-action="notification-check"${formDisabled()}>Kör smart kontroll</button><div id="notification-result"></div>`)}${card("Ny regel", `<form class="form" data-form="notification-rule">${formField("ID", "id", { required: true, placeholder: "paket-snart" })}${formField("Händelse", "event", { type: "select", values: ["smart_calendar_soon", "routine_due", "smart_meal_plan_missing", "smart_shopping_suggestions", "internet_down", "budget_over"] })}${formField("Mål", "target", { value: "all" })}${formField("Meddelandemall", "template", { placeholder: "{title} {when}" })}${formField("Cooldown, minuter", "cooldown_minutes", { type: "number", value: 60 })}<button class="button"${formDisabled()}>Lägg till regel</button></form>`)}${card("Leveransstatus", `<div class="list">${row("Web Push", data.diagnostics.delivery_adapter_configured ? "Adapter tillgänglig" : "Ej tillgänglig")}${row("VAPID", data.diagnostics.public_key_configured ? "Konfigurerad" : "Saknas")}${row("Externa utskick", state.externalSideEffects ? "Aktiverade" : "Blockerade", badge(state.externalSideEffects ? "Aktiva" : "Säkert av", state.externalSideEffects ? "warning" : "good"))}</div>`)}</div>`;
}

async function loadWishlists() {
  return api("/api/v2/wishlists/overview");
}

function renderWishlists(data) {
  const members = data.members || [];
  return `${mutationBanner()}<div class="grid">${card("Önskningar", list(data.items || [], item => row(`${item.member}: ${item.title}`, `${item.price == null ? "Pris saknas" : money(item.price)}${item.reserved_by ? ` · reserverad av ${item.reserved_by}` : ""}`, `<div class="row__actions">${button(item.purchased ? "Återöppna" : "Köpt", "wishlist-purchased", `${item.id}|${item.purchased ? "0" : "1"}`)}${button("Reservera", "wishlist-reserve", item.id)}${button("Radera", "wishlist-delete", item.id, "danger")}</div>`)))}${card("Lägg till önskning", `<form class="form" data-form="wishlist-create">${formField("Person", "member", { type: "select", values: members })}${formField("Önskning", "title", { required: true })}${formField("Länk", "url", { type: "url" })}${formField("Pris", "price", { type: "number" })}${formField("Anteckning", "note", { type: "textarea" })}<button class="button"${formDisabled()}>Lägg till</button></form>`)}</div>`;
}

async function loadHousehold() {
  return api("/api/v2/household/overview");
}

function renderHousehold(data) {
  const places = data.places || [];
  const placeOptions = places.map(place => ({ value: place.path, label: `${place.path} (${place.item_count || 0})` }));
  if (!placeOptions.length) placeOptions.push({ value: "Hem", label: "Hem" });
  return `${mutationBanner()}<div class="grid">${card("Saker", list(data.items || [], item => row(item.name, `${item.location}${item.owner ? ` · ${item.owner}` : ""}`, `<div class="row__actions">${button("Radera", "household-delete", item.id, "danger")}</div>`)))}${card("Platser", list(places, place => row(place.path, `${place.item_count || 0} saker`)))}${card("Lägg till sak", `<form class="form" data-form="household-item">${formField("Namn", "name", { required: true })}${formField("Plats", "location", { type: "select", values: placeOptions })}${formField("Kategori", "category")}${formField("Ägare", "owner")}${formField("Anteckning", "note", { type: "textarea" })}<button class="button"${formDisabled()}>Lägg till sak</button></form>`)}${card("Ny plats", `<form class="form" data-form="household-place">${formField("Sökväg", "path", { required: true, placeholder: "Hall / Byrå / Översta lådan" })}${formField("Anteckning", "note", { type: "textarea" })}<button class="button"${formDisabled()}>Spara plats</button></form>`)}${card("Senaste händelser", list((data.log || []).slice(0, 20), item => row(item.title, `${item.category || "Händelse"} · ${dateTime(item.created_at)}`)))}</div>`;
}

function renderSecurity(data) {
  const profiles = data.access?.profiles || [];
  const sessions = data.sessions || [];
  const audit = data.audit || [];
  return `${mutationBanner()}<div class="grid">${card("Driftskydd", `<div class="list">${row("Read-only", data.read_only ? "Ja" : "Nej", badge(data.read_only ? "Skyddat" : "Skrivläge", data.read_only ? "good" : "warning"))}${row("Externa sidoeffekter", data.external_side_effects ? "På" : "Av")}${row("Legacy-skrivning", data.legacy_writes ? "Tillåten" : "Blockerad")}</div>`)}${card("Profiler", list(profiles, profile => row(profile.user, `${profile.sections?.length || 0} sektioner`, badge(profile.readonly ? "Read-only" : "Skrivbar", profile.readonly ? "warning" : "good"))))}${card("Sessioner", `<div class="toolbar"><button class="button button--danger" type="button" data-action="sessions-revoke"${formDisabled()}>Återkalla övriga sessioner</button></div>${list(sessions, session => row(session.token_hint || "Session", `Går ut ${dateTime(session.expires_at)}`, session.current ? badge("Denna", "good") : ""))}`)}${card("Revisionslogg", list(audit.slice(0, 40), item => row(item.action, `${item.actor} · ${dateTime(item.created_at)}`)))}</div>`;
}

async function loadBackups() {
  const [backups, security] = await Promise.all([api("/api/v2/admin/backups"), loadSecurity()]);
  return { backups: backups.backups || [], security };
}

function renderBackups(data) {
  return `${mutationBanner()}<div class="grid">${card("Skapa backup", `<form class="form" data-form="backup-create">${formField("Etikett", "label", { value: "manual" })}<button class="button"${formDisabled()}>Skapa Next-backup</button></form>`)}${card("Backuper", list(data.backups, item => row(item.name, `${Math.round((item.size_bytes || 0) / 1024)} kB · ${dateTime(item.modified_at)}`, `<div class="row__actions"><button class="button" type="button" data-action="backup-verify" data-value="${escapeHtml(item.name)}">Verifiera</button>${button("Radera", "backup-delete", item.name, "danger")}</div>`)))}</div>`;
}

function renderIntegrations(data) {
  const items = data.items || data.integrations || [];
  return `<div class="grid">${card("Integrationer", list(items, item => row(item.label || item.id, item.detail || item.status || "", badge(item.ok ? "OK" : item.configured ? "Kontrollera" : "Ej konfigurerad", item.ok ? "good" : "warning"))))}${card("Direktkontroller", `<div class="toolbar"><button class="button" data-action="probe-ha">Testa Home Assistant</button><button class="button" data-action="probe-tailscale">Testa Tailscale</button></div><div id="probe-result">${emptyState("Ingen kontroll körd")}</div>`)}</div>`;
}

function renderHomelab(data) {
  const integrations = data.integrations || [];
  const devices = data.device_profiles || [];
  return `<div class="grid">${card("Lokal status", `<div class="list">${row("Live-prober", data.live_probes_performed ? "Utförda" : "Inte utförda", badge(data.live_probes_performed ? "Aktiv" : "Säker", data.live_probes_performed ? "warning" : "good"))}${row("Känsliga värden", data.sensitive_values_exposed ? "Exponerade" : "Dolda", badge(data.sensitive_values_exposed ? "Varning" : "Dolda", data.sensitive_values_exposed ? "danger" : "good"))}</div>`)}${card("Enhetsprofiler", list(devices.slice(0, 20), item => row(item.name || item.label || item.mac || "Enhet", item.owner || item.type || "")))}${card("Integrationer", list(integrations, item => row(item.name || item.id, item.configured ? "Konfigurerad" : "Inte konfigurerad")))}</div>`;
}

function payload(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  form.querySelectorAll('input[type="checkbox"]').forEach(input => { values[input.name] = input.checked; });
  return values;
}

function showNotice(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5000);
}

async function mutate(path, options, message = "Sparat") {
  try {
    await api(path, options);
    showNotice(message);
    await openView(state.current, false);
  } catch (error) {
    showNotice(error.message || "Åtgärden misslyckades", "danger");
  }
}

async function handleSubmit(event) {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const values = payload(form);
  const kind = form.dataset.form;
  if (kind === "budget-sync") {
    return mutate("/api/v2/budget/sync", { method: "PUT", body: { ...values, poll_seconds: Number(values.poll_seconds || 60) } });
  }
  if (kind === "budget-import") {
    try {
      const budgetDocument = JSON.parse(values.document || "{}");
      return mutate("/api/v2/budget/import", { method: "POST", body: { document: budgetDocument, replace: Boolean(values.replace), confirm: Boolean(values.confirm) } }, "Budget importerad");
    } catch {
      return showNotice("Budgetexporten är inte giltig JSON", "danger");
    }
  }
  if (kind === "task-create") {
    const due = values.due ? new Date(values.due).toISOString() : "";
    return mutate("/api/v2/calendar/tasks", { method: "POST", body: { ...values, due } }, "Google Task skapad");
  }
  if (kind === "notification-rule") {
    const rules = [...(state.data.rules || []), { ...values, enabled: true, severity: "normal", cooldown_minutes: Number(values.cooldown_minutes || 0), conditions: {} }];
    return mutate("/api/v2/notifications/rules", { method: "PUT", body: { rules } }, "Regel sparad");
  }
  if (kind === "wishlist-create") {
    const body = { ...values, price: values.price === "" ? null : Number(values.price), url: values.url || null };
    return mutate("/api/v2/wishlists/items", { method: "POST", body }, "Önskning tillagd");
  }
  if (kind === "household-item") return mutate("/api/v2/household/items", { method: "POST", body: values }, "Sak tillagd");
  if (kind === "household-place") return mutate("/api/v2/household/places", { method: "PUT", body: { ...values, old_path: "", info: "", image_url: "" } }, "Plats sparad");
  if (kind === "backup-create") return mutate("/api/v2/admin/backups", { method: "POST", body: values }, "Backup skapad");
}

async function handleAction(event) {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const action = target.dataset.action;
  const value = target.dataset.value || "";
  if (action === "budget-export") {
    try {
      const exportedBudget = await api("/api/v2/budget/export");
      const blob = new Blob([JSON.stringify(exportedBudget, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `network-dashboard-budget-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (error) {
      showNotice(error.message, "danger");
    }
    return;
  }
  if (action === "notification-check") return mutate("/api/v2/notifications/checks", { method: "POST", body: {} }, "Notifieringskontroll körd");
  if (action === "task-complete" || action === "task-delete") {
    const [tasklist, task] = value.split("|");
    const base = `/api/v2/calendar/tasks/${encodeURIComponent(tasklist)}/${encodeURIComponent(task)}`;
    return action === "task-complete"
      ? mutate(`${base}/completion`, { method: "PATCH", body: { completed: true } }, "Uppgift klar")
      : mutate(base, { method: "DELETE", body: { confirm: true } }, "Uppgift raderad");
  }
  if (action === "wishlist-purchased") {
    const [id, purchased] = value.split("|");
    return mutate(`/api/v2/wishlists/items/${encodeURIComponent(id)}`, { method: "PATCH", body: { purchased: purchased === "1" } });
  }
  if (action === "wishlist-reserve") {
    const reservedBy = window.prompt("Reserverad av:", "johnny");
    if (reservedBy === null) return;
    return mutate(`/api/v2/wishlists/items/${encodeURIComponent(value)}`, { method: "PATCH", body: { reserved_by: reservedBy } }, "Önskning reserverad");
  }
  if (action === "wishlist-delete") return mutate(`/api/v2/wishlists/items/${encodeURIComponent(value)}`, { method: "DELETE" }, "Önskning raderad");
  if (action === "household-delete") return mutate(`/api/v2/household/items/${encodeURIComponent(value)}`, { method: "DELETE" }, "Sak raderad");
  if (action === "sessions-revoke") return mutate("/api/v2/admin/security/sessions/revoke", { method: "POST", body: { keep_current: true } }, "Övriga sessioner återkallade");
  if (action === "backup-delete") return mutate(`/api/v2/admin/backups/${encodeURIComponent(value)}`, { method: "DELETE" }, "Backup raderad");
  if (action === "backup-verify") {
    try {
      const result = await api(`/api/v2/admin/backups/${encodeURIComponent(value)}/verify`);
      showNotice(result.ok ? "Backupen är verifierad" : `Integritetsfel: ${result.integrity}`, result.ok ? "good" : "danger");
    } catch (error) {
      showNotice(error.message, "danger");
    }
    return;
  }
  if (action === "probe-ha" || action === "probe-tailscale") {
    const targetResult = document.querySelector("#probe-result");
    targetResult.innerHTML = skeleton(2);
    const path = action === "probe-ha" ? "/api/v2/admin/integrations/home-assistant/status?fresh=true" : "/api/v2/admin/integrations/tailscale/status?fresh=true";
    try {
      const result = await api(path);
      targetResult.innerHTML = `<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
    } catch (error) {
      targetResult.innerHTML = errorState(error);
    }
  }
}

async function openView(name, updateHash = true) {
  const view = views[name] || views.overview;
  state.current = views[name] ? name : "overview";
  nav.querySelectorAll("button").forEach(buttonElement => buttonElement.classList.toggle("active", buttonElement.dataset.view === state.current));
  content.innerHTML = skeleton(6);
  try {
    const data = await view.load();
    state.data = data;
    content.innerHTML = view.render(data);
  } catch (error) {
    content.innerHTML = errorState(error);
    content.querySelector("[data-retry]")?.addEventListener("click", () => openView(state.current, false));
  }
  if (updateHash) location.hash = state.current;
}

async function bootstrap() {
  try {
    const access = await accessControl();
    if (!access.admin) throw new Error("Adminsession krävs");
    await loadSecurity();
    nav.innerHTML = Object.entries(views).map(([id, view]) => `<button type="button" data-view="${id}">${escapeHtml(view.label)}</button>`).join("");
    nav.addEventListener("click", event => {
      const target = event.target.closest("[data-view]");
      if (target) openView(target.dataset.view);
    });
    content.addEventListener("submit", handleSubmit);
    content.addEventListener("click", handleAction);
    await openView((location.hash || "#overview").slice(1), false);
  } catch (error) {
    renderInto(content, errorState(error));
  }
}

window.addEventListener("hashchange", () => {
  const name = (location.hash || "#overview").slice(1);
  if (name !== state.current) openView(name, false);
});

bootstrap();
