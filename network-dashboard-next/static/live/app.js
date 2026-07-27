import { api, accessControl } from "/assets/api.js";
import { badge, card, dateTime, emptyState, errorState, escapeHtml, money, renderInto, skeleton } from "/assets/ui.js";

const state = { access: null, active: "home", data: null, readOnly: true, externalSideEffects: false };
const main = document.querySelector("#app-main");
const userLabel = document.querySelector("#user-label");
const runtimeMode = document.querySelector("#runtime-mode");
const notice = document.querySelector("#app-notice");

const routes = {
  home: { label: "Hem", load: loadHome, render: renderHome },
  planning: { label: "Planera", load: () => api("/api/v2/planning/overview"), render: renderPlanning },
  family: { label: "Familj", load: () => api("/api/v2/family/overview"), render: renderFamily },
  food: { label: "Mat", load: () => api("/api/v2/food/overview"), render: renderFood },
  more: { label: "Mer", load: loadMore, render: renderMore },
  shopping: { label: "Inköp", load: () => api("/api/v2/shopping/overview"), render: renderShopping },
  inventory: { label: "Förråd", load: () => api("/api/v2/inventory/overview"), render: renderInventory },
  wishlists: { label: "Önskelistor", load: () => api("/api/v2/wishlists/overview"), render: renderWishlists },
  household: { label: "Saker hemma", load: () => api("/api/v2/household/overview"), render: renderHousehold },
  dashboard: { label: "Min sida", load: loadDashboard, render: renderDashboard },
};

function rows(items, mapper, emptyTitle = "Inget att visa") {
  if (!items?.length) return emptyState(emptyTitle);
  return `<div class="list">${items.map(mapper).join("")}</div>`;
}

