import { api, accessControl, query } from "/assets/api.js";
import { badge, card, dateTime, emptyState, errorState, escapeHtml, money, renderInto, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const mode = document.querySelector("#v2-mode");
const notice = document.querySelector("#v2-notice");

const state = {
  current: "overview",
  data: null,
  readOnly: true,
  externalSideEffects: false,
  selectedCalendar: "primary",
  selectedBudgetSheet: "",
};

function list(items, mapper, title = "Ingen data", detail = "") {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState(title, detail);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${end}</div>`;
}

function button(label, action, value = "", tone = "", options = {}) {
  const disabled = (state.readOnly && !options.readOnlySafe) || options.disabled ? " disabled" : "";
  return `<button type="button" class="button${tone ? ` button--${tone}` : ""}${options.small === false ? "" : " button--small"}" data-action="${escapeHtml(action)}" data-value="${escapeHtml(value)}"${disabled}>${escapeHtml(label)}</button>`;
}

function mutationBanner() {
  if (!state.readOnly) return "";
  return `<section class="mode-banner"><strong>Skrivskyddat parallelläge</strong><span>Alla kontroller och formulär finns för verifiering, men ändringar blockeras tills Next aktiveras för skrivning.</span></section>`;
}

function formDisabled(extra = false) {
  return state.readOnly || extra ? " disabled" : "";
}

function formField(label, name, options = {}) {
  const type = options.type || "text";
  const value = options.value ?? "";
  const required = options.required ? " required" : "";
  const placeholder = options.placeholder ? ` placeholder="${escapeHtml(options.placeholder)}"` : "";
  const disabled = options.disabled ? " disabled" : "";
  if (type === "textarea") {
    return `<label class="field"><span>${escapeHtml(label)}</span><textarea name="${escapeHtml(name)}"${placeholder}${required}${disabled}>${escapeHtml(value)}</textarea></label>`;
  }
  if (type === "select") {
    return `<label class="field"><span>${escapeHtml(label)}</span><select name="${escapeHtml(name)}"${required}${disabled}>${(options.values || []).map(item => {
      const option = typeof item === "string" ? { value: item, label: item } : item;
      return `<option value="${escapeHtml(option.value)}"${String(option.value) === String(value) ? " selected" : ""}>${escapeHtml(option.label)}</option>`;
    }).join("")}</select></label>`;
  }
  return `<label class="field"><span>${escapeHtml(label)}</span><input type="${escapeHtml(type)}" name="${escapeHtml(name)}" value="${escapeHtml(value)}"${placeholder}${required}${disabled}></label>`;
}

function showNotice(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5500);
}

function payload(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  form.querySelectorAll('input[type="checkbox"]').forEach(input => { values[input.name] = input.checked; });
  return values;
}

async function loadSecurity() {
  const security = await api("/api/v2/admin/security/overview");
  state.readOnly = Boolean(security.read_only);
  state.externalSideEffects = Boolean(security.external_side_effects);
  mode.textContent = state.readOnly ? "Säker test" : "Skrivläge";
  mode.className = `badge badge--${state.readOnly ? "good" : "warning"}`;
  return security;
}

const views = {
  overview: { label: "Översikt", load: loadOverview, render: renderOverview },
  budget: { label: "Budget", load: loadBudget, render: renderBudget },
  calendar: { label: "Kalender & Tasks", load: loadCalendar, render: renderCalendar },
  presence: { label: "Närvaro", load: loadPresence, render: renderPresence },
  notifications: { label: "Notifieringar", load: loadNotifications, render: renderNotifications },
  wishlists: { label: "Önskelistor", load: () => api("/api/v2/wishlists/overview"), render: renderWishlists },
  household: { label: "Saker hemma", load: () => api("/api/v2/household/overview"), render: renderHousehold },
  security: { label: "Säkerhet", load: loadSecurity, render: renderSecurity },
  backups: { label: "Backuper", load: loadBackups, render: renderBackups },
  integrations: { label: "Integrationer", load: () => api("/api/v2/admin/integrations/overview"), render: renderIntegrations },
  homelab: { label: "Homelab", load: () => api("/api/v2/admin/homelab/overview"), render: renderHomelab },
};

async function loadOverview() {
  const [home, security, diagnostics, presence, integrations, calendar] = await Promise.all([
    api("/api/v2/home/summary"),
    loadSecurity(),
    api("/api/v2/notifications/diagnostics"),
    api("/api/v2/presence/overview"),
    api("/api/v2/admin/integrations/overview"),
    api("/api/v2/calendar/auth-status"),
  ]);
  return { home, security, diagnostics, presence, integrations, calendar };
}

function renderOverview(data) {
  const totals = data.home?.totals || {};
  const people = data.presence?.people || [];
  const integrations = data.integrations?.items || [];
  const scheduler = data.diagnostics.scheduler || {};
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Version 2 · Kontrollpanel</p><h2>Systemet i ett ögonblick</h2><p>Driftläge, familjedata, integrationer och säkerhet samlat i en administrativ arbetsyta.</p><div class="stats"><div class="stat"><strong>${totals.open_reminders || 0}</strong><span>Påminnelser</span></div><div class="stat"><strong>${people.filter(person => person.present).length}</strong><span>Hemma</span></div><div class="stat"><strong>${integrations.filter(item => item.ok).length}/${integrations.length}</strong><span>Integrationer OK</span></div></div></section><div class="grid">${card("Driftläge", `<div class="list">${row("Databas", state.readOnly ? "Separat kopia, skrivskyddad" : "Next-databas i skrivläge", badge(state.readOnly ? "Säker test" : "Aktiv", state.readOnly ? "good" : "warning"))}${row("Externa sidoeffekter", state.externalSideEffects ? "Aktiverade" : "Avstängda", badge(state.externalSideEffects ? "Aktiva" : "Blockerade", state.externalSideEffects ? "warning" : "good"))}${row("Legacy-skrivningar", data.security.legacy_writes ? "Tillåtna" : "Blockerade", badge(data.security.legacy_writes ? "Varning" : "Blockerade", data.security.legacy_writes ? "danger" : "good"))}</div>`, { eyebrow: "Säkerhet" })}${card("Notifieringsmotor", `<div class="list">${row("Prenumerationer", String(data.diagnostics.subscriptions || 0))}${row("Regler", String(data.diagnostics.rules || 0))}${row("Scheduler", scheduler.active ? "Kör" : scheduler.configured ? "Konfigurerad men av" : "Inte aktiverad", badge(scheduler.active ? "Aktiv" : "Av", scheduler.active ? "warning" : "good"))}${row("VAPID", data.diagnostics.public_key_configured ? "Konfigurerad" : "Saknas")}</div>`, { eyebrow: "Bakgrundsjobb" })}${card("Google", `<div class="list">${row("Client-konfiguration", data.calendar.auth?.client_configured ? "Finns" : "Saknas")}${row("Token", data.calendar.auth?.authenticated ? "Ansluten" : data.calendar.auth?.status || "Saknas", badge(data.calendar.auth?.authenticated ? "Ansluten" : "Åtgärd krävs", data.calendar.auth?.authenticated ? "good" : "warning"))}</div><p><button class="button button--soft" data-open-view="calendar">Öppna kalenderinställningar</button></p>`, { eyebrow: "Workspace" })}${card("Närvaro", `<div class="presence-grid">${people.map(person => `<div class="presence-person${person.present ? " presence-person--home" : ""}"><span class="presence-person__icon">${person.present ? "⌂" : "○"}</span><div><strong>${escapeHtml(person.owner)}</strong><small>${person.present ? "Hemma" : person.configured ? "Inte hemma" : "Ej kopplad"}</small></div></div>`).join("")}</div>`, { eyebrow: data.presence?.privacy?.raw_identifiers_stored ? "Kontrollera integritet" : "Rådata sparas inte" })}${card("Integrationer", list(integrations, item => row(item.id || item.label, item.state || "", badge(item.ok ? "OK" : item.configured ? "Kontrollera" : "Ej konfigurerad", item.ok ? "good" : "warning"))), { eyebrow: "Extern status" })}</div>`;
}

async function loadBudget() {
  const overviewPath = query("/api/v2/budget/overview", { sheet: state.selectedBudgetSheet });
  const [month, year, sync] = await Promise.all([
    api(overviewPath),
    api("/api/v2/budget/year"),
    api("/api/v2/budget/sync"),
  ]);
  if (!state.selectedBudgetSheet) state.selectedBudgetSheet = month.budget?.current || "";
  return { month, year, sync };
}

function budgetRows(items, kind) {
  return list(items, item => {
    const amount = kind === "expense" ? item.actual || item.budgeted : item.amount;
    const detail = kind === "expense" ? `Budget ${money(item.budgeted)} · faktiskt ${money(item.actual)}` : money(item.amount);
    return row(item.category, detail, `<div class="row__actions">${button("Ändra", "budget-edit", `${item.id}|${kind}|${amount}`)}${button("Radera", "budget-delete", item.id, "danger")}</div>`);
  }, `Inga ${kind === "income" ? "inkomster" : kind === "expense" ? "utgifter" : "sparposter"}`);
}

function renderBudget(data) {
  const budget = data.month?.budget || data.month || {};
  const totals = budget.totals || {};
  const year = data.year || {};
  const sync = data.sync || {};
  const sheetOptions = (budget.sheets || []).map(sheet => ({ value: sheet, label: sheet }));
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Budget</p><h2>${escapeHtml(budget.current || "Ingen månad vald")}</h2><p>Aktuella poster, årsbild och kontrollerad import/export.</p><div class="stats"><div class="stat"><strong>${money(totals.income)}</strong><span>Inkomst</span></div><div class="stat"><strong>${money(totals.expenses_actual)}</strong><span>Utgifter</span></div><div class="stat"><strong>${money(totals.balance_actual)}</strong><span>Balans</span></div></div></section><div class="toolbar">${formField("Månad", "sheet", { type: "select", value: budget.current || "", values: sheetOptions })}</div><div class="grid">${card("Inkomster", budgetRows(budget.income || [], "income"))}${card("Utgifter", budgetRows(budget.expenses || [], "expense"))}${card("Sparande", budgetRows(budget.savings || [], "savings"))}${card("Ny budgetpost", `<form class="form" data-form="budget-entry">${formField("Månad", "sheet", { type: "select", value: budget.current || "", values: sheetOptions, required: true })}${formField("Typ", "kind", { type: "select", values: [{ value: "income", label: "Inkomst" }, { value: "expense", label: "Utgift" }, { value: "savings", label: "Sparande" }] })}${formField("Namn", "label", { required: true })}${formField("Fält", "field", { type: "select", values: [{ value: "amount", label: "Belopp" }, { value: "budgeted", label: "Budgeterat" }, { value: "actual", label: "Faktiskt" }] })}${formField("Värde", "value", { type: "number", value: 0, required: true })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Lägg till</button></div></form>`, { eyebrow: "Redigera" })}${card("Året", `<div class="list">${row("Inkomst", money(year.totals?.income))}${row("Utgifter", money(year.totals?.expenses))}${row("Sparande", money(year.totals?.savings))}${row("Balans", money(year.totals?.balance), badge((year.totals?.balance || 0) >= 0 ? "Plus" : "Minus", (year.totals?.balance || 0) >= 0 ? "good" : "danger"))}</div>${list((year.months || []).slice(0, 12), item => row(item.sheet, `Utgifter ${money(item.expenses)}`, money(item.balance)))}`, { eyebrow: "Helårsbild" })}${card("Största kategorier", list((year.categories || []).slice(0, 12), item => row(item.category, "Årssumma", money(item.amount))))}${card("Säker synk", `<div class="list">${row("Läge", sync.mode || "not_configured", badge(sync.mode === "configured" ? "Konfigurerad" : "Kontrollera", sync.mode === "configured" ? "good" : "warning"))}${row("Källa", sync.source_path || "Ingen fil vald")}${row("Senaste fel", sync.last_error || "Inga")}</div><form class="form" data-form="budget-sync">${formField("Källfil", "source_path", { value: sync.source_path || "", placeholder: "/mnt/c/.../budget.xlsx" })}${formField("Intervall, sekunder", "poll_seconds", { type: "number", value: sync.poll_seconds || 60 })}${formField("Konfliktpolicy", "conflict_policy", { type: "select", value: sync.conflict_policy || "review", values: ["review", "source_wins", "app_wins"] })}<label class="check"><input type="checkbox" name="auto_sync"${sync.auto_sync ? " checked" : ""}> Automatisk synk</label><div class="form__actions"><button class="button button--primary"${formDisabled()}>Spara inställningar</button></div></form>`, { eyebrow: "Excel-förberedelse" })}${card("Import och export", `<div class="toolbar"><button class="button" type="button" data-action="budget-export">Ladda ned JSON-export</button></div><form class="form" data-form="budget-import">${formField("Budgetexport", "document", { type: "textarea", placeholder: "Klistra in network-dashboard-budget-v1 JSON" })}<label class="check"><input type="checkbox" name="replace"> Ersätt alla blad</label><label class="check"><input type="checkbox" name="confirm"> Jag bekräftar ersättning</label><div class="form__actions"><button class="button button--primary"${formDisabled()}>Importera</button></div></form>`, { eyebrow: "Versionssäker dataflytt" })}</div>`;
}

async function loadCalendar() {
  const calendarPath = query("/api/v2/calendar/overview", { calendar_id: state.selectedCalendar });
  const [calendar, security] = await Promise.all([api(calendarPath), loadSecurity()]);
  return { calendar, security };
}

function renderCalendar(data) {
  const workspace = data.calendar || {};
  const events = workspace.calendar?.events || [];
  const tasks = workspace.tasks?.tasks || [];
  const calendars = workspace.calendars?.calendars || [];
  const auth = workspace.auth || {};
  const externalBlocked = !state.externalSideEffects || state.readOnly;
  const calendarOptions = calendars.length
    ? calendars.map(item => ({ value: item.id, label: `${item.primary ? "★ " : ""}${item.title}` }))
    : [{ value: "primary", label: "Primär kalender" }];
  return `${mutationBanner()}${externalBlocked ? `<section class="mode-banner"><strong>Google-skrivningar avstängda</strong><span>OAuth, skapa och ändra kräver både skrivläge och EXTERNAL_SIDE_EFFECTS=true.</span></section>` : ""}<section class="hero"><p class="eyebrow">Google Workspace</p><h2>Kalender och uppgifter</h2><p>Välj kalender, skapa händelser och hantera Google Tasks.</p><div class="stats"><div class="stat"><strong>${events.length}</strong><span>Händelser</span></div><div class="stat"><strong>${tasks.length}</strong><span>Tasks</span></div><div class="stat"><strong>${calendars.length}</strong><span>Kalendrar</span></div></div></section><div class="grid">${card("Google-anslutning", `<div class="list">${row("Client secret", auth.client_configured ? "Finns" : "Saknas")}${row("Token", auth.authenticated ? "Ansluten" : auth.status || "Saknas", badge(auth.authenticated ? "Ansluten" : "Åtgärd krävs", auth.authenticated ? "good" : "warning"))}${row("Tokenrefresh", auth.token_refresh_persisted ? "Får sparas" : "Blockerad")}</div><div class="toolbar">${auth.authenticated ? button("Koppla från", "google-disconnect", "", "danger", { disabled: externalBlocked }) : button("Anslut Google", "google-connect", "", "primary", { disabled: externalBlocked, small: false })}</div>`, { eyebrow: "OAuth" })}${card("Kalenderval", `<label class="field"><span>Visad kalender</span><select data-calendar-select>${calendarOptions.map(item => `<option value="${escapeHtml(item.value)}"${item.value === state.selectedCalendar ? " selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}</select></label>${list(calendars, item => row(item.title, item.access_role || "", item.primary ? badge("Primär", "good") : ""), "Inga kalendrar tillgängliga")}`, { eyebrow: "Urval" })}${card("Kommande händelser", list(events.slice(0, 30), event => row(event.title, `${dateTime(event.start)}${event.location ? ` · ${event.location}` : ""}`, event.html_link ? `<a class="button button--small" href="${escapeHtml(event.html_link)}" target="_blank" rel="noreferrer">Google</a>` : ""), "Inga kommande händelser"))}${card("Ny händelse", `<form class="form" data-form="event-create">${formField("Kalender", "calendar_id", { type: "select", value: state.selectedCalendar, values: calendarOptions })}${formField("Titel", "title", { required: true })}${formField("Start", "start", { type: "datetime-local", required: true })}${formField("Slut", "end", { type: "datetime-local", required: true })}${formField("Plats", "location")}${formField("Beskrivning", "description", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${formDisabled(externalBlocked)}>Skapa händelse</button></div></form>`, { eyebrow: "Calendar" })}${card("Google Tasks", list(tasks.slice(0, 40), task => row(task.title, `${task.tasklist || "Tasks"}${task.due ? ` · ${dateTime(task.due)}` : ""}`, `<div class="row__actions">${button("Klar", "task-complete", `${task.tasklist_id}|${task.id}`, "", { disabled: externalBlocked })}${button("Radera", "task-delete", `${task.tasklist_id}|${task.id}`, "danger", { disabled: externalBlocked })}</div>`), "Inga öppna Tasks"))}${card("Ny Google Task", `<form class="form" data-form="task-create">${formField("Titel", "title", { required: true })}${formField("Anteckning", "notes", { type: "textarea" })}${formField("Förfallodatum", "due", { type: "datetime-local" })}${formField("Tasklista", "tasklist_id", { value: "@default" })}<div class="form__actions"><button class="button button--primary"${formDisabled(externalBlocked)}>Skapa uppgift</button></div></form>`, { eyebrow: "Tasks" })}</div>`;
}

async function loadPresence() {
  const [overview, devices, security] = await Promise.all([
    api("/api/v2/presence/overview"),
    api("/api/v2/presence/devices"),
    loadSecurity(),
  ]);
  return { overview, devices: devices.devices || [], privacy: devices.privacy || {}, security };
}

function renderPresence(data) {
  const people = data.overview.people || [];
  const devices = data.devices || [];
  const events = data.overview.events || [];
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Integritetsskyddad närvaro</p><h2>Telefoner utan rå nätverksdata</h2><p>Endast HMAC-koppling och sanerad hemma/borta-status lagras. IP, MAC och hash visas aldrig.</p><div class="stats"><div class="stat"><strong>${people.filter(person => person.present).length}</strong><span>Hemma</span></div><div class="stat"><strong>${devices.length}</strong><span>Kopplade telefoner</span></div><div class="stat"><strong>${events.length}</strong><span>Senaste händelser</span></div></div></section><div class="grid">${card("Familjestatus", `<div class="presence-grid">${people.map(person => `<div class="presence-person${person.present ? " presence-person--home" : ""}"><span class="presence-person__icon">${person.present ? "⌂" : "○"}</span><div><strong>${escapeHtml(person.owner)}</strong><small>${person.present ? "Hemma" : person.configured ? "Inte hemma" : "Telefon ej kopplad"}</small></div></div>`).join("")}</div>`, { eyebrow: data.overview.mode === "hemma" ? "Någon är hemma" : "Ingen registrerad hemma" })}${card("Registrerade telefoner", list(devices, device => row(device.label || device.owner, `${device.owner} · ${device.initialized ? device.present ? "hemma" : "borta" : "väntar på första observation"}`, `<div class="row__actions">${device.notify_arrival ? badge("Ankomstavisering", "good") : badge("Ingen avisering", "neutral")}${button("Ta bort", "presence-delete", device.id, "danger")}</div>`), "Inga telefoner kopplade"), { eyebrow: "Sanerade poster" })}${card("Koppla telefon", `<form class="form" data-form="presence-device">${formField("Familjemedlem", "owner", { required: true, placeholder: "Johnny" })}${formField("Visningsnamn", "label", { placeholder: "Johnnys telefon" })}${formField("Telefonens identifierare", "source_id", { required: true, placeholder: "MAC från den befintliga watchern" })}<label class="check"><input type="checkbox" name="notify_arrival" checked> Skapa ankomstavisering</label><p class="helper">Identifieraren HMAC-hashas direkt och sparas aldrig i klartext.</p><div class="form__actions"><button class="button button--primary"${formDisabled()}>Koppla telefon</button></div></form>`, { eyebrow: "Admin" })}${card("Närvarohändelser", list(events.slice(0, 40), event => row(event.message || event.event_type, `${event.owner} · ${dateTime(event.created_at)}`), "Inga övergångar registrerade"))}${card("Integritetskontroll", `<div class="list">${row("Rå identifierare sparas", data.privacy.raw_identifiers_stored ? "Ja" : "Nej", badge(data.privacy.raw_identifiers_stored ? "Varning" : "Skyddat", data.privacy.raw_identifiers_stored ? "danger" : "good"))}${row("Nätverksvärden exponeras", data.privacy.raw_network_values_exposed ? "Ja" : "Nej", badge(data.privacy.raw_network_values_exposed ? "Varning" : "Dolda", data.privacy.raw_network_values_exposed ? "danger" : "good"))}${row("Källhash exponeras", data.privacy.source_hash_exposed ? "Ja" : "Nej", badge(data.privacy.source_hash_exposed ? "Varning" : "Dold", data.privacy.source_hash_exposed ? "danger" : "good"))}</div>`)}</div>`;
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
  const scheduler = data.diagnostics.scheduler || {};
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Notifieringar</p><h2>Lugnt läge, när något faktiskt behövs</h2><p>Regler, diagnostik, schemalagd kontroll och leveranskanaler.</p><div class="stats"><div class="stat"><strong>${items.filter(item => !item.read).length}</strong><span>Olästa</span></div><div class="stat"><strong>${rules.filter(rule => rule.enabled).length}</strong><span>Aktiva regler</span></div><div class="stat"><strong>${data.diagnostics.subscriptions || 0}</strong><span>Push-enheter</span></div></div></section><div class="grid">${card("Aktiva aviseringar", list(items.slice(0, 40), item => row(item.message, `${item.type} · ${dateTime(item.created_at)}`, item.read ? badge("Läst", "good") : badge("Ny", "warning")), "Inga aviseringar"))}${card("Regler", list(rules, rule => row(rule.id, `${rule.event || rule.type} · ${rule.target || "all"} · ${rule.cooldown_minutes || 0} min`, badge(rule.enabled ? "Aktiv" : "Av", rule.enabled ? "good" : "neutral")), "Inga regler"))}${card("Kör kontroll", `<p>Kontrollerar påminnelser, rutiner, matplan, inköpsförslag, internet och budget.</p><button class="button button--primary" type="button" data-action="notification-check"${formDisabled()}>Kör smart kontroll</button><div id="notification-result"></div>`, { eyebrow: "Manuellt" })}${card("Ny regel", `<form class="form" data-form="notification-rule">${formField("ID", "id", { required: true, placeholder: "paket-snart" })}${formField("Händelse", "event", { type: "select", values: ["smart_calendar_soon", "routine_due", "smart_meal_plan_missing", "smart_shopping_suggestions", "internet_down", "budget_over"] })}${formField("Mål", "target", { value: "all" })}${formField("Meddelandemall", "template", { placeholder: "{title} {when}" })}${formField("Cooldown, minuter", "cooldown_minutes", { type: "number", value: 60 })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Lägg till regel</button></div></form>`)}${card("Leveransstatus", `<div class="list">${row("Web Push", data.diagnostics.delivery_adapter_configured ? "Adapter tillgänglig" : "Ej tillgänglig")}${row("VAPID", data.diagnostics.public_key_configured ? "Konfigurerad" : "Saknas")}${row("Externa utskick", state.externalSideEffects ? "Aktiverade" : "Blockerade", badge(state.externalSideEffects ? "Aktiva" : "Säkert av", state.externalSideEffects ? "warning" : "good"))}${row("Scheduler", scheduler.active ? `Kör var ${scheduler.interval_seconds}s` : scheduler.configured ? "Konfigurerad men blockerad" : "Av", badge(scheduler.active ? "Aktiv" : "Av", scheduler.active ? "warning" : "good"))}</div>`)}</div>`;
}

function renderWishlists(data) {
  const members = data.members || [];
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Önskelistor</p><h2>Administration av familjens önskningar</h2><p>Reservera, markera köpt och rensa poster.</p><div class="stats"><div class="stat"><strong>${(data.items || []).length}</strong><span>Poster</span></div><div class="stat"><strong>${(data.items || []).filter(item => item.reserved_by).length}</strong><span>Reserverade</span></div><div class="stat"><strong>${(data.items || []).filter(item => item.purchased).length}</strong><span>Köpta</span></div></div></section><div class="grid">${card("Önskningar", list(data.items || [], item => row(`${item.member}: ${item.title}`, `${item.price == null ? "Pris saknas" : money(item.price)}${item.reserved_by ? ` · reserverad av ${item.reserved_by}` : ""}`, `<div class="row__actions">${button(item.purchased ? "Återöppna" : "Köpt", "wishlist-purchased", `${item.id}|${item.purchased ? "0" : "1"}`)}${button("Reservera", "wishlist-reserve", item.id)}${button("Radera", "wishlist-delete", item.id, "danger")}</div>`), "Inga önskningar"))}${card("Lägg till önskning", `<form class="form" data-form="wishlist-create">${formField("Person", "member", { type: "select", values: members })}${formField("Önskning", "title", { required: true })}${formField("Länk", "url", { type: "url" })}${formField("Pris", "price", { type: "number" })}${formField("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Lägg till</button></div></form>`)}</div>`;
}

function renderHousehold(data) {
  const places = data.places || [];
  const placeOptions = places.map(place => ({ value: place.path, label: `${place.path} (${place.item_count || 0})` }));
  if (!placeOptions.length) placeOptions.push({ value: "Hem", label: "Hem" });
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Saker hemma</p><h2>Struktur för platser och ägodelar</h2><p>Administrera hierarkin och följ senaste hushållshändelser.</p><div class="stats"><div class="stat"><strong>${(data.items || []).length}</strong><span>Saker</span></div><div class="stat"><strong>${places.length}</strong><span>Platser</span></div><div class="stat"><strong>${(data.log || []).length}</strong><span>Loggrader</span></div></div></section><div class="grid">${card("Saker", list(data.items || [], item => row(item.name, `${item.location}${item.owner ? ` · ${item.owner}` : ""}`, button("Radera", "household-delete", item.id, "danger")), "Inga saker"))}${card("Platser", list(places, place => row(place.path, `${place.item_count || 0} saker`), "Inga platser"))}${card("Lägg till sak", `<form class="form" data-form="household-item">${formField("Namn", "name", { required: true })}${formField("Plats", "location", { type: "select", values: placeOptions })}${formField("Kategori", "category")}${formField("Ägare", "owner")}${formField("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Lägg till sak</button></div></form>`)}${card("Ny plats", `<form class="form" data-form="household-place">${formField("Sökväg", "path", { required: true, placeholder: "Hall / Byrå / Översta lådan" })}${formField("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Spara plats</button></div></form>`)}${card("Senaste händelser", list((data.log || []).slice(0, 30), item => row(item.title || "Händelse", `${item.category || ""} · ${dateTime(item.created_at)}`), "Ingen aktivitet"))}</div>`;
}

function renderSecurity(data) {
  const profiles = data.access?.profiles || [];
  const choices = data.access?.choices || [];
  const sessions = data.sessions || [];
  const audit = data.audit || [];
  const profileOptions = profiles.map(profile => ({ value: profile.user, label: profile.user }));
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Säkerhet</p><h2>Åtkomst, sessioner och revisionsspår</h2><p>Kontrollera vem som ser vad och när administratörsåtgärder har utförts.</p><div class="stats"><div class="stat"><strong>${profiles.length}</strong><span>Profiler</span></div><div class="stat"><strong>${sessions.length}</strong><span>Sessioner</span></div><div class="stat"><strong>${audit.length}</strong><span>Loggposter</span></div></div></section><div class="grid">${card("Driftskydd", `<div class="list">${row("Read-only", data.read_only ? "Ja" : "Nej", badge(data.read_only ? "Skyddat" : "Skrivläge", data.read_only ? "good" : "warning"))}${row("Externa sidoeffekter", data.external_side_effects ? "På" : "Av")}${row("Legacy-skrivning", data.legacy_writes ? "Tillåten" : "Blockerad")}</div>`)}${card("Profiler", list(profiles, profile => row(profile.user, `${profile.sections?.length || 0} sektioner`, badge(profile.readonly ? "Read-only" : "Skrivbar", profile.readonly ? "warning" : "good")), "Inga profiler"))}${card("Uppdatera åtkomst", `<form class="form" data-form="access-profile">${formField("Profil", "user", { type: "select", values: profileOptions })}${formField("Sektioner, kommaseparerade", "sections", { placeholder: choices.join(", ") })}<label class="check"><input type="checkbox" name="readonly"> Endast läsning</label><div class="form__actions"><button class="button button--primary"${formDisabled()}>Spara åtkomst</button></div></form>`, { eyebrow: "Tillåtna sektioner" })}${card("Byt adminlösenord", `<form class="form" data-form="password-change">${formField("Nuvarande lösenord", "current_password", { type: "password", required: true })}${formField("Nytt lösenord", "new_password", { type: "password", required: true })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Byt lösenord</button></div></form>`)}${card("Sessioner", `<div class="toolbar"><button class="button button--danger" type="button" data-action="sessions-revoke"${formDisabled()}>Återkalla övriga sessioner</button></div>${list(sessions, session => row(session.token_hint || "Session", `Går ut ${dateTime(session.expires_at)}`, session.current ? badge("Denna", "good") : ""), "Inga sessioner")}`)}${card("Revisionslogg", list(audit.slice(0, 60), item => row(item.action, `${item.actor}${item.target ? ` · ${item.target}` : ""} · ${dateTime(item.created_at)}`), "Ingen revisionslogg"))}</div>`;
}

async function loadBackups() {
  const [backups, security] = await Promise.all([api("/api/v2/admin/backups"), loadSecurity()]);
  return { backups: backups.backups || [], security };
}

function renderBackups(data) {
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Backuper</p><h2>Next-databasen, isolerad och återställningsbar</h2><p>Verifiera integritet innan återställning. En säkerhetsbackup skapas automatiskt före restore.</p><div class="stats"><div class="stat"><strong>${data.backups.length}</strong><span>Backuper</span></div><div class="stat"><strong>${Math.round(data.backups.reduce((sum, item) => sum + (item.size_bytes || 0), 0) / 1024)}</strong><span>kB totalt</span></div><div class="stat"><strong>${state.readOnly ? "Av" : "Redo"}</strong><span>Restore</span></div></div></section><div class="grid">${card("Skapa backup", `<form class="form" data-form="backup-create">${formField("Etikett", "label", { value: "manual" })}<div class="form__actions"><button class="button button--primary"${formDisabled()}>Skapa Next-backup</button></div></form>`)}${card("Backuper", list(data.backups, item => row(item.name, `${Math.round((item.size_bytes || 0) / 1024)} kB · ${dateTime(item.modified_at)}`, `<div class="row__actions"><button class="button button--small" type="button" data-action="backup-verify" data-value="${escapeHtml(item.name)}">Verifiera</button>${button("Återställ", "backup-restore", item.name, "warning")}${button("Radera", "backup-delete", item.name, "danger")}</div>`), "Inga backuper"))}</div>`;
}

function renderIntegrations(data) {
  const items = data.items || data.integrations || [];
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Integrationer</p><h2>Home Assistant, Tailscale och externa tjänster</h2><p>Liveprober körs explicit och känsliga värden visas inte.</p><div class="stats"><div class="stat"><strong>${items.filter(item => item.ok).length}</strong><span>OK</span></div><div class="stat"><strong>${items.filter(item => item.configured).length}</strong><span>Konfigurerade</span></div><div class="stat"><strong>${data.sensitive_values_exposed ? "Ja" : "Nej"}</strong><span>Känsliga värden</span></div></div></section><div class="grid">${card("Integrationer", list(items, item => row(item.label || item.id, item.detail || item.state || item.status || "", badge(item.ok ? "OK" : item.configured ? "Kontrollera" : "Ej konfigurerad", item.ok ? "good" : "warning")), "Inga integrationer"))}${card("Direktkontroller", `<div class="toolbar"><button class="button" data-action="probe-ha">Testa Home Assistant</button><button class="button" data-action="probe-tailscale">Testa Tailscale</button><button class="button" data-action="load-ha-entities">Ladda entiteter</button></div><div id="probe-result">${emptyState("Ingen kontroll körd")}</div>`, { eyebrow: "Läsning" })}${card("Home Assistant-kommando", `<form class="form" data-form="ha-service">${formField("Entity ID", "entity_id", { placeholder: "light.kok" })}${formField("Service", "service", { type: "select", values: ["turn_on", "turn_off", "toggle"] })}<div class="form__actions"><button class="button button--primary"${formDisabled(!state.externalSideEffects)}>Kör service</button></div></form><p class="helper">Endast den begränsade service-listan i backend accepteras.</p>`, { eyebrow: "Kontrollerad mutation" })}</div>`;
}

function renderHomelab(data) {
  const integrations = data.integrations || [];
  const devices = data.device_profiles || [];
  return `${mutationBanner()}<section class="hero"><p class="eyebrow">Homelab</p><h2>Sanerad teknisk översikt</h2><p>Profiler och lagrad status utan aktiva nätverksskanningar från familjegränssnittet.</p><div class="stats"><div class="stat"><strong>${devices.length}</strong><span>Enhetsprofiler</span></div><div class="stat"><strong>${integrations.length}</strong><span>Integrationer</span></div><div class="stat"><strong>${data.live_probes_performed ? "Ja" : "Nej"}</strong><span>Liveprober</span></div></div></section><div class="grid">${card("Lokal status", `<div class="list">${row("Live-prober", data.live_probes_performed ? "Utförda" : "Inte utförda", badge(data.live_probes_performed ? "Aktiv" : "Säker", data.live_probes_performed ? "warning" : "good"))}${row("Känsliga värden", data.sensitive_values_exposed ? "Exponerade" : "Dolda", badge(data.sensitive_values_exposed ? "Varning" : "Dolda", data.sensitive_values_exposed ? "danger" : "good"))}</div>`)}${card("Enhetsprofiler", list(devices.slice(0, 40), item => row(item.name || item.label || "Enhet", item.owner || item.type || ""), "Inga profiler"))}${card("Integrationer", list(integrations, item => row(item.name || item.id, item.configured ? "Konfigurerad" : "Inte konfigurerad"), "Inga integrationer"))}</div>`;
}

async function mutate(path, options, message = "Sparat") {
  if (state.readOnly) {
    showNotice("Next kör skrivskyddat. Åtgärden är blockerad.", "warning");
    return null;
  }
  try {
    const result = await api(path, options);
    showNotice(message);
    await openView(state.current, false);
    return result;
  } catch (error) {
    showNotice(error.message || "Åtgärden misslyckades", "danger");
    return null;
  }
}

async function handleSubmit(event) {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const values = payload(form);
  const kind = form.dataset.form;
  if (kind === "budget-sync") return mutate("/api/v2/budget/sync", { method: "PUT", body: { ...values, poll_seconds: Number(values.poll_seconds || 60) } }, "Synkinställningar sparade");
  if (kind === "budget-entry") return mutate("/api/v2/budget/entries", { method: "POST", body: { ...values, value: Number(values.value || 0), field: values.field || null } }, "Budgetpost tillagd");
  if (kind === "budget-import") {
    try {
      const parsed = JSON.parse(values.document || "{}");
      const budgetPayload = parsed.payload || parsed;
      return mutate("/api/v2/budget/import", { method: "POST", body: { payload: budgetPayload, replace: Boolean(values.replace), confirm: Boolean(values.confirm) } }, "Budget importerad");
    } catch {
      return showNotice("Budgetexporten är inte giltig JSON", "danger");
    }
  }
  if (kind === "event-create") {
    return mutate("/api/v2/calendar/events", { method: "POST", body: { ...values, start: new Date(values.start).toISOString(), end: new Date(values.end).toISOString() } }, "Kalenderhändelse skapad");
  }
  if (kind === "task-create") {
    const due = values.due ? new Date(values.due).toISOString() : "";
    return mutate("/api/v2/calendar/tasks", { method: "POST", body: { ...values, due } }, "Google Task skapad");
  }
  if (kind === "presence-device") return mutate("/api/v2/presence/devices", { method: "POST", body: values }, "Telefon kopplad");
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
  if (kind === "access-profile") {
    const sections = String(values.sections || "").split(",").map(value => value.trim()).filter(Boolean);
    return mutate("/api/v2/admin/security/access", { method: "PUT", body: { user: values.user, sections, readonly: Boolean(values.readonly) } }, "Åtkomstprofil uppdaterad");
  }
  if (kind === "password-change") return mutate("/api/v2/admin/security/password", { method: "PUT", body: values }, "Adminlösenord ändrat");
  if (kind === "backup-create") return mutate("/api/v2/admin/backups", { method: "POST", body: values }, "Backup skapad");
  if (kind === "ha-service") return mutate("/api/v2/admin/integrations/home-assistant/service", { method: "POST", body: values }, "Home Assistant-service körd");
}

async function handleAction(event) {
  const openTarget = event.target.closest("[data-open-view]");
  if (openTarget) return openView(openTarget.dataset.openView);
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
  if (action === "budget-edit") {
    const [id, kind, current] = value.split("|");
    const field = kind === "expense" ? window.prompt("Fält (budgeted eller actual):", "actual") : "amount";
    if (!field) return;
    const nextValue = window.prompt("Nytt värde:", current || "0");
    if (nextValue === null) return;
    return mutate(`/api/v2/budget/entries/${encodeURIComponent(id)}`, { method: "PATCH", body: { field, value: Number(nextValue) } }, "Budgetpost uppdaterad");
  }
  if (action === "budget-delete") {
    if (!window.confirm("Radera budgetposten?")) return;
    return mutate(`/api/v2/budget/entries/${encodeURIComponent(value)}`, { method: "DELETE", body: { confirm: true } }, "Budgetpost raderad");
  }
  if (action === "google-connect") {
    try {
      const result = await api("/api/v2/calendar/oauth/start", { method: "POST", body: {} });
      window.location.assign(result.authorization_url);
    } catch (error) {
      showNotice(error.message, "danger");
    }
    return;
  }
  if (action === "google-disconnect") {
    if (!window.confirm("Koppla från Google Workspace?")) return;
    return mutate("/api/v2/calendar/oauth", { method: "DELETE" }, "Google kopplades från");
  }
  if (action === "notification-check") return mutate("/api/v2/notifications/checks", { method: "POST", body: {} }, "Notifieringskontroll körd");
  if (action === "task-complete" || action === "task-delete") {
    const [tasklist, task] = value.split("|");
    const base = `/api/v2/calendar/tasks/${encodeURIComponent(tasklist)}/${encodeURIComponent(task)}`;
    return action === "task-complete"
      ? mutate(`${base}/completion`, { method: "PATCH", body: { completed: true } }, "Uppgift klar")
      : mutate(base, { method: "DELETE", body: { confirm: true } }, "Uppgift raderad");
  }
  if (action === "presence-delete") {
    if (!window.confirm("Ta bort telefonkopplingen?")) return;
    return mutate(`/api/v2/presence/devices/${encodeURIComponent(value)}`, { method: "DELETE" }, "Telefonkoppling borttagen");
  }
  if (action === "wishlist-purchased") {
    const [id, purchased] = value.split("|");
    return mutate(`/api/v2/wishlists/items/${encodeURIComponent(id)}`, { method: "PATCH", body: { purchased: purchased === "1" } }, "Önskelista uppdaterad");
  }
  if (action === "wishlist-reserve") {
    const reservedBy = window.prompt("Reserverad av:", "johnny");
    if (reservedBy === null) return;
    return mutate(`/api/v2/wishlists/items/${encodeURIComponent(value)}`, { method: "PATCH", body: { reserved_by: reservedBy } }, "Önskning reserverad");
  }
  if (action === "wishlist-delete") {
    if (!window.confirm("Radera önskningen?")) return;
    return mutate(`/api/v2/wishlists/items/${encodeURIComponent(value)}`, { method: "DELETE" }, "Önskning raderad");
  }
  if (action === "household-delete") {
    if (!window.confirm("Radera saken?")) return;
    return mutate(`/api/v2/household/items/${encodeURIComponent(value)}`, { method: "DELETE" }, "Sak raderad");
  }
  if (action === "sessions-revoke") return mutate("/api/v2/admin/security/sessions/revoke", { method: "POST", body: { keep_current: true } }, "Övriga sessioner återkallade");
  if (action === "backup-delete") {
    if (!window.confirm("Radera backupen?")) return;
    return mutate(`/api/v2/admin/backups/${encodeURIComponent(value)}`, { method: "DELETE" }, "Backup raderad");
  }
  if (action === "backup-restore") {
    if (!window.confirm("Återställ denna backup? En ny säkerhetsbackup skapas först.")) return;
    return mutate(`/api/v2/admin/backups/${encodeURIComponent(value)}/restore`, { method: "POST", body: { confirm: true } }, "Backup återställd");
  }
  if (action === "backup-verify") {
    try {
      const result = await api(`/api/v2/admin/backups/${encodeURIComponent(value)}/verify`);
      showNotice(result.ok ? "Backupen är verifierad" : `Integritetsfel: ${result.integrity}`, result.ok ? "good" : "danger");
    } catch (error) {
      showNotice(error.message, "danger");
    }
    return;
  }
  if (["probe-ha", "probe-tailscale", "load-ha-entities"].includes(action)) {
    const targetResult = document.querySelector("#probe-result");
    targetResult.innerHTML = skeleton(2);
    const path = action === "probe-ha"
      ? "/api/v2/admin/integrations/home-assistant/status?fresh=true"
      : action === "load-ha-entities"
        ? "/api/v2/admin/integrations/home-assistant/entities?fresh=true"
        : "/api/v2/admin/integrations/tailscale/status?fresh=true";
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
  content.innerHTML = `<div class="skeleton-list"><div class="skeleton skeleton--hero"></div>${skeleton(4)}</div>`;
  try {
    const data = await view.load();
    state.data = data;
    content.innerHTML = view.render(data);
    content.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
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
    content.addEventListener("change", event => {
      const calendarSelect = event.target.closest("[data-calendar-select]");
      if (calendarSelect) {
        state.selectedCalendar = calendarSelect.value || "primary";
        openView("calendar", false);
        return;
      }
      const budgetSelect = event.target.closest('select[name="sheet"]');
      if (budgetSelect && event.target.closest(".toolbar")) {
        state.selectedBudgetSheet = budgetSelect.value;
        openView("budget", false);
      }
    });
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
