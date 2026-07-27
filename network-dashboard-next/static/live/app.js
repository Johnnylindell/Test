import { api, accessControl, query } from "/assets/api.js";
import { badge, card, dateTime, emptyState, errorState, escapeHtml, money, renderInto, skeleton } from "/assets/ui.js";

const state = {
  access: null,
  active: "home",
  data: null,
  readOnly: true,
  externalSideEffects: false,
  recipePreview: null,
};

const main = document.querySelector("#app-main");
const userLabel = document.querySelector("#user-label");
const runtimeMode = document.querySelector("#runtime-mode");
const notice = document.querySelector("#app-notice");
const notificationCount = document.querySelector("#notification-count");
const searchDialog = document.querySelector("#search-dialog");
const newDialog = document.querySelector("#new-dialog");
const profileDialog = document.querySelector("#profile-dialog");
const searchResults = document.querySelector("#global-search-results");

const routes = {
  home: { label: "Hem", load: loadHome, render: renderHome },
  planning: { label: "Planera", load: () => api("/api/v2/planning/overview"), render: renderPlanning },
  family: { label: "Familj", load: loadFamily, render: renderFamily },
  food: { label: "Mat", load: () => api("/api/v2/food/overview"), render: renderFood },
  more: { label: "Mer", load: loadMore, render: renderMore },
  shopping: { label: "Inköp", load: () => api("/api/v2/shopping/overview"), render: renderShopping },
  inventory: { label: "Förråd", load: () => api("/api/v2/inventory/overview"), render: renderInventory },
  wishlists: { label: "Önskelistor", load: () => api("/api/v2/wishlists/overview"), render: renderWishlists },
  household: { label: "Saker hemma", load: () => api("/api/v2/household/overview"), render: renderHousehold },
  dashboard: { label: "Min sida", load: loadDashboard, render: renderDashboard },
};

function rows(items, mapper, emptyTitle = "Inget att visa", emptyDetail = "") {
  if (!items?.length) return emptyState(emptyTitle, emptyDetail);
  return `<div class="list">${items.map(mapper).join("")}</div>`;
}