function row(title, detail = "", trailing = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${trailing}</div>`;
}

function action(label, name, value = "", tone = "") {
  return `<button type="button" class="button${tone ? ` button--${tone}` : ""}" data-action="${escapeHtml(name)}" data-value="${escapeHtml(value)}"${state.readOnly ? " disabled" : ""}>${escapeHtml(label)}</button>`;
}

function field(label, name, options = {}) {
  const value = options.value ?? "";
  const type = options.type || "text";
  const required = options.required ? " required" : "";
  const placeholder = options.placeholder ? ` placeholder="${escapeHtml(options.placeholder)}"` : "";
  if (type === "textarea") return `<label class="field"><span>${escapeHtml(label)}</span><textarea name="${escapeHtml(name)}"${placeholder}${required}>${escapeHtml(value)}</textarea></label>`;
  if (type === "select") return `<label class="field"><span>${escapeHtml(label)}</span><select name="${escapeHtml(name)}">${(options.values || []).map(option => {
    const item = typeof option === "string" ? { value: option, label: option } : option;
    return `<option value="${escapeHtml(item.value)}"${String(item.value) === String(value) ? " selected" : ""}>${escapeHtml(item.label)}</option>`;
  }).join("")}</select></label>`;
  return `<label class="field"><span>${escapeHtml(label)}</span><input type="${escapeHtml(type)}" name="${escapeHtml(name)}" value="${escapeHtml(value)}"${placeholder}${required}></label>`;
}

function banner() {
  return state.readOnly ? `<section class="mode-banner"><strong>Skrivskyddat parallelläge</strong><span>Du kan kontrollera all data, men inga ändringar sparas förrän Next aktiveras för skrivning.</span></section>` : "";
}

function showNotice(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  setTimeout(() => { notice.innerHTML = ""; }, 5000);
}

function formData(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  form.querySelectorAll('input[type="checkbox"]').forEach(input => { values[input.name] = input.checked; });
  return values;
}

async function mutate(path, options, message = "Sparat") {
  try {
    await api(path, options);
    showNotice(message);
    await openView(state.active, true, false);
  } catch (error) {
    showNotice(error.message || "Åtgärden misslyckades", "danger");
  }
}

async function loadHome() {
  const [home, experience, quests] = await Promise.all([
    api("/api/v2/home/summary"),
    api("/api/v2/experience/overview"),
    api("/api/v2/experience/quests"),
  ]);
  state.readOnly = Boolean(home.runtime?.read_only);
  state.externalSideEffects = Boolean(home.runtime?.external_side_effects);
  runtimeMode.textContent = state.readOnly ? "Read-only" : "Skrivläge";
  runtimeMode.className = `badge badge--${state.readOnly ? "warning" : "good"}`;
  return { home, experience, quests };
}

function renderHome(data) {
  const home = data.home || {};
  const totals = home.totals || {};
  const reminders = home.planning?.reminders || [];
  const profiles = home.family?.profiles || [];
  const cards = data.experience?.cards || {};
  const quests = data.quests?.quests || [];
  return `${banner()}<section class="hero"><p>Familjens översikt</p><h2>Hej ${escapeHtml(state.access.user || "familjen")}</h2><p>Det viktigaste samlat på ett ställe.</p><div class="stats"><div class="stat"><strong>${totals.open_reminders || 0}</strong><span>Påminnelser</span></div><div class="stat"><strong>${cards.shopping || 0}</strong><span>Inköp</span></div><div class="stat"><strong>${cards.inventory_inbox || 0}</strong><span>Att placera</span></div></div></section><div class="grid">${card("Kommande", rows(reminders.slice(0, 8), item => row(item.title || "Påminnelse", dateTime(item.remind_at), item.done ? badge("Klar", "good") : action("Klar", "reminder-done", item.id)), "Inga kommande påminnelser"))}${card("Dagens små uppdrag", rows(quests, item => row(item.title, `${item.detail || ""} · ${item.minutes || 0} min`, action(item.done ? "Ångra" : "Klar", "quest-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Inga uppdrag"))}${card("Snabbvägar", `<div class="quick-grid"><button data-open="shopping">Inköpslista</button><button data-open="inventory">Förråd</button><button data-open="dashboard">Min sida</button><button data-open="wishlists">Önskelistor</button><button data-open="household">Saker hemma</button></div>`)}${card("Familjen", rows(profiles, item => row(item.label || item.name || item.id, item.role || "Familjemedlem"), "Inga profiler hittades"))}</div>`;
}

function renderPlanning(data) {
  const reminders = data.reminders || [];
  const rules = data.routine_rules || [];
  const instances = data.routine_instances || [];
  const checklist = data.checklist_items || [];
  return `${banner()}<div class="grid">${card("Påminnelser", rows(reminders, item => row(item.title, `${item.owner || "Alla"} · ${dateTime(item.remind_at)}`, `<div class="row__actions">${action(item.done ? "Återöppna" : "Klar", "reminder-done", `${item.id}|${item.done ? "0" : "1"}`)}${action("Radera", "reminder-delete", item.id, "danger")}</div>`), "Inga påminnelser"))}${card("Ny påminnelse", `<form class="form" data-form="reminder-create">${field("Titel", "title", { required: true })}${field("Vem", "owner", { value: state.access.user || "" })}${field("Tid", "remind_at", { type: "datetime-local" })}${field("Anteckning", "note", { type: "textarea" })}<button class="button"${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)}${card("Rutiner", rows(rules, item => row(item.title, `${item.assigned_to || "Alla"} · ${item.schedule || "Ingen tidplan"}`, item.active ? badge("Aktiv", "good") : badge("Pausad", "warning")), "Inga rutiner"))}${card("Rutiner att göra", rows(instances, item => row(item.title || "Rutin", dateTime(item.scheduled_for || item.due_at), action(item.done ? "Ångra" : "Klar", "routine-instance", `${item.id}|${item.done ? "0" : "1"}`)), "Inga rutiner att göra"))}${card("Checklistor", rows(checklist, item => row(item.title || item.text, item.owner || "", action(item.done ? "Ångra" : "Klar", "checklist-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Inga checklistpunkter"))}${card("Ny rutin", `<form class="form" data-form="routine-create">${field("Titel", "title", { required: true })}${field("Tilldelad", "assigned_to", { value: "alla" })}${field("Tidplan", "schedule", { placeholder: "Varje söndag 18:00" })}<button class="button"${state.readOnly ? " disabled" : ""}>Skapa rutin</button></form>`)}</div>`;
}

function renderFamily(data) {
  const profiles = data.profiles || [];
  const lists = data.lists || [];
  const notes = data.notes || [];
  const dayMessage = data.day_message || {};
  return `${banner()}<div class="grid">${card("Dagens meddelande", `<p class="lead">${escapeHtml(dayMessage.message || "Inget meddelande idag")}</p><form class="form" data-form="day-message">${field("Nytt meddelande", "message", { value: dayMessage.message || "" })}<button class="button"${state.readOnly ? " disabled" : ""}>Spara</button></form>`)}${card("Familjemedlemmar", rows(profiles, item => row(item.label || item.name || item.id, item.role || ""), "Inga profiler"))}${lists.map(listItem => card(listItem.title || listItem.id, `${rows(listItem.items || [], item => row(item.text, item.owner || "", action(item.done ? "Ångra" : "Klar", "family-item-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Listan är tom")}<form class="inline-form" data-form="family-list-item" data-list-id="${escapeHtml(listItem.id)}"><input name="text" placeholder="Ny punkt" required><input name="owner" placeholder="Vem"><button${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)).join("")}${card("Anteckningar", `${rows(notes, item => row(item.text, `${item.owner || ""} · ${dateTime(item.created_at)}`, action("Radera", "family-note-delete", item.id, "danger")), "Inga anteckningar")}<form class="form" data-form="family-note">${field("Anteckning", "text", { type: "textarea", required: true })}${field("Ägare", "owner", { value: state.access.user || "" })}<button class="button"${state.readOnly ? " disabled" : ""}>Spara anteckning</button></form>`)}</div>`;
}

function renderFood(data) {
  const meals = data.meals || [];
  const recipes = data.recipes || [];
  const shopping = data.shopping?.active || [];
  return `${banner()}<div class="grid">${card("Matsedel", rows(meals, item => row(item.day || item.date || item.week_start, item.title || "Ingen rätt"), "Ingen matsedel"))}${card("Sätt måltid", `<form class="form" data-form="meal-set">${field("Veckans måndag", "week_start", { type: "date", required: true })}${field("Dag", "day", { type: "select", values: ["måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag"] })}${field("Rätt", "title", { required: true })}<button class="button"${state.readOnly ? " disabled" : ""}>Spara måltid</button></form>`)}${card("Recept", rows(recipes, recipe => row(recipe.title, `${recipe.servings || ""}${recipe.favorite ? " · favorit" : ""}`, `<div class="row__actions">${action("Ingredienser → inköp", "recipe-shopping", recipe.id)}${action("Radera", "recipe-delete", recipe.id, "danger")}</div>`), "Inga sparade recept"))}${card("Nytt recept", `<form class="form" data-form="recipe-create">${field("Titel", "title", { required: true })}${field("Ingredienser, en per rad", "ingredients", { type: "textarea" })}${field("Steg, ett per rad", "steps", { type: "textarea" })}${field("Portioner", "servings")}${field("Källa", "source_url", { type: "url" })}<button class="button"${state.readOnly ? " disabled" : ""}>Spara recept</button></form>`)}${card("Inköpslistan", rows(shopping.slice(0, 12), item => row(item.text, `${item.quantity || 1} ${item.unit || ""}`.trim()), "Inköpslistan är tom"))}</div>`;
}

function renderShopping(data) {
  const active = data.active || [];
  const completed = data.completed || [];
  return `${banner()}<div class="toolbar"><button class="button" data-open="more">← Tillbaka</button></div><div class="grid">${card("Att köpa", rows(active, item => row(item.text, `${item.quantity || 1} ${item.unit || ""}${item.store ? ` · ${item.store}` : ""}`.trim(), action("Köpt", "shopping-toggle", `${item.id}|1`)), "Inköpslistan är tom"))}${card("Lägg till", `<form class="form" data-form="shopping-create">${field("Vara", "text", { required: true })}${field("Antal", "quantity", { type: "number", value: 1 })}${field("Enhet", "unit")}${field("Kategori", "category")}${field("Butik", "store")}<button class="button"${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)}${card("Senast köpt", rows(completed.slice(0, 30), item => row(item.text, dateTime(item.completed_at), action("Återöppna", "shopping-toggle", `${item.id}|0`)), "Inga köpta varor"))}</div>`;
}

function renderInventory(data) {
  const items = data.items || [];
  const inbox = data.inbox || [];
  const suggestions = data.suggestions || [];
  const locations = (data.locations || []).map(item => ({ value: item.id, label: item.label }));
  return `${banner()}<div class="toolbar"><button class="button" data-open="more">← Tillbaka</button></div><div class="grid">${card("Förråd", rows(items, item => row(item.name, `${item.quantity || 0} ${item.unit || ""} · ${item.location || "other"}/${item.shelf || "Standard"}`, `<div class="row__actions">${action("−", "inventory-adjust", `${item.id}|-1`)}${action("+", "inventory-adjust", `${item.id}|1`)}${action("Radera", "inventory-delete", item.id, "danger")}</div>`), "Förrådet är tomt"))}${card("Lägg till vara", `<form class="form" data-form="inventory-create">${field("Namn", "name", { required: true })}${field("Antal", "quantity", { type: "number", value: 1 })}${field("Enhet", "unit")}${field("Plats", "location", { type: "select", values: locations })}${field("Hylla", "shelf", { value: "Standard" })}<button class="button"${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)}${card("Att placera", rows(inbox, item => row(item.name || item.text, `${item.quantity || 1} ${item.unit || ""}`, action("Placera", "inventory-place", item.id)), "Inget väntar på placering"))}${card("Inköpsförslag", rows(suggestions, item => row(item.text, item.reason || "Slut i lager", `<div class="row__actions">${action("Till inköp", "suggestion-shopping", item.id)}${action("Avfärda", "suggestion-dismiss", item.id)}</div>`), "Inga förslag"))}</div>`;
}

function renderWishlists(data) {
  const members = data.members || [];
  return `${banner()}<div class="toolbar"><button class="button" data-open="more">← Tillbaka</button></div><div class="grid">${card("Önskningar", rows(data.items || [], item => row(`${item.member}: ${item.title}`, `${item.price == null ? "Pris saknas" : money(item.price)}${item.reserved_by ? ` · reserverad av ${item.reserved_by}` : ""}`, action(item.purchased ? "Återöppna" : "Köpt", "wishlist-toggle", `${item.id}|${item.purchased ? "0" : "1"}`)), "Inga önskningar"))}${card("Ny önskning", `<form class="form" data-form="wishlist-create">${field("Person", "member", { type: "select", values: members })}${field("Önskning", "title", { required: true })}${field("Pris", "price", { type: "number" })}${field("Länk", "url", { type: "url" })}${field("Anteckning", "note", { type: "textarea" })}<button class="button"${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)}</div>`;
}

function renderHousehold(data) {
  const places = data.places || [];
  const options = places.length ? places.map(item => ({ value: item.path, label: item.path })) : [{ value: "Hem", label: "Hem" }];
  return `${banner()}<div class="toolbar"><button class="button" data-open="more">← Tillbaka</button></div><div class="grid">${card("Saker hemma", rows(data.items || [], item => row(item.name, `${item.location}${item.owner ? ` · ${item.owner}` : ""}`, action("Radera", "household-delete", item.id, "danger")), "Inga saker registrerade"))}${card("Ny sak", `<form class="form" data-form="household-create">${field("Namn", "name", { required: true })}${field("Plats", "location", { type: "select", values: options })}${field("Kategori", "category")}${field("Ägare", "owner")}${field("Anteckning", "note", { type: "textarea" })}<button class="button"${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)}${card("Platser", rows(places, item => row(item.path, `${item.item_count || 0} saker`), "Inga platser"))}</div>`;
}

async function loadDashboard() {
  const [dashboard, quests] = await Promise.all([api("/api/v2/experience/my-dashboard"), api("/api/v2/experience/quests")]);
  return { dashboard, quests };
}

function renderDashboard(data) {
  const dashboard = data.dashboard || {};
  return `${banner()}<div class="toolbar"><button class="button" data-open="more">← Tillbaka</button></div><div class="grid">${card("Mina påminnelser", rows(dashboard.reminders || [], item => row(item.title, dateTime(item.remind_at)), "Inga påminnelser"))}${card("Tilldelat till mig", rows(dashboard.assigned_list_items || [], item => row(item.text, item.list_title || "Lista"), "Inga tilldelade punkter"))}${card("Glöm inte", `${rows(dashboard.forget_items || [], item => row(item.title, dateTime(item.due_at), action(item.done ? "Ångra" : "Klar", "forget-toggle", `${item.id}|${item.done ? "0" : "1"}`)), "Inga glöm-inte-poster")}<form class="form" data-form="forget-create">${field("Titel", "title", { required: true })}${field("Tid", "due_at", { type: "datetime-local" })}${field("Anteckning", "note", { type: "textarea" })}<button class="button"${state.readOnly ? " disabled" : ""}>Lägg till</button></form>`)}${card("Min önskelista", rows(dashboard.wishlist?.items || [], item => row(item.title, item.price == null ? "" : money(item.price)), "Inga önskningar"))}</div>`;
}

async function loadMore() {
  const [notifications, experience] = await Promise.all([api("/api/v2/notifications/overview"), api("/api/v2/experience/overview")]);
  return { notifications, experience };
}

function renderMore(data) {
  const items = data.notifications?.items || [];
  const cards = data.experience?.cards || {};
  const admin = state.access.admin ? card("Administration", `<p>Tekniska funktioner och Version 2 är tillgängliga.</p><p><a class="button" href="/preview-v2">Öppna Version 2</a></p>`) : "";
  return `${banner()}<div class="grid">${card("Funktioner", `<div class="quick-grid"><button data-open="shopping">Inköp (${cards.shopping || 0})</button><button data-open="inventory">Förråd (${cards.inventory_inbox || 0})</button><button data-open="dashboard">Min sida</button><button data-open="wishlists">Önskelistor</button><button data-open="household">Saker hemma</button></div>`)}${card("Aviseringar", rows(items, item => row(item.message, dateTime(item.created_at), item.read ? badge("Läst", "good") : action("Läst", "alert-ack", item.id)), "Inga aviseringar"))}${admin}${card("Session", `<p>Inloggad som <strong>${escapeHtml(state.access.user)}</strong>.</p><p><a href="/choose-user">Byt profil</a> · <a href="/logout">Logga ut</a></p>`)}</div>`;
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
    case "recipe-create": return mutate("/api/v2/food/recipes", { method: "POST", body: { title: values.title, source_url: values.source_url || "", source_name: "Manuellt", image_url: "", ingredients: values.ingredients.split("\n").map(v => v.trim()).filter(Boolean), steps: values.steps.split("\n").map(v => v.trim()).filter(Boolean), tags: [], servings: values.servings || "", favorite: true } }, "Recept sparat");
    case "shopping-create": return mutate("/api/v2/shopping/items", { method: "POST", body: { list_id: "shopping", text: values.text, quantity: Number(values.quantity || 1), unit: values.unit || "", category: values.category || "", store: values.store || "" } }, "Vara tillagd");
    case "inventory-create": return mutate("/api/v2/inventory/items", { method: "POST", body: { ...values, quantity: Number(values.quantity || 0), note: "" } }, "Förrådsvara tillagd");
    case "wishlist-create": return mutate("/api/v2/wishlists/items", { method: "POST", body: { ...values, price: values.price ? Number(values.price) : null, url: values.url || null } }, "Önskning tillagd");
    case "household-create": return mutate("/api/v2/household/items", { method: "POST", body: { ...values, info: "", image_url: "" } }, "Sak tillagd");
    case "forget-create": return mutate("/api/v2/experience/forget-items", { method: "POST", body: { ...values, due_at: values.due_at ? new Date(values.due_at).toISOString() : "", owner: state.access.user || "" } }, "Glöm-inte-post tillagd");
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
    case "reminder-done": return mutate(`/api/v2/planning/reminders/${encodeURIComponent(id || value)}`, { method: "PATCH", body: { done: flag ? flag === "1" : true } }, "Påminnelse uppdaterad");
    case "reminder-delete": return mutate(`/api/v2/planning/reminders/${encodeURIComponent(value)}`, { method: "DELETE" }, "Påminnelse raderad");
    case "routine-instance": return mutate(`/api/v2/planning/routine-instances/${encodeURIComponent(id)}`, { method: "PUT", body: { done: flag === "1" } }, "Rutin uppdaterad");
    case "checklist-toggle": return mutate(`/api/v2/planning/checklist-items/${encodeURIComponent(id)}`, { method: "PUT", body: { done: flag === "1" } }, "Checklistan uppdaterad");
    case "family-item-toggle": return mutate(`/api/v2/family/list-items/${encodeURIComponent(id)}`, { method: "PATCH", body: { done: flag === "1" } }, "Listan uppdaterad");
    case "family-note-delete": return mutate(`/api/v2/family/notes/${encodeURIComponent(value)}`, { method: "DELETE" }, "Anteckning raderad");
    case "shopping-toggle": return mutate(`/api/v2/shopping/items/${encodeURIComponent(id)}/completion`, { method: "PATCH", body: { done: flag === "1" } }, "Inköpslistan uppdaterad");
    case "inventory-adjust": return mutate(`/api/v2/inventory/items/${encodeURIComponent(id)}/quantity`, { method: "PATCH", body: { delta: Number(flag) } }, "Antal uppdaterat");
    case "inventory-delete": return mutate(`/api/v2/inventory/items/${encodeURIComponent(value)}?confirm=true`, { method: "DELETE" }, "Vara raderad");
    case "inventory-place": {
      const location = prompt("Plats (fridge/freezer/pantry/chest_freezer/other):", "pantry");
      if (location === null) return;
      const shelf = prompt("Hylla:", "Standard");
      if (shelf === null) return;
      return mutate(`/api/v2/inventory/inbox/${encodeURIComponent(value)}/place`, { method: "POST", body: { location, shelf } }, "Vara placerad");
    }
    case "suggestion-shopping": return mutate(`/api/v2/inventory/suggestions/${encodeURIComponent(value)}/shopping`, { method: "POST", body: { list_id: "shopping" } }, "Tillagd på inköpslistan");
    case "suggestion-dismiss": return mutate(`/api/v2/inventory/suggestions/${encodeURIComponent(value)}`, { method: "DELETE" }, "Förslag avfärdat");
    case "wishlist-toggle": return mutate(`/api/v2/wishlists/items/${encodeURIComponent(id)}`, { method: "PATCH", body: { purchased: flag === "1" } }, "Önskelistan uppdaterad");
    case "household-delete": return mutate(`/api/v2/household/items/${encodeURIComponent(value)}`, { method: "DELETE" }, "Sak raderad");
    case "forget-toggle": return mutate(`/api/v2/experience/forget-items/${encodeURIComponent(id)}`, { method: "PATCH", body: { done: flag === "1" } }, "Glöm-inte uppdaterad");
    case "quest-toggle": return mutate(`/api/v2/experience/quests/${encodeURIComponent(id)}`, { method: "PUT", body: { done: flag === "1" } }, "Uppdrag uppdaterat");
    case "alert-ack": return mutate(`/api/v2/notifications/alerts/${encodeURIComponent(value)}/ack`, { method: "POST", body: {} }, "Avisering markerad som läst");
    case "recipe-delete": return mutate(`/api/v2/food/recipes/${encodeURIComponent(value)}`, { method: "DELETE" }, "Recept raderat");
    case "recipe-shopping": {
      const recipe = (state.data.recipes || []).find(item => item.id === value);
      const ingredients = recipe?.ingredients || [];
      return mutate("/api/v2/food/ingredients/shopping", { method: "POST", body: { ingredients, list_id: "shopping", source: recipe?.title || "Recept" } }, "Ingredienser tillagda på inköpslistan");
    }
  }
}

async function openView(name, force = false, updateHash = true) {
  const route = routes[name] || routes.home;
  state.active = routes[name] ? name : "home";
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-current", String(button.dataset.view === state.active)));
  main.innerHTML = skeleton(5);
  try {
    const data = await route.load(force);
    state.data = data;
    main.innerHTML = route.render(data);
  } catch (error) {
    main.innerHTML = errorState(error);
    main.querySelector("[data-retry]")?.addEventListener("click", () => openView(state.active, true, false));
  }
  if (updateHash) location.hash = state.active;
}

async function bootstrap() {
  try {
    state.access = await accessControl();
    userLabel.textContent = state.access.admin ? "Admin" : state.access.user;
    document.querySelector("#admin-link")?.toggleAttribute("hidden", !state.access.admin);
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
