import { api } from "/assets/api.js";

const VIEW_SECTIONS = {
  home: "app",
  more: "app",
  dashboard: "app",
  planning: "planning",
  family: "family",
  shopping: "shopping",
  inventory: "inventory",
  food: "food",
  wishlists: "wishlists",
  household: "household",
};

const QUICK_SECTIONS = {
  reminder: "planning",
  shopping: "shopping",
  note: "family",
  wishlist: "wishlists",
  recipe: "food",
  thing: "household",
};

let access = null;

function allowed(section) {
  return Boolean(access?.admin || access?.sections?.includes(section));
}

function applyPermissions() {
  if (!access) return;
  document.documentElement.dataset.profileReadonly = String(Boolean(access.readonly));
  document.querySelectorAll("[data-view]").forEach(element => {
    const section = VIEW_SECTIONS[element.dataset.view];
    element.hidden = Boolean(section && !allowed(section));
  });
  document.querySelectorAll("[data-open]").forEach(element => {
    const section = VIEW_SECTIONS[element.dataset.open];
    element.hidden = Boolean(section && !allowed(section));
  });
  document.querySelectorAll("[data-quick-create]").forEach(element => {
    const section = QUICK_SECTIONS[element.dataset.quickCreate];
    element.hidden = Boolean(section && !allowed(section));
  });
  if (access.readonly) {
    document.querySelector("#new-button")?.setAttribute("hidden", "");
    const runtime = document.querySelector("#runtime-mode");
    if (runtime) runtime.textContent = "Profil: endast läsning";
  }
}

async function loadPermissions() {
  try {
    access = await api("/api/access-control");
    applyPermissions();
  } catch {
    access = null;
  }
}

const observer = new MutationObserver(applyPermissions);
observer.observe(document.body, { childList: true, subtree: true });
loadPermissions();