function row(title, detail = "", trailing = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${trailing}</div>`;
}

function action(label, name, value = "", tone = "", options = {}) {
  const disabled = state.readOnly && !options.readOnlySafe ? " disabled" : "";
  const small = options.small === false ? "" : " button--small";
  return `<button type="button" class="button${tone ? ` button--${tone}` : ""}${small}" data-action="${escapeHtml(name)}" data-value="${escapeHtml(value)}"${disabled}>${escapeHtml(label)}</button>`;
}

function field(label, name, options = {}) {
  const value = options.value ?? "";
  const type = options.type || "text";
  const required = options.required ? " required" : "";
  const disabled = options.disabled ? " disabled" : "";
  const placeholder = options.placeholder ? ` placeholder="${escapeHtml(options.placeholder)}"` : "";
  const id = options.id ? ` id="${escapeHtml(options.id)}"` : "";
  if (type === "textarea") {
    return `<label class="field"><span>${escapeHtml(label)}</span><textarea${id} name="${escapeHtml(name)}"${placeholder}${required}${disabled}>${escapeHtml(value)}</textarea></label>`;
  }
  if (type === "select") {
    return `<label class="field"><span>${escapeHtml(label)}</span><select${id} name="${escapeHtml(name)}"${required}${disabled}>${(options.values || []).map(option => {
      const item = typeof option === "string" ? { value: option, label: option } : option;
      return `<option value="${escapeHtml(item.value)}"${String(item.value) === String(value) ? " selected" : ""}>${escapeHtml(item.label)}</option>`;
    }).join("")}</select></label>`;
  }
  return `<label class="field"><span>${escapeHtml(label)}</span><input${id} type="${escapeHtml(type)}" name="${escapeHtml(name)}" value="${escapeHtml(value)}"${placeholder}${required}${disabled}></label>`;
}

function initials(value) {
  const words = String(value || "L").trim().split(/\s+/).filter(Boolean);
  return (words.slice(0, 2).map(word => word[0]).join("") || "L").toUpperCase();
}

function banner() {
  return state.readOnly
    ? `<section class="mode-banner"><strong>Skrivskyddat parallelläge</strong><span>All information kan kontrolleras, men inga ändringar sparas innan Next aktiveras.</span></section>`
    : "";
}

function backToolbar() {
  return `<div class="toolbar"><button class="button button--soft" type="button" data-open="more">← Tillbaka till Mer</button></div>`;
}

function showNotice(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5200);
}

function formData(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  form.querySelectorAll('input[type="checkbox"]').forEach(input => { values[input.name] = input.checked; });
  return values;
}

function updateRuntime(home) {
  state.readOnly = Boolean(home.runtime?.read_only);
  state.externalSideEffects = Boolean(home.runtime?.external_side_effects);
  runtimeMode.textContent = state.readOnly ? "Säker test" : "Skrivläge";
  runtimeMode.className = state.readOnly ? "runtime--safe" : "runtime--active";
  document.querySelector("#profile-dialog-mode").textContent = state.readOnly
    ? "Skrivskyddad parallellversion"
    : "Next kör i skrivläge";
}

function updateNotificationCounter(items = []) {
  const unread = items.filter(item => !item.read).length;
  notificationCount.textContent = String(unread > 99 ? "99+" : unread);
  notificationCount.hidden = unread === 0;
}

async function mutate(path, options, message = "Sparat") {
  if (state.readOnly) {
    showNotice("Next kör skrivskyddat. Åtgärden är blockerad.", "warning");
    return null;
  }
  try {
    const result = await api(path, options);
    showNotice(message);
    await openView(state.active, true, false);
    return result;
  } catch (error) {
    showNotice(error.message || "Åtgärden misslyckades", "danger");
    return null;
  }
}

async function loadHome() {
  const [home, experience, quests, compass, presence, notifications] = await Promise.all([
    api("/api/v2/home/summary"),
    api("/api/v2/experience/overview"),
    api("/api/v2/experience/quests"),
    api("/api/v2/experience/compass"),
    api("/api/v2/presence/overview"),
    api("/api/v2/notifications/overview"),
  ]);
  updateRuntime(home);
  updateNotificationCounter(notifications.items || []);
  return { home, experience, quests, compass, presence, notifications };
}

function renderCompass(compass) {
  const mode = compass.mode || {};
  const compassActions = compass.actions || [];
  return card(
    `${mode.emoji || "🧭"} ${mode.title || "Home Compass"}`,
    `<p class="lead">${escapeHtml(compass.summary || "Ett litet nästa steg räcker.")}</p>${rows(
      compassActions,
      item => row(item.title, item.detail, action("Öppna", "compass-open", item.view, "soft", { readOnlySafe: true })),
      "Lugnt just nu",
      "Det finns inget akut att göra."
    )}`,
    { eyebrow: mode.tone || "Nästa bästa steg" }
  ).replace('class="card"', 'class="card card--accent"');
}

function renderPresence(presence) {
  const people = presence.people || [];
  return card(
    "Familjen hemma",
    `<div class="presence-grid">${people.map(person => `<div class="presence-person${person.present ? " presence-person--home" : ""}"><span class="presence-person__icon">${person.present ? "⌂" : "○"}</span><div><strong>${escapeHtml(person.owner)}</strong><small>${person.present ? "Hemma" : person.configured ? "Inte hemma" : "Telefon ej kopplad"}</small></div></div>`).join("")}</div>`,
    { eyebrow: presence.mode === "hemma" ? "Någon är hemma" : "Hemmet är tomt" }
  );
}

function renderHome(data) {
  const home = data.home || {};
  const totals = home.totals || {};
  const reminders = home.planning?.reminders || [];
  const profiles = home.family?.profiles || [];
  const cards = data.experience?.cards || {};
  const quests = data.quests?.quests || [];
  const mode = data.compass?.mode || {};
  return `${banner()}<section class="hero"><p class="eyebrow">${escapeHtml(mode.tone || "Familjens översikt")}</p><h2>${escapeHtml(mode.emoji || "")}&nbsp; Hej ${escapeHtml(state.access.user || "familjen")}</h2><p>${escapeHtml(data.compass?.summary || "Det viktigaste samlat på ett ställe.")}</p><div class="stats"><div class="stat"><strong>${totals.open_reminders || cards.open_reminders || 0}</strong><span>Påminnelser</span></div><div class="stat"><strong>${cards.shopping || 0}</strong><span>Inköp</span></div><div class="stat"><strong>${cards.inventory_inbox || 0}</strong><span>Att placera</span></div></div></section><div class="grid">${renderCompass(data.compass || {})}${renderPresence(data.presence || {})}${card("Kommande", rows(reminders.slice(0, 8), item => row(item.title || "Påminnelse", dateTime(item.remind_at || item.due_at), item.done ? badge("Klar", "good") : action("Klar", "reminder-done", item.id)), "Inga kommande påminnelser", "Skapa en via + Nytt."), { eyebrow: "Planering" })}${card("Dagens små uppdrag", rows(quests, item => row(item.title, `${item.detail || ""} · ${item.minutes || 0} min`, action(item.done ? "Ångra" : "Klar", "quest-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Inga uppdrag"), { eyebrow: "Home quests" })}${card("Snabbvägar", `<div class="quick-grid"><button data-open="shopping"><strong>Inköpslista</strong><small>${cards.shopping || 0} kvar</small></button><button data-open="inventory"><strong>Förråd</strong><small>${cards.inventory_inbox || 0} att placera</small></button><button data-open="dashboard"><strong>Min sida</strong><small>Egna uppgifter</small></button><button data-open="wishlists"><strong>Önskelistor</strong><small>Idéer och presenter</small></button></div>`, { eyebrow: "Genvägar" })}${card("Familjeprofiler", rows(profiles, item => row(item.label || item.name || item.id, item.role || "Familjemedlem"), "Inga profiler hittades"), { eyebrow: "Åtkomst" })}</div>`;
}

function renderPlanning(data) {
  const reminders = data.reminders || [];
  const rules = data.routine_rules || [];
  const instances = data.routine_instances || [];
  const checklist = data.checklist_items || [];
  return `${banner()}<section class="hero"><p class="eyebrow">Planera tillsammans</p><h2>Det som behöver bli gjort</h2><p>Påminnelser, återkommande rutiner och checklistor på samma ställe.</p><div class="stats"><div class="stat"><strong>${reminders.filter(item => !item.done).length}</strong><span>Öppna</span></div><div class="stat"><strong>${rules.filter(item => item.active).length}</strong><span>Rutiner</span></div><div class="stat"><strong>${checklist.filter(item => !item.done).length}</strong><span>Checklistor</span></div></div></section><div class="grid">${card("Påminnelser", rows(reminders, item => row(item.title, `${item.owner || "Alla"} · ${dateTime(item.remind_at || item.due_at)}`, `<div class="row__actions">${action(item.done ? "Återöppna" : "Klar", "reminder-done", `${item.id}|${item.done ? "0" : "1"}`)}${action("Radera", "reminder-delete", item.id, "danger")}</div>`), "Inga påminnelser", "Lägg till den första i formuläret bredvid."))}${card("Ny påminnelse", `<form class="form" data-form="reminder-create">${field("Titel", "title", { required: true })}${field("Vem", "owner", { value: state.access.user || "" })}${field("Tid", "remind_at", { type: "datetime-local" })}${field("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Lägg till</button></div></form>`, { eyebrow: "Skapa" })}${card("Rutiner", rows(rules, item => row(item.title, `${item.assigned_to || "Alla"} · ${item.schedule || "Ingen tidplan"}`, item.active ? badge("Aktiv", "good") : badge("Pausad", "warning")), "Inga rutiner"))}${card("Rutiner att göra", rows(instances, item => row(item.title || "Rutin", dateTime(item.scheduled_for || item.due_at), action(item.done ? "Ångra" : "Klar", "routine-instance", `${item.id}|${item.done ? "0" : "1"}`)), "Inga rutiner att göra"))}${card("Checklistor", rows(checklist, item => row(item.title || item.text, item.owner || "", action(item.done ? "Ångra" : "Klar", "checklist-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Inga checklistpunkter"))}${card("Ny rutin", `<form class="form" data-form="routine-create">${field("Titel", "title", { required: true })}${field("Tilldelad", "assigned_to", { value: "alla" })}${field("Tidplan", "schedule", { placeholder: "Varje söndag 18:00" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Skapa rutin</button></div></form>`, { eyebrow: "Återkommande" })}</div>`;
}

async function loadFamily() {
  const [family, presence] = await Promise.all([
    api("/api/v2/family/overview"),
    api("/api/v2/presence/overview"),
  ]);
  return { family, presence };
}

function renderFamily(data) {
  const family = data.family || {};
  const profiles = family.profiles || [];
  const lists = family.lists || [];
  const notes = family.notes || [];
  const dayMessage = family.day_message || {};
  return `${banner()}<section class="hero"><p class="eyebrow">Familjen</p><h2>${escapeHtml(dayMessage.message || "Vad behöver vi veta idag?")}</h2><p>Meddelanden, gemensamma listor och status för hemmet.</p><div class="stats"><div class="stat"><strong>${profiles.length}</strong><span>Profiler</span></div><div class="stat"><strong>${lists.length}</strong><span>Listor</span></div><div class="stat"><strong>${(data.presence?.people || []).filter(item => item.present).length}</strong><span>Hemma</span></div></div></section><div class="grid">${renderPresence(data.presence || {})}${card("Dagens meddelande", `<p class="lead">${escapeHtml(dayMessage.message || "Inget meddelande idag")}</p><form class="form" data-form="day-message">${field("Nytt meddelande", "message", { value: dayMessage.message || "" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Spara</button></div></form>`, { eyebrow: "På kylskåpsdörren" })}${card("Familjemedlemmar", rows(profiles, item => row(item.label || item.name || item.id, item.role || ""), "Inga profiler"))}${lists.map(listItem => card(listItem.title || listItem.id, `${rows(listItem.items || [], item => row(item.text, item.owner || "", action(item.done ? "Ångra" : "Klar", "family-item-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Listan är tom")}<form class="inline-form" data-form="family-list-item" data-list-id="${escapeHtml(listItem.id)}"><input name="text" placeholder="Ny punkt" required><input name="owner" placeholder="Vem"><button${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)).join("")}${card("Anteckningar", `${rows(notes, item => row(item.text, `${item.owner || ""} · ${dateTime(item.created_at)}`, action("Radera", "family-note-delete", item.id, "danger")), "Inga anteckningar")}<form class="form" data-form="family-note">${field("Anteckning", "text", { type: "textarea", required: true })}${field("Ägare", "owner", { value: state.access.user || "" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Spara anteckning</button></div></form>`)}</div>`;
}

function renderRecipePreview(preview) {
  const recipe = preview?.recipe;
  if (!recipe) return emptyState("Ingen förhandsgranskning", "Klistra in en HTTPS-länk till ett recept.");
  return `<div class="recipe-preview">${recipe.image_url ? `<img src="${escapeHtml(recipe.image_url)}" alt="">` : ""}<div class="recipe-preview__content"><p class="eyebrow">${escapeHtml(recipe.source_name || "Extern källa")}</p><h3>${escapeHtml(recipe.title)}</h3><div class="recipe-preview__meta">${badge(`${recipe.ingredients?.length || 0} ingredienser`, "good")}${recipe.servings ? badge(recipe.servings, "neutral") : ""}${badge("Inte sparat", "warning")}</div><p class="helper">${escapeHtml((recipe.ingredients || []).slice(0, 4).join(" · "))}</p><div class="toolbar"><button class="button button--primary" type="button" data-action="recipe-import-save"${state.readOnly ? " disabled" : ""}>Spara receptet</button></div></div></div>`;
}

function renderFood(data) {
  const meals = data.meals || [];
  const recipes = data.recipes || [];
  const shopping = data.shopping?.active || [];
  return `${banner()}<section class="hero"><p class="eyebrow">Mat och inköp</p><h2>Enklare beslut kring maten</h2><p>Planera veckan, spara recept och flytta ingredienser direkt till inköpslistan.</p><div class="stats"><div class="stat"><strong>${meals.length}</strong><span>Planerade rätter</span></div><div class="stat"><strong>${recipes.length}</strong><span>Recept</span></div><div class="stat"><strong>${shopping.length}</strong><span>Inköp</span></div></div></section><div class="grid">${card("Matsedel", rows(meals, item => row(item.day || item.date || item.week_start, item.title || "Ingen rätt"), "Ingen matsedel", "Börja med en enkel rätt för en dag."))}${card("Sätt måltid", `<form class="form" data-form="meal-set">${field("Veckans måndag", "week_start", { type: "date", required: true })}${field("Dag", "day", { type: "select", values: ["måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag"] })}${field("Rätt", "title", { required: true })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Spara måltid</button></div></form>`, { eyebrow: "Veckoplan" })}${card("Importera recept", `<form class="form" data-form="recipe-import-preview">${field("Receptlänk", "url", { type: "url", required: true, id: "recipe-import-url", placeholder: "https://…" })}<p class="helper">Förhandsgranskningen sparar ingenting och blockerar lokala nätadresser.</p><div class="form__actions"><button class="button button--primary">Förhandsgranska</button></div></form><div id="recipe-preview-result">${renderRecipePreview(state.recipePreview)}</div>`, { eyebrow: "Från webben" })}${card("Sparade recept", rows(recipes, recipe => row(recipe.title, `${recipe.servings || ""}${recipe.favorite ? " · favorit" : ""}`, `<div class="row__actions">${action("Till inköp", "recipe-shopping", recipe.id)}${action("Radera", "recipe-delete", recipe.id, "danger")}</div>`), "Inga sparade recept", "Importera ett eller skapa manuellt."))}${card("Nytt recept", `<form class="form" data-form="recipe-create">${field("Titel", "title", { required: true })}${field("Ingredienser, en per rad", "ingredients", { type: "textarea" })}${field("Steg, ett per rad", "steps", { type: "textarea" })}${field("Portioner", "servings")}${field("Källa", "source_url", { type: "url" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Spara recept</button></div></form>`, { eyebrow: "Manuellt" })}${card("Inköpslistan", rows(shopping.slice(0, 12), item => row(item.text, `${item.quantity || 1} ${item.unit || ""}`.trim()), "Inköpslistan är tom"), { action: `<button class="button button--soft button--small" data-open="shopping">Öppna</button>` })}</div>`;
}

function renderShopping(data) {
  const active = data.active || [];
  const completed = data.completed || [];
  const suggestions = data.smart_suggestions || [];
  return `${banner()}${backToolbar()}<section class="hero"><p class="eyebrow">Inköp</p><h2>Listan som lär sig</h2><p>Vanliga återköp föreslås automatiskt utan att skapa dubbletter.</p><div class="stats"><div class="stat"><strong>${active.length}</strong><span>Att köpa</span></div><div class="stat"><strong>${suggestions.length}</strong><span>Förslag</span></div><div class="stat"><strong>${completed.length}</strong><span>Senast köpt</span></div></div></section><div class="grid">${card("Att köpa", rows(active, item => row(item.text, `${item.quantity || 1} ${item.unit || ""}${item.store ? ` · ${item.store}` : ""}`.trim(), action("Köpt", "shopping-toggle", `${item.id}|1`)), "Inköpslistan är tom", "Lägg till något via + Nytt."))}${card("Smarta förslag", rows(suggestions, item => row(item.text, `${item.reason || "Återkommande köp"}${item.last_bought ? ` · senast ${dateTime(item.last_bought)}` : ""}`, `<div class="row__actions">${action("Lägg till", "shopping-suggestion-add", item.id, "primary")}${action("Inte nu", "shopping-suggestion-dismiss", item.id)}</div>`), "Inga förslag just nu", "Förslag visas efter minst två historiska köp."), { eyebrow: "Baserat på historik" })}${card("Lägg till", `<form class="form" data-form="shopping-create">${field("Vara", "text", { required: true })}${field("Antal", "quantity", { type: "number", value: 1 })}${field("Enhet", "unit")}${field("Kategori", "category")}${field("Butik", "store")}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Lägg till</button></div></form>`, { eyebrow: "Ny vara" })}${card("Senast köpt", rows(completed.slice(0, 30), item => row(item.text, dateTime(item.completed_at), action("Återöppna", "shopping-toggle", `${item.id}|0`)), "Inga köpta varor"))}</div>`;
}

function renderInventory(data) {
  const items = data.items || [];
  const inbox = data.inbox || [];
  const suggestions = data.suggestions || [];
  const locations = (data.locations || []).map(item => ({ value: item.id, label: item.label }));
  if (!locations.length) locations.push({ value: "other", label: "Övrigt" });
  return `${banner()}${backToolbar()}<section class="hero"><p class="eyebrow">Förråd</p><h2>Vet vad som finns hemma</h2><p>Placera inköp, justera antal och få inköpsförslag när något tar slut.</p><div class="stats"><div class="stat"><strong>${items.length}</strong><span>Varor</span></div><div class="stat"><strong>${inbox.length}</strong><span>Att placera</span></div><div class="stat"><strong>${suggestions.length}</strong><span>Förslag</span></div></div></section><div class="grid">${card("Förråd", rows(items, item => row(item.name, `${item.quantity || 0} ${item.unit || ""} · ${item.location || "other"}/${item.shelf || "Standard"}`, `<div class="row__actions">${action("−", "inventory-adjust", `${item.id}|-1`)}${action("+", "inventory-adjust", `${item.id}|1`)}${action("Radera", "inventory-delete", item.id, "danger")}</div>`), "Förrådet är tomt"))}${card("Lägg till vara", `<form class="form" data-form="inventory-create">${field("Namn", "name", { required: true })}${field("Antal", "quantity", { type: "number", value: 1 })}${field("Enhet", "unit")}${field("Plats", "location", { type: "select", values: locations })}${field("Hylla", "shelf", { value: "Standard" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Lägg till</button></div></form>`)}${card("Att placera", rows(inbox, item => row(item.name || item.text, `${item.quantity || 1} ${item.unit || ""} · förslag ${item.suggested_location || "other"}/${item.suggested_shelf || "Standard"}`, action("Placera", "inventory-place", item.id)), "Inget väntar på placering"))}${card("Inköpsförslag", rows(suggestions, item => row(item.text, item.reason || "Slut i lager", `<div class="row__actions">${action("Till inköp", "suggestion-shopping", item.id)}${action("Avfärda", "suggestion-dismiss", item.id)}</div>`), "Inga förslag"))}</div>`;
}

function renderWishlists(data) {
  const members = data.members || [];
  return `${banner()}${backToolbar()}<section class="hero"><p class="eyebrow">Önskelistor</p><h2>Idéer utan stress</h2><p>Spara önskningar, länkar och priser för hela familjen.</p><div class="stats"><div class="stat"><strong>${(data.items || []).length}</strong><span>Önskningar</span></div><div class="stat"><strong>${members.length}</strong><span>Personer</span></div><div class="stat"><strong>${(data.items || []).filter(item => item.purchased).length}</strong><span>Köpta</span></div></div></section><div class="grid">${card("Önskningar", rows(data.items || [], item => row(`${item.member}: ${item.title}`, `${item.price == null ? "Pris saknas" : money(item.price)}${item.reserved_by ? ` · reserverad av ${item.reserved_by}` : ""}`, action(item.purchased ? "Återöppna" : "Köpt", "wishlist-toggle", `${item.id}|${item.purchased ? "0" : "1"}`)), "Inga önskningar"))}${card("Ny önskning", `<form class="form" data-form="wishlist-create">${field("Person", "member", { type: "select", values: members })}${field("Önskning", "title", { required: true })}${field("Pris", "price", { type: "number" })}${field("Länk", "url", { type: "url" })}${field("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Lägg till</button></div></form>`)}</div>`;
}

function renderHousehold(data) {
  const places = data.places || [];
  const options = places.length ? places.map(item => ({ value: item.path, label: item.path })) : [{ value: "Hem", label: "Hem" }];
  return `${banner()}${backToolbar()}<section class="hero"><p class="eyebrow">Saker hemma</p><h2>Hitta det ni redan äger</h2><p>Registrera sak, plats och ägare så familjen slipper leta.</p><div class="stats"><div class="stat"><strong>${(data.items || []).length}</strong><span>Saker</span></div><div class="stat"><strong>${places.length}</strong><span>Platser</span></div><div class="stat"><strong>${(data.log || []).length}</strong><span>Händelser</span></div></div></section><div class="grid">${card("Saker hemma", rows(data.items || [], item => row(item.name, `${item.location}${item.owner ? ` · ${item.owner}` : ""}`, action("Radera", "household-delete", item.id, "danger")), "Inga saker registrerade"))}${card("Ny sak", `<form class="form" data-form="household-create">${field("Namn", "name", { required: true })}${field("Plats", "location", { type: "select", values: options })}${field("Kategori", "category")}${field("Ägare", "owner")}${field("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Lägg till</button></div></form>`)}${card("Platser", rows(places, item => row(item.path, `${item.item_count || 0} saker`), "Inga platser"))}${card("Senaste händelser", rows((data.log || []).slice(0, 20), item => row(item.title || item.name || "Händelse", `${item.category || ""} · ${dateTime(item.created_at)}`), "Ingen aktivitet ännu"))}</div>`;
}

async function loadDashboard() {
  const [dashboard, quests] = await Promise.all([
    api("/api/v2/experience/my-dashboard"),
    api("/api/v2/experience/quests"),
  ]);
  return { dashboard, quests };
}

function renderDashboard(data) {
  const dashboard = data.dashboard || {};
  return `${banner()}${backToolbar()}<section class="hero"><p class="eyebrow">Min sida</p><h2>${escapeHtml(state.access.user || "Min vardag")}</h2><p>Dina påminnelser, tilldelade uppgifter och sådant du inte vill glömma.</p><div class="stats"><div class="stat"><strong>${(dashboard.reminders || []).length}</strong><span>Påminnelser</span></div><div class="stat"><strong>${(dashboard.assigned_list_items || []).filter(item => !item.done).length}</strong><span>Tilldelat</span></div><div class="stat"><strong>${(dashboard.forget_items || []).filter(item => !item.done).length}</strong><span>Glöm inte</span></div></div></section><div class="grid">${card("Mina påminnelser", rows(dashboard.reminders || [], item => row(item.title, dateTime(item.remind_at || item.due_at)), "Inga påminnelser"))}${card("Tilldelat till mig", rows(dashboard.assigned_list_items || [], item => row(item.text, item.list_title || "Lista", item.done ? badge("Klar", "good") : ""), "Inga tilldelade punkter"))}${card("Glöm inte", `${rows(dashboard.forget_items || [], item => row(item.title, dateTime(item.due_at), action(item.done ? "Ångra" : "Klar", "forget-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Inga glöm-inte-poster")}<form class="form" data-form="forget-create">${field("Titel", "title", { required: true })}${field("Tid", "due_at", { type: "datetime-local" })}${field("Anteckning", "note", { type: "textarea" })}<div class="form__actions"><button class="button button--primary"${state.readOnly ? " disabled" : ""}>Lägg till</button></div></form>`)}${card("Min önskelista", rows(dashboard.wishlist?.items || [], item => row(item.title, item.price == null ? "" : money(item.price)), "Inga önskningar"))}</div>`;
}

async function loadMore() {
  const [notifications, experience, weather, presence] = await Promise.all([
    api("/api/v2/notifications/overview"),
    api("/api/v2/experience/overview"),
    api("/api/v2/weather/forecast"),
    api("/api/v2/presence/overview"),
  ]);
  updateNotificationCounter(notifications.items || []);
  return { notifications, experience, weather, presence };
}

function renderMore(data) {
  const items = data.notifications?.items || [];
  const cards = data.experience?.cards || {};
  const current = data.weather?.current || {};
  const admin = state.access.admin ? card("Administration", `<p>Tekniska funktioner, integrationer, backuper och säkerhet finns i kontrollpanelen.</p><p><a class="button button--primary" href="/preview-v2">Öppna administration</a></p>`, { eyebrow: "Endast admin" }) : "";
  return `${banner()}<section class="hero"><p class="eyebrow">Mer</p><h2>Allt annat, nära till hands</h2><p>Förråd, önskelistor, saker hemma, väder och aviseringar.</p><div class="stats"><div class="stat"><strong>${cards.shopping || 0}</strong><span>Inköp</span></div><div class="stat"><strong>${cards.inventory_inbox || 0}</strong><span>Att placera</span></div><div class="stat"><strong>${items.filter(item => !item.read).length}</strong><span>Nya aviseringar</span></div></div></section><div class="grid">${card("Funktioner", `<div class="quick-grid"><button data-open="shopping"><strong>Inköp</strong><small>${cards.shopping || 0} på listan</small></button><button data-open="inventory"><strong>Förråd</strong><small>${cards.inventory_inbox || 0} att placera</small></button><button data-open="dashboard"><strong>Min sida</strong><small>Egna uppgifter</small></button><button data-open="wishlists"><strong>Önskelistor</strong><small>Presenter och idéer</small></button><button data-open="household"><strong>Saker hemma</strong><small>Hitta vad ni äger</small></button></div>`, { eyebrow: "Alla delar" })}${card("Väder just nu", `<p class="lead">${current.temperature_c == null ? "Väderdata saknas" : `${escapeHtml(current.temperature_c)} °C`}</p><div class="list">${row("Nederbörd", current.precip_mm == null ? "—" : `${current.precip_mm} mm`)}${row("Vind", current.wind_speed_mps == null ? "—" : `${current.wind_speed_mps} m/s`)}</div>`, { eyebrow: "Mariehamn" })}${renderPresence(data.presence || {})}${card("Aviseringar", rows(items, item => row(item.message, dateTime(item.created_at), item.read ? badge("Läst", "good") : action("Markera läst", "alert-ack", item.id)), "Inga aviseringar", "Appen håller det lugnt när inget behöver din uppmärksamhet."), { eyebrow: "Det viktiga" })}${admin}${card("Session", `<p>Inloggad som <strong>${escapeHtml(state.access.user)}</strong>.</p><div class="toolbar"><a class="button" href="/choose-user">Byt profil</a><a class="button" href="/logout">Logga ut</a></div>`)}</div>`;
}

async function handleSubmit(event) {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const values = formData(form);
  switch (form.dataset.form) {
    case "reminder-create": return mutate("/api/v2/planning/reminders", { method: "POST", body: { ...values, remind_at: values.remind_at ? new Date(values.remind_at).toISOString() : "" } }, "Påminnelse skapad");
    case "routine-create": return mutate("/api/v2/planning/routines", { method: "POST", body: { ...values, active: true } }, "Rutin skapad");
    case "family-list-item": return mutate("/api/v2/family/list-items", { method: "POST", body: { list_id: form.dataset.listId, text: values.text, owner: values.owner || "" } }, "Listpunkt tillagd");
    case "family-note": return mutate("/api/v2/family/notes", { method: "POST", body: values }, "Anteckning sparad");
    case "day-message": return mutate("/api/v2/family/day-message", { method: "PUT", body: values }, "Dagens meddelande sparat");
    case "meal-set": return mutate("/api/v2/food/meals", { method: "PUT", body: { ...values, meal_id: "", url: "", source: "Manuellt" } }, "Måltid sparad");
    case "recipe-create": return mutate("/api/v2/food/recipes", { method: "POST", body: { title: values.title, source_url: values.source_url || "", source_name: "Manuellt", image_url: "", ingredients: values.ingredients.split("\n").map(value => value.trim()).filter(Boolean), steps: values.steps.split("\n").map(value => value.trim()).filter(Boolean), tags: [], servings: values.servings || "", favorite: true } }, "Recept sparat");
    case "recipe-import-preview": return previewRecipe(values.url);
    case "shopping-create": return mutate("/api/v2/shopping/items", { method: "POST", body: { list_id: "shopping", text: values.text, quantity: Number(values.quantity || 1), unit: values.unit || "", category: values.category || "", store: values.store || "" } }, "Vara tillagd");
    case "inventory-create": return mutate("/api/v2/inventory/items", { method: "POST", body: { ...values, quantity: Number(values.quantity || 0), note: "" } }, "Förrådsvara tillagd");
    case "wishlist-create": return mutate("/api/v2/wishlists/items", { method: "POST", body: { ...values, price: values.price ? Number(values.price) : null, url: values.url || null } }, "Önskning tillagd");
    case "household-create": return mutate("/api/v2/household/items", { method: "POST", body: { ...values, info: "", image_url: "" } }, "Sak tillagd");
    case "forget-create": return mutate("/api/v2/experience/forget-items", { method: "POST", body: { ...values, due_at: values.due_at ? new Date(values.due_at).toISOString() : "", owner: state.access.user || "" } }, "Glöm-inte-post tillagd");
  }
}

async function previewRecipe(url) {
  const target = document.querySelector("#recipe-preview-result");
  if (!target) return;
  target.innerHTML = skeleton(2);
  try {
    const result = await api(query("/api/v2/food/recipes/import/preview", { url }));
    state.recipePreview = result;
    target.innerHTML = renderRecipePreview(result);
    showNotice("Receptet är förhandsgranskat men inte sparat");
  } catch (error) {
    state.recipePreview = null;
    target.innerHTML = errorState(error);
  }
}

async function handleClick(event) {
  const opener = event.target.closest("[data-open]");
  if (opener) return openView(opener.dataset.open);
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const value = target.dataset.value || "";
  const [id, flag] = value.split("|");
  switch (target.dataset.action) {
    case "compass-open": return openView(value || "home");
    case "reminder-done": return mutate(`/api/v2/planning/reminders/${encodeURIComponent(id || value)}`, { method: "PATCH", body: { done: flag ? flag === "1" : true } }, "Påminnelse uppdaterad");
    case "reminder-delete": if (confirm("Radera påminnelsen?")) return mutate(`/api/v2/planning/reminders/${encodeURIComponent(value)}`, { method: "DELETE" }, "Påminnelse raderad"); break;
    case "routine-instance": return mutate(`/api/v2/planning/routine-instances/${encodeURIComponent(id)}`, { method: "PUT", body: { done: flag === "1" } }, "Rutin uppdaterad");
    case "checklist-toggle": return mutate(`/api/v2/planning/checklist-items/${encodeURIComponent(id)}`, { method: "PUT", body: { done: flag === "1" } }, "Checklistan uppdaterad");
    case "family-item-toggle": return mutate(`/api/v2/family/list-items/${encodeURIComponent(id)}`, { method: "PATCH", body: { done: flag === "1" } }, "Listan uppdaterad");
    case "family-note-delete": if (confirm("Radera anteckningen?")) return mutate(`/api/v2/family/notes/${encodeURIComponent(value)}`, { method: "DELETE" }, "Anteckning raderad"); break;
    case "shopping-toggle": return mutate(`/api/v2/shopping/items/${encodeURIComponent(id)}/completion`, { method: "PATCH", body: { done: flag === "1" } }, "Inköpslistan uppdaterad");
    case "shopping-suggestion-add": return mutate(`/api/v2/shopping/suggestions/${encodeURIComponent(value)}/shopping`, { method: "POST", body: {} }, "Förslaget lades till");
    case "shopping-suggestion-dismiss": return mutate(`/api/v2/shopping/suggestions/${encodeURIComponent(value)}`, { method: "DELETE" }, "Förslaget pausades i 30 dagar");
    case "inventory-adjust": return mutate(`/api/v2/inventory/items/${encodeURIComponent(id)}/quantity`, { method: "PATCH", body: { delta: Number(flag) } }, "Antal uppdaterat");
    case "inventory-delete": if (confirm("Radera förrådsvaran?")) return mutate(`/api/v2/inventory/items/${encodeURIComponent(value)}?confirm=true`, { method: "DELETE" }, "Vara raderad"); break;
    case "inventory-place": return placeInventory(value);
    case "suggestion-shopping": return mutate(`/api/v2/inventory/suggestions/${encodeURIComponent(value)}/shopping`, { method: "POST", body: { list_id: "shopping" } }, "Tillagd på inköpslistan");
    case "suggestion-dismiss": return mutate(`/api/v2/inventory/suggestions/${encodeURIComponent(value)}`, { method: "DELETE" }, "Förslag avfärdat");
    case "wishlist-toggle": return mutate(`/api/v2/wishlists/items/${encodeURIComponent(id)}`, { method: "PATCH", body: { purchased: flag === "1" } }, "Önskelistan uppdaterad");
    case "household-delete": if (confirm("Radera saken?")) return mutate(`/api/v2/household/items/${encodeURIComponent(value)}`, { method: "DELETE" }, "Sak raderad"); break;
    case "forget-toggle": return mutate(`/api/v2/experience/forget-items/${encodeURIComponent(id)}`, { method: "PATCH", body: { done: flag === "1" } }, "Glöm-inte uppdaterad");
    case "quest-toggle": return mutate(`/api/v2/experience/quests/${encodeURIComponent(id)}`, { method: "PUT", body: { done: flag === "1" } }, "Uppdrag uppdaterat");
    case "alert-ack": return mutate(`/api/v2/notifications/alerts/${encodeURIComponent(value)}/ack`, { method: "POST", body: {} }, "Avisering markerad som läst");
    case "recipe-delete": if (confirm("Radera receptet?")) return mutate(`/api/v2/food/recipes/${encodeURIComponent(value)}`, { method: "DELETE" }, "Recept raderat"); break;
    case "recipe-shopping": {
      const recipe = (state.data.recipes || []).find(item => item.id === value);
      const ingredients = recipe?.ingredients || [];
      return mutate("/api/v2/food/ingredients/shopping", { method: "POST", body: { ingredients, list_id: "shopping", source: recipe?.title || "Recept" } }, "Ingredienser tillagda på inköpslistan");
    }
    case "recipe-import-save": {
      const recipe = state.recipePreview?.recipe;
      if (!recipe) return showNotice("Förhandsgranska receptet först", "warning");
      return mutate("/api/v2/food/recipes/import/save", { method: "POST", body: { recipe, confirm: true } }, "Receptet importerades");
    }
  }
}

function placeInventory(itemId) {
  if (state.readOnly) return showNotice("Next kör skrivskyddat", "warning");
  const location = window.prompt("Plats (fridge, freezer, pantry, chest_freezer eller other):", "pantry");
  if (location === null) return;
  const shelf = window.prompt("Hylla:", "Standard");
  if (shelf === null) return;
  return mutate(`/api/v2/inventory/inbox/${encodeURIComponent(itemId)}/place`, { method: "POST", body: { location, shelf } }, "Vara placerad");
}

async function openView(name, force = false, updateHash = true) {
  const route = routes[name] || routes.home;
  state.active = routes[name] ? name : "home";
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-current", button.dataset.view === state.active ? "page" : "false"));
  main.innerHTML = `<div class="skeleton-list"><div class="skeleton skeleton--hero"></div>${skeleton(3)}</div>`;
  try {
    const data = await route.load(force);
    state.data = data;
    main.innerHTML = route.render(data);
    main.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    main.innerHTML = errorState(error);
    main.querySelector("[data-retry]")?.addEventListener("click", () => openView(state.active, true, false));
  }
  if (updateHash) location.hash = state.active;
}

function openDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

async function runGlobalSearch(event) {
  event.preventDefault();
  const q = new FormData(event.currentTarget).get("q")?.toString().trim() || "";
  if (q.length < 2) {
    searchResults.innerHTML = emptyState("Skriv minst två tecken");
    return;
  }
  searchResults.innerHTML = skeleton(4);
  try {
    const result = await api(query("/api/v2/experience/search", { q }));
    searchResults.innerHTML = rows(result.results || [], item => row(item.title, `${item.kind} · ${item.detail || ""}`, `<button class="button button--small button--soft" data-search-url="${escapeHtml(item.url || "/#home")}">Öppna</button>`), "Inga träffar", "Prova ett annat ord.");
  } catch (error) {
    searchResults.innerHTML = errorState(error);
  }
}

async function quickCreate(kind) {
  const targets = {
    reminder: ["planning", 'form[data-form="reminder-create"] input[name="title"]'],
    shopping: ["shopping", 'form[data-form="shopping-create"] input[name="text"]'],
    note: ["family", 'form[data-form="family-note"] textarea[name="text"]'],
    wishlist: ["wishlists", 'form[data-form="wishlist-create"] input[name="title"]'],
    recipe: ["food", "#recipe-import-url"],
    thing: ["household", 'form[data-form="household-create"] input[name="name"]'],
  };
  const [view, selector] = targets[kind] || targets.reminder;
  closeDialog(newDialog);
  await openView(view);
  window.setTimeout(() => main.querySelector(selector)?.focus(), 100);
}

function configureChrome() {
  const user = state.access.user || "Familj";
  const avatar = initials(user);
  userLabel.textContent = state.access.admin ? "Admin" : user;
  document.querySelector("#profile-avatar").textContent = avatar;
  document.querySelector("#profile-dialog-avatar").textContent = avatar;
  document.querySelector("#profile-dialog-user").textContent = state.access.admin ? `Admin · ${user}` : user;
  document.querySelector("#profile-dialog-title").textContent = state.access.admin ? "Administration" : "Min profil";
  document.querySelector("#admin-link")?.toggleAttribute("hidden", !state.access.admin);

  document.querySelector("#search-button")?.addEventListener("click", () => {
    openDialog(searchDialog);
    window.setTimeout(() => document.querySelector("#global-search-input")?.focus(), 50);
  });
  document.querySelector("#notification-button")?.addEventListener("click", () => openView("more"));
  document.querySelector("#new-button")?.addEventListener("click", () => openDialog(newDialog));
  document.querySelector("#profile-button")?.addEventListener("click", () => openDialog(profileDialog));
  document.querySelector("#global-search-form")?.addEventListener("submit", runGlobalSearch);
  searchResults?.addEventListener("click", event => {
    const target = event.target.closest("[data-search-url]");
    if (!target) return;
    closeDialog(searchDialog);
    const hash = new URL(target.dataset.searchUrl, location.origin).hash.slice(1) || "home";
    openView(hash);
  });
  newDialog?.addEventListener("click", event => {
    const target = event.target.closest("[data-quick-create]");
    if (target) quickCreate(target.dataset.quickCreate);
  });
  profileDialog?.addEventListener("click", event => {
    const target = event.target.closest('[data-profile-action="dashboard"]');
    if (target) {
      closeDialog(profileDialog);
      openView("dashboard");
    }
  });
}

async function bootstrap() {
  try {
    state.access = await accessControl();
    configureChrome();
    document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => openView(button.dataset.view)));
    main.addEventListener("submit", handleSubmit);
    main.addEventListener("click", handleClick);
    await openView((location.hash || "#home").slice(1), false, false);
  } catch (error) {
    renderInto(main, errorState(error));
  }
}

window.addEventListener("hashchange", () => {
  const name = (location.hash || "#home").slice(1);
  if (name !== state.active) openView(name, false, false);
});

bootstrap();
