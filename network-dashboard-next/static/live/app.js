import { api, accessControl } from "/assets/api.js";
import { badge, card, dateTime, emptyState, errorState, escapeHtml, renderInto, skeleton } from "/assets/ui.js";

const state = { access: null, active: "home", loaded: new Set() };
const main = document.querySelector("#app-main");
const userLabel = document.querySelector("#user-label");

const routes = {
  home: { label: "Hem", endpoint: "/api/v2/home/summary", render: renderHome },
  planning: { label: "Planera", endpoint: "/api/v2/planning/overview", render: renderPlanning },
  family: { label: "Familj", endpoint: "/api/v2/family/overview", render: renderFamily },
  food: { label: "Mat", endpoint: "/api/v2/food/overview", render: renderFood },
  more: { label: "Mer", endpoint: "/api/v2/notifications/overview", render: renderMore },
};

function rows(items, mapper, emptyTitle = "Inget att visa") {
  if (!items?.length) return emptyState(emptyTitle);
  return `<div class="list">${items.map(mapper).join("")}</div>`;
}

function row(title, detail = "", trailing = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${trailing}</div>`;
}

function renderHome(data) {
  const totals = data.totals || {};
  const reminders = data.planning?.reminders || [];
  const profiles = data.family?.profiles || [];
  return `<section class="hero"><p>Familjens översikt</p><h2>Hej ${escapeHtml(state.access.user || "familjen")}</h2><p>Det viktigaste samlat utan att ladda tekniska integrationer.</p><div class="stats"><div class="stat"><strong>${totals.open_reminders || 0}</strong><span>Påminnelser</span></div><div class="stat"><strong>${totals.open_routines || 0}</strong><span>Rutiner</span></div><div class="stat"><strong>${data.family?.open_list_items || 0}</strong><span>Listpunkter</span></div></div></section><div class="grid">${card("Kommande", rows(reminders.slice(0, 6), item => row(item.title || item.text || "Påminnelse", dateTime(item.remind_at || item.starts_at), item.done ? badge("Klar", "good") : badge("Öppen")), "Inga kommande påminnelser"))}${card("Familjen", rows(profiles, item => row(item.label || item.name || item.id, item.role || "Familjemedlem"), "Inga profiler hittades"))}</div>`;
}

function renderPlanning(data) {
  const tasks = data.tasks?.open || data.checklist_items || [];
  const routines = data.routines || data.routine_instances || [];
  const reminders = data.reminders || [];
  return `<div class="grid">${card("Uppgifter", rows(tasks, item => row(item.title || item.text, item.owner || item.due_date || ""), "Inga öppna uppgifter"))}${card("Rutiner", rows(routines, item => row(item.title, item.owner || item.assigned_to || "", item.done ? badge("Klar", "good") : badge("Aktiv")), "Inga aktiva rutiner"))}${card("Påminnelser", rows(reminders, item => row(item.title || item.text, dateTime(item.remind_at || item.starts_at)), "Inga påminnelser"))}</div>`;
}

function renderFamily(data) {
  const profiles = data.profiles || data.members || [];
  const lists = data.lists || [];
  return `<div class="grid">${card("Familjemedlemmar", rows(profiles, item => row(item.label || item.name || item.id, item.role || ""), "Inga profiler"))}${card("Listor", rows(lists, item => row(item.title || item.id, `${item.open_count ?? item.count ?? 0} öppna`), "Inga listor"))}</div>`;
}

function renderFood(data) {
  const days = data.days || [];
  const shopping = data.shopping?.active || [];
  const inventory = data.inventory?.items || [];
  return `<div class="grid">${card("Matsedel", rows(days, item => row(item.label || item.date, item.meal?.title || "Ingen rätt planerad"), "Ingen matsedel"))}${card("Inköp", rows(shopping.slice(0, 12), item => row(item.text || item.name, [item.quantity, item.unit].filter(Boolean).join(" ")), "Inköpslistan är tom"))}${card("Förråd", rows(inventory.slice(0, 12), item => row(item.name, `${item.quantity || 0} ${item.unit || ""}`.trim(), Number(item.quantity || 0) === 0 ? badge("Slut", "warning") : ""), "Förrådet är tomt"))}</div>`;
}

function renderMore(data) {
  const items = data.items || [];
  const admin = state.access.admin ? card("Administration", `<p>Tekniska funktioner och Version 2 är tillgängliga.</p><p><a href="/preview-v2">Öppna Version 2</a></p>`) : "";
  return `<div class="grid">${card("Aviseringar", rows(items, item => row(item.message, dateTime(item.created_at), item.read ? badge("Läst", "good") : badge("Ny", "warning")), "Inga aviseringar"))}${admin}${card("Session", `<p>Inloggad som <strong>${escapeHtml(state.access.user)}</strong>.</p><p><a href="/choose-user">Byt profil</a> · <a href="/logout">Logga ut</a></p>`)}</div>`;
}

async function openView(name, force = false) {
  const route = routes[name] || routes.home;
  state.active = name;
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-current", String(button.dataset.view === name)));
  main.innerHTML = skeleton(5);
  try {
    const data = await api(`${route.endpoint}${force ? `?refresh=${Date.now()}` : ""}`);
    main.innerHTML = route.render(data);
    state.loaded.add(name);
  } catch (error) {
    main.innerHTML = errorState(error);
    main.querySelector("[data-retry]")?.addEventListener("click", () => openView(name, true));
  }
  location.hash = name;
}

async function bootstrap() {
  try {
    state.access = await accessControl();
    userLabel.textContent = state.access.admin ? "Admin" : state.access.user;
    document.querySelector("#admin-link")?.toggleAttribute("hidden", !state.access.admin);
    document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => openView(button.dataset.view)));
    await openView((location.hash || "#home").slice(1));
  } catch (error) {
    renderInto(main, errorState(error));
  }
}

bootstrap();
